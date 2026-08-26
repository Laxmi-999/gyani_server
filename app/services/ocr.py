from PIL import Image
import pytesseract
import os 
from sqlalchemy.orm import Session

from app.models.file import FileAttachment,OCRStatus

def process_image_ocr(file_id:int, db_session_factory):
    db:Session = db_session_factory()
    try:
        file_record = db.query(FileAttachment).filter(FileAttachment.id == file_id).first()
        if not file_record or not os.path.exists(file_record.file_path):
            return

        file_record.ocr_status = OCRStatus.PROCESSING.value
        db.commit()

        # Run OCR using Pillow and pytesseract
        image = Image.open(file_record.file_path)
        raw_text = pytesseract.image_to_string(image)

        file_record.extracted_text = raw_text.strip()
        file_record.ocr_status = OCRStatus.COMPLETED.value
        db.commit()
    except Exception as e :
        db.rollback()
        file_record = db.query(FileAttachment).filter(FileAttachment.id == file_id).first()
        if file_record:
            file_record.ocr_status = OCRStatus.FAILED.value
            db.commit()
    finally:
        db.close()

