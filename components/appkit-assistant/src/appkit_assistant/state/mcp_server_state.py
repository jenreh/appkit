"""State management for MCP servers."""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import reflex as rx

from appkit_assistant.backend.models import MCPServer
from appkit_assistant.backend.repositories import (
    mcp_server_repo,
)
from appkit_commons.database.session import get_asyncdb_session

logger = logging.getLogger(__name__)


class MCPServerState(rx.State):
    """State class for managing MCP servers."""

    servers: list[MCPServer] = []
    current_server: MCPServer | None = None
    loading: bool = False

    async def load_servers(self) -> None:
        """Load all MCP servers from the database.

        Raises exceptions to let callers decide how to handle errors.
        """
        self.loading = True
        try:
            async with get_asyncdb_session() as session:
                servers = await mcp_server_repo.find_all_ordered_by_name(session)
                self.servers = [MCPServer(**s.model_dump()) for s in servers]
            logger.debug("Loaded %d MCP servers", len(self.servers))
        except Exception as e:
            logger.error("Failed to load MCP servers: %s", e)
            raise
        finally:
            self.loading = False

    async def load_servers_with_toast(self) -> AsyncGenerator[Any, Any]:
        """Load servers and show an error toast on failure."""
        try:
            await self.load_servers()
        except Exception:
            yield rx.toast.error(
                "Fehler beim Laden der MCP Server.",
                position="top-right",
            )

    async def get_server(self, server_id: int) -> None:
        """Get a specific MCP server by ID."""
        try:
            async with get_asyncdb_session() as session:
                server = await mcp_server_repo.find_by_id(session, server_id)
                if server:
                    self.current_server = MCPServer(**server.model_dump())
                else:
                    self.current_server = None

            if not self.current_server:
                logger.warning("MCP server with ID %d not found", server_id)
        except Exception as e:
            logger.error("Failed to get MCP server %d: %s", server_id, e)

    async def set_current_server(self, server: MCPServer) -> None:
        """Set the current server."""
        self.current_server = server

    async def add_server(self, form_data: dict[str, Any]) -> AsyncGenerator[Any, Any]:
        """Add a new MCP server."""
        try:
            headers = self._parse_headers_from_form(form_data)
            server_entity = MCPServer(
                name=form_data["name"],
                url=form_data["url"],
                headers=headers,
                description=form_data.get("description") or None,
                prompt=form_data.get("prompt") or None,
            )

            async with get_asyncdb_session() as session:
                server = await mcp_server_repo.save(session, server_entity)
                # Ensure we have the name before session closes if used later
                server_name = server.name

            await self.load_servers()
            yield rx.toast.info(
                "MCP Server {} wurde hinzugefügt.".format(form_data["name"]),
                position="top-right",
            )
            logger.debug("Added MCP server: %s", server_name)

        except ValueError as e:
            logger.error("Invalid form data for MCP server: %s", e)
            yield rx.toast.error(
                str(e),
                position="top-right",
            )
        except Exception as e:
            logger.error("Failed to add MCP server: %s", e)
            yield rx.toast.error(
                "Fehler beim Hinzufügen des MCP Servers.",
                position="top-right",
            )

    async def modify_server(
        self, form_data: dict[str, Any]
    ) -> AsyncGenerator[Any, Any]:
        """Modify an existing MCP server."""
        if not self.current_server:
            yield rx.toast.error(
                "Kein Server ausgewählt.",
                position="top-right",
            )
            return

        try:
            headers = self._parse_headers_from_form(form_data)
            updated_name = ""

            async with get_asyncdb_session() as session:
                # Re-fetch server to ensure we have the latest and bound to session
                existing_server = await mcp_server_repo.find_by_id(
                    session, self.current_server.id
                )

                updated_server = None
                if existing_server:
                    existing_server.name = form_data["name"]
                    existing_server.url = form_data["url"]
                    existing_server.headers = headers
                    existing_server.description = form_data.get("description") or None
                    existing_server.prompt = form_data.get("prompt") or None

                    updated_server = await mcp_server_repo.save(
                        session, existing_server
                    )
                    updated_name = updated_server.name

            if updated_name:
                await self.load_servers()
                yield rx.toast.info(
                    "MCP Server {} wurde aktualisiert.".format(form_data["name"]),
                    position="top-right",
                )
                logger.debug("Updated MCP server: %s", updated_name)
            else:
                yield rx.toast.error(
                    "MCP Server konnte nicht gefunden werden.",
                    position="top-right",
                )

        except ValueError as e:
            logger.error("Invalid form data for MCP server: %s", e)
            yield rx.toast.error(
                str(e),
                position="top-right",
            )
        except Exception as e:
            logger.error("Failed to update MCP server: %s", e)
            yield rx.toast.error(
                "Fehler beim Aktualisieren des MCP Servers.",
                position="top-right",
            )

    async def delete_server(self, server_id: int) -> AsyncGenerator[Any, Any]:
        """Delete an MCP server."""
        try:
            async with get_asyncdb_session() as session:
                # Get server name for the success message
                server = await mcp_server_repo.find_by_id(session, server_id)
                if not server:
                    yield rx.toast.error(
                        "MCP Server nicht gefunden.",
                        position="top-right",
                    )
                    return

                server_name = server.name

                # Delete server using repository
                success = await mcp_server_repo.delete_by_id(session, server_id)

            if success:
                await self.load_servers()
                yield rx.toast.info(
                    f"MCP Server {server_name} wurde gelöscht.",
                    position="top-right",
                )
                logger.debug("Deleted MCP server: %s", server_name)
            else:
                yield rx.toast.error(
                    "MCP Server konnte nicht gelöscht werden.",
                    position="top-right",
                )

        except Exception as e:
            logger.error("Failed to delete MCP server %d: %s", server_id, e)
            yield rx.toast.error(
                "Fehler beim Löschen des MCP Servers.",
                position="top-right",
            )

    def _parse_headers_from_form(self, form_data: dict[str, Any]) -> dict[str, str]:
        """Parse headers from form data."""
        headers_json = form_data.get("headers_json", "").strip()
        if not headers_json:
            return "{}"

        try:
            headers = json.loads(headers_json)
            if not isinstance(headers, dict):
                logger.warning("Headers JSON is not a dictionary: %s", headers_json)
                raise ValueError("Headers JSON must be a dictionary")

            # Ensure all keys and values are strings
            cleaned_headers = {}
            for key, value in headers.items():
                if isinstance(key, str) and isinstance(value, str):
                    cleaned_headers[key] = value
                else:
                    logger.warning("Invalid header key-value pair: %s=%s", key, value)
                    raise ValueError(f"Invalid header key-value pair: {key}={value}")

            logger.debug("Parsed headers from JSON: %s", cleaned_headers)
            return headers_json

        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in headers field: %s", e)
            raise ValueError(
                "Ungültiges JSON-Format in den HTTP-Headern. "
                "Bitte überprüfen Sie die Eingabe."
            ) from e
        except ValueError:
            # Re-raise ValueError exceptions (invalid dictionary or key-value pairs)
            raise

    @rx.var
    def server_count(self) -> int:
        """Get the number of servers."""
        return len(self.servers)

    @rx.var
    def has_servers(self) -> bool:
        """Check if there are any servers."""
        return len(self.servers) > 0
