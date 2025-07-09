from sqlalchemy import Column, MetaData, String, Table, UniqueConstraint, Boolean
from sqlalchemy.orm import composite, registry


metadata = MetaData()
mapper_registry = registry()

user_table = Table(
"user",
    metadata,
    Column("id", String(32), key="db_userid", primary_key=True),
    Column("username", String(255), key="db_username",nullable=False, unique=True),
    Column("email", String(255), key="db_email",nullable=False, unique=True),
    Column("password_hash", String(255), key="db_password_hash",nullable=False),
    Column("verified_flag", Boolean, key="db_verified_flag",nullable=False),
    UniqueConstraint("db_username", name="uc_user_username"),
    UniqueConstraint("db_email", name="uc_user_email"),
)


def init_orm_mappers():
    """
    Initializes SQLAlchemy ORM mappers for domain models.

    Maps the `User` domain model to the `user_table` database table,
    using composite types for value objects like UserID, Username, Email,
    PasswordHash, and VerifiedFlag.
    """
    from src.domain.model import User, UserID, Username, Email, PasswordHash, VerifiedFlag

    mapper_registry.map_imperatively(
        User,
        user_table,
        properties={
            "userid": composite(UserID, user_table.c.db_userid),
            "username": composite(Username, user_table.c.db_username),
            "email": composite(Email, user_table.c.db_email),
            "password_hash": composite(PasswordHash, user_table.c.db_password_hash),
            "verified_flag": composite(VerifiedFlag, user_table.c.db_verified_flag),
        }
    )
