import uuid
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ImageTagResult(BaseModel):
    """The vision model's structured output. Used both as the Gemini
    response_schema (constrains generation) AND re-validated on the
    response text with model_validate_json() — constrained generation can
    still occasionally emit something malformed; we never skip the second
    check just because the first one exists."""
    subject: str
    category: str
    attributes: List[str] = Field(default_factory=list)
    caption: str
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("subject", "category", "caption")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be blank")
        return v

    @field_validator("subject", "category", "caption", "attributes")
    @classmethod
    def not_placeholder_echo(cls, v):
        """Caught a real failure mode in practice: the vision model
        sometimes echoes the prompt's own instructional wording back
        verbatim instead of describing the image (e.g. subject: "the
        specific thing shown, e.g. dog"). Syntactically valid JSON, but
        semantically worthless -- reject it like any other invalid
        response so it gets retried instead of silently stored."""
        text = " ".join(v) if isinstance(v, list) else str(v)
        suspicious = ["e.g.", "the specific thing shown", "short descriptive tags", "general category"]
        if any(s in text.lower() for s in suspicious):
            raise ValueError(f"looks like echoed prompt template, not a real description: {text!r}")
        return v


class JobStatusResponse(BaseModel):
    id: uuid.UUID
    job_type: str
    status: str
    total_items: int
    processed_items: int
    failed_items: int


class TriggerJobResponse(BaseModel):
    job_id: uuid.UUID
    message: str


class PostCreate(BaseModel):
    title: str
    content: str

    @field_validator("title", "content")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be blank")
        return v


class PostResponse(BaseModel):
    id: uuid.UUID
    title: str
    content: str


class SuggestionResponse(BaseModel):
    post_id: uuid.UUID
    image_id: Optional[uuid.UUID]
    image_filename: Optional[str] = None
    similarity_score: Optional[float]
    guard_verdict: str
    explanation: str
