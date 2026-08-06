from fastapi import APIRouter

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload")
async def upload_document():
    return {"message": "Upload document - to be implemented in Phase 2"}


@router.get("/{doc_id}")
async def get_document(doc_id: str):
    return {"message": f"Get document {doc_id} - to be implemented in Phase 2"}


@router.get("/knowledge-base/{kb_id}")
async def list_documents(kb_id: str):
    return {"message": f"List documents for knowledge base {kb_id} - to be implemented in Phase 2"}


@router.post("/{doc_id}/process")
async def process_document(doc_id: str):
    return {"message": f"Process document {doc_id} - to be implemented in Phase 2"}


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    return {"message": f"Delete document {doc_id} - to be implemented in Phase 2"}