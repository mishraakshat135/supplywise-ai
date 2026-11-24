"""One error shape for the whole API: {"detail": "...", "code": "..."}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

log = logging.getLogger("supplywise")


class AppError(Exception):
    status_code, code = 400, "bad_request"

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class NotFoundError(AppError):
    status_code, code = 404, "not_found"


class ConflictError(AppError):
    status_code, code = 409, "conflict"


class BusinessRuleError(AppError):
    status_code, code = 422, "business_rule_violation"


class PermissionDeniedError(AppError):
    status_code, code = 403, "forbidden"


class UnauthorizedError(AppError):
    status_code, code = 401, "unauthorized"


class AIUnavailableError(AppError):
    status_code, code = 503, "ai_unavailable"


class AIWorkflowError(AppError):
    status_code, code = 502, "ai_workflow_failed"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "code": exc.code})

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        msgs = "; ".join(f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors())
        return JSONResponse(status_code=422, content={"detail": msgs, "code": "validation_error"})

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.exception("Unhandled error")
        return JSONResponse(status_code=500, content={"detail": "Internal server error", "code": "internal_error"})
