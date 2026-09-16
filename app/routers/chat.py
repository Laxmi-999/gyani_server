import json
import logging
import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


# Adjust imports below 
from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse, SourceNote
from app.core.deps import get_current_user
from app.models.user import User
