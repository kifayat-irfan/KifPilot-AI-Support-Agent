from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status, Query
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from uuid import UUID
from io import BytesIO

from app.services.documents import document_service, DocumentStatus
from app.services.documents.exceptions import (
    DocumentNotFoundError,
    FileValidationError,
    FileSizeError,
    UnsupportedFileTypeError,
    DuplicateFileError,
    ParsingError,
    ChunkingError,
    EmbeddingGenerationError,
    VectorStoreError,
    DatabaseError,
)
from app.database.models import Document
from app.core.logging import get_logger
from app.presentation.api.v1.dependencies import (
    get_current_active_user,
    require_upload_documents,
    require_delete_documents,
    get_current_organization_id,
)

router = APIRouter(prefix="/documents", tags=["Documents"])
logger = get_logger(__name__)


def validate_uuid(value: str) -> str:
    try:
        UUID(value)
        return value
    except ValueError:
        raise ValueError("Invalid UUID format")


class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    language: Optional[str] = None
    file_type: str
    mime_type: str
    file_size: int
    status: str
    company: str
    page_count: int
    chunk_count: int
    embeddings_created: int
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: str
    updated_at: str
    deleted_at: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    pages: int
    chunks_created: int
    embeddings_created: int
    processing_time_ms: int


class DuplicateDocumentResponse(BaseModel):
    duplicate: bool
    existing_document_id: str
    filename: str
    message: str


class UpdateDocumentRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = Field(None, max_items=50)
    language: Optional[str] = Field(None, max_length=10, pattern="^[a-z]{2}(-[A-Z]{2})?$")

    @validator("tags")
    def validate_tags(cls, v):
        if v is not None:
            for tag in v:
                if not tag or len(tag.strip()) == 0:
                    raise ValueError("Tags cannot be empty")
                if len(tag) > 50:
                    raise ValueError("Tag length cannot exceed 50 characters")
        return v


class DeleteResponse(BaseModel):
    success: bool
    document_id: str
    message: str


class RestoreResponse(BaseModel):
    success: bool
    document_id: str
    message: str


@router.post(
    "/upload",
    responses={
        201: {"model": UploadResponse, "description": "Document uploaded and processed"},
        200: {"model": DuplicateDocumentResponse, "description": "Duplicate document detected"},
        400: {"description": "File validation error"},
        413: {"description": "File too large"},
        415: {"description": "Unsupported file type"},
        409: {"description": "Duplicate file"},
        500: {"description": "Processing error"},
    },
    dependencies=[Depends(require_upload_documents)],
)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    force_reindex: bool = Form(default=False, description="Force reindex even if duplicate exists"),
    current_user = Depends(get_current_active_user),
    organization_id: str = Depends(get_current_organization_id),
):
    """Upload and process a document with optional metadata. 
    If a document with the same content already exists, returns duplicate info unless force_reindex is true.
    """
    try:
        logger.info("Document upload started", filename=file.filename, organization_id=organization_id, force_reindex=force_reindex)

        # Parse tags from comma-separated string
        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        # Read file content
        content = await file.read()
        file_size = len(content)

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Empty file", "code": "EMPTY_FILE"},
            )

        # Process document - wrap bytes in BytesIO for file-like interface
        document, is_duplicate = await document_service.upload_document(
            file=BytesIO(content),
            filename=file.filename or "unknown",
            file_size=file_size,
            organization_id=organization_id,
            title=title,
            description=description,
            category=category,
            tags=tag_list,
            language=language,
            force_reindex=force_reindex,
        )

        if is_duplicate:
            logger.info("Returning duplicate document response", document_id=document.id)
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=DuplicateDocumentResponse(
                    duplicate=True,
                    existing_document_id=document.id,
                    filename=document.filename,
                    message="Document already exists.",
                ).model_dump(),
            )

        return UploadResponse(
            document_id=document.id,
            filename=document.filename,
            pages=document.page_count,
            chunks_created=document.chunk_count,
            embeddings_created=document.embeddings_created,
            processing_time_ms=document.processing_time_ms or 0,
        )

    except FileSizeError as e:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except UnsupportedFileTypeError as e:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except DuplicateFileError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except (ParsingError, ChunkingError, EmbeddingGenerationError, VectorStoreError, DatabaseError) as e:
        logger.error("Document processing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except Exception as e:
        logger.error("Unexpected error during upload", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "code": "INTERNAL_ERROR"},
        )


