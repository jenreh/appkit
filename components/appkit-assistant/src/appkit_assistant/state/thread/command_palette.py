"""Command palette mixin for ThreadState.

Provides slash-command detection, palette navigation, and command selection.
"""

import logging
import re

import reflex as rx

from appkit_assistant.backend.database.repositories import user_prompt_repo
from appkit_assistant.backend.schemas import CommandDefinition
from appkit_commons.database.session import get_asyncdb_session

logger = logging.getLogger(__name__)


class CommandPaletteMixin:
    """Mixin for slash-command palette management.

    Expects state vars: ``show_command_palette``, ``filtered_commands``,
    ``selected_command_index``, ``command_search_prefix``,
    ``command_trigger_position``, ``available_commands``, ``prompt``,
    ``available_mcp_servers``, ``selected_mcp_servers``,
    ``temp_selected_mcp_servers``, ``server_selection_state``,
    ``_current_user_id``.
    """

    @rx.var
    def filtered_user_prompts(self) -> list[CommandDefinition]:
        """User's own prompts (editable), sorted alphabetically."""
        return sorted(
            [cmd for cmd in self.filtered_commands if cmd.is_editable],
            key=lambda c: c.id.lower(),
        )

    @rx.var
    def filtered_shared_prompts(self) -> list[CommandDefinition]:
        """Shared prompts from others (not editable), sorted alphabetically."""
        return sorted(
            [cmd for cmd in self.filtered_commands if not cmd.is_editable],
            key=lambda c: c.id.lower(),
        )

    @rx.var
    def has_filtered_user_prompts(self) -> bool:
        """Check if there are any filtered user prompts."""
        return any(cmd.is_editable for cmd in self.filtered_commands)

    @rx.var
    def has_filtered_shared_prompts(self) -> bool:
        """Check if there are any filtered shared prompts."""
        return any(not cmd.is_editable for cmd in self.filtered_commands)

    @rx.event
    async def reload_commands(self) -> None:
        """Reload user prompts as commands.

        Call this after creating, updating, or deleting prompts to refresh
        the command palette.
        """
        if self._current_user_id:
            await self._load_user_prompts_as_commands(int(self._current_user_id))
            self._update_command_palette(self.prompt)

    async def _load_user_prompts_as_commands(self, user_id: int) -> None:
        """Load user prompts from database and convert to CommandDefinitions."""
        try:
            async with get_asyncdb_session() as session:
                own_prompts = await user_prompt_repo.find_latest_prompts_by_user(
                    session, user_id
                )
                shared_prompts = await user_prompt_repo.find_latest_shared_prompts(
                    session, user_id
                )

                self.available_commands = [
                    CommandDefinition(
                        id=p.handle,
                        label=f"/{p.handle}",
                        description=p.description,
                        icon="",
                        is_editable=True,
                        user_id=user_id,
                        mcp_server_ids=list(p.mcp_server_ids),
                    )
                    for p in own_prompts
                ] + [
                    CommandDefinition(
                        id=p["handle"],
                        label=f"/{p['handle']}",
                        description=p.get("description", ""),
                        icon="share",
                        is_editable=False,
                        user_id=p.get("user_id", 0),
                        mcp_server_ids=p.get("mcp_server_ids", []),
                    )
                    for p in shared_prompts
                ]

                logger.debug(
                    "Loaded %d commands (%d own, %d shared) for user %d",
                    len(self.available_commands),
                    len(own_prompts),
                    len(shared_prompts),
                    user_id,
                )
        except Exception as e:
            logger.error("Error loading user prompts as commands: %s", e)
            self.available_commands = []

    def _update_command_palette(self, prompt: str) -> None:
        """Update command palette state based on prompt content."""
        match = re.search(r"(?:^|\s)/([^\s]*)$", prompt)

        if not match:
            self._hide_command_palette()
            return

        text_after_slash = match.group(1)
        slash_pos = match.end() - len(text_after_slash) - 1

        search_term = text_after_slash.lower()
        self.filtered_commands = [
            cmd
            for cmd in self.available_commands
            if cmd.id.lower().startswith(search_term)
            or cmd.label.lower().startswith(f"/{search_term}")
        ]

        self.show_command_palette = True
        self.command_search_prefix = text_after_slash
        self.command_trigger_position = slash_pos
        self.selected_command_index = 0

    def _hide_command_palette(self) -> None:
        """Hide the command palette and reset state."""
        self.show_command_palette = False
        self.filtered_commands = []
        self.selected_command_index = 0
        self.command_search_prefix = ""
        self.command_trigger_position = 0

    @rx.event
    def navigate_command_palette(self, direction: str) -> None:
        """Navigate through command palette items.

        Args:
            direction: "up" or "down" to move selection.
        """
        if not self.show_command_palette or not self.filtered_commands:
            return

        count = len(self.filtered_commands)
        if direction == "up":
            self.selected_command_index = (self.selected_command_index - 1) % count
        elif direction == "down":
            self.selected_command_index = (self.selected_command_index + 1) % count

    @rx.event
    def select_command(self, command_id: str) -> None:
        """Select a command from the palette and insert into the prompt.

        Also activates any MCP servers associated with the prompt.
        """
        command = next(
            (c for c in self.filtered_commands if c.id == command_id),
            None,
        )
        if not command:
            self._hide_command_palette()
            return

        before_slash = self.prompt[: self.command_trigger_position]
        self.prompt = before_slash + command.label + " "

        # Activate MCP servers associated with the prompt
        if command.mcp_server_ids:
            available_ids = {s.id for s in self.available_mcp_servers}
            valid_ids = [sid for sid in command.mcp_server_ids if sid in available_ids]
            if valid_ids:
                servers_to_add = [
                    s for s in self.available_mcp_servers if s.id in valid_ids
                ]
                existing_ids = {s.id for s in self.selected_mcp_servers}
                for server in servers_to_add:
                    if server.id not in existing_ids:
                        self.selected_mcp_servers.append(server)
                        existing_ids.add(server.id)
                for sid in valid_ids:
                    if sid not in self.temp_selected_mcp_servers:
                        self.temp_selected_mcp_servers.append(sid)
                        self.server_selection_state[sid] = True

        self._hide_command_palette()

    @rx.event
    def select_current_command(self) -> None:
        """Select the currently highlighted command in the palette."""
        if not self.show_command_palette or not self.filtered_commands:
            return

        if 0 <= self.selected_command_index < len(self.filtered_commands):
            command = self.filtered_commands[self.selected_command_index]
            self.select_command(command.id)

    @rx.event
    def dismiss_command_palette(self) -> None:
        """Dismiss the command palette without selecting."""
        self._hide_command_palette()
