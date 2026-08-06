# Document Processing Pipeline

## Overview

End-to-end document ingestion: upload → validate → extract → chunk → embed → store → index.

## Pipeline Stages

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   UPLOAD    │──▶│  VALIDATE   │──▶│  EXTRACT    │──▶│   CHUNK     │──▶│   EMBED     │──▶│   STORE     │──▶│   INDEX     │
│             │   │             │   │             │   │             │   │             │   │             │   │             │
│ • Receive   │   │ • MIME type │   │ • PDF       │   │ • Recursive │   │ • Batch     │   │ • ChromaDB  │   │ • BM25      │
│ • Size check│   │ • Extension │   │ • DOCX      │   │   splitter  │   │ • Ollama    │   │   vectors   │   │   update    │
│ • Filename  │   │ • Magic     │   │ • TXT/MD    │   │ • 1000/200  │   │   nomic-    │   │ • Metadata  │   │ • Persist   │
│   sanitize  │   │   bytes     │   │ • CSV/JSON  │   │   tokens    │   │   embed-text│   │ • Chunks    │   │   doc meta  │
└─────────────┘   │ • Executable│   │   etc.      │   │ • Overlap   │   │ • Retry     │   │ • Doc meta  │   └─────────────┘
                  │   scan      │   └─────────────┘   └─────────────┘   │   backoff   │   └─────────────┘
                  │ • Zip bomb  │                                         └─────────────┘
                  │   detect    │
                  └─────────────┘
```

## Upload Endpoint

```python
# presentation/api/v1/routes/documents.py
@router.post(
    "/upload",
    responses={
        201: {"model": UploadResponse},
        200: {"model": DuplicateDocumentResponse},
        400: {"description": "Validation error"},
        413: {"description": "File too large"},
        415: {"description": "Unsupported type"},
        409: {"description": "Duplicate"},
    },
    dependencies=[Depends(require_upload_documents)]
)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    force_reindex: bool = Form(False),
    current_user: User = Depends(get_current_active_user),
    organization_id: str = Depends(get_current_organization_id),
):
    # 1. Read file content
    content = await file.read()
    file_size = len(content)
    
    # 2. Validate (handled by middleware + service)
    if file_size == 0:
        raise HTTPException(400, "Empty file not allowed")
    
    # 3. Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    
    # 4. Process document
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
        force_reindex=force_reindex
    )
    
    if is_duplicate:
        return JSONResponse(200, DuplicateDocumentResponse(...).model_dump())
    
    return UploadResponse(...)
