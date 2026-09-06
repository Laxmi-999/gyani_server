from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.note import Note
from app.models.user import User
from app.schemas.note import NoteCreate, NoteOut, NoteUpdate

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("/", response_model=NoteOut, status_code=201)
def create_note(
    note_in: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = Note(**note_in.model_dump(), owner_id=current_user.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/", response_model=list[NoteOut])
def list_notes(
    q: str | None = None,
    tag: str | None = Query(
        None, description="Filter by extracted entity tag"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Note).filter(Note.owner_id == current_user.id)

    # 1. Filter by specific entity tag or user tag
    if tag:
        query = query.filter(
            or_(
                Note.tags.ilike(f"%{tag}%"),
                func.json_extract_path_text(Note.auto_tags).ilike(f"%{tag}%"),
            )
        )

    # 2. General search query (title, content, tags)
    if q:
        query = query.filter(
            or_(
                Note.title.ilike(f"%{q}%"),
                Note.content.ilike(f"%{q}%"),
                Note.tags.ilike(f"%{q}%"),
                func.json_extract_path_text(Note.auto_tags).ilike(f"%{q}%"),
            )
        )

    return query.order_by(Note.created_at.desc()).all()


@router.get("/tags/summary")
def get_tags_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns distinct entities aggregated by category for user notes."""
    notes = db.query(Note.entities).filter(Note.owner_id == current_user.id).all()

    summary: dict[str, set[str]] = {
        "PERSON": set(),
        "GPE": set(),
        "ORG": set(),
        "MONEY": set(),
        "DATE": set(),
    }

    for (ent_dict,) in notes:
        if isinstance(ent_dict, dict):
            for cat, items in ent_dict.items():
                if cat in summary and isinstance(items, list):
                    summary[cat].update(items)

    return {cat: sorted(list(val)) for cat, val in summary.items()}


@router.get("/{note_id}", response_model=NoteOut)
def get_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_note(db, note_id, current_user.id)


@router.patch("/{note_id}", response_model=NoteOut)
def update_note(
    note_id: int,
    note_in: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = _get_owned_note(db, note_id, current_user.id)
    for field, value in note_in.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=204)
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = _get_owned_note(db, note_id, current_user.id)
    db.delete(note)
    db.commit()


def _get_owned_note(db: Session, note_id: int, owner_id: int) -> Note:
    note = (
        db.query(Note)
        .filter(Note.id == note_id, Note.owner_id == owner_id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note Not Found")
    return note