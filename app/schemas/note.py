from datetime import datetime 
from pydantic import BaseModel

class NoteCreate (BaseModel):
    title:str
    content : str
    tags : str | None = None

class NoteUpdate(BaseModel):
    title : str
    content : str | None = None
    tags : str | None = None

class NoteOut(BaseModel):
    id: int
    title:str
    content : str
    tags: str | None
    created_at: datetime
    updated_at : datetime

    class Config:
       from_attributes = True

