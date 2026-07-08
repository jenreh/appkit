"""Polymorphism: multi-label node hierarchies with a shared primary_label.

Querying the base class returns the correct concrete subtypes; querying a
subtype filters to just that type. Subtypes inherit base fields.

Run against embedded FalkorDB (no server needed):
    uv run python skill/runic/examples/polymorphism.py
"""

from __future__ import annotations

import logging

from redislite import FalkorDB
from runic.ogm import Node, Repository, Session, select
from runic.ogm.driver.falkordb import FalkorDBDriver

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


# The base carries shared fields and the common label. primary_label is the
# label used to MATCH/decode the whole hierarchy.
class Location(Node, labels=["Location"], primary_label="Location"):
    id: str
    title: str
    latitude: float | None = None
    longitude: float | None = None


# Subtypes add their own label (and keep "Location") plus extra fields.
class Country(Location, labels=["Location", "Country"], primary_label="Location"):
    iso_code: str
    population: int | None = None


class City(Location, labels=["Location", "City"], primary_label="Location"):
    country_code: str | None = None


class Museum(Location, labels=["Location", "Museum"], primary_label="Location"):
    opening_hours: str | None = None


def main() -> None:
    db = FalkorDB(protocol=2)
    driver = FalkorDBDriver(db.select_graph("polymorphism_demo"))

    with Session(driver) as session:
        session.add_all(
            [
                Country(id="FR", title="France", iso_code="FR", population=67_000_000),
                Country(id="DE", title="Germany", iso_code="DE", population=83_000_000),
                City(id="PAR", title="Paris", country_code="FR"),
                Museum(id="LOUVRE", title="Louvre", opening_hours="09:00-18:00"),
            ]
        )
        session.commit()

    # Query the BASE class → mixed concrete subtypes, each as its real type.
    with Session(driver) as session:
        repo = Repository(session, Location)
        for loc in repo.find_all():
            log.info("[%s] %s — %s", type(loc).__name__, loc.id, loc.title)

    # Query a SUBTYPE → only that type, with subtype fields available.
    with Session(driver) as session:
        big = session.scalars(
            select(Country).where(Country.population > 70_000_000)
        )
        log.info("countries > 70M: %s", [(c.iso_code, c.population) for c in big])

    driver.close()


if __name__ == "__main__":
    main()
