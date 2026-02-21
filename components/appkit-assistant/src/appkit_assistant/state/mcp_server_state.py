"""State management for MCP servers."""

import json
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import reflex as rx

from appkit_assistant.backend.database.models import MCPAuthType, MCPServer
from appkit_assistant.backend.database.repositories import (
    mcp_server_repo,
)
from appkit_commons.database.session import get_asyncdb_session

logger = logging.getLogger(__name__)


class MCPServerState(rx.State):
    """State class for managing MCP servers."""

    servers: list[MCPServer] = []
    current_server: MCPServer | None = None
    loading: bool = False
    updating_active_server_id: int | None = None
    updating_role_server_id: int | None = None
    add_modal_open: bool = False
    opening_add_modal: bool = False
    edit_modal_open: bool = False
    opening_edit_server_id: int | None = None
    search_filter: str = ""
    available_roles: list[dict[str, str]] = []
    role_labels: dict[str, str] = {}

    def set_search_filter(self, value: str) -> None:
        """Set the search filter."""
        self.search_filter = value

    @rx.var
    def filtered_servers(self) -> list[MCPServer]:
        """Get filtered servers based on search criteria."""
        if not self.search_filter:
            return self.servers

        search = self.search_filter.lower()
        return [server for server in self.servers if search in server.name.lower()]

    async def open_add_modal(self) -> AsyncGenerator[Any, Any]:
        """Open the add server modal."""
        self.opening_add_modal = True
        yield
        self.add_modal_open = True
        self.opening_add_modal = False

    def close_add_modal(self) -> None:
        """Close the add server modal."""
        self.add_modal_open = False

    async def open_edit_modal(self, server_id: int) -> AsyncGenerator[Any, Any]:
        """Open the edit server modal."""
        self.opening_edit_server_id = server_id
        yield

        # Find server in list (sync operation but inside async loop)
        for server in self.servers:
            if server.id == server_id:
                self.current_server = server
                self.edit_modal_open = True
                break

        self.opening_edit_server_id = None

    def close_edit_modal(self) -> None:
        """Close the edit server modal."""
        self.edit_modal_open = False
        self.current_server = None

    def set_available_roles(
        self,
        available_roles: list[dict[str, str]],
        role_labels: dict[str, str],
    ) -> None:
        """Set the available roles for MCP server access control."""
        self.available_roles = available_roles
        self.role_labels = role_labels

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
            auth_type = form_data.get("auth_type", MCPAuthType.API_KEY)

            server_entity = MCPServer(
                name=form_data["name"],
                url=form_data["url"],
                headers=headers,
                description=form_data.get("description") or None,
                prompt=form_data.get("prompt") or None,
                required_role=form_data.get("required_role") or None,
                auth_type=auth_type,
                oauth_client_id=(
                    form_data.get("oauth_client_id")
                    if auth_type == MCPAuthType.OAUTH_DISCOVERY
                    else None
                ),
                oauth_client_secret=(
                    form_data.get("oauth_client_secret")
                    if auth_type == MCPAuthType.OAUTH_DISCOVERY
                    else None
                ),
                oauth_issuer=form_data.get("oauth_issuer"),
                oauth_authorize_url=form_data.get("oauth_authorize_url"),
                oauth_token_url=form_data.get("oauth_token_url"),
                oauth_scopes=form_data.get("oauth_scopes"),
                oauth_discovered_at=(
                    datetime.now(UTC) if form_data.get("oauth_issuer") else None
                ),
            )

            async with get_asyncdb_session() as session:
                server = await mcp_server_repo.save(session, server_entity)
                # Ensure we have the name before session closes if used later
                server_name = server.name

            await self.load_servers()
            self.add_modal_open = False
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
            auth_type = form_data.get("auth_type", MCPAuthType.API_KEY)
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
                    existing_server.required_role = (
                        form_data.get("required_role") or None
                    )
                    existing_server.auth_type = auth_type
                    existing_server.oauth_client_id = (
                        form_data.get("oauth_client_id")
                        if auth_type == MCPAuthType.OAUTH_DISCOVERY
                        else None
                    )
                    existing_server.oauth_client_secret = (
                        form_data.get("oauth_client_secret")
                        if auth_type == MCPAuthType.OAUTH_DISCOVERY
                        else None
                    )
                    existing_server.oauth_issuer = form_data.get("oauth_issuer")
                    existing_server.oauth_authorize_url = form_data.get(
                        "oauth_authorize_url"
                    )
                    existing_server.oauth_token_url = form_data.get("oauth_token_url")
                    existing_server.oauth_scopes = form_data.get("oauth_scopes")
                    if form_data.get("oauth_issuer"):
                        existing_server.oauth_discovered_at = datetime.now(UTC)

                    updated_server = await mcp_server_repo.save(
                        session, existing_server
                    )
                    updated_name = updated_server.name

            if updated_name:
                await self.load_servers()
                self.edit_modal_open = False
                self.current_server = None
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

    async def toggle_server_active(
        self, server_id: int, active: bool
    ) -> AsyncGenerator[Any, Any]:
        """Toggle the active status of an MCP server."""
        # Set updating state
        self.updating_active_server_id = server_id

        # Optimistic update: update UI immediately for better UX
        original_servers = list(self.servers)
        for i, s in enumerate(self.servers):
            if s.id == server_id:
                # Create a copy to trigger reactivity if needed
                new_server = s.model_copy(update={"active": active})
                self.servers[i] = new_server
                break

        # Trigger list update (Reflex needs list reference change or explicit
        # modification)
        self.servers = list(self.servers)

        # Yield immediately to flush state update to frontend
        yield

        try:
            async with get_asyncdb_session() as session:
                server = await mcp_server_repo.find_by_id(session, server_id)
                if not server:
                    # Revert optimistic update
                    self.servers = original_servers
                    self.updating_active_server_id = None
                    yield rx.toast.error(
                        "MCP Server nicht gefunden.",
                        position="top-right",
                    )
                    return

                server.active = active
                await mcp_server_repo.save(session, server)
                server_name = server.name

            status_text = "aktiviert" if active else "deaktiviert"

            # Clear updating state
            self.updating_active_server_id = None

            yield rx.toast.info(
                f"MCP Server {server_name} wurde {status_text}.",
                position="top-right",
            )
            logger.debug("Toggled MCP server %s active=%s", server_name, active)

        except Exception as e:
            # Revert optimistic update on error
            self.servers = original_servers
            self.updating_active_server_id = None
            logger.error("Failed to toggle MCP server %d: %s", server_id, e)
            yield rx.toast.error(
                "Fehler beim Ändern des MCP Server Status.",
                position="top-right",
            )

    async def update_server_role(
        self, server_id: int, new_role: str | None
    ) -> AsyncGenerator[Any, Any]:
        """Update the required role for an MCP server."""
        self.updating_role_server_id = server_id
        yield

        # Optimistic update
        # We need to find the server in the list and update it
        original_servers = []
        for s in self.servers:
            original_servers.append(s.model_copy())
            if s.id == server_id:
                s.required_role = new_role

        # Trigger update
        self.servers = list(self.servers)
        yield

        try:
            async with get_asyncdb_session() as session:
                server = await mcp_server_repo.find_by_id(session, server_id)
                if not server:
                    # Revert
                    self.servers = original_servers
                    self.updating_role_server_id = None
                    yield rx.toast.error(
                        "MCP Server nicht gefunden.",
                        position="top-right",
                    )
                    return

                server.required_role = new_role
                await mcp_server_repo.save(session, server)
                server_name = server.name

            self.updating_role_server_id = None
            yield rx.toast.info(
                f"Rolle für {server_name} aktualisiert.",
                position="top-right",
            )

        except Exception as e:
            # Revert
            self.servers = original_servers
            self.updating_role_server_id = None
            logger.error("Failed to update role for server %d: %s", server_id, e)
            yield rx.toast.error(
                "Fehler beim Ändern der Rolle.",
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
