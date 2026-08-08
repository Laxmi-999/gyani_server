from datetime import datetime
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email:EmailStr
    password:str


class UserOut(BaseModel):
        id:int
        email:EmailStr
        created_at: datetime

        class Config:
            from_attributes = True

# in this file (PYNDATIC) defines how data is formatted and validated over the HTTP API network
# main responsibility" validate incoming request JSON payloads and shapes outgoing response JSON.