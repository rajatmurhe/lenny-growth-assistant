"""Initial migration: create all tables with pgvector and FTS indexes.

Revision ID: 001_initial
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # sessions table
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=False, server_default="ollama"),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # episodes table
    op.create_table(
        "episodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("guest", sa.String(), nullable=True),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("source_path", sa.String(), nullable=True),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("post_url", sa.String(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # chunks table with vector column and tsvector
    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("embedding", sa.Text(), nullable=True),  # stored as vector type via raw SQL below
        sa.Column("tsv", postgresql.TSVECTOR(), nullable=True),
        sa.Column("embed_model", sa.String(), nullable=True),
        sa.Column("speaker", sa.String(), nullable=True),
        sa.Column("chunk_start_time", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Alter embedding column to use proper vector type
    op.execute("ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(768) USING NULL::vector(768)")

    # Create ivfflat index for approximate nearest neighbor search on embeddings
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # Create GIN index on tsvector for full-text search
    op.create_index("idx_chunks_tsv", "chunks", ["tsv"], postgresql_using="gin")

    # Create index on episode_id for chunk lookups
    op.create_index("idx_chunks_episode_id", "chunks", ["episode_id"])

    # messages table
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("citations", postgresql.JSONB(), nullable=True),
        sa.Column("skill_used", sa.String(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("token_counts", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_messages_session_id", "messages", ["session_id"])

    # retrieval_events table
    op.create_table(
        "retrieval_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=True),
        sa.Column("query_used", sa.Text(), nullable=True),
        sa.Column("chunk_ids", postgresql.JSONB(), nullable=True),
        sa.Column("scores", postgresql.JSONB(), nullable=True),
        sa.Column("retrieval_method", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # artifacts table
    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(), nullable=False, server_default="markdown"),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("sanitized_content", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ingestion_runs table
    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("episodes_processed", sa.Integer(), server_default="0"),
        sa.Column("chunks_created", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(), nullable=False, server_default="running"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("ingestion_runs")
    op.drop_table("artifacts")
    op.drop_table("retrieval_events")
    op.drop_index("idx_messages_session_id")
    op.drop_table("messages")
    op.drop_index("idx_chunks_episode_id")
    op.drop_index("idx_chunks_tsv")
    op.execute("DROP INDEX IF EXISTS idx_chunks_embedding")
    op.drop_table("chunks")
    op.drop_table("episodes")
    op.drop_table("sessions")
