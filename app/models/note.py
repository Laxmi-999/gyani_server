from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)

    # Standard user-entered tags (e.g., "personal, urgent")
    tags = Column(String, nullable=True)

    # AI/NLP extracted structured data
    entities = Column(JSON, nullable=True, default={})

    # Stores list: ["Laxmi", "Kathmandu", "Rs. 2500"]
    auto_tags = Column(JSON, nullable=True, default=[])

    # Reference to source file if created via OCR/File Upload
    source_file_id = Column(
        Integer, ForeignKey("files.id"), nullable=True
    )

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    owner = relationship("User", back_populates="notes")

    # Explicitly map the relationship to files attached to this note
    files = relationship(
        "FileAttachment", 
        back_populates="note",
        foreign_keys="FileAttachment.note_id"
    )

    # Optional: Relationship pointing back to the specific source file that generated this note
    source_file = relationship(
        "FileAttachment",
        foreign_keys=[source_file_id]
    )