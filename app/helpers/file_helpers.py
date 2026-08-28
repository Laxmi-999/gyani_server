import os
import uuid
from fastapi import UploadFile

from app.helpers.constants import UPLOAD_DIR, IMAGE_MIME_TYPES, DOC_EXTENSIONS


def is_processable_file(content_type: str, file_ext: str) -> bool:
    """Checks whether the uploaded file supports text extraction/OCR."""
    return (content_type in IMAGE_MIME_TYPES) or (file_ext.lower() in DOC_EXTENSIONS)


async def save_upload_file_to_disk(file: UploadFile) -> tuple[str, str, int]:
    """
    Saves an uploaded file to disk with a unique UUID filename.
    
    Returns:
        tuple[saved_path, file_ext, file_size]
    """
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    saved_path = os.path.join(UPLOAD_DIR, unique_filename)

    content = await file.read()
    file_size = len(content)

    with open(saved_path, "wb") as f:
        f.write(content)

    return saved_path, file_ext, file_size


def remove_file_from_disk(file_path: str) -> None:
    """Safely removes a file from local disk storage if it exists."""
    if os.path.exists(file_path):
        os.remove(file_path)