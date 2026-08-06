import re
from typing import List, Optional
from uuid import uuid4

from app.services.documents.metadata import DocumentChunk, ParsedDocument, ParsedPage
from app.core.config import get_settings

settings = get_settings()


class TextChunker:
    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def chunk_document(
        self,
        parsed_doc: ParsedDocument,
        document_id: str,
        document_name: str,
        company: str,
        file_type: str,
    ) -> List[DocumentChunk]:
        chunks = []
        chunk_index = 0

        for page in parsed_doc.pages:
            page_chunks = self._chunk_page(
                page=page,
                document_id=document_id,
                document_name=document_name,
                company=company,
                file_type=file_type,
                chunk_index=chunk_index,
            )
            chunks.extend(page_chunks)
            chunk_index += len(page_chunks)

        return chunks

    def _chunk_page(
        self,
        page: ParsedPage,
        document_id: str,
        document_name: str,
        company: str,
        file_type: str,
        chunk_index: int,
    ) -> List[DocumentChunk]:
        text = page.text.strip()
        if not text:
            return []

        # Split into paragraphs
        paragraphs = self._split_paragraphs(text)
        chunks = []
        current_chunk = ""
        current_token_count = 0

        for para in paragraphs:
            para_tokens = self._estimate_tokens(para)
            
            # If paragraph alone exceeds chunk size, split it
            if para_tokens > self.chunk_size:
                # Flush current chunk if any
                if current_chunk:
                    chunk = self._create_chunk(
                        text=current_chunk.strip(),
                        page=page.page_number,
                        chunk_index=chunk_index,
                        document_id=document_id,
                        document_name=document_name,
                        company=company,
                        file_type=file_type,
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    current_chunk = ""
                    current_token_count = 0
                
                # Split large paragraph
                sub_chunks = self._split_large_paragraph(
                    para,
                    document_id=document_id,
                    document_name=document_name,
                    company=company,
                    file_type=file_type,
                    page=page.page_number,
                    chunk_index=chunk_index,
                )
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
            elif current_token_count + para_tokens <= self.chunk_size:
                current_chunk += para + "\n\n"
                current_token_count += para_tokens
            else:
                # Flush current chunk
                if current_chunk:
                    chunk = self._create_chunk(
                        text=current_chunk.strip(),
                        page=page.page_number,
                        chunk_index=chunk_index,
                        document_id=document_id,
                        document_name=document_name,
                        company=company,
                        file_type=file_type,
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap(current_chunk)
                current_chunk = overlap_text + para + "\n\n"
                current_token_count = self._estimate_tokens(current_chunk)

        # Flush remaining
        if current_chunk.strip():
            chunk = self._create_chunk(
                text=current_chunk.strip(),
                page=page.page_number,
                chunk_index=chunk_index,
                document_id=document_id,
                document_name=document_name,
                company=company,
                file_type=file_type,
            )
            chunks.append(chunk)

        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        # Split by double newlines, preserving them
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _estimate_tokens(self, text: str) -> int:
        # Rough estimation: ~4 chars per token
        return len(text) // 4

    def _split_large_paragraph(
        self,
        paragraph: str,
        document_id: str,
        document_name: str,
        company: str,
        file_type: str,
        page: int,
        chunk_index: int,
    ) -> List[DocumentChunk]:
        chunks = []
        words = paragraph.split()
        current_chunk = ""
        current_tokens = 0

        for word in words:
            word_tokens = self._estimate_tokens(word)
            if current_tokens + word_tokens <= self.chunk_size:
                current_chunk += word + " "
                current_tokens += word_tokens
            else:
                if current_chunk:
                    chunks.append(self._create_chunk(
                        text=current_chunk.strip(),
                        page=page,
                        chunk_index=chunk_index,
                        document_id=document_id,
                        document_name=document_name,
                        company=company,
                        file_type=file_type,
                    ))
                    chunk_index += 1
                current_chunk = word + " "
                current_tokens = word_tokens

        if current_chunk.strip():
            chunks.append(self._create_chunk(
                text=current_chunk.strip(),
                page=page,
                chunk_index=chunk_index,
                document_id=document_id,
                document_name=document_name,
                company=company,
                file_type=file_type,
            ))

        return chunks

    def _get_overlap(self, text: str) -> str:
        tokens = self._estimate_tokens(text)
        if tokens <= self.chunk_overlap:
            return text
        # Get last N tokens worth of text
        overlap_chars = self.chunk_overlap * 4
        return text[-overlap_chars:]

    def _create_chunk(
        self,
        text: str,
        page: int,
        chunk_index: int,
        document_id: str,
        document_name: str,
        company: str,
        file_type: str,
    ) -> DocumentChunk:
        chunk_id = str(uuid4())
        token_count = self._estimate_tokens(text)
        
        return DocumentChunk(
            chunk_id=chunk_id,
            chunk_index=chunk_index,
            text=text,
            page=page,
            token_count=token_count,
            metadata={
                "document_id": document_id,
                "document_name": document_name,
                "company": company,
                "file_type": file_type,
                "page": page,
                "chunk_id": chunk_id,
                "chunk_index": chunk_index,
            },
        )


def get_chunker(chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None) -> TextChunker:
    return TextChunker(chunk_size, chunk_overlap)