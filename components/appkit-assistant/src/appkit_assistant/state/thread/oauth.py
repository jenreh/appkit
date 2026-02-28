"""MCP OAuth mixin for ThreadState.

Handles the OAuth flow for MCP server authentication.
"""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import reflex as rx

from appkit_assistant.backend.schemas import MessageType
from appkit_assistant.backend.services.response_accumulator import (
    ResponseAccumulator,
)

logger = logging.getLogger(__name__)


class OAuthMixin:
    """Mixin for MCP OAuth authentication flow.

    Expects state vars: ``pending_auth_server_id``,
    ``pending_auth_server_name``, ``pending_auth_url``,
    ``show_auth_card``, ``pending_oauth_message``, ``oauth_result``,
    ``messages``, ``_current_user_id``, ``_skip_user_message``, ``prompt``.
    """

    @rx.event
    def start_mcp_oauth(self) -> rx.event.EventSpec:
        """Start the OAuth flow by opening the auth URL in a popup."""
        if not self.pending_auth_url:
            return rx.toast.error("Keine Authentifizierungs-URL verfügbar")

        auth_url = self.pending_auth_url
        auth_url_js = json.dumps(auth_url)
        return rx.call_script(
            f"window.open({auth_url_js}, 'mcp_oauth', 'width=600,height=700')"
        )

    @rx.event
    async def handle_mcp_oauth_success(
        self, server_id: str, server_name: str
    ) -> AsyncGenerator[Any, Any]:
        """Handle successful OAuth completion from popup window."""
        logger.debug("OAuth success for server %s (%s)", server_name, server_id)
        self.show_auth_card = False
        self.pending_auth_server_id = ""
        self.pending_auth_server_name = ""
        self.pending_auth_url = ""

        pending_message = self.pending_oauth_message
        self.pending_oauth_message = ""

        if pending_message:
            if self.messages and self.messages[-1].type == MessageType.ASSISTANT:
                self.messages = self.messages[:-1]
            yield rx.toast.success(
                f"Erfolgreich mit {server_name} verbunden. "
                "Anfrage wird erneut gesendet...",
                position="top-right",
            )
            self.prompt = pending_message
            self._skip_user_message = True
            yield type(self).submit_message
        else:
            yield rx.toast.success(
                f"Erfolgreich mit {server_name} verbunden.",
                position="top-right",
            )

    @rx.event
    async def process_oauth_result(
        self,
    ) -> AsyncGenerator[Any, Any]:
        """Process OAuth result from synced LocalStorage.

        Called via on_mount when oauth_result becomes non-empty.
        The rx.LocalStorage(sync=True) automatically syncs from popup.
        """
        if not self.oauth_result:
            return

        try:
            data = json.loads(self.oauth_result)
            if data.get("type") != "mcp-oauth-success":
                return

            server_id = data.get("serverId", "")
            server_name = data.get("serverName", "Unknown")
            user_id = data.get("userId", "")

            if (
                user_id
                and self._current_user_id
                and str(user_id) != str(self._current_user_id)
            ):
                logger.warning(
                    "OAuth user mismatch: got %s, expected %s",
                    user_id,
                    self._current_user_id,
                )
                self.oauth_result = ""
                return

            logger.info(
                "Processing OAuth success: server_id=%s, server_name=%s",
                server_id,
                server_name,
            )
            self.oauth_result = ""

            async for event in self.handle_mcp_oauth_success(server_id, server_name):
                yield event

        except json.JSONDecodeError:
            logger.warning("Failed to parse OAuth result: %s", self.oauth_result)
            self.oauth_result = ""

    @rx.event
    def dismiss_auth_card(self) -> None:
        """Dismiss the auth card without authenticating."""
        self.show_auth_card = False

    def _handle_auth_required_from_accumulator(
        self, accumulator: ResponseAccumulator
    ) -> None:
        """Handle auth required state from accumulator."""
        self.pending_auth_server_id = accumulator.auth_required_data.get(
            "server_id", ""
        )
        self.pending_auth_server_name = accumulator.auth_required_data.get(
            "server_name", ""
        )
        self.pending_auth_url = accumulator.auth_required_data.get("auth_url", "")
        self.show_auth_card = True

        accumulator.auth_required = False

        for msg in reversed(self.messages):
            if msg.type == MessageType.HUMAN:
                self.pending_oauth_message = msg.text
                break
        logger.debug(
            "Auth required for server %s, showing auth card",
            self.pending_auth_server_name,
        )
