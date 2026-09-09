from app.db.session  import SessionLocal
from app.models.note import Note 
from app.services.embedding import generate_embedding

def run_test():
    db = SessionLocal()
    search-query = "how do i protect my endpoints"
    print(f"\n --- Generating embedding for query : '{search_query}' ---")
    query_vector = generate_embedding(search_query)

    # Perform cosine distance ordering using pgvector operator (<=>)
    # distance = 0 means identical, distance closer to 0 means higher similarity
    results = (
        db.query(
            Note.id,
            Note.title,
            Note.content,
            Note.embedding.cosine_distance(query_vector).label("distance")
        )
        .filter(Note.embedding.isnot(None))
        .order_by("distance")
        .limit(5)
        .all()
    )

    print(f"\nTop {len(results)} semantic Match(es):")
    for row in results:
        similarity_score = round(1-row.distance, 4) #Convert distance to similiarity score
        print(f"ID: {row.id} | Score: {similarity_score} | Title: {row.title}")
        print(f"Content snippet:{row.content[:100]}...")

    db.close()

if __name__ == "__main__":
    run_test()