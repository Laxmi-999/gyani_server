import logging
from app.database import SessionLocal
from app.helpers.extractors import extract_text_from_file
from app.helpers.nlp import extract_entities_from_text
from app.models.enums import OCRStatus
from app.models.file import FileAttachment
from app.models.note import Note
from arq.connections import RedisSettings
from app.services.embedding import generate_embedding


logger = logging.getLogger(__name__)


def derive_note_title(
    filename: str, entities: dict[str, list[str]]
) -> str:
    """Generates a smart note title based on extracted entities or falls back to the filename."""
    if entities:
        if entities.get("ORG") and len(entities["ORG"]) > 0:
            return f"Document from {entities['ORG'][0]}"
        elif entities.get("PERSON") and len(entities["PERSON"]) > 0:
            return f"Identity / Doc - {entities['PERSON'][0]}"

    # Fallback to cleaned filename
    return f"Doc: {filename}"


async def process_file_ocr(ctx: dict, file_id: int):
    """ARQ task handler to run background OCR / text extraction, entity extraction,

    and automatically generate a unified Note record.
    """
    db = SessionLocal()
    try:
        db_file = (
            db.query(FileAttachment)
            .filter(FileAttachment.id == file_id)
            .first()
        )
        if not db_file:
            logger.warning(
                f"[ARQ Worker] FileAttachment with ID {file_id} not found."
            )
            return

        # 1. Update status to PROCESSING
        db_file.ocr_status = OCRStatus.PROCESSING.value
        db.commit()

        # 2. Perform OCR extraction
        logger.info(
            f"[ARQ Worker] Extracting text from file: {db_file.file_path}"
        )
        extracted_text = extract_text_from_file(db_file.file_path)
        db_file.extracted_text = extracted_text
        

        entities = {}
        flattened_tags = []

        # 3. Perform hybrid NLP entity extraction if text exists
        if extracted_text and extracted_text.strip():
            logger.info(
                f"[ARQ Worker] Running NLP entity extraction for file ID: {file_id}"
            )
            entities = extract_entities_from_text(extracted_text)
            db_file.entities = entities

            # Extract unique string tags from all entity categories
            unique_tags = {
                item.strip()
                for items in entities.values()
                if isinstance(items, list)
                for item in items
                if len(item.strip()) > 1
            }
            flattened_tags = sorted(list(unique_tags))

        # 4. Create or Update corresponding Note record
        title = derive_note_title(db_file.filename, entities)
        note_text_to_embed = f"{title}\n{extracted_text or ''}"
        embedding_vector = generate_embedding(note_text_to_embed)

        # Check if note already exists for this source file to prevent duplicate creation on retries
        existing_note = (
            db.query(Note).filter(Note.source_file_id == db_file.id).first()
        )

        if existing_note:
            existing_note.title = title
            existing_note.content = (
                extracted_text or "No text could be extracted."
            )
            existing_note.entities = entities
            existing_note.auto_tags = flattened_tags
            existing_note.embedding = embedding_vector
            db_file.note_id = existing_note.id
        else:
            new_note = Note(
                owner_id=db_file.owner_id,
                title=title,
                content=extracted_text
                or "No text could be extracted from this document.",
                entities=entities,
                auto_tags=flattened_tags,
                source_file_id=db_file.id,
                embedding = embedding_vector,
            )
            db.add(new_note)
            db.flush()
            db_file.note_id = new_note.id

          

        # 5. Mark job as COMPLETED
        db_file.ocr_status = OCRStatus.COMPLETED.value
        db.commit()

        logger.info(
            f"[ARQ Worker] Successfully processed OCR, NLP & created Note for file ID: {file_id}"
        )

    except Exception as exc:
        db.rollback()
        logger.error(
            f"[ARQ Worker] Processing failed for file ID {file_id}: {exc}"
        )

        db_file = (
            db.query(FileAttachment)
            .filter(FileAttachment.id == file_id)
            .first()
        )
        if db_file:
            db_file.ocr_status = OCRStatus.FAILED.value
            db.commit()

        raise exc

    finally:
        db.close()


class WorkerSettings:
    functions = [process_file_ocr]
    redis_settings = RedisSettings(host="localhost", port=6379)