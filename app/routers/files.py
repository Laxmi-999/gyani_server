import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db, SessionLocal
from app.models.file import FileAttachment, OCRStatus
from app.models.user import User
from app.schemas.file import FileOut
from app.services.ocr import process_image_ocr

router = APIRouter(prefix="/files", tags=["files"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
IMAGE_MIME_TYPES = ["image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff"]

@router.post("/", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    background_tasks:BackgroundTasks,
    file: UploadFile = File(...),
    note_id: int | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Create unique filename on disk to avoid collisions
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    saved_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Read and save file content
    content = await file.read()
    file_size = len(content)

    with open(saved_path, "wb") as f:
        f.write(content)
    content_type = file.content_type or "application/octet-stream"
    is_image = content_type  in IMAGE_MIME_TYPES

    db_file = FileAttachment(
        owner_id=current_user.id,
        note_id=note_id,
        filename=file.filename,
        file_path=saved_path,
        content_type=file.content_type or "application/octet-stream",
        file_size=file_size,
        ocr_status = OCRStatus.PENDING.value if is_image else None,
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    if is_image:
        background_tasks.add_task(process_image_ocr, db_file.id, SessionLocal)
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

    if not db_file or not os.path.exists(db_file.file_path):
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

    # Delete from disk
    if os.path.exists(db_file.file_path):
        os.remove(db_file.file_path)

    # Delete row from DB
    db.delete(db_file)
    db.commit()