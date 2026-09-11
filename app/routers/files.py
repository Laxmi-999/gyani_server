import os
from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import String, cast  # <-- Added String import here
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.redis import get_redis_pool
from app.database import get_db
from app.helpers.file_helpers import (
    is_processable_file,
    remove_file_from_disk,
    save_upload_file_to_disk,
)
from app.models.file import FileAttachment, OCRStatus
from app.models.note import Note
from app.models.user import User
from app.schemas.file import FileOut

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    note_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Save binary file to disk using utility helper
    saved_path, file_ext, file_size = await save_upload_file_to_disk(file)
    content_type = file.content_type or "application/octet-stream"

    # Evaluate if file is eligible for background text & entity extraction
    processable = is_processable_file(content_type, file_ext)

    db_file = FileAttachment(
        owner_id=current_user.id,
        note_id=note_id,
        filename=file.filename or "unnamed_file",
        file_path=saved_path,
        content_type=content_type,
        file_size=file_size,
        ocr_status=OCRStatus.PENDING.value if processable else None,
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    # Trigger background ARQ worker for supported file types
    if processable:
        redis = await get_redis_pool()
        await redis.enqueue_job("process_file_ocr", db_file.id)

    return db_file


@router.get("/", response_model=list[FileOut])
def list_files(
    entity: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all user files.

    Optionally filter by extracted entity text or entity type (e.g., ?entity=PERSON or ?entity=Kathmandu)
    """
    query = db.query(FileAttachment).filter(
        FileAttachment.owner_id == current_user.id
    )

    # If entity query search term is passed, perform JSON search across entities column
    if entity:
        search_pattern = f"%{entity.lower()}%"
        # Cast JSON column to JSONB/Text to perform string pattern matching across keys and values
        query = query.filter(
            cast(FileAttachment.entities, JSONB).cast(String).ilike(search_pattern)
        )

    return query.all()


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_file = (
        db.query(FileAttachment)
        .filter(
            FileAttachment.id == file_id,
            FileAttachment.owner_id == current_user.id,
        )
        .first()
    )

    if not db_file or not os.path.exists(db_file.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    return FileResponse(
        path=db_file.file_path,
        filename=db_file.filename,
        media_type=db_file.content_type,
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_file = (
        db.query(FileAttachment)
        .filter(
            FileAttachment.id == file_id,
            FileAttachment.owner_id == current_user.id,
        )
        .first()
    )

    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    # A generated note may reference this file as its source document.
    db.query(Note).filter(Note.source_file_id == db_file.id).update(
        {Note.source_file_id: None}, synchronize_session=False
    )
    db.delete(db_file)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    remove_file_from_disk(db_file.file_path)