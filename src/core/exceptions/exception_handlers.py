from fastapi import Request
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from fastapi.responses import JSONResponse
from src.core.exceptions.exceptions import *
from aio_pika.exceptions import AMQPError

async def generic_error_handler(request: Request, exc: Error):
    return JSONResponse(
        status_code=exc.code,
        content={
        "detail": exc.detail,
    })

async def pydantic_validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),  # Pydantic'in ürettiği detay yapısı
        },
    )

async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):

    return JSONResponse(
        status_code=422,
        content={
            "detail": [{
                "loc": ["db"],
                "msg": str(exc.orig) if hasattr(exc, "orig") else str(exc),
                "type": f"sqlalchemy.{type(exc).__name__}",
            }]
        }
    )

async def aio_pika_exception_handler(request: Request, exc: AMQPError):

    return JSONResponse(
        status_code=500,
        content={
            "detail": [{
            "loc": ["broker"],
            "msg": str(exc),
            "type": f"aio_pika.{exc.__class__.__name__}"
            }]
        }
    )

async def fastapi_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": [
                {
                    "loc": ["route"],
                    "msg": exc.detail,
                    "type": f"http_error.{exc.status_code}"
                }
            ]
        }
    )

async def fastapi_validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors()
        }
    )

EXCEPTION_HANDLERS = {
    EmailAlreadyRegisteredException: generic_error_handler,
    UsernameAlreadyRegisteredException: generic_error_handler,
    ValidationError: pydantic_validation_error_handler,
    SQLAlchemyError: sqlalchemy_error_handler,
    AMQPError: aio_pika_exception_handler,
    HTTPException: fastapi_http_exception_handler,
    RequestValidationError: fastapi_validation_exception_handler
}
