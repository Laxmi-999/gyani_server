from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.note import Note
from app.models.user import User
from app.schemas.note import NoteCreate, NoteOut, NoteUpdate
from app.schemas.search import SearchResponse, NoteSearchResult, SearchType
from app.services.embedding import generate_embedding

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


@router.get("/search", response_model=SearchResponse)
def search_notes(
    q: str = Query(..., min_length=1, description="Search query string"),
    type: SearchType = Query(
        SearchType.HYBRID, description="'semantic' for pure vector, 'hybrid' for vector + keyword"
    ),
    limit: int = Query(5, ge=1, le=20, description="Max results to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search notes using either Pure Semantic Search or Hybrid Search (Vector + Full-Text Keyword).
    """
    query_vector = generate_embedding(q)

    # -------------------------------------------------------------
    # OPTION A: PURE SEMANTIC SEARCH
    # -------------------------------------------------------------
    if type == SearchType.SEMANTIC:
        raw_results = (
            db.query(
                Note,
                (1 - Note.embedding.cosine_distance(query_vector)).label("score"),
            )
            .filter(Note.embedding.isnot(None))
            .order_by(Note.embedding.cosine_distance(query_vector))
            .limit(limit)
            .all()
        )

        formatted_results = [
            NoteSearchResult(
                id=note.id,
                title=note.title,
                content=note.content,
                entities=note.entities,
                auto_tags=note.auto_tags,
                score=round(float(score), 4),
            )
            for note, score in raw_results
        ]

    # -------------------------------------------------------------
    # OPTION B: HYBRID SEARCH (Reciprocal Rank Fusion - RRF)
    # -------------------------------------------------------------
    else:
        # Convert list of floats to PostgreSQL vector string format: '[0.12, -0.05, ...]'
        vector_str = f"[{','.join(map(str, query_vector))}]"

        # Combined SQL query running vector distance and full-text keyword search in parallel
        hybrid_sql = text("""
            WITH semantic_search AS (
                SELECT id, RANK() OVER (ORDER BY embedding <=> CAST(:vector AS vector)) AS rank
                FROM notes
                WHERE embedding IS NOT NULL
                LIMIT 20
            ),
            keyword_search AS (
                SELECT id, RANK() OVER (
                    ORDER BY ts_rank_cd(
                        to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(content, '')), 
                        plainto_tsquery('english', :query)
                    ) DESC
                ) AS rank
                FROM notes
                WHERE to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(content, '')) @@ plainto_tsquery('english', :query)
                LIMIT 20
            )
            SELECT 
                n.id, n.title, n.content, n.entities, n.auto_tags,
                (COALESCE(1.0 / (60 + s.rank), 0.0) + COALESCE(1.0 / (60 + k.rank), 0.0)) AS rrf_score
            FROM notes n
            LEFT JOIN semantic_search s ON n.id = s.id
            LEFT JOIN keyword_search k ON n.id = k.id
            WHERE s.id IS NOT NULL OR k.id IS NOT NULL
            ORDER BY rrf_score DESC
            LIMIT :limit;
        """)

        # 3. Pass all 3 parameters in the dictionary
        db_results = db.execute(
            hybrid_sql, 
            {
                "vector": vector_str, 
                "query": q, 
                "limit": limit
            }
        ).fetchall()

        formatted_results = [
            NoteSearchResult(
                id=row.id,
                title=row.title,
                content=row.content,
                entities=row.entities,
                auto_tags=row.auto_tags,
                similarity_score=round(float(row.rrf_score), 4),
            )
            for row in db_results
        ]

    return SearchResponse(
        query=q,
        search_type=type,
        total=len(formatted_results),
        results=formatted_results,
    )



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