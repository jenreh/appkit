"""Async sessions with runic.ogm — and the lazy-loading sharp edge.

AsyncSession mirrors Session, but I/O methods are coroutines you must await.
The critical difference: there is NO lazy relationship loading in async. Touching
an unloaded relation raises LazyLoadError — you must eager-load with fetch=.

The async FalkorDB client cannot use embedded redislite, so this example needs a
live FalkorDB server:
    FALKORDB_HOST=localhost FALKORDB_PORT=6379 \\
        uv run python skill/runic/examples/async_session.py
"""

from __future__ import annotations

import asyncio
import logging
import os

from falkordb.asyncio import FalkorDB
from runic.ogm import AsyncSession, Field, Node, Relation, select
from runic.ogm.driver.falkordb import AsyncFalkorDBDriver
from runic.ogm.exceptions import LazyLoadError

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


class Article(Node, labels=["Article"]):
    id: str = Field(primary_key=True)
    title: str


class User(Node, labels=["User"]):
    id: str = Field(primary_key=True)
    name: str
    articles: list[Article] = Relation(
        relationship="AUTHORED", direction="OUTGOING", target="Article"
    )


async def main() -> None:
    host = os.getenv("FALKORDB_HOST", "localhost")
    port = int(os.getenv("FALKORDB_PORT", "6379"))
    db = FalkorDB(host=host, port=port)
    driver = AsyncFalkorDBDriver(db.select_graph("async_demo"))

    # add()/add_all()/delete() are sync; commit()/get()/scalars() are coroutines.
    async with AsyncSession(driver) as session:
        session.add_all(
            [
                User(id="alice", name="Alice"),
                Article(id="p1", title="Async Graphs"),
            ]
        )
        await session.commit()

        alice = await session.get(User, "alice")
        p1 = await session.get(Article, "p1")
        assert alice and p1
        await session.relate(alice, User.articles, p1)
        await session.commit()

    # Lazy access in async raises LazyLoadError — DON'T do this:
    async with AsyncSession(driver) as session:
        alice = await session.get(User, "alice")
        assert alice is not None
        try:
            _ = alice.articles            # no fetch= → raises
        except LazyLoadError as exc:
            log.info("Expected LazyLoadError: %s", exc)

    # DO eager-load with fetch= instead:
    async with AsyncSession(driver) as session:
        alice = await session.get(User, "alice", fetch=["articles"])
        assert alice is not None
        log.info("Alice's articles: %s", [a.title for a in alice.articles])

        # Query builder execution is async too.
        users = await session.scalars(select(User).order_by(User.name))
        log.info("All users: %s", [u.name for u in users])

    await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
