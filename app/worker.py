from arq.connections import RedisSettings
from app.database import SessionLocal
from app.models.file import FileAttachment  # adjust model import path if needed
from app.models.enums import OCRStatus      # adjust enum import path if needed
from app.helpers.extractors import extract_text_from_file # adjust extraction import path

async def process_file_ocr(ctx: dict, file_id: int):
    """
    ARQ task handler to run background OCR / text extraction.
    """
    db = SessionLocal()
    try:
        db_file = db.query(FileAttachment).filter(FileAttachment.id == file_id).first()
        if not db_file:
            return

        # Update status to processing
        db_file.ocr_status = OCRStatus.PROCESSING.value
        db.commit()

        # Run extraction (handles standard text PDFs, images, scanned PDFs via Poppler)
        extracted_text = extract_text_from_file(db_file.file_path)

        # Update database with result
        db_file.extracted_text = extracted_text
        db_file.ocr_status = OCRStatus.COMPLETED.value
        db.commit()

    except Exception as exc:
        db.rollback()
        db_file = db.query(FileAttachment).filter(FileAttachment.id == file_id).first()
        if db_file:
            db_file.ocr_status = OCRStatus.FAILED.value
            db.commit()
        raise exc
    finally:
        db.close()


class WorkerSettings:
    functions = [process_file_ocr]
    redis_settings = RedisSettings(host="localhost", port=6379)