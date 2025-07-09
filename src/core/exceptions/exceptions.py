from pydantic import Field
from http import HTTPStatus
from typing import List, Dict, Any
from functools import cached_property
from pydantic.dataclasses import dataclass
from src.core.exceptions.types import ErrorCategory

"""
Örnek:
| `loc` değeri               | Anlamı                                          |
| -------------------------- | ----------------------------------------------- |
| `["body", "email"]`        | Request body içinde "email" alanı               |
| `["query", "page"]`        | URL'deki query param olan `?page=...`           |
| `["path", "user_id"]`      | URL path parametresi `/users/{user_id}`         |
| `["header", "x-token"]`    | Header’da bulunan `X-Token` eksik veya geçersiz |
| `["cookie", "session_id"]` | Cookie üzerinden gelen `session_id` hatalı      |
"""


@dataclass(frozen=True)
class Error(Exception):
    code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    loc: List[str] = Field(default_factory=list)
    msg: str = Field(default="Unknown error.")
    type: ErrorCategory.UnknownError = Field(default=ErrorCategory.UnknownError.UNCLASSIFIED_ERROR)

    @cached_property
    def detail(self) -> List[Dict[str, Any]]:
        return [{
            "loc": self.loc,
            "msg": self.msg,
            "type": self.type,
        }]


@dataclass(frozen=True)
class EmailAlreadyRegisteredException(Error):
    code: int = HTTPStatus.CONFLICT
    loc: List[str] = Field(default=["body", "email"])
    msg: str = Field(default="Email already exists.")
    type: ErrorCategory.DomainError = Field(default=ErrorCategory.DomainError.AGGREGATE_STATE_INVALID)


@dataclass(frozen=True)
class UsernameAlreadyRegisteredException(Error):
    code: int = HTTPStatus.CONFLICT
    loc: List[str] = Field(default=["body", "username"])
    msg: str = Field(default="Username already exists.")
    type: ErrorCategory.DomainError = Field(default=ErrorCategory.DomainError.AGGREGATE_STATE_INVALID)


@dataclass(frozen=True)
class InvalidMessageTypeException(Error):
    code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    loc: List[str] = Field(default=[])
    msg: str = Field(default="Unidentified event/command.")
    type: ErrorCategory.ApplicationError = ErrorCategory.ApplicationError.MAPPING_ERROR

@dataclass(frozen=True)
class EventSerializationException(Error):
    code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    loc: List[str] = Field(default=[])
    msg: str = Field(default="Event serialization is failed.")
    type: ErrorCategory.MessagingError = ErrorCategory.MessagingError.MESSAGE_SERIALIZATION_ERROR

@dataclass(frozen=True)
class ConnectionClosedException(Error):
    code: int = HTTPStatus.SERVICE_UNAVAILABLE
    loc: List[str] = Field(default=[])
    msg: str = Field(default="Connection closed.")
    type: ErrorCategory.MessagingError = ErrorCategory.MessagingError.CONNECTION_CLOSED_ERROR