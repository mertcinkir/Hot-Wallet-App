import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional, List
from pydantic.dataclasses import dataclass
from pydantic import EmailStr, Field, StrictBool, BaseModel
from src.core.events import events


def normalize_fullname(fullname: str) -> str:
    return " ".join(name.capitalize() for name in fullname.split())

@dataclass(frozen=True)
class BaseValueObject:
    # def __composite_values__(self) -> tuple[Any, ...]:
    #     return tuple(getattr(self, field.name) for field in fields(self))
    #
    # def __eq__(self, other):
    #     return isinstance(other, type(self)) and all(getattr(self, field.name) == getattr(other, field.name) for field in fields(self))
    #
    # def __ne__(self, other):
    #     return not self.__eq__(other)
    ...

@dataclass(frozen=True)
class Username(BaseValueObject):
    value: Annotated[
        str,
        Field(pattern=r'^\w{3,20}$')
    ]

@dataclass(frozen=True)
class Email(BaseValueObject):
    value: EmailStr

@dataclass(frozen=True)
class UserID(BaseValueObject):
    value: Annotated[
        str,
        Field(pattern=r"^[0-9a-f]{32}$")
    ]

@dataclass(frozen=True)
class PasswordHash(BaseValueObject):
    value: Annotated[
        str,
        Field(
            pattern=r'^\$(?<algorithm>[a-z0-9-]+)(\$(?<version>v=\d+))?(\$[^\s$]+)+\$(?<salt>[^\s$]+)\$(?<hash>[^\s$]+)$'
        )
    ]

@dataclass(frozen=True)
class VerifiedFlag(BaseValueObject):
    value: StrictBool


class User:
    """
    Represents the User aggregate root.

    Encapsulates user-related data and business logic.
    Maintains a list of domain events for publishing.
    """

    def __init__(self,
                 userid: UserID,
                 username: Username,
                 email: Email,
                 password_hash: PasswordHash,
                 verified_flag: VerifiedFlag,
                 ):
        """
        Initializes a User instance.

        Args:
            userid (UserID): Unique identifier for the user.
            username (Username): User's chosen username.
            email (Email): User's email address.
            password_hash (PasswordHash): Hashed password.
            verified_flag (VerifiedFlag): User's verification status.
        """
        self.userid = userid
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.verified_flag = verified_flag
        self.events = []

    @classmethod
    def create(
            cls,
            userid: str,
            username: str,
            email: EmailStr,
            password_hash: str,
            verified_flag: bool,
    ):
        """
        Factory method to create a new User.

        Appends a UserEmailVerificationRequested event upon creation.

        Args:
            userid (str): Raw user ID string.
            username (str): Raw username string.
            email (EmailStr): Raw email string.
            password_hash (str): Raw password hash string.
            verified_flag (bool): Raw verification status.

        Returns:
            User: A new User instance.
        """
        user = cls(
            UserID(userid),
            Username(username),
            Email(email),
            PasswordHash(password_hash),
            VerifiedFlag(verified_flag),
        )

        user.events.append(
            events.UserEmailVerificationRequested(
                userid=user.userid.value,
                username=user.username.value,
                email=user.email.value,
            )
        )
        return user


class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefresh(BaseModel):
    refresh_token: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    email: EmailStr
    reset_token: str
    new_password: str

class WalletResponse(BaseModel):
    id: int
    wallet_name: str
    public_key: str
    is_default: bool

class WalletUpdate(BaseModel):
    wallet_name: Optional[str] = None
    is_default: Optional[bool] = None

class UserProfileResponse(BaseModel):
    id: int
    username: str
    email: str

class UserProfileUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None

class WalletDetailsResponse(BaseModel):
    id: int
    wallet_name: str
    public_key: str
    encrypted_private_key: str
    is_default: bool

if __name__ == "__main__":
    print(Username("tester"). value)
