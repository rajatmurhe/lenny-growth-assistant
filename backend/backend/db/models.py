from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Float, JSON, Date, UniqueConstraint
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from pgvector.sqlalchemy import Vector
import uuid
from datetime import datetime

Base = declarative_base()

class Session(Base):
    __tablename__ = "sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=True)
    provider = Column(String, default="ollama")
    model = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    role = Column(String)
    content = Column(Text)
    citations = Column(JSONB, nullable=True)
    skill_used = Column(String, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    token_counts = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Episode(Base):
    __tablename__ = "episodes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String, unique=True)
    title = Column(String)
    guest = Column(String, nullable=True)
    published_at = Column(Date, nullable=True)
    source_path = Column(String)
    content_hash = Column(String)
    post_url = Column(String, nullable=True)
    word_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    episode_id = Column(UUID(as_uuid=True), ForeignKey("episodes.id"))
    ordinal = Column(Integer)
    text = Column(Text)
    token_count = Column(Integer)
    embedding = Column(Vector(768))
    tsv = Column(TSVECTOR)
    embed_model = Column(String)
    speaker = Column(String, nullable=True)
    chunk_start_time = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RetrievalEvent(Base):
    __tablename__ = "retrieval_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"))
    query_used = Column(Text)
    chunk_ids = Column(JSONB)
    scores = Column(JSONB)
    retrieval_method = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Artifact(Base):
    __tablename__ = "artifacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)
    type = Column(String)
    title = Column(String)
    content = Column(Text)
    sanitized_content = Column(Text)
    version = Column(Integer, default=1)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("artifacts.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    episodes_processed = Column(Integer, default=0)
    chunks_created = Column(Integer, default=0)
    status = Column(String)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
