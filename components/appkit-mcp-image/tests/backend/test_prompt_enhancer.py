"""Unit tests for OpenAIPromptEnhancer service."""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from appkit_mcp_image.backend.generators.openai import OpenAIPromptEnhancer

logger = logging.getLogger(__name__)


# Fixtures
@pytest.fixture
def mock_openai_client() -> MagicMock:
    """Mock AsyncAzureOpenAI client."""
    return MagicMock()


@pytest.fixture
def prompt_enhancer(mock_openai_client: MagicMock) -> OpenAIPromptEnhancer:
    """Create OpenAIPromptEnhancer instance with mocked client."""
    return OpenAIPromptEnhancer(mock_openai_client, "gpt-4")


@pytest.fixture
def caplog_handler(caplog) -> object:
    """Enable caplog at DEBUG level."""
    caplog.set_level(logging.DEBUG)
    return caplog


# Initialization Tests
class TestOpenAIPromptEnhancerInit:
    """Tests for OpenAIPromptEnhancer initialization."""

    def test_init_stores_client(self, mock_openai_client: MagicMock) -> None:
        """Test that client is stored on initialization."""
        enhancer = OpenAIPromptEnhancer(mock_openai_client, "gpt-4")

        assert enhancer.client is mock_openai_client

    def test_init_with_different_clients(self) -> None:
        """Test initialization with different client instances."""
        client1 = MagicMock()
        client2 = MagicMock()

        enhancer1 = OpenAIPromptEnhancer(client1, "gpt-4")
        enhancer2 = OpenAIPromptEnhancer(client2, "gpt-4")

        assert enhancer1.client is client1
        assert enhancer2.client is client2
        assert enhancer1.client is not enhancer2.client


