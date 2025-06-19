from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import jwt
from sqlalchemy.orm import Session
from database import SessionLocal, Base, engine
from models import User, Wallet, WalletCreate

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Base.metadata.create_all(bind=engine)


@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db), token: str = Depends(get_token)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.post("/users/{user_id}/wallets/")
def create_wallet(user_id: int, wallet: WalletCreate, db: Session = Depends(get_db), token: str = Depends(get_token)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_wallet = Wallet(user_id=user_id, wallet_name=wallet.wallet_name,
                      encrypted_private_key=wallet.encrypted_private_key,
                      public_key=wallet.public_key, is_default=wallet.is_default)
    db.add(db_wallet)
    db.commit()
    # Send wallet update event to RabbitMQ
    send_rabbitmq_message("wallet_updated", {"user_id": user_id, "wallet_id": db_wallet.id})
    return {"message": "Wallet created"}


def get_token(token: str = Depends(get_token_header)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["user_id"]
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_token_header(token: str = Header(...)):
    return token


from auth_service import send_rabbitmq_message