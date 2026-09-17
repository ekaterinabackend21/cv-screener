from functools import lru_cache

from sentence_transformers import SentenceTransformer

from settings import Settings


@lru_cache(maxsize=4)
def load_embedding_model(model_name: str) -> SentenceTransformer:
    """Load and cache one sentence-transformers model by its configured name."""
    return SentenceTransformer(model_name)


def embed_text(text: str, *, settings: Settings) -> list[float]:
    """Encode text into a normalized vector compatible with the Elasticsearch mapping."""
    if not text.strip():
        raise ValueError("Cannot embed empty text.")
    model = load_embedding_model(settings.embedding_model)
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()