# enhance Tests
class TestEnhancePrompt:
    """Tests for enhance method."""

    @pytest.mark.asyncio
    async def test_enhance_success(
        self, prompt_enhancer: OpenAIPromptEnhancer, caplog_handler
    ) -> None:
        """Test successful prompt enhancement."""
        prompt_enhancer.client.chat.completions.create = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Enhanced prompt for image generation"))
        ]
        prompt_enhancer.client.chat.completions.create.return_value = mock_response

        result = await prompt_enhancer.enhance("simple prompt")

        assert result == "Enhanced prompt for image generation"
        assert "Starting prompt enhancement" in caplog_handler.text
        assert "Prompt enhanced successfully" in caplog_handler.text

    @pytest.mark.asyncio
    async def test_enhance_calls_correct_model(
        self, prompt_enhancer: OpenAIPromptEnhancer
    ) -> None:
        """Test that enhancement calls correct model."""
        prompt_enhancer.client.chat.completions.create = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Enhanced"))]
        prompt_enhancer.client.chat.completions.create.return_value = mock_response

        await prompt_enhancer.enhance("test prompt")

        call_kwargs = prompt_enhancer.client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_enhance_sets_stream_false(
        self, prompt_enhancer: OpenAIPromptEnhancer
    ) -> None:
        """Test that stream is disabled."""
        prompt_enhancer.client.chat.completions.create = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Enhanced"))]
        prompt_enhancer.client.chat.completions.create.return_value = mock_response

        await prompt_enhancer.enhance("test prompt")

        call_kwargs = prompt_enhancer.client.chat.completions.create.call_args.kwargs
        assert call_kwargs["stream"] is False

    @pytest.mark.asyncio
    async def test_enhance_sends_correct_messages(
        self, prompt_enhancer: OpenAIPromptEnhancer
    ) -> None:
        """Test that correct system and user messages are sent."""
        prompt_enhancer.client.chat.completions.create = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Enhanced"))]
        prompt_enhancer.client.chat.completions.create.return_value = mock_response

        test_prompt = "create a beautiful landscape"
        await prompt_enhancer.enhance(test_prompt)

        call_kwargs = prompt_enhancer.client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]

        # Verify system message
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "image generation assistant" in messages[0]["content"]
        assert "optimizing user prompts" in messages[0]["content"]

        # Verify user message
        assert messages[1]["role"] == "user"
        assert test_prompt in messages[1]["content"]
        assert "Enhance this prompt" in messages[1]["content"]

    @pytest.mark.asyncio
    async def test_enhance_strips_whitespace(
        self, prompt_enhancer: OpenAIPromptEnhancer
    ) -> None:
        """Test that response is stripped of whitespace."""
        prompt_enhancer.client.chat.completions.create = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="  Enhanced prompt  \n"))
        ]
        prompt_enhancer.client.chat.completions.create.return_value = mock_response

        result = await prompt_enhancer.enhance("test")

        assert result == "Enhanced prompt"

    @pytest.mark.asyncio
    async def test_enhance_returns_original_on_empty_response(
        self, prompt_enhancer: OpenAIPromptEnhancer, caplog_handler
    ) -> None:
        """Test that original prompt is returned when enhancement returns empty."""
        prompt_enhancer.client.chat.completions.create = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=""))]
        prompt_enhancer.client.chat.completions.create.return_value = mock_response

        original_prompt = "simple prompt"
        result = await prompt_enhancer.enhance(original_prompt)

        assert result == original_prompt
        assert "Prompt enhancement returned empty" in caplog_handler.text

    @pytest.mark.asyncio
    async def test_enhance_returns_original_on_whitespace_response(
        self, prompt_enhancer: OpenAIPromptEnhancer
    ) -> None:
        """Test that original prompt is returned when response is only whitespace."""
        prompt_enhancer.client.chat.completions.create = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="   \n  \t  "))]
        prompt_enhancer.client.chat.completions.create.return_value = mock_response

        original_prompt = "test prompt"
        result = await prompt_enhancer.enhance(original_prompt)

        assert result == original_prompt

    @pytest.mark.asyncio
    async def test_enhance_returns_original_on_api_error(
        self, prompt_enhancer: OpenAIPromptEnhancer, caplog_handler
    ) -> None:
        """Test that original prompt is returned on API error."""
        prompt_enhancer.client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error: 401 Unauthorized")
        )

        original_prompt = "test prompt"
        result = await prompt_enhancer.enhance(original_prompt)

        assert result == original_prompt
        assert "Prompt enhancement failed" in caplog_handler.text
        assert "API Error" in caplog_handler.text

    @pytest.mark.asyncio
    async def test_enhance_returns_original_on_timeout(
        self, prompt_enhancer: OpenAIPromptEnhancer, caplog_handler
    ) -> None:
        """Test that original prompt is returned on timeout."""
        prompt_enhancer.client.chat.completions.create = AsyncMock(
            side_effect=TimeoutError("Request timed out")
        )

        original_prompt = "test prompt"
        result = await prompt_enhancer.enhance(original_prompt)

        assert result == original_prompt
        assert "Prompt enhancement failed" in caplog_handler.text


