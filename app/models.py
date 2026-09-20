import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.database import Base


def uuid_pk():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def now_utc():
    return datetime.now(timezone.utc)


class Image(Base):
    __tablename__ = "images"

    id = uuid_pk()
    filename = Column(String, nullable=False, unique=True)
    source_category = Column(String, nullable=False)  # ground truth from manifest

    subject = Column(String, nullable=True)            # from vision model
    category = Column(String, nullable=True)
    attributes = Column(ARRAY(String), nullable=True)
    caption = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    flagged_low_confidence = Column(Boolean, default=False)

    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    embedding = relationship("ImageEmbedding", back_populates="image", uselist=False)


class ImageEmbedding(Base):
    __tablename__ = "image_embeddings"

    id = uuid_pk()
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id"), nullable=False, unique=True)
    embedding = Column(ARRAY(Float), nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    image = relationship("Image", back_populates="embedding")


class Post(Base):
    __tablename__ = "posts"

    id = uuid_pk()
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    embedding = relationship("PostEmbedding", back_populates="post", uselist=False)


class PostEmbedding(Base):
    __tablename__ = "post_embeddings"

    id = uuid_pk()
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False, unique=True)
    embedding = Column(ARRAY(Float), nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    post = relationship("Post", back_populates="embedding")


class Suggestion(Base):
    __tablename__ = "suggestions"

    id = uuid_pk()
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id"), nullable=True)  # null = no match

    similarity_score = Column(Float, nullable=True)
    guard_verdict = Column(String, nullable=False)   # approved | rejected | no_match
    explanation = Column(Text, nullable=False)
    review_status = Column(String, nullable=False, default="pending")  # pending|approved|rejected

    created_at = Column(DateTime(timezone=True), default=now_utc)


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = uuid_pk()
    job_type = Column(String, nullable=False)   # vision_tagging | embedding
    status = Column(String, nullable=False, default="pending")  # pending|running|completed|failed
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class CostLogEntry(Base):
    __tablename__ = "cost_log"

    id = uuid_pk()
    call_type = Column(String, nullable=False)     # vision | embedding
    reference_id = Column(UUID(as_uuid=True), nullable=True)  # image_id or post_id
    estimated_cost_micros = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)
