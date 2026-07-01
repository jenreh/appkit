"""Native FalkorDB types: Vector, GeoLocation, interned strings, auto-converters.

Vector (vecf32), GeoLocation (point), and Field(interned=True) (intern) are
FalkorDB-specific wrappers. datetime and Enum fields get their converters
assigned automatically — no converter= argument required.

NOTE: the Vector/GeoLocation/intern wrappers apply only on FalkorDB; other
backends store the raw value.

Run against embedded FalkorDB (no server needed):
    uv run python skill/runic/examples/native_types.py
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import StrEnum

from redislite import FalkorDB

from runic.ogm import Field, GeoLocation, Node, Session, Vector, select
from runic.ogm.driver.falkordb import FalkorDBDriver

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


class ArticleStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class Article(Node, labels=["Article"]):
    id: str = Field(primary_key=True)

    # Auto-converters: no converter= needed for these annotations.
    status: ArticleStatus                       # EnumConverter
    published_at: datetime | None = None         # DatetimeConverter

    # FalkorDB-native wrappers:
    country: str = Field(interned=True)          # intern() — dedups repeats
    embedding: Vector | None = None              # vecf32() — embeddings
    origin: GeoLocation | None = None            # point() — geo coordinates


def main() -> None:
    db = FalkorDB(protocol=2)
    driver = FalkorDBDriver(db.select_graph("native_types_demo"))

    with Session(driver) as session:
        session.add_all(
            [
                Article(
                    id="a1",
                    status=ArticleStatus.PUBLISHED,
                    published_at=datetime(2024, 6, 1, 9, 0, tzinfo=UTC),
                    country="Germany",
                    embedding=Vector([0.12, 0.45, 0.78, 0.23]),
                    origin=GeoLocation(latitude=52.520, longitude=13.405),
                ),
                Article(
                    id="a2",
                    status=ArticleStatus.DRAFT,
                    country="Germany",  # same interned value — stored once
                    embedding=Vector([0.98, 0.01, 0.33, 0.67]),
                ),
            ]
        )
        session.commit()

    # Everything round-trips back to its Python type.
    with Session(driver) as session:
        a1 = session.get(Article, "a1")
        assert a1 is not None
        assert a1.status is ArticleStatus.PUBLISHED          # enum member
        assert isinstance(a1.published_at, datetime)         # tz-aware datetime
        assert isinstance(a1.embedding, Vector)              # Vector
        assert isinstance(a1.origin, GeoLocation)            # GeoLocation
        log.info(
            "a1: status=%s country=%s origin=(%.3f, %.3f)",
            a1.status.value, a1.country, a1.origin.latitude, a1.origin.longitude,
        )

    # Native-typed fields work in query filters too.
    with Session(driver) as session:
        german = session.scalars(select(Article).where(Article.country == "Germany"))
        log.info("country == 'Germany': %s", [a.id for a in german])
        published = session.scalars(
            select(Article).where(Article.status == ArticleStatus.PUBLISHED)
        )
        log.info("status == PUBLISHED: %s", [a.id for a in published])

    driver.close()


if __name__ == "__main__":
    main()
