import json
import logging
import os
from fastapi import APIRouter, Depends, HTTPException, Query, status
from openai import OpenAI
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.core.deps import get_current_user
from app.database import get_db
from app.helpers.perform_hybrid_search import perform_hybrid_search
from app.models.note import Note
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, SourceNote
from app.schemas.note import NoteCreate, NoteOut, NoteUpdate
from app.schemas.search import NoteSearchResult, SearchResponse, SearchType
from app.services.embedding import generate_embedding
from app.config import settings
from app.helpers.perform_hybrid_search import perform_hybrid_search
from app.helpers.query_expansion import expand_query_variants, merge_search_results
from app.helpers.context_truncation import truncate_content
from app.helpers.query_expansion import expand_query_variants, merge_search_results, strip_language_directive

logger = logging.getLogger(__name__)

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
    # -------------------------------------------------------------
    # OPTION A: PURE SEMANTIC SEARCH
    # -------------------------------------------------------------
    if type == SearchType.SEMANTIC:
        query_vector = generate_embedding(q)
        raw_results = (
            db.query(
                Note,
                (1 - Note.embedding.cosine_distance(query_vector)).label("score"),
            )
            .filter(
                Note.embedding.isnot(None),
                Note.owner_id == current_user.id,
            )
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
                similarity_score=round(float(score), 4),
            )
            for note, score in raw_results
        ]

    # -------------------------------------------------------------
    # OPTION B: HYBRID SEARCH (Reciprocal Rank Fusion - RRF)
    # -------------------------------------------------------------
    else:
        db_results = perform_hybrid_search(
            db=db,
            query_text=q,
            owner_id=current_user.id,
            limit=limit,
        )

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



@router.post("/chat", response_model=ChatResponse)
def chat_with_notes(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    RAG Endpoint: Expands the question into alternate phrasings for cross-language
    retrieval, searches with all variants, constructs an anti-hallucination prompt,
    and calls a Groq-hosted model.
    """
    question_text = request.question.strip()
    if not question_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )

    # 1. Set up the LLM client early — needed for both query expansion and the final answer
    api_key = settings.groq_api_key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GROQ_API_KEY environment variable is not set."
        )

    llm_client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
    )
    target_model = "openai/gpt-oss-20b"


    search_question = strip_language_directive(question_text)
    if search_question != question_text:
        logger.info(f"[RAG Chat] Stripped language directive for search: {search_question!r}")

    # 3. Expand the search-safe question into alternate phrasings
    query_variants = expand_query_variants(llm_client, target_model, search_question)
    all_queries = [search_question] + query_variants
    logger.info(f"[RAG Chat] Searching with query variants: {all_queries}")

    # 4. Run hybrid search for every variant, then merge and de-duplicate results
    result_sets = [
        perform_hybrid_search(db=db, query_text=q, owner_id=current_user.id, limit=5)
        for q in all_queries
    ]
    search_rows = merge_search_results(result_sets)[:5]
    logger.info(
        f"[RAG Chat] Retrieved {len(search_rows)} notes: "
        f"{[(r.id, r.title, round(float(r.rrf_score), 4)) for r in search_rows]}"
    )

    # 4. Handle no-relevant-notes case explicitly
    if not search_rows:
        return ChatResponse(
            answer="I couldn't find any relevant notes to answer your question.",
            sources=[]
        )

    # 5. Build context blocks and sources list (with per-note truncation)
    context_blocks = []
    sources = []
    for row in search_rows:
        truncated = truncate_content(row.content or "")
        context_blocks.append(f"--- Note ID: {row.id} | Title: {row.title} ---\n{truncated}")
        sources.append(SourceNote(id=row.id, title=row.title))

    combined_context = "\n\n".join(context_blocks)

    # 6. Construct anti-hallucination prompt with explicit language rules
    system_prompt = (
        "You are a helpful assistant. Answer the user's question ONLY using the provided retrieved notes context. "
        "If the answer cannot be found in the provided notes, clearly state: 'I could not find the answer in your notes.' "
        "Do not use external knowledge or fabricate information outside of this context.\n\n"
        "Language rules for your response:\n"
        "1. If the user explicitly asks for the answer in a specific language, always follow that instruction.\n"
        "2. Otherwise, if the user's question itself is written in a non-English script (e.g. Devanagari, Cyrillic), "
        "respond in that same language.\n"
        "3. Otherwise — including romanized/Latin-script versions of another language, or genuinely ambiguous "
        "cases — respond in English by default."
    )

    user_prompt = f"""CONTEXT NOTES:
{combined_context}

USER QUESTION:
{question_text}
"""

    # 7. Generate the answer
    try:
        response = llm_client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"[RAG Chat Error]: {e}")
        if "reduce the length" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your question matched notes with too much content to process at once. Try a more specific question."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate an answer from the intelligence engine."
        )

    # 8. Return the answer with its sources
    return ChatResponse(answer=answer, sources=sources)



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