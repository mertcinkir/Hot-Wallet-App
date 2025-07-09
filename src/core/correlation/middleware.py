from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from uuid import uuid4
from src.core.correlation.context import set_correlation_id

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())
        set_correlation_id(correlation_id)

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
