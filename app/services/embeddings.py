import time
import requests
from typing import List

from app.config import OLLAMA_BASE_URL, OLLAMA_EMBEDDING_MODEL

EMBED_MAX_RETRIES = 3
EMBED_RETRY_BACKOFF_SECONDS = 2


class EmbeddingCallFailed(Exception):
    pass


def embed_text(text: str) -> List[float]:
    """Embeds a piece of text (an image caption, or a post's title+content)
    into a vector via Ollama's local embedding model. Raises
    EmbeddingCallFailed if every retry fails — never returns a zero-vector
    or other silent fallback, since that would corrupt every downstream
    similarity score without any visible sign of failure."""
    last_error = None
    for attempt in range(1, EMBED_MAX_RETRIES + 1):
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={"model": OLLAMA_EMBEDDING_MODEL, "prompt": text},
                timeout=60,
            )
            response.raise_for_status()
            embedding = response.json().get("embedding")
            if not embedding or not isinstance(embedding, list):
                raise ValueError(f"no embedding in response: {response.text[:200]}")
            return embedding
        except (requests.RequestException, ValueError) as e:
            last_error = e
            if attempt < EMBED_MAX_RETRIES:
                time.sleep(EMBED_RETRY_BACKOFF_SECONDS * attempt)
            continue

    raise EmbeddingCallFailed(f"Failed after {EMBED_MAX_RETRIES} attempts: {last_error}")
