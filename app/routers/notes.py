from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.note import Note
from app.models.user import User 
from app.schemas.note import NoteCreate, NoteOut, NoteUpdate

router = APIRouter(prefix = "/notes", tags =['notes'])

@router.post("/", response_model=NoteOut, status_code=201)
def create_note(
    note_in : NoteCreate,
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user),
    ):
    note = Note(**note_in.model_dump(), owner_id = current_user.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note

@router.get("/", response_model = list[NoteOut])
def list_notes(
    q:str | None = None,
    db: Session = Depends(get_db),
    current_user:User = Depends(get_current_user)
):
    query = db.query(Note).filter(Note.owner_id == current_user.id)
    if q:
        query = query.filter(Note.content.ilike(f"%{q}%") | Note.title.ilike("f%{q}%"))
        return query.order_by(Note.created_at.desc()).all()

@router.get("/{note_id}", response_model = NoteOut)
def get_note(
    note_id :int,
    db:Session = Depends(get_db),
    current_user : User  = Depends(get_current_user),
):
    return _get_owned_note(db,note_id, current_user.id)

@router.patch("/{note}", response_model = NoteOut)
def update_note(
    note_id: int,
    note_in : NoteUpdate,
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user),
):
    note = _get_owned_note(db, note_id, current_user.id)
    for field, value in note_in.model_dump(exclude_unset = True). items():
        setattr(note, field, value)
        db.commit()
        db.refresh(note)
        return note

@router.delete("/{note_id}", status_code = 204)
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = _get_owned_note(db, note_id, current_user.id)
    db.delete(note)
    db.commit()

def _get_owned_note(db:Session, note_id: int, owner_id: int) -> Note:
    note = db.query(Note).filter(Note.id == note_id, Note.owner_id == owner_id).first()
    if not note:
        raise HTTPException(status_code = 404, detail = "Note Not Found")
    return note


