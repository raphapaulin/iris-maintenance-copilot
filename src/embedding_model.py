"""Reusable text embedding model."""

from functools import lru_cache

from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


@lru_cache(maxsize=1)
def get_embedding_model():
    """Load the embedding model once per Python process."""
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts):
    embeddings = get_embedding_model().encode(texts, convert_to_numpy=True)
    if embeddings.shape[1] != EMBEDDING_DIMENSION:
        raise RuntimeError(
            f"Expected {EMBEDDING_DIMENSION} dimensions, got {embeddings.shape[1]}"
        )
    return embeddings


def embed_text(text):
    return embed_texts([text])[0]


def vector_to_string(vector):
    """Serialize a vector for IRIS TO_VECTOR through the DB-API driver."""
    if len(vector) != EMBEDDING_DIMENSION:
        raise ValueError(f"Embedding must contain {EMBEDDING_DIMENSION} values")
    return ",".join(str(float(value)) for value in vector)