```

## Security Validation

```python
# security/upload_security.py
class UploadSecurityValidator:
    def validate_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: Optional[str] = None
    ) -> Tuple[str, dict]:
        metadata = {"original_filename": filename, "size": len(file_content)}
        
        # 1. Size check
        if len(file_content) > self.config.max_file_size:
            raise ValueError(f"File too large: {len(file_content)} bytes")
        if len(file_content) == 0:
            raise ValueError("Empty file not allowed")
        
        # 2. Extension validation
        extension = Path(filename).suffix.lower()
        if extension in self.config.blocked_extensions:
            raise ValueError(f"Extension {extension} is blocked")
        if extension not in self.config.allowed_extensions:
            raise ValueError(f"Extension {extension} not allowed")
        
        # 3. MIME detection (magic bytes)
        detected_mime = self._detect_mime_type(file_content)
        metadata["detected_mime_type"] = detected_mime
        
        if detected_mime in self.config.blocked_mime_types:
            raise ValueError(f"File type {detected_mime} is blocked")
        if detected_mime not in self.config.allowed_mime_types:
            raise ValueError(f"File type {detected_mime} not allowed")
        
        # 4. Content-type header verification
        if content_type and not self._is_acceptable_mismatch(content_type, detected_mime):
            logger.warning("MIME mismatch", declared=content_type, detected=detected_mime)
        
        # 5. Executable detection
        self._check_embedded_executables(file_content)
        
        # 6. Zip bomb detection
        if extension in {".zip", ".tar", ".gz", ".tgz"}:
            self._check_zip_bomb(file_content, extension)
        
        # 7. Polyglot check
        self._check_polyglot(file_content, extension)
        
        # 8. Secure filename generation
        secure_filename = self.filename_generator.generate(filename, user_id)
        metadata["secure_filename"] = secure_filename
        
        # 9. Hashes for deduplication
        metadata["sha256"] = hashlib.sha256(file_content).hexdigest()
        metadata["md5"] = hashlib.md5(file_content).hexdigest()
        
        return secure_filename, metadata

    def _detect_mime_type(self, content: bytes) -> str:
        if self._magic:
            return self._magic.from_buffer(content[:8192])
        return self._fallback_mime_detection(content)
    
    def _check_embedded_executables(self, content: bytes):
        # PE (Windows)
        if content[:2] == b"MZ":
            pe_offset = int.from_bytes(content[0x3C:0x40], "little")
            if content[pe_offset:pe_offset+4] == b"PE\0\0":
                raise ValueError("Windows executable embedded")
        # ELF (Linux)
        if content[:4] == b"\x7fELF":
            raise ValueError("ELF executable embedded")
        # Mach-O (macOS)
        if content[:4] in (b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe"):
            raise ValueError("Mach-O executable embedded")
        # Shebang scripts
        if content.startswith(b"#!"):
            shebang = content[:128].decode("ascii", errors="ignore").lower()
            for interp in ["/bin/bash", "/bin/sh", "/usr/bin/python"]:
                if interp in shebang:
                    raise ValueError(f"Script with dangerous interpreter: {interp}")
```

## Text Extraction

```python
# services/documents/processor.py
class DocumentProcessor:
    async def extract(self, file: BinaryIO, filename: str, mime_type: str) -> ExtractedContent:
        extension = Path(filename).suffix.lower()
        
        if mime_type == "application/pdf" or extension == ".pdf":
            return await self._extract_pdf(file)
        elif mime_type in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                           "application/msword") or extension in (".docx", ".doc"):
            return await self._extract_docx(file)
        elif mime_type.startswith("text/") or extension in (".txt", ".md", ".csv", ".json", ".xml"):
            return await self._extract_text(file, mime_type)
        else:
            raise UnsupportedFileTypeError(f"Cannot extract text from {mime_type}")
    
    async def _extract_pdf(self, file: BinaryIO) -> ExtractedContent:
        import fitz  # PyMuPDF
        file.seek(0)
        doc = fitz.open(stream=file.read(), filetype="pdf")
        
        pages = []
        full_text = []
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            pages.append(PageContent(page=page_num + 1, text=text))
            full_text.append(text)
        
        doc.close()
        
        return ExtractedContent(
            text="\n\n".join(full_text),
            pages=pages,
            page_count=len(pages),
            metadata={"extractor": "pymupdf"}
        )
    
    async def _extract_docx(self, file: BinaryIO) -> ExtractedContent:
        from docx import Document as DocxDocument
        file.seek(0)
        doc = DocxDocument(file)
        
        paragraphs = []
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append(para.text)
        
        # Extract tables
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text for cell in row.cells)
                paragraphs.append(row_text)
        
        return ExtractedContent(
            text="\n\n".join(paragraphs),
            pages=[PageContent(page=1, text="\n\n".join(paragraphs))],
            page_count=1,
            metadata={"extractor": "python-docx"}
        )
    
    async def _extract_text(self, file: BinaryIO, mime_type: str) -> ExtractedContent:
        file.seek(0)
        content = file.read().decode("utf-8", errors="ignore")
        
        return ExtractedContent(
            text=content,
            pages=[PageContent(page=1, text=content)],
            page_count=1,
            metadata={"extractor": "text", "mime_type": mime_type}
        )
