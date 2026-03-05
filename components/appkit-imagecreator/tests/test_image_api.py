# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for image_api FastAPI router.

Covers GET /api/images/{image_id} — found and not-found paths.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from appkit_imagecreator.backend.image_api import router

_PATCH = "appkit_imagecreator.backend.image_api"

_app = FastAPI()
_app.include_router(router)


def _db_context(session: AsyncMock | None = None):
    s = session or AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=s)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class TestGetImage:
    @pytest.mark.asyncio
    async def test_found(self) -> None:
        """Returns image data with correct content type."""
        image_bytes = b"\x89PNG\r\n\x1a\n"
        content_type = "image/png"

        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.image_repo") as repo,
        ):
            repo.find_image_data = AsyncMock(return_value=(image_bytes, content_type))

            transport = ASGITransport(app=_app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/images/1")

        assert resp.status_code == 200
        assert resp.content == image_bytes
        assert resp.headers["content-type"] == "image/png"
        assert "max-age=31536000" in resp.headers.get("cache-control", "")

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        """Returns 404 when image does not exist."""
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.image_repo") as repo,
        ):
            repo.find_image_data = AsyncMock(return_value=None)

            transport = ASGITransport(app=_app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/images/999")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_content_disposition(self) -> None:
        """Response includes inline content-disposition."""
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.image_repo") as repo,
        ):
            repo.find_image_data = AsyncMock(return_value=(b"data", "image/jpeg"))

            transport = ASGITransport(app=_app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/images/42")

        assert resp.status_code == 200
        assert "image_42.png" in resp.headers.get("content-disposition", "")
