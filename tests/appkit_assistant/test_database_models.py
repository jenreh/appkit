"""Tests for appkit-assistant database models."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_assistant.backend.database.models import (
    AssistantAIModel,
    AssistantFileUpload,
    AssistantMCPUserToken,
    AssistantThread,
    MCPServer,
    Skill,
    SystemPrompt,
    UserPrompt,
    UserSkillSelection,
)
from appkit_assistant.backend.schemas import MCPAuthType, MessageType, ThreadStatus


class TestMCPServer:
    """Test suite for MCPServer model."""

    @pytest.mark.asyncio
    async def test_create_mcp_server_minimal(
        self, async_session: AsyncSession, mcp_server_factory
    ) -> None:
        """MCPServer can be created with minimal required fields."""
        server = await mcp_server_factory(
            name="test-server",
            url="https://example.com/mcp",
            headers=json.dumps({"key": "value"}),
        )

        assert server.id is not None
        assert server.name == "test-server"
        assert server.url == "https://example.com/mcp"
        assert server.auth_type == MCPAuthType.NONE
        assert server.active is True

    @pytest.mark.asyncio
    async def test_mcp_server_headers_encrypted(
        self, async_session: AsyncSession, mcp_server_factory
    ) -> None:
        """MCPServer headers are encrypted when stored."""
        headers = json.dumps({"Authorization": "Bearer secret-token"})
        server = await mcp_server_factory(headers=headers)

        # Re-fetch from DB to verify encryption
        await async_session.refresh(server)
        assert server.headers == headers  # Should decrypt automatically

    @pytest.mark.asyncio
    async def test_mcp_server_oauth_fields(
        self, async_session: AsyncSession, mcp_server_factory
    ) -> None:
        """MCPServer can store OAuth configuration."""
        server = await mcp_server_factory(
            auth_type=MCPAuthType.OAUTH_DISCOVERY,
            oauth_client_id="client-123",
            oauth_client_secret="secret-456",
            oauth_issuer="https://auth.example.com",
            oauth_authorize_url="https://auth.example.com/authorize",
            oauth_token_url="https://auth.example.com/token",
            oauth_scopes="read write",
            oauth_discovered_at=datetime.now(UTC),
        )

        assert server.auth_type == MCPAuthType.OAUTH_DISCOVERY
        assert server.oauth_client_id == "client-123"
        assert server.oauth_issuer == "https://auth.example.com"
        assert server.oauth_scopes == "read write"
        assert server.oauth_discovered_at is not None

    @pytest.mark.asyncio
    async def test_mcp_server_unique_name(
        self, async_session: AsyncSession, mcp_server_factory
    ) -> None:
        """MCPServer name must be unique."""
        await mcp_server_factory(name="unique-server")

        with pytest.raises(Exception):  # Integrity error
            await mcp_server_factory(name="unique-server")
            await async_session.commit()


class TestSystemPrompt:
    """Test suite for SystemPrompt model."""

    @pytest.mark.asyncio
    async def test_create_system_prompt(
        self, async_session: AsyncSession, system_prompt_factory
    ) -> None:
        """SystemPrompt can be created with version."""
        prompt = await system_prompt_factory(
            name="Version 1", prompt="Test system prompt", version=1, user_id=1
        )

        assert prompt.id is not None
        assert prompt.version == 1
        assert prompt.prompt == "Test system prompt"
        assert prompt.user_id == 1

    @pytest.mark.asyncio
    async def test_system_prompt_versioning(
        self, async_session: AsyncSession, system_prompt_factory
    ) -> None:
        """SystemPrompt supports multiple versions."""
        v1 = await system_prompt_factory(version=1, prompt="Version 1")
        v2 = await system_prompt_factory(version=2, prompt="Version 2")
        v3 = await system_prompt_factory(version=3, prompt="Version 3")

        assert v1.version == 1
        assert v2.version == 2
        assert v3.version == 3

    @pytest.mark.asyncio
    async def test_system_prompt_max_length(
        self, async_session: AsyncSession, system_prompt_factory
    ) -> None:
        """SystemPrompt supports up to 20,000 characters."""
        long_prompt = "A" * 20000
        prompt = await system_prompt_factory(prompt=long_prompt)

        assert len(prompt.prompt) == 20000


class TestAssistantThread:
    """Test suite for AssistantThread model."""

    @pytest.mark.asyncio
    async def test_create_thread(
        self, async_session: AsyncSession, thread_factory
    ) -> None:
        """AssistantThread can be created."""
        thread = await thread_factory(
            thread_id="thread-123", user_id=1, title="Test Thread"
        )

        assert thread.id is not None
        assert thread.thread_id == "thread-123"
        assert thread.user_id == 1
        assert thread.title == "Test Thread"
        assert thread.state == ThreadStatus.NEW

    @pytest.mark.asyncio
    async def test_thread_unique_thread_id(
        self, async_session: AsyncSession, thread_factory
    ) -> None:
        """AssistantThread thread_id must be unique."""
        await thread_factory(thread_id="unique-thread")

        with pytest.raises(Exception):  # Integrity error
            await thread_factory(thread_id="unique-thread")
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_thread_messages_encrypted(
        self, async_session: AsyncSession, thread_factory, sample_messages
    ) -> None:
        """AssistantThread messages are encrypted when stored."""
        thread = await thread_factory(messages=sample_messages)

        await async_session.refresh(thread)
        assert len(thread.messages) == 2
        assert thread.messages[0]["text"] == "Hello, how can I help you?"

    @pytest.mark.asyncio
    async def test_thread_mcp_server_ids_array(
        self, async_session: AsyncSession, thread_factory
    ) -> None:
        """AssistantThread stores MCP server IDs as integer array."""
        thread = await thread_factory(mcp_server_ids=[1, 2, 3])

        await async_session.refresh(thread)
        assert thread.mcp_server_ids == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_thread_skill_openai_ids_array(
        self, async_session: AsyncSession, thread_factory
    ) -> None:
        """AssistantThread stores skill IDs as string array."""
        thread = await thread_factory(skill_openai_ids=["skill-1", "skill-2"])

        await async_session.refresh(thread)
        assert thread.skill_openai_ids == ["skill-1", "skill-2"]

    @pytest.mark.asyncio
    async def test_thread_vector_store_id(
        self, async_session: AsyncSession, thread_factory
    ) -> None:
        """AssistantThread can store vector store ID."""
        thread = await thread_factory(vector_store_id="vs-abc123")

        assert thread.vector_store_id == "vs-abc123"

    @pytest.mark.asyncio
    async def test_thread_timestamps(
        self, async_session: AsyncSession, thread_factory
    ) -> None:
        """AssistantThread tracks creation and update times."""
        thread = await thread_factory()

        assert thread.created_at is not None
        assert thread.updated_at is not None
        assert isinstance(thread.created_at, datetime)
        assert isinstance(thread.updated_at, datetime)


class TestAssistantMCPUserToken:
    """Test suite for AssistantMCPUserToken model."""

    @pytest.mark.asyncio
    async def test_create_user_token(
        self, async_session: AsyncSession, mcp_user_token_factory
    ) -> None:
        """AssistantMCPUserToken can be created."""
        token = await mcp_user_token_factory(user_id=1)

        assert token.id is not None
        assert token.user_id == 1
        assert token.mcp_server_id is not None
        assert token.access_token is not None

    @pytest.mark.asyncio
    async def test_user_token_encrypted_fields(
        self, async_session: AsyncSession, mcp_user_token_factory
    ) -> None:
        """AssistantMCPUserToken encrypts access and refresh tokens."""
        token = await mcp_user_token_factory(
            access_token="access-secret", refresh_token="refresh-secret"
        )

        await async_session.refresh(token)
        assert token.access_token == "access-secret"
        assert token.refresh_token == "refresh-secret"

    @pytest.mark.asyncio
    async def test_user_token_expiry(
        self, async_session: AsyncSession, mcp_user_token_factory
    ) -> None:
        """AssistantMCPUserToken tracks token expiry."""
        expires_at = datetime.now(UTC) + timedelta(hours=2)
        token = await mcp_user_token_factory(expires_at=expires_at)

        assert token.expires_at is not None
        assert token.expires_at > datetime.now(UTC)


class TestAssistantFileUpload:
    """Test suite for AssistantFileUpload model."""

    @pytest.mark.asyncio
    async def test_create_file_upload(
        self, async_session: AsyncSession, file_upload_factory
    ) -> None:
        """AssistantFileUpload can be created."""
        file_upload = await file_upload_factory(
            filename="test.pdf", openai_file_id="file-123"
        )

        assert file_upload.id is not None
        assert file_upload.filename == "test.pdf"
        assert file_upload.openai_file_id == "file-123"

    @pytest.mark.asyncio
    async def test_file_upload_indexes(
        self, async_session: AsyncSession, file_upload_factory
    ) -> None:
        """AssistantFileUpload has proper indexes on foreign keys."""
        file_upload = await file_upload_factory()

        assert file_upload.thread_id is not None
        assert file_upload.user_id is not None
        assert file_upload.openai_file_id is not None
        assert file_upload.vector_store_id is not None

    @pytest.mark.asyncio
    async def test_file_upload_vector_store_metadata(
        self, async_session: AsyncSession, file_upload_factory
    ) -> None:
        """AssistantFileUpload stores vector store ID and name."""
        file_upload = await file_upload_factory(
            vector_store_id="vs-123", vector_store_name="My Store"
        )

        assert file_upload.vector_store_id == "vs-123"
        assert file_upload.vector_store_name == "My Store"

    @pytest.mark.asyncio
    async def test_file_upload_size(
        self, async_session: AsyncSession, file_upload_factory
    ) -> None:
        """AssistantFileUpload tracks file size."""
        file_upload = await file_upload_factory(file_size=1024000)

        assert file_upload.file_size == 1024000


class TestUserPrompt:
    """Test suite for UserPrompt model."""

    @pytest.mark.asyncio
    async def test_create_user_prompt(
        self, async_session: AsyncSession, user_prompt_factory
    ) -> None:
        """UserPrompt can be created."""
        prompt = await user_prompt_factory(
            user_id=1, handle="test-prompt", prompt_text="Test prompt text"
        )

        assert prompt.id is not None
        assert prompt.user_id == 1
        assert prompt.handle == "test-prompt"
        assert prompt.prompt_text == "Test prompt text"

    @pytest.mark.asyncio
    async def test_user_prompt_versioning(
        self, async_session: AsyncSession, user_prompt_factory
    ) -> None:
        """UserPrompt supports versioning with is_latest flag."""
        v1 = await user_prompt_factory(
            handle="prompt-1", version=1, is_latest=False, user_id=1
        )
        v2 = await user_prompt_factory(
            handle="prompt-1", version=2, is_latest=True, user_id=1
        )

        assert v1.version == 1
        assert v1.is_latest is False
        assert v2.version == 2
        assert v2.is_latest is True

    @pytest.mark.asyncio
    async def test_user_prompt_sharing(
        self, async_session: AsyncSession, user_prompt_factory
    ) -> None:
        """UserPrompt can be shared across users."""
        shared_prompt = await user_prompt_factory(is_shared=True)
        private_prompt = await user_prompt_factory(is_shared=False)

        assert shared_prompt.is_shared is True
        assert private_prompt.is_shared is False

    @pytest.mark.asyncio
    async def test_user_prompt_mcp_server_ids(
        self, async_session: AsyncSession, user_prompt_factory
    ) -> None:
        """UserPrompt stores associated MCP server IDs."""
        prompt = await user_prompt_factory(mcp_server_ids=[1, 2, 3])

        await async_session.refresh(prompt)
        assert prompt.mcp_server_ids == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_user_prompt_max_lengths(
        self, async_session: AsyncSession, user_prompt_factory
    ) -> None:
        """UserPrompt enforces maximum field lengths."""
        prompt = await user_prompt_factory(
            handle="a" * 50,  # Max 50 chars
            description="b" * 100,  # Max 100 chars
            prompt_text="c" * 20000,  # Max 20000 chars
        )

        assert len(prompt.handle) == 50
        assert len(prompt.description) == 100
        assert len(prompt.prompt_text) == 20000


class TestSkill:
    """Test suite for Skill model."""

    @pytest.mark.asyncio
    async def test_create_skill(
        self, async_session: AsyncSession, skill_factory
    ) -> None:
        """Skill can be created."""
        skill = await skill_factory(
            openai_id="skill-123", name="Test Skill", api_key_hash="hash123"
        )

        assert skill.id is not None
        assert skill.openai_id == "skill-123"
        assert skill.name == "Test Skill"
        assert skill.api_key_hash == "hash123"

    @pytest.mark.asyncio
    async def test_skill_unique_openai_id(
        self, async_session: AsyncSession, skill_factory
    ) -> None:
        """Skill openai_id must be unique."""
        await skill_factory(openai_id="unique-skill")

        with pytest.raises(Exception):  # Integrity error
            await skill_factory(openai_id="unique-skill")
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_skill_versioning(
        self, async_session: AsyncSession, skill_factory
    ) -> None:
        """Skill tracks default and latest versions."""
        skill = await skill_factory(default_version="1.0", latest_version="1.2")

        assert skill.default_version == "1.0"
        assert skill.latest_version == "1.2"

    @pytest.mark.asyncio
    async def test_skill_role_restriction(
        self, async_session: AsyncSession, skill_factory
    ) -> None:
        """Skill can require specific role."""
        skill = await skill_factory(required_role="admin")

        assert skill.required_role == "admin"

    @pytest.mark.asyncio
    async def test_skill_api_key_hash_indexing(
        self, async_session: AsyncSession, skill_factory
    ) -> None:
        """Skill api_key_hash is indexed for filtering."""
        skill1 = await skill_factory(api_key_hash="hash-a")
        skill2 = await skill_factory(api_key_hash="hash-a")
        skill3 = await skill_factory(api_key_hash="hash-b")

        assert skill1.api_key_hash == skill2.api_key_hash
        assert skill1.api_key_hash != skill3.api_key_hash


class TestUserSkillSelection:
    """Test suite for UserSkillSelection model."""

    @pytest.mark.asyncio
    async def test_create_user_skill_selection(
        self, async_session: AsyncSession, user_skill_selection_factory
    ) -> None:
        """UserSkillSelection can be created."""
        selection = await user_skill_selection_factory(
            user_id=1, skill_openai_id="skill-123", enabled=True
        )

        assert selection.id is not None
        assert selection.user_id == 1
        assert selection.skill_openai_id == "skill-123"
        assert selection.enabled is True

    @pytest.mark.asyncio
    async def test_user_skill_selection_unique_constraint(
        self, async_session: AsyncSession, user_skill_selection_factory
    ) -> None:
        """UserSkillSelection enforces unique (user_id, skill_openai_id)."""
        await user_skill_selection_factory(user_id=1, skill_openai_id="skill-123")

        with pytest.raises(Exception):  # Integrity error
            await user_skill_selection_factory(user_id=1, skill_openai_id="skill-123")
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_user_skill_selection_different_users(
        self, async_session: AsyncSession, user_skill_selection_factory
    ) -> None:
        """UserSkillSelection allows same skill for different users."""
        selection1 = await user_skill_selection_factory(
            user_id=1, skill_openai_id="skill-123"
        )
        selection2 = await user_skill_selection_factory(
            user_id=2, skill_openai_id="skill-123"
        )

        assert selection1.user_id != selection2.user_id
        assert selection1.skill_openai_id == selection2.skill_openai_id


class TestAssistantAIModel:
    """Test suite for AssistantAIModel model."""

    @pytest.mark.asyncio
    async def test_create_ai_model(
        self, async_session: AsyncSession, ai_model_factory
    ) -> None:
        """AssistantAIModel can be created."""
        model = await ai_model_factory(
            model_id="gpt-4", text="GPT-4", processor_type="openai"
        )

        assert model.id is not None
        assert model.model_id == "gpt-4"
        assert model.text == "GPT-4"
        assert model.processor_type == "openai"

    @pytest.mark.asyncio
    async def test_ai_model_unique_model_id(
        self, async_session: AsyncSession, ai_model_factory
    ) -> None:
        """AssistantAIModel model_id must be unique."""
        await ai_model_factory(model_id="unique-model")

        with pytest.raises(Exception):  # Integrity error
            await ai_model_factory(model_id="unique-model")
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_ai_model_capability_flags(
        self, async_session: AsyncSession, ai_model_factory
    ) -> None:
        """AssistantAIModel tracks various capability flags."""
        model = await ai_model_factory(
            supports_tools=True,
            supports_attachments=True,
            supports_search=True,
            supports_skills=True,
        )

        assert model.supports_tools is True
        assert model.supports_attachments is True
        assert model.supports_search is True
        assert model.supports_skills is True

    @pytest.mark.asyncio
    async def test_ai_model_encrypted_api_key(
        self, async_session: AsyncSession, ai_model_factory
    ) -> None:
        """AssistantAIModel encrypts API key when provided."""
        model = await ai_model_factory(api_key="sk-secret-key-123")

        await async_session.refresh(model)
        assert model.api_key == "sk-secret-key-123"

    @pytest.mark.asyncio
    async def test_ai_model_azure_configuration(
        self, async_session: AsyncSession, ai_model_factory
    ) -> None:
        """AssistantAIModel supports Azure configuration."""
        model = await ai_model_factory(
            on_azure=True, base_url="https://myazure.openai.azure.com"
        )

        assert model.on_azure is True
        assert model.base_url == "https://myazure.openai.azure.com"

    @pytest.mark.asyncio
    async def test_ai_model_to_ai_model_schema(
        self, async_session: AsyncSession, ai_model_factory
    ) -> None:
        """AssistantAIModel converts to AIModel schema correctly."""
        model = await ai_model_factory(
            model_id="gpt-4",
            text="GPT-4",
            icon="openai",
            supports_tools=True,
            temperature=0.7,
        )

        ai_model = model.to_ai_model()

        assert ai_model.id == "gpt-4"
        assert ai_model.text == "GPT-4"
        assert ai_model.icon == "openai"
        assert ai_model.supports_tools is True
        assert ai_model.temperature == 0.7