```

## Chunking

```python
# services/documents/chunker.py
class DocumentChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    async def chunk(self, text: str, metadata: dict = None) -> List[Chunk]:
        # Split text
        chunks = self.splitter.split_text(text)
        
        result = []
        for i, chunk_text in enumerate(chunks):
            chunk = Chunk(
                chunk_id=str(uuid.uuid4()),
                chunk_index=i,
                text=chunk_text,
                token_count=len(chunk_text) // 4,  # Rough estimate
                metadata=metadata or {}
            )
            result.append(chunk)
        
        return result
    
    async def chunk_with_structure(self, text: str, pages: List[PageContent]) -> List[Chunk]:
        """Chunk preserving page/section structure"""
        chunks = []
        current_chunk = ""
        current_tokens = 0
        page_idx = 0
        
        for page in pages:
            page_text = page.text
            page_tokens = len(page_text) // 4
            
            if current_tokens + page_tokens > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(Chunk(
                    chunk_id=str(uuid.uuid4()),
                    chunk_index=len(chunks),
                    text=current_chunk.strip(),
                    token_count=current_tokens,
                    page=page_idx,
                    metadata={}
                ))
                # Start new with overlap
                overlap_text = current_chunk[-self.chunk_overlap:]
                current_chunk = overlap_text + "\n\n" + page_text
                current_tokens = len(current_chunk) // 4
            else:
                current_chunk += "\n\n" + page_text
                current_tokens += page_tokens
            
            page_idx += 1
        
        if current_chunk:
            chunks.append(Chunk(...))
        
        return chunks
