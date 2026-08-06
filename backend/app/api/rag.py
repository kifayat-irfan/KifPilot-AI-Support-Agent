from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, Dict, Any

from app.services.rag import (
    rag_service,
    RAGAskRequest,
    RAGAskResponse,
    RAGHealthResponse,
)
from app.services.rag.exceptions import (
    RAGError,
    EmptyQuestionError,
    PromptInjectionError,
    QuestionTooLongError,
    RetrievalFailedError,
    NoContextFoundError,
    GenerationFailedError,
    OllamaUnavailableError,
)
from app.core.logging import get_logger
from app.presentation.api.v1.dependencies import get_current_active_user, require_chat

router = APIRouter(prefix="/rag", tags=["RAG"])
logger = get_logger(__name__)


@router.post(
    "/ask",
    response_model=RAGAskResponse,
    responses={
        200: {"model": RAGAskResponse, "description": "Generated answer"},
        400: {"description": "Invalid question (empty, too long, or prompt injection)"},
        404: {"description": "No relevant context found"},
        500: {"description": "Generation failed"},
        503: {"description": "Ollama service unavailable"},
    },
    dependencies=[Depends(require_chat)],
)
async def ask(request: RAGAskRequest, current_user = Depends(get_current_active_user)):
    """
    Generate a grounded AI answer using retrieved document context.
    
    The model ONLY answers using the supplied context from indexed documentation.
    If the answer cannot be found in the context, it returns:
    "I cannot find this information in the indexed documentation."
    
    **Guardrails enforced:**
    - Empty questions rejected
    - Questions > 2000 chars rejected
    - Prompt injection attempts rejected
    - Requests to reveal system prompt rejected
    """
    try:
        response = await rag_service.ask(request)
        return response

    except (EmptyQuestionError, PromptInjectionError, QuestionTooLongError) as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except RetrievalFailedError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except NoContextFoundError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except GenerationFailedError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except OllamaUnavailableError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except Exception as e:
        logger.error("RAG ask failed", error=str(e), question=request.question[:100] if request.question else "N/A")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "code": "INTERNAL_ERROR"},
        )


@router.get(
    "/health",
    response_model=RAGHealthResponse,
    responses={
        200: {"model": RAGHealthResponse, "description": "Health check status"},
    },
    dependencies=[Depends(get_current_active_user)],
)
async def health_check(current_user = Depends(get_current_active_user)):
    """Check health of RAG system dependencies."""
    response = await rag_service.health_check()
    return response