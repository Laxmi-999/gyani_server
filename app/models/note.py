from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key = True, index = True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable =False)
    title = Column(String, nullable = False)
    content = Column(Text, nullable =False)
    tags = Column(String, nullable =True)
    created_at = Column(DateTime, default = datetime.utcnow)
    updated_at = Column(DateTime, default = datetime.utcnow, onupdate =datetime.utcnow)
    owner = relationship("User", back_populates = "notes")
    files = relationship("FileAttachment", back_populates="note") # Added this line