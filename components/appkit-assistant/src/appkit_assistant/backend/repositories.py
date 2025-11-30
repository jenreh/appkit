"""Repository for MCP server data access operations."""

import logging
from datetime import UTC, datetime

import reflex as rx

from appkit_assistant.backend.models import MCPServer, SystemPrompt

logger = logging.getLogger(__name__)


class MCPServerRepository:
    """Repository class for MCP server database operations."""

    @staticmethod
    async def get_all() -> list[MCPServer]:
        """Retrieve all MCP servers ordered by name."""
        async with rx.asession() as session:
            result = await session.exec(MCPServer.select().order_by(MCPServer.name))
            return result.all()

    @staticmethod
    async def get_by_id(server_id: int) -> MCPServer | None:
        """Retrieve an MCP server by ID."""
        async with rx.asession() as session:
            result = await session.exec(
                MCPServer.select().where(MCPServer.id == server_id)
            )
            return result.first()

    @staticmethod
    async def create(
        name: str,
        url: str,
        headers: str,
        description: str | None = None,
        prompt: str | None = None,
    ) -> MCPServer:
        """Create a new MCP server."""
        async with rx.asession() as session:
            server = MCPServer(
                name=name,
                url=url,
                headers=headers,
                description=description,
                prompt=prompt,
            )
            session.add(server)
            await session.commit()
            await session.refresh(server)
            logger.debug("Created MCP server: %s", name)
            return server

    @staticmethod
    async def update(
        server_id: int,
        name: str,
        url: str,
        headers: str,
        description: str | None = None,
        prompt: str | None = None,
    ) -> MCPServer | None:
        """Update an existing MCP server."""
        async with rx.asession() as session:
            result = await session.exec(
                MCPServer.select().where(MCPServer.id == server_id)
            )
            server = result.first()
            if server:
                server.name = name
                server.url = url
                server.headers = headers
                server.description = description
                server.prompt = prompt
                await session.commit()
                await session.refresh(server)
                logger.debug("Updated MCP server: %s", name)
                return server
            logger.warning("MCP server with ID %s not found for update", server_id)
            return None

    @staticmethod
    async def delete(server_id: int) -> bool:
        """Delete an MCP server by ID."""
        async with rx.asession() as session:
            result = await session.exec(
                MCPServer.select().where(MCPServer.id == server_id)
            )
            server = result.first()
            if server:
                await session.delete(server)
                await session.commit()
                logger.debug("Deleted MCP server: %s", server.name)
                return True
            logger.warning("MCP server with ID %s not found for deletion", server_id)
            return False


class SystemPromptRepository:
    """Repository class for system prompt database operations.

    Implements append-only versioning with full CRUD capabilities.
    """

    @staticmethod
    async def get_all() -> list[SystemPrompt]:
        """Retrieve all system prompt versions ordered by version descending."""
        async with rx.asession() as session:
            result = await session.exec(
                SystemPrompt.select().order_by(SystemPrompt.version.desc())
            )
            return result.all()

    @staticmethod
    async def get_latest() -> SystemPrompt | None:
        """Retrieve the latest system prompt version."""
        async with rx.asession() as session:
            result = await session.exec(
                SystemPrompt.select().order_by(SystemPrompt.version.desc()).limit(1)
            )
            return result.first()

    @staticmethod
    async def get_by_id(prompt_id: int) -> SystemPrompt | None:
        """Retrieve a system prompt by ID."""
        async with rx.asession() as session:
            result = await session.exec(
                SystemPrompt.select().where(SystemPrompt.id == prompt_id)
            )
            return result.first()

    @staticmethod
    async def create(prompt: str, user_id: int) -> SystemPrompt:
        """Neue System Prompt Version anlegen.

        Version ist fortlaufende Ganzzahl, beginnend bei 1.
        """
        async with rx.asession() as session:
            result = await session.exec(
                SystemPrompt.select().order_by(SystemPrompt.version.desc()).limit(1)
            )
            latest = result.first()
            next_version = (latest.version + 1) if latest else 1

            name = f"Version {next_version}"

            system_prompt = SystemPrompt(
                name=name,
                prompt=prompt,
                version=next_version,
                user_id=user_id,
                created_at=datetime.now(UTC),
            )
            session.add(system_prompt)
            await session.commit()
            await session.refresh(system_prompt)

            logger.info(
                "Created system prompt version %s for user %s",
                next_version,
                user_id,
            )
            return system_prompt

    @staticmethod
    async def delete(prompt_id: int) -> bool:
        """Delete a system prompt version by ID."""
        async with rx.asession() as session:
            result = await session.exec(
                SystemPrompt.select().where(SystemPrompt.id == prompt_id)
            )
            prompt = result.first()
            if prompt:
                await session.delete(prompt)
                await session.commit()
                logger.info("Deleted system prompt version: %s", prompt.version)
                return True
            logger.warning(
                "System prompt with ID %s not found for deletion",
                prompt_id,
            )
            return False
