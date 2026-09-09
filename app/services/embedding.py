import logging 
from sentence_transformers import SentenceTransformer


logger = logging.getLogger(__name__)
# Load model globally in module import so it stays warm in memory
MODEL_NAME = "all-MiniLM-L6-v2"
logger.infor(f"Loading embedding model: {MODEL_NAME}")
model = SentenceTransformer(MODEL_NAME)

def generate_embedding(text:str) -> list[float]:
    """Converts a block  of text into a 384-dimensional vector array."""
    if not text or not text.strip():
        return[]

    # encode() returns a numpy array; convert to list for pgvector/SQLALchemy compatibitlity
    embedding = model.encode(text.strip(), convert_to_numpy=True)
    return embedding.tolist()