"""State management for OpenAI Agents."""

import logging
from collections.abc import AsyncGenerator
from typing import Any

import reflex as rx

from appkit_assistant.backend.models import OpenAIAgent
from appkit_assistant.backend.repositories import (
    OpenAIAgentRepository,
)

logger = logging.getLogger(__name__)


class OpenAIAgentState(rx.State):
    """State class for managing OpenAI Agents."""

    agents: list[OpenAIAgent] = []
    current_agent: OpenAIAgent | None = None
    loading: bool = False

    async def load_agents(self) -> None:
        """Load all OpenAI Agents from the database."""
        self.loading = True
        try:
            self.agents = await OpenAIAgentRepository.get_all()
            logger.debug("Loaded %d OpenAI Agents", len(self.agents))
        except Exception as e:
            logger.error("Failed to load OpenAI Agents: %s", e)
            raise
        finally:
            self.loading = False

    async def load_agents_with_toast(self) -> AsyncGenerator[Any, Any]:
        """Load agents and show an error toast on failure."""
        try:
            await self.load_agents()
        except Exception:
            yield rx.toast.error(
                "Fehler beim Laden der Azure Agenten.",
                position="top-right",
            )

    async def get_agent(self, agent_id: int) -> None:
        """Get a specific OpenAI Agent by ID."""
        try:
            self.current_agent = await OpenAIAgentRepository.get_by_id(agent_id)
            if not self.current_agent:
                logger.warning("OpenAI Agent with ID %d not found", agent_id)
        except Exception as e:
            logger.error("Failed to get OpenAI Agent %d: %s", agent_id, e)

    async def set_current_agent(self, agent: OpenAIAgent) -> None:
        """Set the current agent."""
        self.current_agent = agent

    async def add_agent(self, form_data: dict[str, Any]) -> AsyncGenerator[Any, Any]:
        """Add a new OpenAI Agent."""
        try:
            # Convert is_active string to boolean
            is_active_str = form_data.get("is_active", "True")
            is_active = is_active_str == "on"

            agent = await OpenAIAgentRepository.create(
                name=form_data["name"],
                endpoint=form_data["endpoint"],
                api_key=form_data["api_key"],
                description=form_data.get("description") or None,
                is_active=is_active,
            )

            await self.load_agents()
            yield rx.toast.info(
                "Azure Agent {} wurde hinzugefügt.".format(form_data["name"]),
                position="top-right",
            )
            logger.debug("Added OpenAI Agent: %s", agent.name)

        except ValueError as e:
            logger.error("Invalid form data for OpenAI Agent: %s", e)
            yield rx.toast.error(
                str(e),
                position="top-right",
            )
        except Exception as e:
            logger.error("Failed to add OpenAI Agent: %s", e)
            yield rx.toast.error(
                "Fehler beim Hinzufügen des Azure Agents.",
                position="top-right",
            )

    async def modify_agent(self, form_data: dict[str, Any]) -> AsyncGenerator[Any, Any]:
        """Modify an existing OpenAI Agent."""
        if not self.current_agent:
            yield rx.toast.error(
                "Kein Agent ausgewählt.",
                position="top-right",
            )
            return

        try:
            # Convert is_active string to boolean
            is_active_str = form_data.get("is_active", "off")
            is_active = is_active_str == "on"

            updated_agent = await OpenAIAgentRepository.update(
                agent_id=self.current_agent.id,
                name=form_data["name"],
                endpoint=form_data["endpoint"],
                api_key=form_data["api_key"],
                description=form_data.get("description") or None,
                is_active=is_active,
            )

            if updated_agent:
                await self.load_agents()
                yield rx.toast.info(
                    "Azure Agent {} wurde aktualisiert.".format(form_data["name"]),
                    position="top-right",
                )
                logger.debug("Updated OpenAI Agent: %s", updated_agent.name)
            else:
                yield rx.toast.error(
                    "Azure Agent konnte nicht gefunden werden.",
                    position="top-right",
                )

        except ValueError as e:
            logger.error("Invalid form data for OpenAI Agent: %s", e)
            yield rx.toast.error(
                str(e),
                position="top-right",
            )
        except Exception as e:
            logger.error("Failed to update OpenAI Agent: %s", e)
            yield rx.toast.error(
                "Fehler beim Aktualisieren des Azure Agents.",
                position="top-right",
            )

    async def delete_agent(self, agent_id: int) -> AsyncGenerator[Any, Any]:
        """Delete an OpenAI Agent."""
        try:
            agent = await OpenAIAgentRepository.get_by_id(agent_id)
            if not agent:
                yield rx.toast.error(
                    "Azure Agent nicht gefunden.",
                    position="top-right",
                )
                return

            agent_name = agent.name
            success = await OpenAIAgentRepository.delete(agent_id)

            if success:
                await self.load_agents()
                yield rx.toast.info(
                    f"Azure Agent {agent_name} wurde gelöscht.",
                    position="top-right",
                )
                logger.debug("Deleted OpenAI Agent: %s", agent_name)
            else:
                yield rx.toast.error(
                    "Azure Agent konnte nicht gelöscht werden.",
                    position="top-right",
                )

        except Exception as e:
            logger.error("Failed to delete OpenAI Agent %d: %s", agent_id, e)
            yield rx.toast.error(
                "Fehler beim Löschen des Azure Agents.",
                position="top-right",
            )

    @rx.var
    def agent_count(self) -> int:
        """Get the number of agents."""
        return len(self.agents)

    @rx.var
    def has_agents(self) -> bool:
        """Check if there are any agents."""
        return len(self.agents) > 0
