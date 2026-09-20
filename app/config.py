import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://imagematch:imagematch@db:5432/imagematch")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")  # revisited in Phase 3

# Vision: switched to local Ollama after Gemini's free-tier RPD was cut to
# 20/day across all Flash models (see BUILDLOG.md) — unworkable for a
# 50-image batch. Ollama runs as a docker-compose service, no rate limits,
# no API key, fully offline.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava")

LOW_CONFIDENCE_THRESHOLD = 0.6

VISION_MAX_RETRIES = 3
VISION_RETRY_BACKOFF_SECONDS = 5

# No external rate limit anymore, but a small pause between calls is still
# good practice for a shared local resource (CPU-bound inference).
VISION_CALL_MIN_INTERVAL_SECONDS = 1.0

# Cost tracking: vision calls are now local (Ollama, $0), but we still log
# one cost_log entry per call — the requirement is "cost tracked, per call,
# attributed", not "cost must be nonzero". A $0 line item is still a line
# item; the log proves the tracking exists and would catch a real cost if
# the vision path ever moved back to a paid API.
ESTIMATED_VISION_CALL_COST_MICROS = 0
ESTIMATED_EMBEDDING_CALL_COST_MICROS = 2_000   # ~$0.00002 per embedding call (Gemini, Phase 3)