@router.get(
    "",
    response_model=DocumentListResponse,
    responses={
        200: {"model": DocumentListResponse},
        400: {"description": "Invalid query parameters"},
    },
    dependencies=[Depends(get_current_active_user)],
)
async def list_documents(
    category: Optional[str] = Query(None, description="Filter by category"),
    language: Optional[str] = Query(None, description="Filter by language (ISO 639-1)"),
    status: Optional[DocumentStatus] = Query(None, description="Filter by processing status"),
    search: Optional[str] = Query(None, description="Search in title, filename, description"),
    sort_by: str = Query("created_at", pattern="^(created_at|updated_at|filename|title|file_size|status|category)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user = Depends(get_current_active_user),
    organization_id: str = Depends(get_current_organization_id),
):
    """List documents with advanced filtering, search, sorting, and pagination."""
    try:
        logger.info(
            "Document list requested",
            organization_id=organization_id,
            category=category,
            language=language,
            status=status.value if status else None,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )

        offset = (page - 1) * page_size
        documents, total = await document_service.list_documents(
            organization_id=organization_id,
            status=status,
            category=category,
            language=language,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=offset,
            limit=page_size,
        )

        total_pages = (total + page_size - 1) // page_size

        return DocumentListResponse(
            documents=[
                DocumentResponse(
                    id=d.id,
                    filename=d.filename,
                    original_filename=d.original_filename,
                    title=d.title,
                    description=d.description,
                    category=d.category,
                    tags=d.tags,
                    language=d.language,
                    file_type=d.file_type,
                    mime_type=d.mime_type,
                    file_size=d.file_size,
                    status=d.status.value,
                    company=d.company,
                    page_count=d.page_count,
                    chunk_count=d.chunk_count,
                    embeddings_created=d.embeddings_created,
                    error_message=d.error_message,
                    processing_time_ms=d.processing_time_ms,
                    created_at=d.created_at.isoformat(),
                    updated_at=d.updated_at.isoformat(),
                    deleted_at=d.deleted_at.isoformat() if d.deleted_at else None,
                )
                for d in documents
            ],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e), "code": "INVALID_PARAMETER"},
        )
    except Exception as e:
        logger.error("Document list failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "code": "INTERNAL_ERROR"},
        )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    responses={
        200: {"model": DocumentResponse},
        404: {"description": "Document not found"},
    },
    dependencies=[Depends(get_current_active_user)],
)
async def get_document(document_id: str, current_user = Depends(get_current_active_user)):
    """Get document by ID."""
    try:
        validate_uuid(document_id)
        document = await document_service.get_document(document_id)
        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            original_filename=document.original_filename,
            title=document.title,
            description=document.description,
            category=document.category,
            tags=document.tags,
            language=document.language,
            file_type=document.file_type,
            mime_type=document.mime_type,
            file_size=document.file_size,
            status=document.status.value,
            company=document.company,
            page_count=document.page_count,
            chunk_count=document.chunk_count,
            embeddings_created=document.embeddings_created,
            error_message=document.error_message,
            processing_time_ms=document.processing_time_ms,
            created_at=document.created_at.isoformat(),
            updated_at=document.updated_at.isoformat(),
            deleted_at=document.deleted_at.isoformat() if document.deleted_at else None,
        )
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e), "code": "INVALID_UUID"},
        )


@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
    responses={
        200: {"model": DocumentResponse},
        400: {"description": "Invalid request data"},
        404: {"description": "Document not found or deleted"},
    },
    dependencies=[Depends(get_current_active_user)],
)
async def update_document(document_id: str, request: UpdateDocumentRequest, current_user = Depends(get_current_active_user)):
    """Update document metadata."""
    try:
        validate_uuid(document_id)
        
        logger.info("Document update requested", document_id=document_id, fields=request.dict(exclude_unset=True))
        
        document = await document_service.update_document(
            document_id=document_id,
            title=request.title,
            description=request.description,
            category=request.category,
            tags=request.tags,
            language=request.language,
        )

        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            original_filename=document.original_filename,
            title=document.title,
            description=document.description,
            category=document.category,
            tags=document.tags,
            language=document.language,
            file_type=document.file_type,
            mime_type=document.mime_type,
            file_size=document.file_size,
            status=document.status.value,
            company=document.company,
            page_count=document.page_count,
            chunk_count=document.chunk_count,
            embeddings_created=document.embeddings_created,
            error_message=document.error_message,
            processing_time_ms=document.processing_time_ms,
            created_at=document.created_at.isoformat(),
            updated_at=document.updated_at.isoformat(),
            deleted_at=document.deleted_at.isoformat() if document.deleted_at else None,
        )
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e), "code": "INVALID_UUID"},
        )


@router.delete(
    "/{document_id}",
    response_model=DeleteResponse,
    responses={
        200: {"model": DeleteResponse},
        404: {"description": "Document not found"},
    },
    dependencies=[Depends(require_delete_documents)],
)
async def delete_document(document_id: str, hard: bool = Query(False, description="Permanently delete document and vectors"), current_user = Depends(get_current_active_user)):
    """Soft delete a document (default) or hard delete with vectors."""
    try:
        validate_uuid(document_id)
        
        if hard:
            logger.info("Hard delete requested", document_id=document_id)
            await document_service.hard_delete_document(document_id)
            message = "Document permanently deleted"
        else:
            logger.info("Soft delete requested", document_id=document_id)
            await document_service.soft_delete_document(document_id)
            message = "Document moved to trash"
        
        return DeleteResponse(
            success=True,
            document_id=document_id,
            message=message,
        )
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e), "code": "INVALID_UUID"},
        )


@router.post(
    "/{document_id}/restore",
    response_model=RestoreResponse,
    responses={
        200: {"model": RestoreResponse},
        404: {"description": "Document not found or not deleted"},
    },
    dependencies=[Depends(get_current_active_user)],
)
async def restore_document(document_id: str, current_user = Depends(get_current_active_user)):
    """Restore a soft-deleted document."""
    try:
        validate_uuid(document_id)
        
        logger.info("Document restore requested", document_id=document_id)
        
        document = await document_service.restore_document(document_id)
        
        return RestoreResponse(
            success=True,
            document_id=document_id,
            message="Document restored successfully",
        )
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e), "code": "INVALID_UUID"},
        )


@router.get(
    "/{document_id}/chunks",
    response_model=List[dict],
    responses={
        200: {"description": "List of document chunks"},
        404: {"description": "Document not found"},
    },
    dependencies=[Depends(get_current_active_user)],
)
async def get_document_chunks(document_id: str, current_user = Depends(get_current_active_user)):
    """Get all chunks for a document."""
    try:
        validate_uuid(document_id)
        chunks = await document_service.get_document_chunks(document_id)
        return [
            {
                "chunk_id": c.chunk_id,
                "chunk_index": c.chunk_index,
                "text": c.text[:200] + "..." if len(c.text) > 200 else c.text,
                "page": c.page,
                "section": c.section,
                "heading": c.heading,
                "token_count": c.token_count,
            }
            for c in chunks
        ]
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e), "code": "INVALID_UUID"},
        )