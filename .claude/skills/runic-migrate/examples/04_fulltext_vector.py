"""add fulltext and vector indexes for search

Revision ID: d4e5f6789abc
Revises: c3d4e5f67890
Create Date: 2026-05-30T17:00:00+00:00
"""
from datetime import datetime

message = "add fulltext and vector indexes for search"
create_date = datetime.fromisoformat("2026-05-30T17:00:00+00:00")

revision = "d4e5f6789abc"
down_revision = "c3d4e5f67890"
branch_labels = []
depends_on = []
irreversible = False
snapshot = False


def upgrade(op) -> None:
    # Full-text index over multiple properties
    op.create_fulltext_index("Post", "title", "body")
    op.create_fulltext_index(
        "Article", "title",
        language="german",
        stopwords=["der", "die", "das", "und"],
    )

    # Vector index (HNSW) for semantic search
    # similarity: "cosine" | "euclidean"
    op.create_vector_index("Product", "embedding", dimension=256, similarity="cosine")
    op.create_vector_index(
        "Document", "vec",
        dimension=1536,
        similarity="cosine",
        m=32,
        ef_construction=400,
        ef_runtime=20,
    )


def downgrade(op) -> None:
    op.drop_vector_index("Document", "vec")
    op.drop_vector_index("Product", "embedding")
    op.drop_fulltext_index("Article", "title")
    op.drop_fulltext_index("Post", "title", "body")
