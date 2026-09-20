import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://imagematch:imagematch@db:5432/imagematch")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # unused for now, kept in case we revisit

# Vision AND embeddings both run on local Ollama now — after today's Gemini
# free-tier chaos (see BUILDLOG.md), staying local avoids a second round of
# rate-limit surprises for the embeddings step.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

LOW_CONFIDENCE_THRESHOLD = 0.6

VISION_MAX_RETRIES = 3
VISION_RETRY_BACKOFF_SECONDS = 5

# No external rate limit anymore, but a small pause between calls is still
# good practice for a shared local resource (CPU-bound inference).
VISION_CALL_MIN_INTERVAL_SECONDS = 1.0

# Mismatch guard: similarity cutoff below which a match is refused outright
# (tuned properly against the labeled eval set in Phase 4 — this is a
# reasonable starting point for cosine similarity on caption embeddings).
SIMILARITY_THRESHOLD = 0.55

# Animal-category keyword map for the guard's category/subject check.
# Deliberately simple and transparent for this capstone's small, fixed
# domain (5 animal categories) — includes scientific names so "Vulpes
# vulpes" in a post matches an image tagged "fox".
CATEGORY_KEYWORDS = {
    "fox": ["fox", "foxes", "vulpes"],
    "wolf": ["wolf", "wolves", "canis lupus"],
    "dog": ["dog", "dogs", "canine", "retriever", "puppy"],
    "bear": ["bear", "bears", "ursus"],
    "deer": ["deer", "stag", "doe", "buck", "cervidae"],
}

# Cost tracking: vision calls are now local (Ollama, $0), but we still log
# one cost_log entry per call — the requirement is "cost tracked, per call,
# attributed", not "cost must be nonzero". A $0 line item is still a line
# item; the log proves the tracking exists and would catch a real cost if
# the vision path ever moved back to a paid API.
ESTIMATED_VISION_CALL_COST_MICROS = 0
ESTIMATED_EMBEDDING_CALL_COST_MICROS = 2_000   # ~$0.00002 per embedding call (Gemini, Phase 3)
