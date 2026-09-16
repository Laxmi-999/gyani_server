from sqlalchemy import text
from sqlalchemy.orm import Session
from app.services.embedding import generate_embedding


def perform_hybrid_search(db: Session, query_text: str, owner_id: int, limit: int = 5):
    """Executes SQL-level Reciprocal Rank Fusion (RRF) search across vector embeddings and keywords."""
    query_vector = generate_embedding(query_text)
    vector_str = f"[{','.join(map(str, query_vector))}]"

    hybrid_sql = text("""
        WITH semantic_search AS (
            SELECT id, RANK() OVER (ORDER BY embedding <=> CAST(:vector AS vector)) AS rank
            FROM notes
            WHERE embedding IS NOT NULL AND owner_id = :owner_id
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
              AND owner_id = :owner_id
            LIMIT 20
        )
        SELECT
            n.id, n.title, n.content, n.entities, n.auto_tags,
            (COALESCE(1.0 / (60 + s.rank), 0.0) + COALESCE(1.0 / (60 + k.rank), 0.0)) AS rrf_score
        FROM notes n
        LEFT JOIN semantic_search s ON n.id = s.id
        LEFT JOIN keyword_search k ON n.id = k.id
        WHERE (s.id IS NOT NULL OR k.id IS NOT NULL) AND n.owner_id = :owner_id
        ORDER BY rrf_score DESC
        LIMIT :limit;
    """)

    return db.execute(
        hybrid_sql,
        {
            "vector": vector_str,
            "query": query_text,
            "owner_id": owner_id,
            "limit": limit,
        },
    ).fetchall()