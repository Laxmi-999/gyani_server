import logging 
from sentence_transformers import SentenceTransformer


logger = logging.getLogger(__name__)
# Load model globally in module import so it stays warm in memory
MODEL_NAME = "all-MiniLM-L6-v2"
logger.info(f"Loading embedding model: {MODEL_NAME}")
model = SentenceTransformer(MODEL_NAME)
_model_instance = None

def get_embedding_model()->SentenceTransformer:
    global _model_instance
    if _model_instance is None:
        logger.info(f"[ML Model] Loading Sentence-transformers {MODEL_NAME} into RAM....")
        _model_instance = SentenceTransformer(MODEL_NAME)
    return _model_instance

def generate_embedding(text:str) -> list[float]:
    """Converts a block  of text into a 384-dimensional vector array."""
    if not text or not text.strip():
        return[]

    # encode() returns a numpy array; convert to list for pgvector/SQLALchemy compatibitlity
    embedding = model.encode(text.strip(), convert_to_numpy=True)
    return embedding.tolist()