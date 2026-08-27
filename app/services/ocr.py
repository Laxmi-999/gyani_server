import os
import logging
from PIL import Image
import pytesseract
from sqlalchemy.orm import Session

from app.models.file import FileAttachment, OCRStatus

logger = logging.getLogger(__name__)

# Optional: If running on Windows or non-standard PATH, explicitly set tesseract executable path here:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def process_image_ocr(file_id: int, db_session_factory):
    db: Session = db_session_factory()
    try:
        file_record = db.query(FileAttachment).filter(FileAttachment.id == file_id).first()
        if not file_record or not os.path.exists(file_record.file_path):
            logger.error(f"[OCR] File record or disk file missing for file_id={file_id}")
            return

        file_record.ocr_status = OCRStatus.PROCESSING.value
        db.commit()

        # Run OCR using Pillow and pytesseract
        image = Image.open(file_record.file_path)
        raw_text = pytesseract.image_to_string(image)
        cleaned_text = raw_text.strip() if raw_text else ""

        logger.info(f"[OCR] Processed file_id={file_id}. Extracted length: {len(cleaned_text)}")

        # Store empty string or actual text, avoiding unexpected NULL conversion
        file_record.extracted_text = cleaned_text if cleaned_text else "No text found in image."
        file_record.ocr_status = OCRStatus.COMPLETED.value
        db.commit()

    except Exception as e:
        logger.exception(f"[OCR Error] Failed processing file_id={file_id}: {str(e)}")
        db.rollback()
        file_record = db.query(FileAttachment).filter(FileAttachment.id == file_id).first()
        if file_record:
            file_record.ocr_status = OCRStatus.FAILED.value
            db.commit()
    finally:
        db.close()