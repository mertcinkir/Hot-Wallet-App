from pydantic import EmailStr, Field
from pydantic.dataclasses import dataclass
from uuid import UUID, uuid4
from datetime import datetime, timezone
from src.core.correlation.context import get_correlation_id


@dataclass(kw_only=True)
class Event:
    source_service: str = "user"
    event_id: UUID = Field(default_factory=uuid4)
    correlation_id: str = Field(default_factory=get_correlation_id)
    timestamp: float = Field(default_factory=lambda: datetime.now(tz=timezone.utc).timestamp())


@dataclass(kw_only=True)
class IncomingEvent(Event):
    ...


@dataclass(kw_only=True)
class OutgoingEvent(Event):
    ...


@dataclass(kw_only=True)
class  UserEmailVerificationRequested(OutgoingEvent):
    userid: str
    username: str
    email: EmailStr
    event_type: str = "user.email_verification_requested"

@dataclass(kw_only=True)
class UserRegisteredEvent(OutgoingEvent):
    userid: str
    username: str
    email: EmailStr
    event_type: str = "user.registered"

@dataclass(kw_only=True)
class UserLoggedInEvent(OutgoingEvent):
    userid: str
    username: str
    email: EmailStr
    event_type: str = "user.logged_in"

@dataclass(kw_only=True)
class PasswordResetRequestedEvent(OutgoingEvent):
    email: EmailStr
    reset_token: str
    event_type: str = "user.password_reset_requested"

@dataclass(kw_only=True)
class WalletAddedEvent(OutgoingEvent):
    user_id: str
    wallet_id: str
    wallet_name: str
    event_type: str = "wallet.added"

@dataclass(kw_only=True)
class WalletDeletedEvent(OutgoingEvent):
    user_id: str
    wallet_id: str
    event_type: str = "wallet.deleted"

@dataclass(kw_only=True)
class UserProfileUpdatedEvent(OutgoingEvent):
    user_id: str
    username: str
    email: EmailStr
    event_type: str = "user.profile_updated"
