from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    question:str

class SourceNote(BaseModel):
    id:int  #or UUI/str depending on your DB primary key
    title:str

class ChatResponse(BaseModel):
    answer:str
    Sources: List[SourceNote]

    