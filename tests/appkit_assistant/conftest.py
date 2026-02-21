"""Pytest fixtures for appkit-assistant tests."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import pytest_asyncio
from faker import Faker
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
from appkit_assistant.backend.database.repositories import (
    AIModelRepository,
    FileUploadRepository,
    MCPServerRepository,
    SkillRepository,
    SystemPromptRepository,
    ThreadRepository,
    UserPromptRepository,
    UserSkillRepository,
)
from appkit_assistant.backend.schemas import (
    MCPAuthType,
    Message,
    MessageType,
    ThreadStatus,
)


@pytest.fixture
def faker_instance() -> Faker:
    """Provide a Faker instance for generating realistic test data."""
    return Faker()


# Repository fixtures
@pytest_asyncio.fixture
async def mcp_server_repo() -> MCPServerRepository:
    """Provide MCPServerRepository instance."""
    return MCPServerRepository()


@pytest_asyncio.fixture
async def system_prompt_repo() -> SystemPromptRepository:
    """Provide SystemPromptRepository instance."""
    return SystemPromptRepository()


@pytest_asyncio.fixture
async def thread_repo() -> ThreadRepository:
    """Provide ThreadRepository instance."""
    return ThreadRepository()


@pytest_asyncio.fixture
async def file_upload_repo() -> FileUploadRepository:
    """Provide FileUploadRepository instance."""
    return FileUploadRepository()


@pytest_asyncio.fixture
async def user_prompt_repo() -> UserPromptRepository:
    """Provide UserPromptRepository instance."""
    return UserPromptRepository()


@pytest_asyncio.fixture
async def skill_repo() -> SkillRepository:
    """Provide SkillRepository instance."""
    return SkillRepository()


@pytest_asyncio.fixture
async def user_skill_repo() -> UserSkillRepository:
    """Provide UserSkillRepository instance."""
    return UserSkillRepository()


@pytest_asyncio.fixture
async def ai_model_repo() -> AIModelRepository:
    """Provide AIModelRepository instance."""
    return AIModelRepository()


# Model factory fixtures
@pytest_asyncio.fixture
async def mcp_server_factory(async_session: AsyncSession, faker_instance: Faker):
    """Factory for creating test MCPServer instances."""

    async def _create_server(**kwargs: Any) -> MCPServer:
        defaults = {
            "name": f"test-server-{faker_instance.uuid4()[:8]}",
            "description": faker_instance.sentence(),
            "url": f"https://{faker_instance.domain_name()}/mcp",
            "headers": json.dumps({"Authorization": f"Bearer {faker_instance.uuid4()}"}),
            "prompt": faker_instance.sentence(nb_words=10),
            "auth_type": MCPAuthType.NONE,
            "active": True,
            "required_role": None,
        }
        defaults.update(kwargs)
        server = MCPServer(**defaults)
        async_session.add(server)
        await async_session.flush()
        await async_session.refresh(server)
        return server

    return _create_server


@pytest_asyncio.fixture
async def system_prompt_factory(async_session: AsyncSession, faker_instance: Faker):
    """Factory for creating test SystemPrompt instances."""

    async def _create_prompt(**kwargs: Any) -> SystemPrompt:
        defaults = {
            "name": f"System Prompt {faker_instance.word()}",
            "prompt": faker_instance.paragraph(nb_sentences=5),
            "version": 1,
            "user_id": 1,
            "created_at": datetime.now(UTC),
        }
        defaults.update(kwargs)
        prompt = SystemPrompt(**defaults)
        async_session.add(prompt)
        await async_session.flush()
        await async_session.refresh(prompt)
        return prompt

    return _create_prompt


@pytest_asyncio.fixture
async def thread_factory(async_session: AsyncSession, faker_instance: Faker):
    """Factory for creating test AssistantThread instances."""

    async def _create_thread(**kwargs: Any) -> AssistantThread:
        defaults = {
            "thread_id": faker_instance.uuid4(),
            "user_id": 1,
            "title": faker_instance.sentence(nb_words=4),
            "state": ThreadStatus.NEW,
            "ai_model": "gpt-4",
            "active": False,
            "messages": [],
            "mcp_server_ids": [],
            "skill_openai_ids": [],
            "vector_store_id": None,
        }
        defaults.update(kwargs)
        thread = AssistantThread(**defaults)
        async_session.add(thread)
        await async_session.flush()
        await async_session.refresh(thread)
        return thread

    return _create_thread


@pytest_asyncio.fixture
async def file_upload_factory(async_session: AsyncSession, faker_instance: Faker):
    """Factory for creating test AssistantFileUpload instances."""

    async def _create_file(**kwargs: Any) -> AssistantFileUpload:
        # Create a thread first if not provided
        if "thread_id" not in kwargs:
            thread = AssistantThread(
                thread_id=faker_instance.uuid4(),
                user_id=kwargs.get("user_id", 1),
                title="Test Thread",
                state=ThreadStatus.ACTIVE,
                ai_model="gpt-4",
                active=True,
                messages=[],
                mcp_server_ids=[],
                skill_openai_ids=[],
            )
            async_session.add(thread)
            await async_session.flush()
            await async_session.refresh(thread)
            kwargs["thread_id"] = thread.id

        defaults = {
            "filename": faker_instance.file_name(extension="pdf"),
            "openai_file_id": f"file-{faker_instance.uuid4()}",
            "vector_store_id": f"vs-{faker_instance.uuid4()}",
            "vector_store_name": f"Store {faker_instance.word()}",
            "user_id": 1,
            "file_size": faker_instance.random_int(min=1000, max=1000000),
        }
        defaults.update(kwargs)
        file_upload = AssistantFileUpload(**defaults)
        async_session.add(file_upload)
        await async_session.flush()
        await async_session.refresh(file_upload)
        return file_upload

    return _create_file


@pytest_asyncio.fixture
async def user_prompt_factory(async_session: AsyncSession, faker_instance: Faker):
    """Factory for creating test UserPrompt instances."""

    async def _create_user_prompt(**kwargs: Any) -> UserPrompt:
        defaults = {
            "user_id": 1,
            "handle": f"prompt-{faker_instance.uuid4()[:8]}",
            "description": faker_instance.sentence(nb_words=5),
            "prompt_text": faker_instance.paragraph(nb_sentences=3),
            "version": 1,
            "is_latest": True,
            "is_shared": False,
            "mcp_server_ids": [],
        }
        defaults.update(kwargs)
        prompt = UserPrompt(**defaults)
        async_session.add(prompt)
        await async_session.flush()
        await async_session.refresh(prompt)
        return prompt

    return _create_user_prompt


@pytest_asyncio.fixture
async def skill_factory(async_session: AsyncSession, faker_instance: Faker):
    """Factory for creating test Skill instances."""

    async def _create_skill(**kwargs: Any) -> Skill:
        defaults = {
            "openai_id": f"skill-{faker_instance.uuid4()}",
            "name": f"Skill {faker_instance.word()}",
            "description": faker_instance.sentence(),
            "default_version": "1",
            "latest_version": "1",
            "active": True,
            "required_role": None,
            "api_key_hash": faker_instance.sha256(),
            "last_synced": datetime.now(UTC),
        }
        defaults.update(kwargs)
        skill = Skill(**defaults)
        async_session.add(skill)
        await async_session.flush()
        await async_session.refresh(skill)
        return skill

    return _create_skill


@pytest_asyncio.fixture
async def user_skill_selection_factory(
    async_session: AsyncSession, faker_instance: Faker
):
    """Factory for creating test UserSkillSelection instances."""

    async def _create_selection(**kwargs: Any) -> UserSkillSelection:
        defaults = {
            "user_id": 1,
            "skill_openai_id": f"skill-{faker_instance.uuid4()}",
            "enabled": True,
        }
        defaults.update(kwargs)
        selection = UserSkillSelection(**defaults)
        async_session.add(selection)
        await async_session.flush()
        await async_session.refresh(selection)
        return selection

    return _create_selection


@pytest_asyncio.fixture
async def ai_model_factory(async_session: AsyncSession, faker_instance: Faker):
    """Factory for creating test AssistantAIModel instances."""

    async def _create_ai_model(**kwargs: Any) -> AssistantAIModel:
        defaults = {
            "model_id": f"test-model-{faker_instance.uuid4()[:8]}",
            "text": f"Test Model {faker_instance.word()}",
            "icon": "codesandbox",
            "model": "gpt-4",
            "processor_type": "openai",
            "stream": False,
            "temperature": 0.05,
            "supports_tools": True,
            "supports_attachments": True,
            "supports_search": False,
            "supports_skills": False,
            "active": True,
            "requires_role": None,
            "api_key": None,
            "base_url": None,
            "on_azure": False,
            "enable_tracking": True,
        }
        defaults.update(kwargs)
        model = AssistantAIModel(**defaults)
        async_session.add(model)
        await async_session.flush()
        await async_session.refresh(model)
        return model

    return _create_ai_model


@pytest_asyncio.fixture
async def mcp_user_token_factory(async_session: AsyncSession, faker_instance: Faker):
    """Factory for creating test AssistantMCPUserToken instances."""

    async def _create_token(**kwargs: Any) -> AssistantMCPUserToken:
        # Create MCP server first if not provided
        if "mcp_server_id" not in kwargs:
            server = MCPServer(
                name=f"server-{faker_instance.uuid4()[:8]}",
                description="Test Server",
                url=f"https://{faker_instance.domain_name()}/mcp",
                headers=json.dumps({"Authorization": "Bearer test"}),
                auth_type=MCPAuthType.OAUTH_DISCOVERY,
                active=True,
            )
            async_session.add(server)
            await async_session.flush()
            await async_session.refresh(server)
            kwargs["mcp_server_id"] = server.id

        defaults = {
            "user_id": 1,
            "access_token": faker_instance.uuid4(),
            "refresh_token": faker_instance.uuid4(),
            "expires_at": datetime.now(UTC) + timedelta(hours=1),
        }
        defaults.update(kwargs)
        token = AssistantMCPUserToken(**defaults)
        async_session.add(token)
        await async_session.flush()
        await async_session.refresh(token)
        return token

    return _create_token


# Sample data fixtures
@pytest.fixture
def sample_messages() -> list[dict[str, Any]]:
    """Provide sample message list for thread testing."""
    return [
        {
            "id": "msg-1",
            "text": "Hello, how can I help you?",
            "type": MessageType.ASSISTANT,
            "done": True,
            "attachments": [],
            "annotations": [],
        },
        {
            "id": "msg-2",
            "text": "I need help with Python",
            "type": MessageType.HUMAN,
            "done": True,
            "attachments": [],
            "annotations": [],
        },
    ]


@pytest.fixture
def sample_message() -> Message:
    """Provide a sample Message schema instance."""
    return Message(
        text="Test message",
        type=MessageType.HUMAN,
        done=True,
        attachments=[],
        annotations=[],
    )
