from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class FileOut(BaseModel):
    id: int
    owner_id: Optional[int] = None
    filename: str
    content_type: str
    file_size: int
    uploaded_at: datetime

    ocr_status: Optional[str] = None
    extracted_text: Optional[str] = None

    # Extracted NLP entities dictionary
    # Example response: {"PERSON": ["Ram Sharma"], "MONEY": ["रु ५०,०००"], "DATE": ["2026-09-06"]}
    entities: Optional[dict[str, Any]] = None

    # Pydantic v2 configuration (replaces legacy class Config)
    model_config = ConfigDict(from_attributes=True)