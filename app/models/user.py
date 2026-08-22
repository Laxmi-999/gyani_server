from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key =True, index=True)
    email =Column(String, unique=True, index=True, nullable=False)
    hashed_password =Column(String, nullable=False)
    created_at =Column(DateTime, default=datetime.utcnow)
    notes = relationship("Note", back_populates = "owner", cascade = "all, delete-orphan")
    files = relationship("FileAttachment", back_populates="owner", cascade="all, delete-orphan")
    # in this file, (SQLAlchemy) defines how data is stored inside the database
    # main responsibility: maps python classes directly to  PostgreSQL/MYSQL database tables