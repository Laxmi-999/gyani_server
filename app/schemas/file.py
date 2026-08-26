from datetime import datetime
from pydantic import BaseModel

class FileOut(BaseModel):
    id:int
    owner_id: int | None = None
    filename : str
    content_type: str
    file_size: int
    uploaded_at: datetime

    ocr_status :str | None = None
    extracted_text : str | None = None

    class Config:
        from_attributes = True