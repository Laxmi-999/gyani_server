from passlib.context import CryptContext
from datetime import datetime,timedelta
from jose import jwt
from app.config import settings

pwd_context =CryptContext(schemes = ["bcrypt"], deprecated="auto" )

def hash_password(password:str)->str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password:str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    # copy the original data so that the original data does not get altered
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

# Decodes and verifies a JWT access token
def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    