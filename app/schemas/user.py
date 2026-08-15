from datetime import datetime
from pydantic import BaseModel, EmailStr

# incoming payload for login
class UserCreate(BaseModel):
    email:EmailStr
    password:str


class UserOut(BaseModel):
        id:int
        email:EmailStr
        created_at: datetime

        class Config:
            from_attributes = True

# token response returned on login and fresh
class Token(BaseModel):
     access_token:str
     refresh_token:str
     token_type:str = "bearer"

class RefreshTokenRequest(BaseModel):
     refresh_token:str 

class TokenData(BaseModel):
     user_id:int | None = None

# in this file (PYNDATIC) defines how data is formatted and validated over the HTTP API network
# main responsibility" validate incoming request JSON payloads and shapes outgoing response JSON.