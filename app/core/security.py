from passlib.context import CryptContext
from datetime import datetime,timedelta
from jose import JWTError, jwt
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
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(data:dict, expires_delta:timedelta | None = None)->str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(days = settings.refresh_token_expire_days)  #e.g, 7
    )
    to_encode.update({"exp":expire, "type":"refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


# Decodes and verifies a JWT access token
def decode_access_token(token: str, expected_type:str = "access") -> dict:
    """Decodes and validates token signature, expiration, and token type"""
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

    token_type = payload.get("type")
    if(token_type != expected_type):
        raise JWTError(f"Invalida token type : expected {expected_type}, got {token_type}")
    return payload