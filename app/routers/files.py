from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from arq.connections import RedisSettings

from app.core.deps import get_current_user
from app.database import get_db, SessionLocal
from app.models.file import FileAttachment, OCRStatus
from app.models.user import User
from app.schemas.file import FileOut
from app.services.ocr import process_image_ocr
from app.helpers.file_helpers import (
    is_processable_file,
    save_upload_file_to_disk,
    remove_file_from_disk,
)
from app.core.redis import get_redis_pool

router = APIRouter(prefix="/files", tags=["files"])
async def get_redis():
    return await create_pool(RedisSettings(host="localhost", port = 6379))


@router.post("/", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    note_id: int | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Save binary file to disk using utility helper
    saved_path, file_ext, file_size = await save_upload_file_to_disk(file)
    content_type = file.content_type or "application/octet-stream"

    # Evaluate if file is eligible for background text extraction
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

    # Trigger background worker for supported file types
    if processable:
        redis = await get_redis_pool()
        await redis.enqueue_job("process_file_ocr", db_file.id)    

    return db_file


@router.get("/", response_model=list[FileOut])
def list_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(FileAttachment).filter(FileAttachment.owner_id == current_user.id).all()


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_file = db.query(FileAttachment).filter(
        FileAttachment.id == file_id, FileAttachment.owner_id == current_user.id
    ).first()

    if not db_file or not FileResponse(db_file.file_path):
        raise HTTPException(status_code=404, detail="File not found")

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
    db_file = db.query(FileAttachment).filter(
        FileAttachment.id == file_id, FileAttachment.owner_id == current_user.id
    ).first()

    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    # Safely cleanup file on disk and remove row from DB
    remove_file_from_disk(db_file.file_path)
    db.delete(db_file)
    db.commit()