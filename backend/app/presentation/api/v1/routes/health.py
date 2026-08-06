from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": "development",
        "database": "connected",
        "vector_store": "connected",
        "llm": "connected",
    }


@router.get("/ready")
async def readiness_check():
    return {"ready": True}


@router.get("/live")
async def liveness_check():
    return {"alive": True}