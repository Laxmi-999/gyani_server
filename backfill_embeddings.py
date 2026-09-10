from app.database import SessionLocal
from app.models.note import Note
from app.services.embedding import generate_embedding
from app.models.user import User
from app.models.file import FileAttachment
from app.models.note import Note


def run_backfill():
    db = SessionLocal()
    try:
        # Fetch all notes that do not have an embedding yet
        notes_to_update = (
            db.query(Note).filter(Note.embedding.is_(None)).all()
        )

        total_notes = len(notes_to_update)
        print(f"\n--- Found {total_notes} note(s) needing vector embeddings ---")

        if total_notes == 0:
            print("All notes already have embeddings! Nothing to backfill.")
            return

        for index, note in enumerate(notes_to_update, start=1):
            # Combine title and content for rich context embedding
            text_to_embed = f"{note.title or ''}\n{note.content or ''}"

            if not text_to_embed.strip():
                print(f"[{index}/{total_notes}] Skipping Note ID {note.id} (empty content)")
                continue

            print(f"[{index}/{total_notes}] Generating embedding for Note ID {note.id}: '{note.title}'")
            vector = generate_embedding(text_to_embed)
            note.embedding = vector

            # Commit periodically in batches of 20 or on last item
            if index % 20 == 0 or index == total_notes:
                db.commit()
                print(f"--> Saved batch up to item {index}/{total_notes}")

        print("\n✅ Backfill completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Backfill failed due to error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    run_backfill()