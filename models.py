from pydantic import BaseModel
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    email = Column(String, unique=True)

class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    wallet_name = Column(String)
    encrypted_private_key = Column(String)
    public_key = Column(String)
    is_default = Column(Integer, default=0)

class UserCreate(BaseModel):
    username: str
    password: str
    email: str

class WalletCreate(BaseModel):
    wallet_name: str
    encrypted_private_key: str
    public_key: str
    is_default: bool = False