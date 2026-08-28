import os
import logging
from sqlalchemy.orm import Session

from app.models.file import FileAttachment, OCRStatus

# IMPORT: Standalone extractor helpers from extractors.py
from app.helpers.extractors import (
    extract_text_from_image,
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_txt,
    extract_text_from_excel,

)

logger = logging.getLogger(__name__)


def process_image_ocr(file_id: int, db_session_factory):
    """Background task to route files to matching text extractors and store results."""
    db: Session = db_session_factory()
    try:
        file_record = db.query(FileAttachment).filter(FileAttachment.id == file_id).first()
        if not file_record or not os.path.exists(file_record.file_path):
            logger.error(f"[Extraction] File record or disk file missing for file_id={file_id}")
            return

        file_record.ocr_status = OCRStatus.PROCESSING.value
        db.commit()

        # Determine file format extension
        ext = os.path.splitext(file_record.filename)[1].lower()
        cleaned_text = ""

        # Router dispatcher targeting helper utilities
        if ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"]:
            cleaned_text = extract_text_from_image(file_record.file_path)

        elif ext == ".pdf":
            cleaned_text = extract_text_from_pdf(file_record.file_path)

        elif ext in [".docx", ".doc"]:
            cleaned_text = extract_text_from_docx(file_record.file_path)

        elif ext in [".txt", ".md", ".csv", ".json"]:
            cleaned_text = extract_text_from_txt(file_record.file_path)
        elif ext in [".xlsx", ".xls"]:
            cleaned_text = extract_text_from_excel(file_record.file_path)

        logger.info(f"[Extraction Complete] file_id={file_id}. Extracted length: {len(cleaned_text)}")

        file_record.extracted_text = cleaned_text if cleaned_text else "No extractable text found."
        file_record.ocr_status = OCRStatus.COMPLETED.value
        db.commit()

    except Exception as e:
        logger.exception(f"[Extraction Error] Failed processing file_id={file_id}: {str(e)}")
        db.rollback()
        file_record = db.query(FileAttachment).filter(FileAttachment.id == file_id).first()
        if file_record:
            file_record.ocr_status = OCRStatus.FAILED.value
            db.commit()
    finally:
        db.close()