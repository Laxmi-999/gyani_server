from arq.connections import RedisSettings
from app.database import SessionLocal
from app.models.file import FileAttachment
from app.models.enums import OCRStatus     
from app.helpers.extractors import extract_text_from_file 
from app.helpers.nlp import extract_entities_from_text


async def process_file_ocr(ctx: dict, file_id: int):
    """
    ARQ task handler to run background OCR / text extraction.
    """
    db = SessionLocal()
    try:
        db_file = db.query(FileAttachment).filter(FileAttachment.id == file_id).first()
        if not db_file:
            return

        db_file.ocr_status = OCRStatus.PROCESSING.value
        db.commit()

        # Step 1: perform OCR extraction
        extracted_text = extract_text_from_file(db_file.file_path)
        db.file.extracted_text = extracted_text

        #  Perform LLM entity extraction if text exists
        if extracted_text and extracted_text.strip():
            # Automatically routes English/Spanish/French to cached spaCy,
            # and other languages (e.g. Nepali) to Groq Llama 3.3
            entities = extract_entities_from_text(extracted_text)
            db.file.entities = entities

        # MARK JOB AS COMPLETED
        db_file.ocr_status = OCRStatus.COMPLETED.value
        db.commit()

    except Exception as exc:
        db.rollback()
        db_file = (
            db.query(FileAttachment)
            .filter(FileAttachment.id == file_id)
            .first()
         )

        if db_file:
            db_file.ocr_Status = OCRStatus.FAILED.value
            db.commit()
        raise exc
    finally:
        db.close()




class WorkerSettings:
    functions = [process_file_ocr]
    redis_settings = RedisSettings(host="localhost", port=6379)