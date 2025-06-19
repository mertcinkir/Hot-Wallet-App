from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import jwt
import bcrypt
from sqlalchemy.orm import Session
from database import SessionLocal, Base, engine
from models import User, UserCreate
from dotenv import load_dotenv
import os

app = FastAPI()
load_dotenv()
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db    
    finally:
        db.close()

Base.metadata.create_all(bind=engine)

# Register a new user
@app.post("/register/")
def register(user: UserCreate, db: Session = Depends(get_db)):
    hashed = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt())
    db_user = User(username=user.username, hashed_password=hashed.decode(), email=user.email)
    db.add(db_user)
    db.commit()
    # Send registration event to RabbitMQ
    send_rabbitmq_message("user_registered", {"user_id": db_user.id, "username": user.username})
    return {"message": "User registered"}

# Login and generate JWT
@app.post("/login/")
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not bcrypt.checkpw(user.password.encode(), db_user.hashed_password.encode()):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = jwt.encode({"user_id": db_user.id}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

# RabbitMQ integration
import aio_pika

async def send_rabbitmq_message(event_type: str, data: dict):
    connection = await aio_pika.connect_robust("amqp://guest:guest@localhost/")
    async with connection:
        channel = await connection.channel()
        await channel.declare_queue(event_type)
        await channel.default_exchange.publish(
            aio_pika.Message(body=str(data).encode()),
            routing_key=event_type
        )