import os
import time
import hashlib
import asyncio
import logging
from typing import Optional, List
from uuid import uuid4
from datetime import datetime
from io import BytesIO

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.logging import get_logger
from app.database.models import Document, DocumentChunk, DocumentStatus
from app.database.session import database_manager
from app.services.documents.parser import get_parser
from app.services.documents.chunker import get_chunker
from app.services.documents.loader import get_document_loader
from app.services.documents.validators import get_file_validator
from app.services.documents.metadata import DocumentMetadata
from app.services.documents.exceptions import (
    DocumentNotFoundError,
    ParsingError,
    ChunkingError,
    EmbeddingGenerationError,
    VectorStoreError,
    DatabaseError,
    FileValidationError,
    FileSizeError,
    UnsupportedFileTypeError,
    DuplicateFileError,
)
from app.services.vectorstore import vector_store_service
from app.services.vectorstore.models import InsertEmbeddingsRequest, ChunkMetadata
from app.services.llm import ollama_service

settings = get_settings()
logger = get_logger(__name__)


class DocumentService:
    def __init__(
        self,
        loader=None,
        parser=None,
        chunker=None,
        validator=None,
    ):
        self.loader = loader or get_document_loader()
        self.parser = parser or get_parser
        self.chunker = chunker or get_chunker()
        self.validator = validator or get_file_validator()

    @staticmethod
    def compute_content_hash(file: BytesIO) -> str:
        """Compute SHA-256 hash of file content."""
        file.seek(0)
        content = file.read()
        file.seek(0)
        return hashlib.sha256(content).hexdigest()

    async def check_duplicate_hash(self, content_hash: str, organization_id: str) -> Optional[Document]:
        """Check if a document with the same content hash exists for the organization."""
        async with database_manager.session_factory() as session:
            result = await session.execute(
                select(Document)
                .options(selectinload(Document.chunks))
                .where(Document.content_hash == content_hash)
                .where(Document.organization_id == organization_id)
                .where(Document.deleted_at.is_(None))
            )
            return result.scalar_one_or_none()

    async def upload_document(
        self,
        file,
        filename: str,
        file_size: int,
        organization_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        language: Optional[str] = None,
        force_reindex: bool = False,
    ) -> tuple[Document, bool]:
        """
        Upload and process a document.
        Returns tuple of (Document, is_duplicate).
        """
        start_time = time.time()
        
        # Read file content once
        if isinstance(file, BytesIO):
            file.seek(0)
            content = file.read()
            file.seek(0)
        elif hasattr(file, 'read'):
            content = await file.read() if asyncio.iscoroutinefunction(file.read) else file.read()
        else:
            content = file
        
        if not isinstance(content, bytes):
            content = bytes(content)
        
        file_size = len(content)
        content_hash = hashlib.sha256(content).hexdigest()
        logger.info("Content hash generated", content_hash=content_hash[:16], filename=filename, file_size=file_size)
        
        # Check for duplicate
        existing_doc = await self.check_duplicate_hash(content_hash, organization_id)
        if existing_doc and not force_reindex:
            logger.info("Duplicate document detected", 
                       document_id=existing_doc.id, 
                       content_hash=content_hash[:16],
                       filename=filename)
            return existing_doc, True  # Duplicate found
        
        document_id = str(uuid4())
        file_path = None

        try:
            # If force_reindex and duplicate exists, hard delete the old document first
            if existing_doc and force_reindex:
                logger.info("Force reindex requested, deleting existing document", 
                           existing_document_id=existing_doc.id)
                await self.hard_delete_document(existing_doc.id)

            # Create document record in DB with content_hash
            async with database_manager.session_factory() as session:
                document = Document(
                    id=document_id,
                    filename=filename,
                    original_filename=filename,
                    title=title,
                    description=description,
                    category=category,
                    tags=tags,
                    language=language,
                    file_type=self._get_file_type(filename),
                    mime_type=self._get_mime_type(filename),
                    file_size=file_size,
                    content_hash=content_hash,
                    status=DocumentStatus.UPLOADING,
                    organization_id=organization_id,
                )
                session.add(document)
                await session.commit()
                await session.refresh(document)

            logger.info("Document record created", document_id=document_id, filename=filename, content_hash=content_hash[:16])

            # Update status to parsing
            await self._update_status(document_id, DocumentStatus.PARSING)

            # Save file - pass content as BytesIO
            file_path = await self.loader.save_upload(BytesIO(content), filename, file_size)
            logger.info("File saved", document_id=document_id, path=file_path)

            # Parse document
            await self._update_status(document_id, DocumentStatus.PARSING)
            parser = self.parser(self._get_file_type(filename))
            parsed_doc = parser.parse(file_path)
            logger.info("Document parsed", document_id=document_id, pages=parsed_doc.total_pages)

            # Update status to chunking
            await self._update_status(document_id, DocumentStatus.CHUNKING)

            # Chunk document
            chunks = self.chunker.chunk_document(
                parsed_doc=parsed_doc,
                document_id=document_id,
                document_name=filename,
                organization_id=organization_id,
                file_type=self._get_file_type(filename),
            )
            logger.info("Document chunked", document_id=document_id, chunks=len(chunks))

            # Update status to embedding
            await self._update_status(document_id, DocumentStatus.EMBEDDING)

            # Generate embeddings
            embeddings = []
            for chunk in chunks:
                embedding = await ollama_service.generate_single_embedding(chunk.text)
                embeddings.append(embedding)
            
            logger.info("Embeddings generated", document_id=document_id, count=len(embeddings))

            # Update status to storing
            await self._update_status(document_id, DocumentStatus.STORING)

            # Store in vector database
            await self._store_in_vector_db(document_id, filename, organization_id, chunks, embeddings)
            logger.info("Vectors stored", document_id=document_id)

            # Store chunks in SQLite
            await self._store_chunks_in_db(document_id, chunks)
            logger.info("Chunks stored in DB", document_id=document_id)

            # Clean up file
            self.loader.delete_file(file_path)

            # Update final status
            processing_time = int((time.time() - start_time) * 1000)
            await self._complete_document(document_id, len(parsed_doc.pages), len(chunks), len(embeddings), processing_time)

            logger.info("Document processing completed", document_id=document_id, time_ms=processing_time, content_hash=content_hash[:16])

            return await self.get_document(document_id), False  # New document processed

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            logger.error("Document processing failed", document_id=document_id, error=error_msg)
            
            # Clean up file if exists
            if file_path and os.path.exists(file_path):
                self.loader.delete_file(file_path)
            
            # Update status to failed
            await self._fail_document(document_id, error_msg, processing_time)
            raise

    async def get_document(self, document_id: str, include_deleted: bool = False) -> Document:
        async with database_manager.session_factory() as session:
            query = select(Document).options(selectinload(Document.chunks)).where(Document.id == document_id)
            if not include_deleted:
                query = query.where(Document.deleted_at.is_(None))
            result = await session.execute(query)
            document = result.scalar_one_or_none()
            if not document:
                raise DocumentNotFoundError(document_id)
            return document

    async def list_documents(
        self,
        organization_id: str,
        status: Optional[DocumentStatus] = None,
        category: Optional[str] = None,
        language: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        offset: int = 0,
        limit: int = 50,
        include_deleted: bool = False,
    ) -> tuple[List[Document], int]:
        async with database_manager.session_factory() as session:
            query = select(Document).options(selectinload(Document.chunks))
            count_query = select(func.count(Document.id))
            
            if not include_deleted:
                query = query.where(Document.deleted_at.is_(None))
                count_query = count_query.where(Document.deleted_at.is_(None))
            
            # Always filter by organization_id
            query = query.where(Document.organization_id == organization_id)
            count_query = count_query.where(Document.organization_id == organization_id)
            
            if status:
                query = query.where(Document.status == status)
                count_query = count_query.where(Document.status == status)
            if category:
                query = query.where(Document.category == category)
                count_query = count_query.where(Document.category == category)
            if language:
                query = query.where(Document.language == language)
                count_query = count_query.where(Document.language == language)
            
            if search:
                search_term = f"%{search}%"
                search_filter = or_(
                    Document.title.ilike(search_term),
                    Document.filename.ilike(search_term),
                    Document.description.ilike(search_term),
                )
                query = query.where(search_filter)
                count_query = count_query.where(search_filter)
            
            # Validate sort_by
            valid_sort_fields = {
                "created_at": Document.created_at,
                "updated_at": Document.updated_at,
                "filename": Document.filename,
                "title": Document.title,
                "file_size": Document.file_size,
                "status": Document.status,
                "category": Document.category,
            }
            sort_column = valid_sort_fields.get(sort_by, Document.created_at)
            
            if sort_order.lower() == "asc":
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())
            
            query = query.offset(offset).limit(limit)
            
            result = await session.execute(query)
            documents = result.scalars().all()
            
            count_result = await session.execute(count_query)
            total = count_result.scalar() or 0
            
            return documents, total

    async def update_document(
        self,
        document_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        language: Optional[str] = None,
    ) -> Document:
        async with database_manager.session_factory() as session:
            document = await session.get(Document, document_id)
            if not document:
                raise DocumentNotFoundError(document_id)
            
            if document.deleted_at is not None:
                raise DocumentNotFoundError(f"Document {document_id} is deleted")
            
            updated = False
            if title is not None:
                document.title = title
                updated = True
            if description is not None:
                document.description = description
                updated = True
            if category is not None:
                document.category = category
                updated = True
            if tags is not None:
                document.tags = tags
                updated = True
            if language is not None:
                document.language = language
                updated = True
            
            if updated:
                document.updated_at = datetime.utcnow()
                await session.commit()
                await session.refresh(document)
                logger.info("Document metadata updated", document_id=document_id)
            
            return document

    async def soft_delete_document(self, document_id: str) -> Document:
        async with database_manager.session_factory() as session:
            document = await session.get(Document, document_id)
            if not document:
                raise DocumentNotFoundError(document_id)
            
            if document.deleted_at is not None:
                raise DocumentNotFoundError(f"Document {document_id} is already deleted")
            
            document.deleted_at = datetime.utcnow()
            document.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(document)
            logger.info("Document soft deleted", document_id=document_id)
            return document

    async def restore_document(self, document_id: str) -> Document:
        async with database_manager.session_factory() as session:
            # Include deleted documents in query
            result = await session.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()
            if not document:
                raise DocumentNotFoundError(document_id)
            
            if document.deleted_at is None:
                raise DocumentNotFoundError(f"Document {document_id} is not deleted")
            
            document.deleted_at = None
            document.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(document)
            logger.info("Document restored", document_id=document_id)
            return document

    async def hard_delete_document(self, document_id: str) -> bool:
        async with database_manager.session_factory() as session:
            document = await session.get(Document, document_id)
            if not document:
                raise DocumentNotFoundError(document_id)
            
            # Delete from vector store
            chunk_ids = [chunk.chunk_id for chunk in document.chunks]
            if chunk_ids:
                try:
                    from app.services.vectorstore.models import DeleteRequest
                    await vector_store_service.delete_documents(
                        DeleteRequest(organization_id=document.organization_id, ids=chunk_ids)
                    )
                except Exception as e:
                    logger.warning("Failed to delete from vector store", document_id=document_id, error=str(e))
            
            # Delete uploaded file if exists
            # Note: We don't have the file path stored, but we could try to find it
            
            # Delete from DB (cascades to chunks)
            await session.delete(document)
            await session.commit()
            logger.info("Document hard deleted", document_id=document_id)
            return True

    async def get_document_chunks(self, document_id: str) -> List[DocumentChunk]:
        async with database_manager.session_factory() as session:
            document = await session.get(Document, document_id, options=[selectinload(Document.chunks)])
            if not document:
                raise DocumentNotFoundError(document_id)
            return document.chunks

    def _get_file_type(self, filename: str) -> str:
        _, ext = os.path.splitext(filename.lower())
        return ext

    def _get_mime_type(self, filename: str) -> str:
        mime_types = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
            ".md": "text/markdown",
        }
        ext = self._get_file_type(filename)
        return mime_types.get(ext, "application/octet-stream")

    async def _update_status(self, document_id: str, status: DocumentStatus) -> None:
        async with database_manager.session_factory() as session:
            document = await session.get(Document, document_id)
            if document:
                document.status = status
                await session.commit()

    async def _fail_document(self, document_id: str, error: str, processing_time: int) -> None:
        async with database_manager.session_factory() as session:
            document = await session.get(Document, document_id)
            if document:
                document.status = DocumentStatus.FAILED
                document.error_message = error
                document.processing_time_ms = processing_time
                await session.commit()

    async def _complete_document(
        self,
        document_id: str,
        page_count: int,
        chunk_count: int,
        embeddings_created: int,
        processing_time: int,
    ) -> None:
        async with database_manager.session_factory() as session:
            document = await session.get(Document, document_id)
            if document:
                document.status = DocumentStatus.COMPLETED
                document.page_count = page_count
                document.chunk_count = chunk_count
                document.embeddings_created = embeddings_created
                document.processing_time_ms = processing_time
                await session.commit()

    async def _store_in_vector_db(
        self,
        document_id: str,
        filename: str,
        organization_id: str,
        chunks: List,
        embeddings: List[List[float]],
    ) -> None:
        metadatas = []
        for chunk in chunks:
            metadata = ChunkMetadata(
                document_id=document_id,
                document_name=filename,
                company=organization_id,  # Use organization_id as company field for backward compatibility
                file_type=self._get_file_type(filename),
                page=chunk.page,
                section=chunk.section,
                chunk_id=chunk.chunk_id,
                chunk_index=chunk.chunk_index,
                created_at=chunk.metadata.get("created_at", datetime.utcnow()),
                organization_id=organization_id,
            )
            metadatas.append(metadata)

        request = InsertEmbeddingsRequest(
            organization_id=organization_id,
            documents=[chunk.text for chunk in chunks],
            embeddings=embeddings,
            metadatas=metadatas,
            ids=[chunk.chunk_id for chunk in chunks],
        )

        await vector_store_service.insert_embeddings(request)

    async def _store_chunks_in_db(self, document_id: str, chunks: List) -> None:
        async with database_manager.session_factory() as session:
            for chunk in chunks:
                db_chunk = DocumentChunk(
                    id=chunk.chunk_id,
                    document_id=document_id,
                    chunk_index=chunk.chunk_index,
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    page=chunk.page,
                    section=chunk.section,
                    heading=chunk.heading,
                    token_count=chunk.token_count,
                    vector_id=chunk.chunk_id,
                )
                session.add(db_chunk)
            await session.commit()


document_service = DocumentService()