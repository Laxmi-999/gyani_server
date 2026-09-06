from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class NoteCreate(BaseModel):
    title: str
    content: str
    tags: Optional[str] = None


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[str] = None


class NoteOut(BaseModel):
    id: int
    owner_id: int
    title: str
    content: str
    tags: Optional[str] = None

    # New fields for extracted entities & auto-tags
    entities: Optional[Dict[str, List[str]]] = {}
    auto_tags: Optional[List[str]] = []
    source_file_id: Optional[int] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True