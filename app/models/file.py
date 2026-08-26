from  datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ORCStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "Completed"
    FAILED = "failed"


class FileAttachment(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="SET NULL"), nullable =True)

    filename = Column(String, nullable = False)
    file_path = Column(String, nullable = False)
    content_type = Column(String, nullable = False)
    file_size = Column(Integer, nullable =  False)
    uploaded_at = Column(DateTime, default = datetime.utcnow)
    ocr_status = Column(String, default = ORCStatus.PENDING.value)

    # Relationships
    owner  = relationship("User", back_populates ="files")
    note = relationship("Note", back_populates = "files")