```

## Embedding Generation

```python
# services/documents/embeddings.py
class EmbeddingService:
    def __init__(self, ollama_client: OllamaClient, model: str = "nomic-embed-text"):
        self.client = ollama_client
        self.model = model
        self.batch_size = 32
    
    async def generate(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batches with retry"""
        all_embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            embeddings = await self._generate_batch(batch)
            all_embeddings.extend(embeddings)
        
        return all_embeddings
    
    async def _generate_batch(self, texts: List[str]) -> List[List[float]]:
        for attempt in range(3):
            try:
                response = await self.client.embed(
                    model=self.model,
                    input=texts
                )
                return [emb for emb in response.embeddings]
            except Exception as e:
                if attempt == 2:
                    raise EmbeddingGenerationError(f"Failed after 3 retries: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def generate_single(self, text: str) -> List[float]:
        return (await self.generate([text]))[0]
```

## Vector Storage

```python
# services/vectorstore/service.py
class VectorStoreService:
    async def add_documents(
        self,
        collection_name: str,
        documents: List[VectorDocument]
    ) -> List[str]:
        collection = await self.client.get_or_create_collection(collection_name)
        
        ids = [d.id for d in documents]
        embeddings = [d.embedding for d in documents]
        metadatas = [d.metadata for d in documents]
        texts = [d.text for d in documents]
        
        await collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )
        
        return ids
    
    async def delete_document(self, collection_name: str, document_id: str):
        collection = await self.client.get_collection(collection_name)
        # Delete all chunks belonging to document
        await collection.delete(where={"document_id": document_id})
    
    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 10,
        filters: dict = None
    ) -> List[SearchResult]:
        collection = await self.client.get_collection(collection_name)
        
        where_clause = filters or {}
        results = await collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where_clause,
            include=["documents", "metadatas", "distances"]
        )
        
        return [
            SearchResult(
                id=ids[0][i],
                text=docs[0][i],
                metadata=metas[0][i],
                score=1 - dists[0][i]  # Convert distance to similarity
            )
            for i in range(len(results.ids[0]))
        ]
```

## BM25 Index

```python
# services/retrieval/bm25.py
class BM25Index:
    def __init__(self, persist_path: str = "./bm25_index"):
        self.persist_path = persist_path
        self.indices: Dict[str, BM25Okapi] = {}  # org_id -> index
        self.doc_mapping: Dict[str, List[str]] = {}  # org_id -> doc_ids
        self.tokenizer = self._default_tokenizer
    
    def _default_tokenizer(self, text: str) -> List[str]:
        import re
        return re.findall(r'\b\w+\b', text.lower())
    
    def add_documents(self, org_id: str, documents: List[DocumentChunk]):
        if org_id not in self.indices:
            self.indices[org_id] = BM25Okapi([], tokenizer=self.tokenizer)
            self.doc_mapping[org_id] = []
        
        tokenized = [self.tokenizer(d.text) for d in documents]
        self.indices[org_id].add_documents(tokenized)
        self.doc_mapping[org_id].extend([d.id for d in documents])
        self._persist(org_id)
    
    def search(self, org_id: str, query: str, top_k: int = 10) -> List[BM25Result]:
        if org_id not in self.indices:
            return []
        
        tokenized_query = self.tokenizer(query)
        scores = self.indices[org_id].get_scores(tokenized_query)
        
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        return [
            BM25Result(
                document_id=self.doc_mapping[org_id][idx],
                score=float(scores[idx])
            )
            for idx in top_indices if scores[idx] > 0
        ]
    
    def _persist(self, org_id: str):
        import pickle
        Path(self.persist_path).mkdir(parents=True, exist_ok=True)
        with open(f"{self.persist_path}/bm25_{org_id}.pkl", "wb") as f:
            pickle.dump({
                "index": self.indices[org_id],
                "doc_mapping": self.doc_mapping[org_id]
            }, f)
```

## Duplicate Detection

```python
# services/documents/service.py
class DocumentService:
    async def upload_document(self, ...) -> Tuple[Document, bool]:
        # Calculate content hash
        content_hash = hashlib.sha256(file_content).hexdigest()
        
        # Check for duplicate
        existing = await self.repo.get_by_content_hash(content_hash, organization_id)
        if existing and not force_reindex:
            return existing, True  # Duplicate found
        
        # Process new document
        document = await self._process_new_document(file_content, metadata)
        document.content_hash = content_hash
        await self.repo.create(document)
        
        return document, False
```

## Processing Status Tracking

```python
# database/models.py
class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Document(Base):
    # ... other fields
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    page_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    embeddings_created = Column(Integer, default=0)
    content_hash = Column(String(64), index=True)
```

## Error Handling

```python
# services/documents/exceptions.py
class DocumentProcessingError(KifPilotException):
    pass

class FileValidationError(DocumentProcessingError):
    def __init__(self, message: str, details: dict = None):
        super().__init__("FILE_VALIDATION_ERROR", message, details)

class UnsupportedFileTypeError(DocumentProcessingError):
    def __init__(self, mime_type: str):
        super().__init__("UNSUPPORTED_FILE_TYPE", f"Unsupported file type: {mime_type}")

class DuplicateFileError(DocumentProcessingError):
    def __init__(self, existing_doc_id: str):
        super().__init__("DUPLICATE_FILE", "Document already exists", {"existing_document_id": existing_doc_id})

class ParsingError(DocumentProcessingError):
    def __init__(self, message: str):
        super().__init__("PARSING_ERROR", message)

class ChunkingError(DocumentProcessingError):
    pass

class EmbeddingGenerationError(DocumentProcessingError):
    pass
```

## Monitoring

```python
# Metrics
documents_uploaded = Counter("documents_uploaded_total", "Documents uploaded", ["status", "mime_type"])
document_processing_time = Histogram("document_processing_seconds", "Processing time", ["stage"])
document_chunks_created = Histogram("document_chunks_created", "Chunks per document")
document_size_bytes = Histogram("document_size_bytes", "Document sizes")

# In service
start = time.perf_counter()
document = await self._process(file, metadata)
document_processing_time.labels(stage="total").observe(time.perf_counter() - start)
documents_uploaded.labels(status="success", mime_type=mime_type).inc()
```