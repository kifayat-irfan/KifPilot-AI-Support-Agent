from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("")
async def chat():
    return {"message": "Chat - to be implemented in Phase 2"}


@router.post("/stream")
async def chat_stream():
    return {"message": "Chat stream - to be implemented in Phase 2"}