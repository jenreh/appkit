"""Mapping: defining Node and Edge models with runic.ogm.

Covers field declaration styles, primary keys, indexes/constraints, defaults,
and the basic create/read/update/delete cycle that proves a model is wired up.

Run against embedded FalkorDB (no server needed):
    uv run python skill/runic/examples/mapping.py
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import StrEnum

from redislite import FalkorDB
from runic.ogm import Edge, Field, Node, Session
from runic.ogm.driver.falkordb import FalkorDBDriver

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


class Status(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class Article(Node, labels=["Article"]):
    """A node. `labels` is the graph label list applied to the vertex."""

    # Explicit primary key — the clearest way to declare one.
    id: str = Field(primary_key=True)

    # Bare annotation → a required Field. Use this style when no options needed.
    title: str

    # Optional annotation → defaults to None automatically.
    summary: str | None = None

    # Field() options: uniqueness constraint + range index declarations.
    slug: str = Field(unique=True)
    category: str = Field(index=True)

    # default / default_factory.
    views: int = Field(default=0)
    tags: list[str] = Field(default_factory=list)

    # Enum and datetime get their TypeConverter assigned automatically —
    # no converter= needed.
    status: Status = Field(default=Status.DRAFT)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Authored(Edge, type="AUTHORED"):
    """An edge property model. `type` is the relationship type in the graph."""

    at: datetime
    primary: bool = Field(default=False)


def main() -> None:
    db = FalkorDB(protocol=2)
    driver = FalkorDBDriver(db.select_graph("mapping_demo"))

    # CREATE — constructors are keyword-only.
    with Session(driver) as session:
        session.add_all(
            [
                Article(
                    id="a1",
                    title="Intro to Graphs",
                    slug="intro-to-graphs",
                    category="database",
                    status=Status.PUBLISHED,
                ),
                Article(
                    id="a2",
                    title="Cypher Tips",
                    slug="cypher-tips",
                    category="database",
                    tags=["cypher", "tips"],
                ),
            ]
        )
        session.commit()

    # READ by primary key.
    with Session(driver) as session:
        a1 = session.get(Article, "a1")
        assert a1 is not None
        log.info("Loaded %s — status=%s views=%s", a1.title, a1.status, a1.views)
        assert a1.status is Status.PUBLISHED  # enum round-trips as the enum member

    # UPDATE — mutating a loaded entity marks it dirty; commit() emits the SET.
    with Session(driver) as session:
        a1 = session.get(Article, "a1")
        assert a1 is not None
        a1.views += 1
        session.commit()
        log.info("Bumped views to %s", a1.views)

    # DELETE.
    with Session(driver) as session:
        a2 = session.get(Article, "a2")
        assert a2 is not None
        session.delete(a2)
        session.commit()
        log.info("Deleted a2; remaining=%s", session.get(Article, "a2"))

    driver.close()


if __name__ == "__main__":
    main()
