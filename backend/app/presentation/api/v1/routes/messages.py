from fastapi import APIRouter

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.post("")
async def add_message():
    return {"message": "Add message - to be implemented in Phase 2"}


@router.get("/conversation/{conversation_id}")
async def get_messages(conversation_id: str):
    return {"message": f"Get messages for conversation {conversation_id} - to be implemented in Phase 2"}