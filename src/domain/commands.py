from pydantic import EmailStr
from pydantic.dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Command:
    ...


@dataclass(frozen=True)
class UserRegisterCommand(Command):
    username: str
    email: EmailStr
    password: str

@dataclass(frozen=True)
class UserLoginCommand(Command):
    username: str
    password: str

@dataclass(frozen=True)
class PasswordResetRequestCommand(Command):
    email: EmailStr

@dataclass(frozen=True)
class PasswordResetConfirmCommand(Command):
    email: EmailStr
    reset_token: str
    new_password: str

@dataclass(frozen=True)
class AddWalletCommand(Command):
    user_id: str
    wallet_name: str
    encrypted_private_key: str
    public_key: str
    is_default: bool = False

@dataclass(frozen=True)
class UpdateWalletCommand(Command):
    user_id: str
    wallet_id: str
    wallet_name: Optional[str] = None
    is_default: Optional[bool] = None

@dataclass(frozen=True)
class DeleteWalletCommand(Command):
    user_id: str
    wallet_id: str

@dataclass(frozen=True)
class UserProfileUpdateCommand(Command):
    user_id: str
    username: Optional[str] = None
    email: Optional[EmailStr] = None

@dataclass(frozen=True)
class UserProfileDeleteCommand(Command):
    user_id: str