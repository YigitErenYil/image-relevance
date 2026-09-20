import time
import base64
import json
import requests
from pathlib import Path
from pydantic import ValidationError

from app.config import (
    OLLAMA_BASE_URL, OLLAMA_VISION_MODEL,
    VISION_MAX_RETRIES, VISION_RETRY_BACKOFF_SECONDS,
    LOW_CONFIDENCE_THRESHOLD,
)
from app.schemas import ImageTagResult

PROMPT = """Look at this image and identify its main subject, then output
real JSON describing what you actually SEE -- never copy example wording.

Required JSON fields:
- subject (string): the specific thing shown, as specific as possible
- category (string): a general category for the subject
- attributes (array of 3-5 short strings): concrete visual details you observe
- caption (string): one plain sentence describing what is actually in THIS image
- confidence (number 0.0-1.0): your honest certainty in the subject identification

Example of the SHAPE only -- this is an unrelated image, do not reuse any of
these words, describe the image you were actually given:
{"subject": "bicycle", "category": "vehicle", "attributes": ["red frame", "two wheels", "parked"], "caption": "A red bicycle parked against a brick wall.", "confidence": 0.9}

Use a LOWER confidence when the image is blurry, ambiguous, partially
obscured, or could plausibly be more than one species/subject. Do not
default to a high number -- an honest 0.4 is more useful than an
overconfident 0.9. Respond with ONLY the JSON object, nothing else."""


class VisionCallFailed(Exception):
    pass


def _call_ollama(image_bytes: bytes) -> str:
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={
            "model": OLLAMA_VISION_MODEL,
            "prompt": PROMPT,
            "images": [image_b64],
            "format": "json",   # constrains to valid JSON -- not our exact schema
            "stream": False,
        },
        timeout=120,  # local vision inference on CPU can be slow
    )
    response.raise_for_status()
    return response.json()["response"]


def classify_image(image_path: Path) -> ImageTagResult:
    """Classifies one image with retries. Raises VisionCallFailed if every
    attempt fails (HTTP error OR schema validation failure -- an invalid
    response is treated exactly like a failed call, never silently
    accepted). Never returns a guessed/default result."""
    image_bytes = image_path.read_bytes()

    last_error = None
    for attempt in range(1, VISION_MAX_RETRIES + 1):
        try:
            raw_text = _call_ollama(image_bytes)
            # Ollama's format="json" only guarantees SOME valid JSON, not
            # our specific schema -- this re-validation is not optional here.
            result = ImageTagResult.model_validate_json(raw_text)
            return result
        except (ValidationError, ValueError, json.JSONDecodeError, requests.RequestException) as e:
            last_error = e
            if attempt < VISION_MAX_RETRIES:
                time.sleep(VISION_RETRY_BACKOFF_SECONDS * attempt)
            continue

    raise VisionCallFailed(
        f"Failed after {VISION_MAX_RETRIES} attempts for {image_path.name}: {last_error}"
    )


def is_low_confidence(result: ImageTagResult) -> bool:
    return result.confidence < LOW_CONFIDENCE_THRESHOLD
