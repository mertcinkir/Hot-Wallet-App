from fastapi import FastAPI, Depends, status, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from contextlib import asynccontextmanager
from src.domain.commands import UserRegisterCommand, UserLoginCommand  # You need to define UserLoginCommand
from src.service_layer.messagebus import MessageBus
from src.core.exceptions.exception_handlers import EXCEPTION_HANDLERS
from src.core.correlation.middleware import CorrelationIdMiddleware
import logging
import bcrypt
import jwt
import os
import redis.asyncio as aioredis
from datetime import datetime, timedelta
from src.domain.model import UserLogin, Token, TokenRefresh, PasswordResetRequest, PasswordResetConfirm
from src.domain.commands import UserLoginCommand, PasswordResetRequestCommand, PasswordResetConfirmCommand
from src.core.events.events import UserRegisteredEvent, UserLoggedInEvent, PasswordResetRequestedEvent
from fastapi import HTTPException, Body, Security
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
from functools import wraps
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("auth_service")

def get_messagebus(request: Request) -> MessageBus:
    return request.app.state.messagebus

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Import and initialize as in your template's main.py
    from src import config, bootstrap
    from sqlalchemy import create_engine
    from src.adapters.database import orm
    from sqlalchemy.orm import sessionmaker
    from src.service_layer import unit_of_work
    from src.adapters.message_broker import connection_manager, publisher, subscriber

    logger.info("Auth Service starting up...")
    orm.init_orm_mappers()
    engine = create_engine(config.get_primary_url(), echo=True)
    session_factory = sessionmaker(bind=engine)
    orm.metadata.create_all(bind=engine)
    puow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    conn = connection_manager.RabbitMQConnectionManager(connection_url=config.get_rabbitmq_url())
    pub = publisher.EventPublisher(connection_manager=conn)
    mbus = bootstrap.bootstrap(puow=puow, conn=conn, pub=pub)
    sub = subscriber.EventSubscriber(connection_manager=conn, messagebus=mbus)
    app.state.messagebus = mbus
    app.state.connection_manager = conn
    consume_task = None
    try:
        consume_task = app.loop.create_task(sub.start_consuming()) if hasattr(app, 'loop') else None
        yield
    finally:
        logger.info("Auth Service shutting down...")
        await sub.stop_consuming()
        if consume_task:
            await consume_task
        await pub.close()
        await conn.close()
        logger.info("Auth Service shut down successfully.")

app = FastAPI(
    title="Auth Service API",
    description="Handles authentication and JWT token management.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(CorrelationIdMiddleware)
for exc, handler in EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exc, handler)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# JWT/Redis config
JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RATE_LIMIT = int(os.getenv("RATE_LIMIT", 5))  # max attempts
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", 60))  # seconds

redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(data: dict):
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def is_token_blacklisted(token: str) -> bool:
    return await redis_client.get(f"bl:{token}") is not None

async def blacklist_token(token: str, exp: int):
    await redis_client.setex(f"bl:{token}", exp, "1")

def rate_limit(key_func):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request')
            key = f"rl:{key_func(request)}"
            count = await redis_client.incr(key)
            if count == 1:
                await redis_client.expire(key, RATE_LIMIT_WINDOW)
            if count > RATE_LIMIT:
                raise HTTPException(status_code=429, detail="Too many requests")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

@app.post("/register", status_code=status.HTTP_201_CREATED, response_model=Token)
async def register_user(cmd: UserRegisterCommand = Body(...), messagebus: MessageBus = Depends(get_messagebus)):
    # Hash password with bcrypt
    hashed = bcrypt.hashpw(cmd.password.encode(), bcrypt.gensalt())
    cmd = UserRegisterCommand(username=cmd.username, email=cmd.email, password=hashed.decode())
    await messagebus.handle(cmd)
    # Publish event
    event = UserRegisteredEvent(userid="", username=cmd.username, email=cmd.email)  # Fill userid if available
    await messagebus.handle(event)
    # Issue tokens
    access_token = create_access_token({"sub": cmd.username})
    refresh_token = create_refresh_token({"sub": cmd.username})
    return Token(access_token=access_token, refresh_token=refresh_token)

@app.post("/login", response_model=Token)
@rate_limit(lambda req: req.client.host)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), messagebus: MessageBus = Depends(get_messagebus), request: Request = None):
    # Validate user credentials (fetch user, check bcrypt)
    cmd = UserLoginCommand(username=form_data.username, password=form_data.password)
    user = await messagebus.handle(cmd)  # Should return user dict with hashed password
    if not user or not bcrypt.checkpw(form_data.password.encode(), user["password"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Publish event
    event = UserLoggedInEvent(userid=user["id"], username=user["username"], email=user["email"])
    await messagebus.handle(event)
    # Issue tokens
    access_token = create_access_token({"sub": user["username"]})
    refresh_token = create_refresh_token({"sub": user["username"]})
    return Token(access_token=access_token, refresh_token=refresh_token)

@app.post("/refresh", response_model=Token)
async def refresh_token(data: TokenRefresh = Body(...)):
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if await is_token_blacklisted(data.refresh_token):
        raise HTTPException(status_code=401, detail="Token blacklisted")
    access_token = create_access_token({"sub": payload["sub"]})
    refresh_token = create_refresh_token({"sub": payload["sub"]})
    return Token(access_token=access_token, refresh_token=refresh_token)

@app.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    exp = payload.get("exp", int(datetime.utcnow().timestamp()) + 60)
    await blacklist_token(token, exp - int(datetime.utcnow().timestamp()))
    return {"message": "Logged out"}

@app.post("/password/reset")
async def password_reset_request(data: PasswordResetRequest = Body(...), messagebus: MessageBus = Depends(get_messagebus)):
    # Generate reset token (short expiry)
    reset_token = create_access_token({"sub": data.email, "type": "reset"}, expires_delta=timedelta(minutes=30))
    event = PasswordResetRequestedEvent(email=data.email, reset_token=reset_token)
    await messagebus.handle(event)
    return {"message": "Password reset requested. Check your email."}

@app.post("/password/reset/confirm")
async def password_reset_confirm(data: PasswordResetConfirm = Body(...), messagebus: MessageBus = Depends(get_messagebus)):
    payload = decode_token(data.reset_token)
    if payload.get("type") != "reset" or payload.get("sub") != data.email:
        raise HTTPException(status_code=400, detail="Invalid reset token")
    # Hash new password
    hashed = bcrypt.hashpw(data.new_password.encode(), bcrypt.gensalt())
    cmd = PasswordResetConfirmCommand(email=data.email, reset_token=data.reset_token, new_password=hashed.decode())
    await messagebus.handle(cmd)
    return {"message": "Password reset successful."}

@app.get("/health")
async def health():
    return {"status": "ok"}