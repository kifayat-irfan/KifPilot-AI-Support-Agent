from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.core.exceptions import KifPilotException, http_exception_from_kifpilot
from app.core.logging import get_logger

logger = get_logger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except KifPilotException as e:
            logger.error(
                "Application error",
                request_id=getattr(request.state, "request_id", None),
                error_code=e.code,
                message=e.message,
                details=e.details,
            )
            http_exc = http_exception_from_kifpilot(e)
            return JSONResponse(
                status_code=http_exc.status_code,
                content=http_exc.detail,
            )
        except Exception as e:
            logger.exception(
                "Unexpected error",
                request_id=getattr(request.state, "request_id", None),
                error=str(e),
            )
            return JSONResponse(
                status_code=500,
                content={
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {},
                },
            )