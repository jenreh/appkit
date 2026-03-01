"""Tests for SkillService.

Covers client creation, remote API interactions, DB sync logic,
and error handling paths.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.services.skill_service import (
    SkillService,
    compute_api_key_hash,
    get_skill_service,
)

# ============================================================================
# compute_api_key_hash
# ============================================================================


class TestComputeApiKeyHash:
    def test_deterministic(self) -> None:
        h1 = compute_api_key_hash("sk-test-key")
        h2 = compute_api_key_hash("sk-test-key")
        assert h1 == h2

    def test_different_keys_different_hashes(self) -> None:
        h1 = compute_api_key_hash("sk-key-a")
        h2 = compute_api_key_hash("sk-key-b")
        assert h1 != h2

    def test_sha256_hex_length(self) -> None:
        h = compute_api_key_hash("sk-test")
        assert len(h) == 64  # SHA256 hex digest length


# ============================================================================
# SkillService._get_client
# ============================================================================


class TestGetClient:
    def test_with_api_key(self) -> None:
        svc = SkillService()
        client = svc._get_client(api_key="sk-test")
        assert client is not None

    def test_with_api_key_and_base_url(self) -> None:
        svc = SkillService()
        client = svc._get_client(api_key="sk-test", base_url="https://custom.com")
        assert client is not None

    def test_without_api_key_uses_global_service(self) -> None:
        svc = SkillService()
        mock_client = MagicMock()
        with patch(
            "appkit_assistant.backend.services.skill_service.get_openai_client_service"
        ) as mock_get:
            mock_get.return_value.create_client.return_value = mock_client
            result = svc._get_client()
            assert result is mock_client

    def test_without_api_key_no_global_raises(self) -> None:
        svc = SkillService()
        with patch(
            "appkit_assistant.backend.services.skill_service.get_openai_client_service"
        ) as mock_get:
            mock_get.return_value.create_client.return_value = None
            with pytest.raises(RuntimeError, match="not available"):
                svc._get_client()


# ============================================================================
# list_remote_skills
# ============================================================================


class TestListRemoteSkills:
    @pytest.mark.asyncio
    async def test_returns_skill_list(self) -> None:
        svc = SkillService()
        mock_skill = SimpleNamespace(
            id="sk-1",
            name="Search",
            description="A search skill",
            default_version="1",
            latest_version="2",
        )
        mock_page = MagicMock(data=[mock_skill])

        with patch.object(svc, "_get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.skills.list = AsyncMock(return_value=mock_page)
            mock_client_fn.return_value = mock_client

            result = await svc.list_remote_skills(api_key="sk-test")

        assert len(result) == 1
        assert result[0]["id"] == "sk-1"
        assert result[0]["name"] == "Search"
        assert result[0]["description"] == "A search skill"

    @pytest.mark.asyncio
    async def test_empty_list(self) -> None:
        svc = SkillService()
        mock_page = MagicMock(data=[])

        with patch.object(svc, "_get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.skills.list = AsyncMock(return_value=mock_page)
            mock_client_fn.return_value = mock_client

            result = await svc.list_remote_skills()
        assert result == []

    @pytest.mark.asyncio
    async def test_none_description_becomes_empty(self) -> None:
        svc = SkillService()
        mock_skill = SimpleNamespace(
            id="sk-1",
            name="Tool",
            description=None,
            default_version="1",
            latest_version="1",
        )
        mock_page = MagicMock(data=[mock_skill])

        with patch.object(svc, "_get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.skills.list = AsyncMock(return_value=mock_page)
            mock_client_fn.return_value = mock_client

            result = await svc.list_remote_skills()
        assert result[0]["description"] == ""


# ============================================================================
# create_skill
# ============================================================================


class TestCreateSkill:
    @pytest.mark.asyncio
    async def test_create_returns_metadata(self) -> None:
        svc = SkillService()
        mock_skill = SimpleNamespace(
            id="sk-new",
            name="New Skill",
            description="desc",
            default_version="1",
            latest_version="1",
        )

        with patch.object(svc, "_get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.skills.create = AsyncMock(return_value=mock_skill)
            mock_client_fn.return_value = mock_client

            result = await svc.create_skill(b"zipdata", "skill.zip")

        assert result["id"] == "sk-new"
        assert result["name"] == "New Skill"


# ============================================================================
# update_skill
# ============================================================================


class TestUpdateSkill:
    @pytest.mark.asyncio
    async def test_update_creates_new_and_deletes_old(self) -> None:
        svc = SkillService()
        new_data = {
            "id": "sk-new",
            "name": "Skill",
            "description": "",
            "default_version": "1",
            "latest_version": "1",
        }

        with (
            patch.object(
                svc, "create_skill", new_callable=AsyncMock, return_value=new_data
            ),
            patch.object(
                svc, "delete_remote_skill", new_callable=AsyncMock
            ) as mock_delete,
        ):
            result = await svc.update_skill("sk-old", b"data", "f.zip")
            assert result["id"] == "sk-new"
            mock_delete.assert_awaited_once_with("sk-old")

    @pytest.mark.asyncio
    async def test_update_handles_delete_failure(self) -> None:
        svc = SkillService()
        new_data = {
            "id": "sk-new",
            "name": "Skill",
            "description": "",
            "default_version": "1",
            "latest_version": "1",
        }

        with (
            patch.object(
                svc, "create_skill", new_callable=AsyncMock, return_value=new_data
            ),
            patch.object(
                svc,
                "delete_remote_skill",
                new_callable=AsyncMock,
                side_effect=RuntimeError("API error"),
            ),
        ):
            # Should not raise even if delete fails
            result = await svc.update_skill("sk-old", b"data", "f.zip")
            assert result["id"] == "sk-new"


# ============================================================================
# delete_remote_skill
# ============================================================================


class TestDeleteRemoteSkill:
    @pytest.mark.asyncio
    async def test_delete_returns_true(self) -> None:
        svc = SkillService()
        mock_result = MagicMock(deleted=True)

        with patch.object(svc, "_get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.skills.delete = AsyncMock(return_value=mock_result)
            mock_client_fn.return_value = mock_client

            result = await svc.delete_remote_skill("sk-1")
        assert result is True


# ============================================================================
# retrieve_skill
# ============================================================================


class TestRetrieveSkill:
    @pytest.mark.asyncio
    async def test_retrieve_returns_dict(self) -> None:
        svc = SkillService()
        mock_skill = SimpleNamespace(
            id="sk-1",
            name="Skill",
            description="desc",
            default_version="1",
            latest_version="2",
        )

        with patch.object(svc, "_get_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.skills.retrieve = AsyncMock(return_value=mock_skill)
            mock_client_fn.return_value = mock_client

            result = await svc.retrieve_skill("sk-1")
        assert result["name"] == "Skill"
        assert result["latest_version"] == "2"


# ============================================================================
# _upsert_skill
# ============================================================================


class TestUpsertSkill:
    @pytest.mark.asyncio
    async def test_insert_new_skill(self) -> None:
        svc = SkillService()
        session = AsyncMock()
        remote = {
            "id": "sk-new",
            "name": "New",
            "description": "new skill",
            "default_version": "1",
            "latest_version": "1",
        }

        with patch(
            "appkit_assistant.backend.services.skill_service.skill_repo"
        ) as mock_repo:
            mock_repo.find_by_openai_id = AsyncMock(return_value=None)
            await svc._upsert_skill(session, remote)

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_existing_skill(self) -> None:
        svc = SkillService()
        session = AsyncMock()
        existing = MagicMock()
        remote = {
            "id": "sk-1",
            "name": "Updated",
            "description": "updated",
            "default_version": "2",
            "latest_version": "2",
        }

        with patch(
            "appkit_assistant.backend.services.skill_service.skill_repo"
        ) as mock_repo:
            mock_repo.find_by_openai_id = AsyncMock(return_value=existing)
            await svc._upsert_skill(session, remote)

        assert existing.name == "Updated"
        assert existing.latest_version == "2"
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_with_api_key_hash(self) -> None:
        svc = SkillService()
        session = AsyncMock()
        existing = MagicMock()
        remote = {
            "id": "sk-1",
            "name": "Skill",
            "description": "",
            "default_version": "1",
            "latest_version": "1",
        }

        with patch(
            "appkit_assistant.backend.services.skill_service.skill_repo"
        ) as mock_repo:
            mock_repo.find_by_openai_id = AsyncMock(return_value=existing)
            await svc._upsert_skill(session, remote, api_key_hash="abc123")

        assert existing.api_key_hash == "abc123"


# ============================================================================
# sync_all_skills
# ============================================================================


class TestSyncAllSkills:
    @pytest.mark.asyncio
    async def test_sync_deactivates_stale(self) -> None:
        svc = SkillService()
        session = AsyncMock()

        remote_skills = [
            {
                "id": "sk-1",
                "name": "Active",
                "description": "",
                "default_version": "1",
                "latest_version": "1",
            }
        ]
        stale_skill = MagicMock(openai_id="sk-stale", active=True)

        with (
            patch.object(
                svc,
                "list_remote_skills",
                new_callable=AsyncMock,
                return_value=remote_skills,
            ),
            patch.object(svc, "_upsert_skill", new_callable=AsyncMock),
            patch(
                "appkit_assistant.backend.services.skill_service.skill_repo"
            ) as mock_repo,
        ):
            mock_repo.find_all_ordered_by_name = AsyncMock(return_value=[stale_skill])
            count = await svc.sync_all_skills(session)

        assert count == 1
        assert stale_skill.active is False
        session.flush.assert_awaited_once()


# ============================================================================
# delete_skill_full
# ============================================================================


class TestDeleteSkillFull:
    @pytest.mark.asyncio
    async def test_delete_not_found_raises(self) -> None:
        svc = SkillService()
        session = AsyncMock()

        with patch(
            "appkit_assistant.backend.services.skill_service.skill_repo"
        ) as mock_repo:
            mock_repo.find_by_id = AsyncMock(return_value=None)
            with pytest.raises(ValueError, match="not found"):
                await svc.delete_skill_full(session, 999)

    @pytest.mark.asyncio
    async def test_delete_full_cascade(self) -> None:
        svc = SkillService()
        session = AsyncMock()
        skill = SimpleNamespace(name="TestSkill", openai_id="sk-1", id=1)

        with (
            patch(
                "appkit_assistant.backend.services.skill_service.skill_repo"
            ) as mock_skill_repo,
            patch(
                "appkit_assistant.backend.services.skill_service.user_skill_repo"
            ) as mock_user_repo,
            patch.object(svc, "delete_remote_skill", new_callable=AsyncMock),
        ):
            mock_skill_repo.find_by_id = AsyncMock(return_value=skill)
            mock_user_repo.delete_by_skill_openai_id = AsyncMock()
            mock_skill_repo.delete_by_id = AsyncMock()
            result = await svc.delete_skill_full(session, 1)

        assert result == "TestSkill"
        mock_user_repo.delete_by_skill_openai_id.assert_awaited_once()
        mock_skill_repo.delete_by_id.assert_awaited_once()


# ============================================================================
# get_skill_service
# ============================================================================


class TestGetSkillService:
    def test_returns_singleton(self) -> None:
        svc = get_skill_service()
        assert isinstance(svc, SkillService)
        assert get_skill_service() is svc
