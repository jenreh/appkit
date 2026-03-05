"""Pytest fixtures for appkit-mcp-bpmn tests."""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio
from fastmcp.client import Client

from appkit_mcp_bpmn.configuration import BPMNConfig
from appkit_mcp_bpmn.server import create_bpmn_mcp_server

pytest_plugins = ["appkit_commons.testing"]


@pytest_asyncio.fixture
async def bpmn_client(tmp_path: Path) -> AsyncIterator[Client]:
    """Fixture providing a FastMCP Client for the BPMN server."""
    config = BPMNConfig(storage_dir=str(tmp_path / "bpmn"))
    mcp = create_bpmn_mcp_server(config=config)
    async with Client(mcp) as client:
        yield client
