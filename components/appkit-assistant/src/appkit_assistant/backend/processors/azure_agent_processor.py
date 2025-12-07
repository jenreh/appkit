"""Processor for Azure AI Projects named agents using responses API.

Extends OpenAIResponsesProcessor to work with pre-configured agents
managed in Azure AI Projects. Agents are referenced by name and
retrieved dynamically at request time.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from appkit_assistant.backend.models import (
    AIModel,
    Chunk,
    ChunkType,
    MCPServer,
    Message,
)
from appkit_assistant.backend.processors.openai_responses_processor import (
    OpenAIResponsesProcessor,
)

logger = logging.getLogger(__name__)


class AzureAgentProcessor(OpenAIResponsesProcessor):
    """Process requests using Azure AI Projects named agents.

    Extends OpenAIResponsesProcessor to leverage Azure-managed agents
    with the responses API, providing full event streaming, tool handling,
    and error recovery.

    Agents are identified by name and retrieved from the Azure AI Projects
    service. This processor handles agent initialization, streaming,
    and tool reference standardization.

    Attributes:
        endpoint: Azure AI Projects endpoint URL
        _project_client: AIProjectClient for agent management
    """

    def __init__(
        self,
        models: dict[str, AIModel],
        endpoint: str | None = None,
        api_key: str | None = None,
        name: str | None = None,
    ) -> None:
        """Initialize the Azure Agent processor.

        Sets up the OpenAI client and optionally initializes Azure
        AI Projects client if endpoint is provided.

        Args:
            models: Dictionary of supported AIModel configurations
            endpoint: Azure AI Projects endpoint URL (optional)
            api_key: OpenAI API key (optional, uses DefaultAzureCredential
                if not provided)

        Raises:
            ValueError: If both endpoint and credentials are missing
        """
        super().__init__(models=models)
        self.endpoint = endpoint
        self.name = name or None
        self._api_key = api_key
        self._project_client: AIProjectClient | None = None
        self._current_reasoning_session: str | None = None

        if self.endpoint:
            self._initialize_clients()

    def _initialize_clients(self) -> None:
        """Initialize Azure AI Projects and OpenAI clients.

        Uses DefaultAzureCredential for Azure authentication,
        creates AIProjectClient for agent management, and initializes
        OpenAI client from the Azure project connection.

        Logs: Debug messages for client initialization success/failure
        """
        try:
            credential = DefaultAzureCredential()
            self._project_client = AIProjectClient(
                endpoint=self.endpoint,
                credential=credential,
            )
            logger.debug(
                "Initialized Azure AI Projects client",
                extra={"endpoint": self.endpoint},
            )

            # Get OpenAI client from project connection if available
            try:
                # Get an existing agent
                self.name = self._project_client.agents.get(agent_name=self.name)
                logger.debug("Retrieved agent: %s", self.name)
                self.client = self._project_client.get_openai_client()
                logger.debug("Retrieved OpenAI client from Azure AI Projects")
            except Exception as e:
                logger.debug(
                    "Could not get OpenAI client from project connection: %s",
                    str(e),
                )

        except Exception as e:
            logger.error("Failed to initialize Azure clients: %s", str(e))
            raise

    async def process(
        self,
        messages: list[Message],
        model_id: str,
        files: list[str] | None = None,  # noqa: ARG002
        mcp_servers: list[MCPServer] | None = None,  # noqa: ARG002
        payload: dict[str, Any] | None = None,
    ) -> AsyncGenerator[Chunk, None]:
        """Process messages using simplified content accumulator pattern."""
        if not self.client:
            raise ValueError("OpenAI Client not initialized.")

        if model_id not in self.models:
            msg = f"Model {model_id} not supported by OpenAI processor"
            raise ValueError(msg)

        try:
            session = await self._create_agent_request(messages, payload)

            if hasattr(session, "__aiter__"):  # Streaming
                async for event in session:
                    chunk = self._handle_event(event)
                    if chunk:
                        yield chunk
            else:  # Non-streaming
                content = self._extract_responses_content(session)
                if content:
                    yield Chunk(
                        type=ChunkType.TEXT,
                        text=content,
                        chunk_metadata={
                            "source": "responses_api",
                            "streaming": "false",
                        },
                    )
        except Exception as e:
            raise e

    async def _create_agent_request(
        self,
        messages: list[Message],
        payload: dict[str, Any] | None = None,
        stream: bool = True,
    ) -> Any:
        """Create a simplified responses API request."""
        # Convert messages to responses format with system message
        input_messages = await self._convert_messages_to_responses_format(
            messages, mcp_prompt="", use_system_prompt=False
        )

        params = {
            "input": input_messages,
            "stream": stream,
            "extra_body": {"agent": {"name": self.name, "type": "agent_reference"}},
            **(payload or {}),
        }

        logger.debug("Responses API request params: %s", params)
        return await self.client.responses.create(**params)
