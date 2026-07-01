"""Query builder: filtering, projection, aggregation, and traversal.

Covers select() execution via the session, the descriptor filter operators,
boolean composition, ordering/paging, project()/all_rows(), aggregate(), and
multi-hop traversal with edge filters.

Run against embedded FalkorDB (no server needed):
    uv run python skill/runic/examples/query_builder.py
"""

from __future__ import annotations

import logging

from redislite import FalkorDB

from runic.ogm import (
    Edge,
    Field,
    Node,
    Relation,
    Session,
    avg,
    count,
    select,
    sum_,
)
from runic.ogm.driver.falkordb import FalkorDBDriver

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


class Rated(Edge, type="RATED"):
    score: float = Field()


class Movie(Node, labels=["Movie"]):
    id: str = Field(primary_key=True)
    title: str = Field()
    genre: str = Field()
    year: int = Field()
    rating: float = Field(default=0.0)


class User(Node, labels=["User"]):
    id: str = Field(primary_key=True)
    name: str = Field()
    rated: list[Movie] = Relation(
        relationship="RATED", direction="OUTGOING", target="Movie", edge_model=Rated
    )


def main() -> None:
    db = FalkorDB(protocol=2)
    driver = FalkorDBDriver(db.select_graph("query_demo"))

    with Session(driver) as session:
        movies = [
            Movie(id="m1", title="Inception", genre="sci-fi", year=2010, rating=8.8),
            Movie(id="m2", title="The Matrix", genre="sci-fi", year=1999, rating=8.7),
            Movie(id="m3", title="The Godfather", genre="drama", year=1972, rating=9.2),
            Movie(id="m4", title="Interstellar", genre="sci-fi", year=2014, rating=8.6),
        ]
        session.add_all([User(id="alice", name="Alice"), *movies])
        session.commit()

    # --- Filtering: operators on class-level field descriptors ---
    with Session(driver) as session:
        scifi = session.scalars(
            select(Movie).where(Movie.genre == "sci-fi").order_by(Movie.year)
        )
        log.info("sci-fi by year: %s", [m.title for m in scifi])

        recent = session.scalars(select(Movie).where(Movie.year >= 2010))
        log.info("year >= 2010: %s", [m.title for m in recent])

        named = session.scalars(select(Movie).where(Movie.title.contains("The")))
        log.info("title contains 'The': %s", [m.title for m in named])

    # --- Boolean composition: parenthesize each operand ---
    with Session(driver) as session:
        good_scifi = session.scalars(
            select(Movie).where((Movie.genre == "sci-fi") & (Movie.rating > 8.6))
        )
        log.info("good sci-fi: %s", [m.title for m in good_scifi])

    # --- one-or-none, count ---
    with Session(driver) as session:
        top = session.scalar(select(Movie).where(Movie.id == "m3"))
        log.info("scalar m3: %s", top and top.title)
        log.info("count sci-fi: %d", session.count(select(Movie).where(Movie.genre == "sci-fi")))

    # --- order / limit / skip ---
    with Session(driver) as session:
        top2 = session.scalars(select(Movie).order_by(Movie.rating, desc=True).limit(2))
        log.info("top 2 by rating: %s", [m.title for m in top2])

    # --- projection: project() → all_rows() (dicts keyed "n.<field>") ---
    with Session(driver) as session:
        rows = session.all_rows(
            select(Movie).order_by(Movie.year).project(Movie.title, Movie.year)
        )
        log.info("projected: %s", [(r["n.title"], r["n.year"]) for r in rows])

    # --- aggregation: aggregate() → all_rows() ---
    with Session(driver) as session:
        # Name aggregation columns distinctly — avoid the default node alias "n".
        summary = session.all_rows(
            select(Movie).where(Movie.genre == "sci-fi").aggregate(
                count("*").as_("total"),
                avg(Movie.rating).as_("avg_rating"),
                sum_(Movie.year).as_("year_sum"),
            )
        )
        log.info("sci-fi summary: %s", summary[0])

    # --- grouped aggregation: count per FIELD via group_by="n.<field>" ---
    # (the default node alias is "n"; result rows are keyed by "n.genre")
    with Session(driver) as session:
        per_genre = session.all_rows(
            select(Movie).aggregate(count("*").as_("n_movies"), group_by="n.genre")
        )
        log.info("movies per genre: %s", per_genre)

    # --- traversal: who rated highly + read the edge property ---
    with Session(driver) as session:
        alice = session.get(User, "alice")
        m1 = session.get(Movie, "m1")
        m3 = session.get(Movie, "m3")
        assert alice and m1 and m3
        session.relate(alice, User.rated, m1, edge=Rated(score=9.0))
        session.relate(alice, User.rated, m3, edge=Rated(score=7.0))

    with Session(driver) as session:
        # Filtering on an edge property → use optional=False (required join).
        rows = session.all_with_edges(
            select(User).alias("u").where(User.id == "alice")
            .traverse(User.rated, edge_alias="r", optional=False).alias("m")
            .where(Rated.score >= 8.0, on="r")
            .return_nodes("u", "m").return_edge("r")
        )
        for user, edge, movie in rows:
            log.info("%s rated %r → %.1f", user.name, movie.title, edge.score)

    # --- inspect generated Cypher without executing ---
    cypher, params = (
        select(Movie).where(Movie.genre == "sci-fi").order_by(Movie.year).limit(3)
    ).build()
    log.info("Cypher: %s | params: %s", cypher, params)

    driver.close()


if __name__ == "__main__":
    main()
