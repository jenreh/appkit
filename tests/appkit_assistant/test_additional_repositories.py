"""Tests for AI model, user prompt, and skill repositories."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class TestAIModelRepository:
    """Test suite for AIModelRepository."""

    @pytest.mark.asyncio
    async def test_find_all_ordered_by_text(
        self, async_session: AsyncSession, ai_model_factory, ai_model_repo
    ) -> None:
        """find_all_ordered_by_text returns all models sorted by text."""
        model_b = await ai_model_factory(text="B Model")
        model_a = await ai_model_factory(text="A Model")
        model_c = await ai_model_factory(text="C Model")

        results = await ai_model_repo.find_all_ordered_by_text(async_session)

        assert len(results) == 3
        assert results[0].id == model_a.id
        assert results[1].id == model_b.id
        assert results[2].id == model_c.id

    @pytest.mark.asyncio
    async def test_find_all_ordered_by_text_includes_inactive(
        self, async_session: AsyncSession, ai_model_factory, ai_model_repo
    ) -> None:
        """find_all_ordered_by_text includes inactive models."""
        active = await ai_model_factory(active=True)
        inactive = await ai_model_factory(active=False)

        results = await ai_model_repo.find_all_ordered_by_text(async_session)

        assert len(results) == 2
        model_ids = {m.id for m in results}
        assert active.id in model_ids
        assert inactive.id in model_ids

    @pytest.mark.asyncio
    async def test_find_all_active_ordered_by_text(
        self, async_session: AsyncSession, ai_model_factory, ai_model_repo
    ) -> None:
        """find_all_active_ordered_by_text returns only active models."""
        active1 = await ai_model_factory(text="Active 1", active=True)
        active2 = await ai_model_factory(text="Active 2", active=True)
        inactive = await ai_model_factory(text="Inactive", active=False)

        results = await ai_model_repo.find_all_active_ordered_by_text(async_session)

        assert len(results) == 2
        model_ids = {m.id for m in results}
        assert active1.id in model_ids
        assert active2.id in model_ids
        assert inactive.id not in model_ids

    @pytest.mark.asyncio
    async def test_find_by_model_id_existing(
        self, async_session: AsyncSession, ai_model_factory, ai_model_repo
    ) -> None:
        """find_by_model_id returns model by model_id string."""
        model = await ai_model_factory(model_id="gpt-4-turbo")

        result = await ai_model_repo.find_by_model_id(async_session, "gpt-4-turbo")

        assert result is not None
        assert result.id == model.id
        assert result.model_id == "gpt-4-turbo"

    @pytest.mark.asyncio
    async def test_find_by_model_id_nonexistent(
        self, async_session: AsyncSession, ai_model_repo
    ) -> None:
        """find_by_model_id returns None for nonexistent model_id."""
        result = await ai_model_repo.find_by_model_id(
            async_session, "nonexistent-model"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_processor_type(
        self, async_session: AsyncSession, ai_model_factory, ai_model_repo
    ) -> None:
        """find_by_processor_type returns active models for processor."""
        openai1 = await ai_model_factory(processor_type="openai", active=True)
        openai2 = await ai_model_factory(processor_type="openai", active=True)
        claude = await ai_model_factory(processor_type="claude", active=True)
        openai_inactive = await ai_model_factory(processor_type="openai", active=False)

        results = await ai_model_repo.find_by_processor_type(async_session, "openai")

        assert len(results) == 2
        model_ids = {m.id for m in results}
        assert openai1.id in model_ids
        assert openai2.id in model_ids
        assert claude.id not in model_ids
        assert openai_inactive.id not in model_ids

    @pytest.mark.asyncio
    async def test_find_all_skill_capable(
        self, async_session: AsyncSession, ai_model_factory, ai_model_repo
    ) -> None:
        """find_all_skill_capable returns OpenAI models with skills support."""
        skill_model = await ai_model_factory(
            processor_type="openai", supports_skills=True
        )
        openai_no_skills = await ai_model_factory(
            processor_type="openai", supports_skills=False
        )
        claude_with_skills = await ai_model_factory(
            processor_type="claude", supports_skills=True
        )

        results = await ai_model_repo.find_all_skill_capable(async_session)

        assert len(results) == 1
        assert results[0].id == skill_model.id

    @pytest.mark.asyncio
    async def test_update_active(
        self, async_session: AsyncSession, ai_model_factory, ai_model_repo
    ) -> None:
        """update_active updates active flag."""
        model = await ai_model_factory(active=True)

        updated = await ai_model_repo.update_active(
            async_session, model.id, active=False
        )

        assert updated is not None
        assert updated.active is False

    @pytest.mark.asyncio
    async def test_update_active_nonexistent(
        self, async_session: AsyncSession, ai_model_repo
    ) -> None:
        """update_active returns None for nonexistent model."""
        updated = await ai_model_repo.update_active(async_session, 99999, active=False)

        assert updated is None

    @pytest.mark.asyncio
    async def test_update_role(
        self, async_session: AsyncSession, ai_model_factory, ai_model_repo
    ) -> None:
        """update_role updates requires_role field."""
        model = await ai_model_factory(requires_role=None)

        updated = await ai_model_repo.update_role(
            async_session, model.id, requires_role="admin"
        )

        assert updated is not None
        assert updated.requires_role == "admin"

    @pytest.mark.asyncio
    async def test_update_role_clear(
        self, async_session: AsyncSession, ai_model_factory, ai_model_repo
    ) -> None:
        """update_role can clear role requirement."""
        model = await ai_model_factory(requires_role="admin")

        updated = await ai_model_repo.update_role(
            async_session, model.id, requires_role=None
        )

        assert updated is not None
        assert updated.requires_role is None


class TestUserPromptRepository:
    """Test suite for UserPromptRepository."""

    @pytest.mark.asyncio
    async def test_find_latest_prompts_by_user(
        self, async_session: AsyncSession, user_prompt_factory, user_prompt_repo
    ) -> None:
        """find_latest_prompts_by_user returns latest versions only."""
        v1 = await user_prompt_factory(
            user_id=1, handle="prompt-1", version=1, is_latest=False
        )
        v2 = await user_prompt_factory(
            user_id=1, handle="prompt-1", version=2, is_latest=True
        )
        other_user = await user_prompt_factory(
            user_id=2, handle="prompt-2", is_latest=True
        )

        results = await user_prompt_repo.find_latest_prompts_by_user(
            async_session, user_id=1
        )

        assert len(results) == 1
        assert results[0].id == v2.id

    @pytest.mark.asyncio
    async def test_find_latest_prompts_by_user_orders_by_handle(
        self, async_session: AsyncSession, user_prompt_factory, user_prompt_repo
    ) -> None:
        """find_latest_prompts_by_user orders by handle alphabetically."""
        prompt_z = await user_prompt_factory(user_id=1, handle="z-prompt")
        prompt_a = await user_prompt_factory(user_id=1, handle="a-prompt")

        results = await user_prompt_repo.find_latest_prompts_by_user(
            async_session, user_id=1
        )

        assert results[0].id == prompt_a.id
        assert results[1].id == prompt_z.id

    @pytest.mark.asyncio
    async def test_find_latest_by_handle_existing(
        self, async_session: AsyncSession, user_prompt_factory, user_prompt_repo
    ) -> None:
        """find_latest_by_handle returns latest version for handle."""
        await user_prompt_factory(user_id=1, handle="test", version=1, is_latest=False)
        v2 = await user_prompt_factory(
            user_id=1, handle="test", version=2, is_latest=True
        )

        result = await user_prompt_repo.find_latest_by_handle(
            async_session, user_id=1, handle="test"
        )

        assert result is not None
        assert result.id == v2.id

    @pytest.mark.asyncio
    async def test_find_latest_by_handle_nonexistent(
        self, async_session: AsyncSession, user_prompt_repo
    ) -> None:
        """find_latest_by_handle returns None for nonexistent handle."""
        result = await user_prompt_repo.find_latest_by_handle(
            async_session, user_id=1, handle="nonexistent"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_handle_unique_available(
        self, async_session: AsyncSession, user_prompt_repo
    ) -> None:
        """validate_handle_unique returns True when handle is available."""
        is_unique = await user_prompt_repo.validate_handle_unique(
            async_session, user_id=1, handle="new-handle"
        )

        assert is_unique is True

    @pytest.mark.asyncio
    async def test_validate_handle_unique_taken(
        self, async_session: AsyncSession, user_prompt_factory, user_prompt_repo
    ) -> None:
        """validate_handle_unique returns False when handle exists."""
        await user_prompt_factory(user_id=1, handle="taken-handle")

        is_unique = await user_prompt_repo.validate_handle_unique(
            async_session, user_id=1, handle="taken-handle"
        )

        assert is_unique is False

    @pytest.mark.asyncio
    async def test_create_new_prompt(
        self, async_session: AsyncSession, user_prompt_repo
    ) -> None:
        """create_new_prompt creates version 1 with is_latest=True."""
        prompt = await user_prompt_repo.create_new_prompt(
            async_session,
            user_id=1,
            handle="new-prompt",
            description="Test description",
            prompt_text="Test prompt text",
            is_shared=False,
            mcp_server_ids=[1, 2],
        )

        assert prompt.version == 1
        assert prompt.is_latest is True
        assert prompt.handle == "new-prompt"
        assert prompt.mcp_server_ids == [1, 2]

    @pytest.mark.asyncio
    async def test_create_next_version(
        self, async_session: AsyncSession, user_prompt_factory, user_prompt_repo
    ) -> None:
        """create_next_version increments version and updates is_latest."""
        v1 = await user_prompt_factory(
            user_id=1, handle="test", version=1, is_latest=True, prompt_text="V1 text"
        )

        v2 = await user_prompt_repo.create_next_version(
            async_session, user_id=1, handle="test", prompt_text="V2 text"
        )

        assert v2.version == 2
        assert v2.is_latest is True
        assert v2.prompt_text == "V2 text"

        # Check v1 is no longer latest
        await async_session.refresh(v1)
        assert v1.is_latest is False

    @pytest.mark.asyncio
    async def test_create_next_version_copies_unspecified_fields(
        self, async_session: AsyncSession, user_prompt_factory, user_prompt_repo
    ) -> None:
        """create_next_version copies fields not provided."""
        await user_prompt_factory(
            user_id=1,
            handle="test",
            version=1,
            is_latest=True,
            description="Original desc",
            prompt_text="Original text",
            is_shared=True,
            mcp_server_ids=[1, 2],
        )

        v2 = await user_prompt_repo.create_next_version(
            async_session, user_id=1, handle="test", prompt_text="New text"
        )

        assert v2.description == "Original desc"  # Copied
        assert v2.prompt_text == "New text"  # Updated
        assert v2.is_shared is True  # Copied
        assert v2.mcp_server_ids == [1, 2]  # Copied

    @pytest.mark.asyncio
    async def test_delete_all_versions(
        self, async_session: AsyncSession, user_prompt_factory, user_prompt_repo
    ) -> None:
        """delete_all_versions deletes all versions of a prompt."""
        await user_prompt_factory(user_id=1, handle="delete-me", version=1)
        await user_prompt_factory(user_id=1, handle="delete-me", version=2)
        await user_prompt_factory(user_id=1, handle="keep-me", version=1)

        success = await user_prompt_repo.delete_all_versions(
            async_session, user_id=1, handle="delete-me"
        )

        assert success is True

        # Verify deleted
        remaining = await user_prompt_repo.find_latest_prompts_by_user(
            async_session, user_id=1
        )
        assert len(remaining) == 1
        assert remaining[0].handle == "keep-me"

    @pytest.mark.asyncio
    async def test_update_handle(
        self, async_session: AsyncSession, user_prompt_factory, user_prompt_repo
    ) -> None:
        """update_handle updates handle for all versions."""
        v1 = await user_prompt_factory(user_id=1, handle="old-handle", version=1)
        v2 = await user_prompt_factory(user_id=1, handle="old-handle", version=2)

        success = await user_prompt_repo.update_handle(
            async_session, user_id=1, old_handle="old-handle", new_handle="new-handle"
        )

        assert success is True
        await async_session.refresh(v1)
        await async_session.refresh(v2)
        assert v1.handle == "new-handle"
        assert v2.handle == "new-handle"


class TestSkillRepository:
    """Test suite for SkillRepository."""

    @pytest.mark.asyncio
    async def test_find_all_ordered_by_name(
        self, async_session: AsyncSession, skill_factory, skill_repo
    ) -> None:
        """find_all_ordered_by_name returns all skills sorted by name."""
        skill_b = await skill_factory(name="B Skill")
        skill_a = await skill_factory(name="A Skill")
        skill_c = await skill_factory(name="C Skill")

        results = await skill_repo.find_all_ordered_by_name(async_session)

        assert len(results) == 3
        assert results[0].id == skill_a.id
        assert results[1].id == skill_b.id
        assert results[2].id == skill_c.id

    @pytest.mark.asyncio
    async def test_find_all_active_ordered_by_name(
        self, async_session: AsyncSession, skill_factory, skill_repo
    ) -> None:
        """find_all_active_ordered_by_name returns only active skills."""
        active1 = await skill_factory(name="Active 1", active=True)
        active2 = await skill_factory(name="Active 2", active=True)
        inactive = await skill_factory(name="Inactive", active=False)

        results = await skill_repo.find_all_active_ordered_by_name(async_session)

        assert len(results) == 2
        skill_ids = {s.id for s in results}
        assert active1.id in skill_ids
        assert active2.id in skill_ids
        assert inactive.id not in skill_ids

    @pytest.mark.asyncio
    async def test_find_by_openai_id_existing(
        self, async_session: AsyncSession, skill_factory, skill_repo
    ) -> None:
        """find_by_openai_id returns skill by openai_id."""
        skill = await skill_factory(openai_id="skill-abc123")

        result = await skill_repo.find_by_openai_id(async_session, "skill-abc123")

        assert result is not None
        assert result.id == skill.id
        assert result.openai_id == "skill-abc123"

    @pytest.mark.asyncio
    async def test_find_by_openai_id_nonexistent(
        self, async_session: AsyncSession, skill_repo
    ) -> None:
        """find_by_openai_id returns None for nonexistent openai_id."""
        result = await skill_repo.find_by_openai_id(async_session, "nonexistent-skill")

        assert result is None

    @pytest.mark.asyncio
    async def test_find_all_by_api_key_hash(
        self, async_session: AsyncSession, skill_factory, skill_repo
    ) -> None:
        """find_all_by_api_key_hash returns skills for specific key hash."""
        skill1 = await skill_factory(api_key_hash="hash-a")
        skill2 = await skill_factory(api_key_hash="hash-a")
        skill3 = await skill_factory(api_key_hash="hash-b")

        results = await skill_repo.find_all_by_api_key_hash(async_session, "hash-a")

        assert len(results) == 2
        skill_ids = {s.id for s in results}
        assert skill1.id in skill_ids
        assert skill2.id in skill_ids
        assert skill3.id not in skill_ids

    @pytest.mark.asyncio
    async def test_find_all_active_by_api_key_hash(
        self, async_session: AsyncSession, skill_factory, skill_repo
    ) -> None:
        """find_all_active_by_api_key_hash filters by active status."""
        active = await skill_factory(api_key_hash="hash-a", active=True)
        inactive = await skill_factory(api_key_hash="hash-a", active=False)

        results = await skill_repo.find_all_active_by_api_key_hash(
            async_session, "hash-a"
        )

        assert len(results) == 1
        assert results[0].id == active.id

    @pytest.mark.asyncio
    async def test_update_required_role(
        self, async_session: AsyncSession, skill_factory, skill_repo
    ) -> None:
        """update_required_role updates role requirement."""
        skill = await skill_factory(required_role=None)

        success = await skill_repo.update_required_role(
            async_session, skill.id, required_role="admin"
        )

        assert success is True
        await async_session.refresh(skill)
        assert skill.required_role == "admin"

    @pytest.mark.asyncio
    async def test_update_required_role_nonexistent(
        self, async_session: AsyncSession, skill_repo
    ) -> None:
        """update_required_role returns False for nonexistent skill."""
        success = await skill_repo.update_required_role(
            async_session, 99999, required_role="admin"
        )

        assert success is False


class TestUserSkillRepository:
    """Test suite for UserSkillRepository."""

    @pytest.mark.asyncio
    async def test_find_by_user_id(
        self, async_session: AsyncSession, user_skill_selection_factory, user_skill_repo
    ) -> None:
        """find_by_user_id returns all selections for user."""
        selection1 = await user_skill_selection_factory(
            user_id=1, skill_openai_id="skill-1"
        )
        selection2 = await user_skill_selection_factory(
            user_id=1, skill_openai_id="skill-2"
        )
        other_user = await user_skill_selection_factory(
            user_id=2, skill_openai_id="skill-3"
        )

        results = await user_skill_repo.find_by_user_id(async_session, user_id=1)

        assert len(results) == 2
        selection_ids = {s.id for s in results}
        assert selection1.id in selection_ids
        assert selection2.id in selection_ids
        assert other_user.id not in selection_ids

    @pytest.mark.asyncio
    async def test_upsert_creates_new(
        self, async_session: AsyncSession, user_skill_repo
    ) -> None:
        """upsert creates new selection when none exists."""
        selection = await user_skill_repo.upsert(
            async_session, user_id=1, skill_openai_id="skill-123", enabled=True
        )

        assert selection.id is not None
        assert selection.user_id == 1
        assert selection.skill_openai_id == "skill-123"
        assert selection.enabled is True

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(
        self, async_session: AsyncSession, user_skill_selection_factory, user_skill_repo
    ) -> None:
        """upsert updates existing selection."""
        existing = await user_skill_selection_factory(
            user_id=1, skill_openai_id="skill-123", enabled=True
        )

        updated = await user_skill_repo.upsert(
            async_session, user_id=1, skill_openai_id="skill-123", enabled=False
        )

        assert updated.id == existing.id
        assert updated.enabled is False

    @pytest.mark.asyncio
    async def test_delete_by_skill_openai_id(
        self, async_session: AsyncSession, user_skill_selection_factory, user_skill_repo
    ) -> None:
        """delete_by_skill_openai_id removes all user selections for skill."""
        await user_skill_selection_factory(user_id=1, skill_openai_id="skill-delete")
        await user_skill_selection_factory(user_id=2, skill_openai_id="skill-delete")
        await user_skill_selection_factory(user_id=1, skill_openai_id="skill-keep")

        count = await user_skill_repo.delete_by_skill_openai_id(
            async_session, "skill-delete"
        )

        assert count == 2

        # Verify skill-keep still exists
        remaining = await user_skill_repo.find_by_user_id(async_session, user_id=1)
        assert len(remaining) == 1
        assert remaining[0].skill_openai_id == "skill-keep"
