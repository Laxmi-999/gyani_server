from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.core.deps import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_access_token, hash_password, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserOut, RefreshTokenRequest
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=user_in.email, hashed_password=hash_password(user_in.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
             detail="Incorrect email or password"
            )

#    send both short lived access and long lived refresh tokens
    token_data = {"sub": str(user.id)}
    access_token = create_access_token(data = token_data)
    refresh_token = create_refresh_token(data=token_data)
    return Token(access_token=access_token, refresh_token=refresh_token)

@router.post("/refresh", response_model = Token)
def  refresh_token(body: RefreshTokenRequest, db:Session= Depends(get_db)):
    try:
        # 1. Decode and verify that token is a valid REFRESH TOKEN (not expired or tempered)
        payload = decode_access_token(body.refresh_token, expected_type="refresh")
        user_id = payload.get("sub")
        if not user_id:

            raise HTTPException(status_code=401,  detail= "Invalid token payload")
    except JWTError:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid or expired refresh token",
        )
# 2. verify user still exists in database
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail = "User  not found")
# 3. Issue a fresh pair of tokens
    token_data = {"sub": str(user.id)}
    new_access_token = create_access_token(data=token_data)
    new_refresh_token = create_refresh_token(data=token_data)

    return Token(access_token = new_access_token, refresh_token = new_refresh_token)

    

@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
