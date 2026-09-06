import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.enums import OCRStatus
from typing import Any, Optional


class FileAttachment(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="SET NULL"), nullable=True)

    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    ocr_status = Column(String, default=OCRStatus.PENDING.value)
    entities = Column(JSON, nullable=True, default=dict)   
    extracted_text = Column(Text, nullable=True)

    # Relationships
    owner = relationship("User", back_populates="files")

    # Explicitly specify note_id as the foreign key for this relationship
    note = relationship(
        "Note", 
        back_populates="files", 
        foreign_keys=[note_id]
    )