# Parametrized Tests
class TestEnhanceParametrized:
    """Parametrized tests for enhance method."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("input_prompt", "expected_enhanced"),
        [
            ("cat", "A majestic cat in natural lighting"),
            ("landscape", "Scenic landscape with mountains"),
            ("portrait", "Professional portrait photography"),
            ("", ""),  # Empty prompt returns empty
        ],
        ids=["simple_subject", "landscape", "portrait", "empty_prompt"],
    )
    async def test_enhance_various_prompts(
        self,
        prompt_enhancer: OpenAIPromptEnhancer,
        input_prompt: str,
        expected_enhanced: str,
    ) -> None:
        """Test enhancement of various prompt types."""
        prompt_enhancer.client.chat.completions.create = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=expected_enhanced))
        ]
        prompt_enhancer.client.chat.completions.create.return_value = mock_response

        result = await prompt_enhancer.enhance(input_prompt)

        assert result == expected_enhanced

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("response_content", "stripped_content"),
        [
            ("Enhanced prompt", "Enhanced prompt"),
            ("  Enhanced prompt  ", "Enhanced prompt"),
            ("\nEnhanced prompt\n", "Enhanced prompt"),
            ("\t Enhanced prompt \t", "Enhanced prompt"),
            ("  \n  Enhanced prompt  \n  ", "Enhanced prompt"),
        ],
        ids=[
            "no_whitespace",
            "surrounding_spaces",
            "surrounding_newlines",
            "surrounding_tabs",
            "mixed_whitespace",
        ],
    )
    async def test_enhance_strips_various_whitespace(
        self,
        prompt_enhancer: OpenAIPromptEnhancer,
        response_content: str,
        stripped_content: str,
    ) -> None:
        """Test that various whitespace patterns are stripped."""
        prompt_enhancer.client.chat.completions.create = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=response_content))]
        prompt_enhancer.client.chat.completions.create.return_value = mock_response

        result = await prompt_enhancer.enhance("test")

        assert result == stripped_content

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error_type", "error_message"),
        [
            (Exception, "API Error: 401 Unauthorized"),
            (TimeoutError, "Request timed out after 30s"),
            (ConnectionError, "Failed to connect to API"),
            (RuntimeError, "Unexpected runtime error"),
        ],
        ids=["generic_exception", "timeout", "connection_error", "runtime_error"],
    )
    async def test_enhance_handles_various_errors(
        self,
        prompt_enhancer: OpenAIPromptEnhancer,
        error_type,
        error_message: str,
        caplog_handler,
    ) -> None:
        """Test that various error types are handled gracefully."""
        prompt_enhancer.client.chat.completions.create = AsyncMock(
            side_effect=error_type(error_message)
        )

        original_prompt = "test prompt"
        result = await prompt_enhancer.enhance(original_prompt)

        assert result == original_prompt
        assert "Prompt enhancement failed" in caplog_handler.text


# Long Prompt Tests
class TestEnhanceLongPrompts:
    """Tests for enhancement of long prompts."""

    @pytest.mark.asyncio
    async def test_enhance_long_prompt(
        self, prompt_enhancer: OpenAIPromptEnhancer
    ) -> None:
        """Test enhancement of long prompt."""
        long_prompt = " ".join(["word"] * 100)
        prompt_enhancer.client.chat.completions.create = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Enhanced long prompt"))
        ]
        prompt_enhancer.client.chat.completions.create.return_value = mock_response

        result = await prompt_enhancer.enhance(long_prompt)

        assert result == "Enhanced long prompt"

    @pytest.mark.asyncio
    async def test_enhance_special_characters(
        self, prompt_enhancer: OpenAIPromptEnhancer
    ) -> None:
        """Test enhancement of prompt with special characters."""
        special_prompt = "🎨 Beautiful cat 🐱 with énhancéd wörds!"
        prompt_enhancer.client.chat.completions.create = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Enhanced emoji prompt"))
        ]
        prompt_enhancer.client.chat.completions.create.return_value = mock_response

        result = await prompt_enhancer.enhance(special_prompt)

        assert result == "Enhanced emoji prompt"
        call_kwargs = prompt_enhancer.client.chat.completions.create.call_args.kwargs
        assert special_prompt in call_kwargs["messages"][1]["content"]


# Call Sequence Tests
class TestEnhanceCallSequence:
    """Tests for enhance call sequence and independence."""

    @pytest.mark.asyncio
    async def test_enhance_multiple_calls_independent(
        self, prompt_enhancer: OpenAIPromptEnhancer
    ) -> None:
        """Test that multiple enhancement calls are independent."""
        prompt_enhancer.client.chat.completions.create = AsyncMock()
        mock_response1 = MagicMock()
        mock_response1.choices = [
            MagicMock(message=MagicMock(content="Enhanced prompt 1"))
        ]
        mock_response2 = MagicMock()
        mock_response2.choices = [
            MagicMock(message=MagicMock(content="Enhanced prompt 2"))
        ]
        prompt_enhancer.client.chat.completions.create.side_effect = [
            mock_response1,
            mock_response2,
        ]

        result1 = await prompt_enhancer.enhance("prompt 1")
        result2 = await prompt_enhancer.enhance("prompt 2")

        assert result1 == "Enhanced prompt 1"
        assert result2 == "Enhanced prompt 2"
        assert prompt_enhancer.client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_enhance_state_not_modified(
        self, prompt_enhancer: OpenAIPromptEnhancer, mock_openai_client: MagicMock
    ) -> None:
        """Test that enhance does not modify internal state."""
        prompt_enhancer.client.chat.completions.create = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Enhanced"))]
        prompt_enhancer.client.chat.completions.create.return_value = mock_response

        original_client = prompt_enhancer.client
        await prompt_enhancer.enhance("test")

        assert prompt_enhancer.client is original_client
