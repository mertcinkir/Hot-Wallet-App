import logging
import asyncio
from fastapi import FastAPI, status, Depends, Request, HTTPException, Body, Depends, Security, Path
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import jwt
import os
from fastapi import HTTPException, Body, Depends, Security, Path
from fastapi.security import OAuth2PasswordBearer
from src.domain.model import (
    UserProfileResponse, UserProfileUpdate, WalletResponse, WalletUpdate, WalletDetailsResponse
)
from src.domain.commands import (
    UserProfileUpdateCommand, UserProfileDeleteCommand, AddWalletCommand, UpdateWalletCommand, DeleteWalletCommand
)
from src.core.events.events import (
    WalletAddedEvent, WalletDeletedEvent, UserProfileUpdatedEvent
)
from src.adapters.database.aes_crypto import AESCipher
from typing import List
from src.service_layer.messagebus import MessageBus
from src.core.correlation.middleware import CorrelationIdMiddleware
from src.core.exceptions.exception_handlers import EXCEPTION_HANDLERS

# Import your config, bootstrap, and domain modules as in the template
# from src import config
# from src.adapters.database import orm
# from src.service_layer import unit_of_work
# from src.adapters.message_broker import connection_manager, publisher, subscriber
# from src.service_layer.messagebus import MessageBus
# from src.domain.commands import UserRegisterCommand

# For this example, we will use placeholders and comments where you need to adapt or import from your template

logger = logging.getLogger("user_service")

JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@asynccontextmanager
async def lifespan(app: FastAPI):
    from src import config, bootstrap
    from sqlalchemy import create_engine
    from src.adapters.database import orm
    from sqlalchemy.orm import sessionmaker
    from src.service_layer import unit_of_work
    from src.adapters.message_broker import connection_manager, publisher, subscriber

    logger.info("User Service starting up...")
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
        logger.info("User Service shutting down...")
        await sub.stop_consuming()
        if consume_task:
            await consume_task
        await pub.close()
        await conn.close()
        logger.info("User Service shut down successfully.")

def get_messagebus(request: Request) -> MessageBus:
    return request.app.state.messagebus

app = FastAPI(
    title="User Service API",
    description="Handles user profile and wallet management.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(CorrelationIdMiddleware)
for exc, handler in EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exc, handler)

# Profile Endpoints 
@app.get("/users/me", response_model=UserProfileResponse)
async def get_profile(current_user: str = Depends(get_current_user), messagebus: MessageBus = Depends(get_messagebus)):
    # Fetch user profile from DB (pseudo-code, adapt to your repo)
    user = ... # fetch user by username=current_user
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfileResponse(id=user.id, username=user.username, email=user.email)

@app.patch("/users/me", response_model=UserProfileResponse)
async def update_profile(update: UserProfileUpdate, current_user: str = Depends(get_current_user), messagebus: MessageBus = Depends(get_messagebus)):
    # Update user profile (pseudo-code)
    user = ... # fetch user by username=current_user
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    cmd = UserProfileUpdateCommand(user_id=user.id, username=update.username, email=update.email)
    await messagebus.handle(cmd)
    # Publish event
    event = UserProfileUpdatedEvent(user_id=user.id, username=update.username or user.username, email=update.email or user.email)
    await messagebus.handle(event)
    return UserProfileResponse(id=user.id, username=update.username or user.username, email=update.email or user.email)

@app.delete("/users/me")
async def delete_profile(current_user: str = Depends(get_current_user), messagebus: MessageBus = Depends(get_messagebus)):
    user = ... # fetch user by username=current_user
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    cmd = UserProfileDeleteCommand(user_id=user.id)
    await messagebus.handle(cmd)
    return {"message": "User deleted"}

# --- Wallet Endpoints ---
@app.post("/users/wallets", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def add_wallet(wallet: WalletUpdate, current_user: str = Depends(get_current_user), messagebus: MessageBus = Depends(get_messagebus)):
    user = ... # fetch user by username=current_user
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    cipher = AESCipher()
    encrypted_key = cipher.encrypt(wallet.encrypted_private_key)
    cmd = AddWalletCommand(user_id=user.id, wallet_name=wallet.wallet_name, encrypted_private_key=encrypted_key, public_key=wallet.public_key, is_default=wallet.is_default or False)
    wallet_obj = await messagebus.handle(cmd)
    event = WalletAddedEvent(user_id=user.id, wallet_id=wallet_obj.id, wallet_name=wallet.wallet_name)
    await messagebus.handle(event)
    return WalletResponse(id=wallet_obj.id, wallet_name=wallet.wallet_name, public_key=wallet.public_key, is_default=wallet.is_default or False)

@app.get("/users/wallets", response_model=List[WalletResponse])
async def list_wallets(current_user: str = Depends(get_current_user), messagebus: MessageBus = Depends(get_messagebus)):
    user = ... # fetch user by username=current_user
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    wallets = ... # fetch wallets by user_id=user.id
    return [WalletResponse(id=w.id, wallet_name=w.wallet_name, public_key=w.public_key, is_default=w.is_default) for w in wallets]

@app.patch("/users/wallets/{wallet_id}", response_model=WalletResponse)
async def update_wallet(wallet_id: int = Path(...), update: WalletUpdate = Body(...), current_user: str = Depends(get_current_user), messagebus: MessageBus = Depends(get_messagebus)):
    user = ... # fetch user by username=current_user
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    cmd = UpdateWalletCommand(user_id=user.id, wallet_id=wallet_id, wallet_name=update.wallet_name, is_default=update.is_default)
    wallet_obj = await messagebus.handle(cmd)
    return WalletResponse(id=wallet_obj.id, wallet_name=wallet_obj.wallet_name, public_key=wallet_obj.public_key, is_default=wallet_obj.is_default)

@app.delete("/users/wallets/{wallet_id}")
async def delete_wallet(wallet_id: int = Path(...), current_user: str = Depends(get_current_user), messagebus: MessageBus = Depends(get_messagebus)):
    user = ... # fetch user by username=current_user
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    cmd = DeleteWalletCommand(user_id=user.id, wallet_id=wallet_id)
    await messagebus.handle(cmd)
    event = WalletDeletedEvent(user_id=user.id, wallet_id=wallet_id)
    await messagebus.handle(event)
    return {"message": "Wallet deleted"}

@app.get("/users/wallets/{wallet_id}/details", response_model=WalletDetailsResponse)
async def get_wallet_details(wallet_id: int = Path(...), current_user: str = Depends(get_current_user), messagebus: MessageBus = Depends(get_messagebus)):
    user = ... # fetch user by username=current_user
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    wallet = ... # fetch wallet by id and user_id
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    cipher = AESCipher()
    decrypted_key = cipher.decrypt(wallet.encrypted_private_key)
    return WalletDetailsResponse(id=wallet.id, wallet_name=wallet.wallet_name, public_key=wallet.public_key, encrypted_private_key=decrypted_key, is_default=wallet.is_default)

@app.get("/users/ping", summary="Ping endpoint for User Service.")
async def ping():
    return {"ping": "pong!"}

@app.get("/users/info", summary="Service info.")
async def info():
    return {
        "service": "User Service",
        "status": "active",
        "current_time": datetime.now(tz=timezone.utc).isoformat(),
    } 