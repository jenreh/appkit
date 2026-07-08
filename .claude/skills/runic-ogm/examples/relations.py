"""Relations: declaring and traversing relationships with runic.ogm.

Covers Relation() declaration (single, collection, edge model, directions),
lazy vs eager loading, relate()/unrelate() mutation, and reading edge
properties with all_with_edges().

Run against embedded FalkorDB (no server needed):
    uv run python skill/runic/examples/relations.py
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from redislite import FalkorDB
from runic.ogm import Edge, Field, Node, Relation, Session, select
from runic.ogm.driver.falkordb import FalkorDBDriver

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


class Authored(Edge, type="AUTHORED"):
    """Properties carried on the AUTHORED edge."""

    at: datetime
    primary: bool = Field(default=False)


class Article(Node, labels=["Article"]):
    id: str = Field(primary_key=True)
    title: str
    # INCOMING mirror of User.articles — same AUTHORED edges, seen from Article.
    authors: list[User] = Relation(
        relationship="AUTHORED", direction="INCOMING", target="User"
    )


class User(Node, labels=["User"]):
    id: str = Field(primary_key=True)
    name: str

    # Single related node (annotate Target | None).
    manager: User | None = Relation(
        relationship="REPORTS_TO", direction="OUTGOING", target="User"
    )
    # Collection with edge properties (annotate list[Target]).
    articles: list[Article] = Relation(
        relationship="AUTHORED",
        direction="OUTGOING",
        target="Article",
        edge_model=Authored,
    )
    # Undirected / symmetric relationship.
    contacts: list[User] = Relation(
        relationship="KNOWS", direction="BOTH", target="User"
    )


def main() -> None:
    db = FalkorDB(protocol=2)
    driver = FalkorDBDriver(db.select_graph("relations_demo"))

    # Seed nodes.
    with Session(driver) as session:
        session.add_all(
            [
                User(id="alice", name="Alice"),
                User(id="bob", name="Bob"),
                Article(id="p1", title="Graph Modeling"),
                Article(id="p2", title="Query Patterns"),
            ]
        )
        session.commit()

    # Create relationships with relate() — MERGE semantics (idempotent).
    # Pass the class-level descriptor (User.articles) for type-safe call sites.
    with Session(driver) as session:
        alice = session.get(User, "alice")
        bob = session.get(User, "bob")
        p1 = session.get(Article, "p1")
        p2 = session.get(Article, "p2")
        assert alice and bob and p1 and p2

        session.relate(
            alice, User.articles, p1,
            edge=Authored(at=datetime.now(UTC), primary=True),
        )
        session.relate(alice, User.articles, p2, edge=Authored(at=datetime.now(UTC)))
        session.relate(bob, User.manager, alice)      # bob REPORTS_TO alice
        session.relate(alice, User.contacts, bob)     # KNOWS (undirected)
        log.info("Created relationships")

    # LAZY loading (default) — first access runs a query; needs a live session.
    with Session(driver) as session:
        alice = session.get(User, "alice")
        assert alice is not None
        log.info("Alice's articles (lazy): %s", [a.title for a in alice.articles])

    # EAGER loading — fetch alongside the parent in one query (avoids N+1).
    with Session(driver) as session:
        alice = session.get(User, "alice", fetch=["articles"])
        assert alice is not None
        log.info("Alice's articles (eager): %s", [a.title for a in alice.articles])

    # Read EDGE PROPERTIES via traversal + all_with_edges().
    with Session(driver) as session:
        rows = session.all_with_edges(
            select(User).alias("u").where(User.id == "alice")
            .traverse(User.articles, edge_alias="e").alias("a")
            .return_nodes("u", "a").return_edge("e")
        )
        for user, edge, article in rows:  # (User, Authored, Article) tuples
            flag = "primary" if edge and edge.primary else "secondary"
            log.info("%s authored %r (%s)", user.name, article.title, flag)

    # INCOMING mirror — the same edges seen from the Article side.
    with Session(driver) as session:
        p1 = session.get(Article, "p1")
        assert p1 is not None
        log.info("p1 authors (incoming mirror): %s", [u.name for u in p1.authors])

    # Remove a relationship.
    with Session(driver) as session:
        alice = session.get(User, "alice")
        p2 = session.get(Article, "p2")
        assert alice and p2
        session.unrelate(alice, User.articles, p2)
        log.info("Unrelated alice -/-> p2")

    driver.close()


if __name__ == "__main__":
    main()
