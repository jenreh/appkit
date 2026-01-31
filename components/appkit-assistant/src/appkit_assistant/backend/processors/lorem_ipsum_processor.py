"""
Lorem Ipsum processor for generating random text responses.
"""

import asyncio
import logging
import random
from collections.abc import AsyncGenerator
from typing import Any

from appkit_assistant.backend.models import (
    AIModel,
    Chunk,
    ChunkType,
    MCPServer,
    Message,
)
from appkit_assistant.backend.processor import Processor

logger = logging.getLogger(__name__)

# List of Lorem Ipsum paragraphs for random selection
LOREM_PARAGRAPHS = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",  # noqa: E501
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",  # noqa: E501
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",  # noqa: E501
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",  # noqa: E501
    "Integer posuere erat a ante venenatis dapibus posuere velit aliquet.",
    "Cras mattis consectetur purus sit amet fermentum. Nullam quis risus eget urna mollis ornare vel eu leo.",  # noqa: E501
    "Donec sed odio dui. Maecenas faucibus mollis interdum. Cras justo odio, dapibus ac facilisis in, egestas eget quam.",  # noqa: E501
    "Vestibulum id ligula porta felis euismod semper. Lorem ipsum dolor sit amet, consectetur adipiscing elit.",  # noqa: E501
]

# Models supported by this processor as a dictionary with model ID as the key
LOREM_MODELS = {
    "lorem-short": AIModel(
        id="lorem-short",
        text="Lorem Ipsum",
        icon="codesandbox",
        model="lorem-short",
        stream=True,
        supports_attachments=True,
        supports_tools=True,
    )
}


class LoremIpsumProcessor(Processor):
    """Processor that generates Lorem Ipsum text responses."""

    def __init__(self, models: dict[str, AIModel] = LOREM_MODELS) -> None:
        """Initialize the Lorem Ipsum processor."""
        self.models = models
        logger.debug("Lorem Ipsum processor initialized")

    async def process(
        self,
        messages: list[Message],  # noqa: ARG002
        model_id: str,
        files: list[str] | None = None,  # noqa: ARG002
        mcp_servers: list[MCPServer] | None = None,  # noqa: ARG002
        cancellation_token: asyncio.Event | None = None,
        **kwargs: Any,  # noqa: ARG002
    ) -> AsyncGenerator[Chunk, None]:
        """
        Generate a Lorem Ipsum response of varying lengths based on the model_id.

        Args:
            messages: List of messages (ignored for this processor).
            model_id: The model ID (determines response length).
            files: Optional list of files (ignored for this processor).
            mcp_servers: Optional list of MCP servers (ignored for this processor).
            cancellation_token: Optional event to signal cancellation.
            **kwargs: Additional arguments.

        Returns:
            An async generator that yields Chunk objects with text content.
        """
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not supported by Lorem Ipsum processor")

        # Simulate thinking process
        yield Chunk(
            type=ChunkType.THINKING,
            text="I think i need to generate Lorem Ipsum content...",
            chunk_metadata={"source": "lorem_ipsum", "model": model_id},
        )
        await asyncio.sleep(0.5)

        num_paragraphs = random.randint(4, 8)  # noqa: S311
        for i in range(num_paragraphs):
            if cancellation_token and cancellation_token.is_set():
                break
            paragraph = random.choice(LOREM_PARAGRAPHS)  # noqa: S311
            words = paragraph.split()
            for word in words:
                if cancellation_token and cancellation_token.is_set():
                    break
                content = word + " "
                await asyncio.sleep(0.01)
                yield Chunk(
                    type=ChunkType.TEXT,
                    text=content,
                    chunk_metadata={
                        "source": "lorem_ipsum",
                        "paragraph": str(i + 1),
                        "total_paragraphs": str(num_paragraphs),
                    },
                )

            if i < num_paragraphs - 1:
                yield Chunk(
                    type=ChunkType.TEXT,
                    text="\n\n",
                    chunk_metadata={
                        "source": "lorem_ipsum",
                        "type": "paragraph_separator",
                    },
                )

        yield Chunk(
            type=ChunkType.THINKING,
            text="So, generated enough Lorem Ipsum for you!",
            chunk_metadata={"source": "lorem_ipsum", "model": model_id},
        )

    def get_supported_models(self) -> dict[str, AIModel]:
        """
        Get dictionary of supported models.

        Returns:
            Dictionary mapping model IDs to AIModel objects.
        """
        return self.models
