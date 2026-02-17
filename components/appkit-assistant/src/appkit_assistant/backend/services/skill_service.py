"""Service for interacting with the OpenAI Skills API."""

import logging
from datetime import UTC, datetime

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_assistant.backend.database.models import Skill
from appkit_assistant.backend.database.repositories import (
    skill_repo,
    user_skill_repo,
)
from appkit_assistant.backend.services.openai_client_service import (
    OpenAIClientService,
    get_openai_client_service,
)
from appkit_assistant.configuration import AssistantConfig
from appkit_commons.registry import service_registry

logger = logging.getLogger(__name__)


class SkillService:
    """Wraps OpenAI Skills API calls and local DB synchronisation."""

    def _get_client(self) -> AsyncOpenAI:
        config = service_registry().get(AssistantConfig)
        """Return an authenticated AsyncOpenAI client or raise."""
        client = OpenAIClientService(  # FIXME: this needs to intialized based on the configuration. The configuration currently lacks a param that defines if skills are supported on azure
            api_key=config.openai_api_key.get_secret_value(),
            on_azure=False,
        ).create_client()
        if client is None:
            raise RuntimeError("OpenAI client not available - API key missing.")
        return client

    async def list_remote_skills(self) -> list[dict]:
        """List all skills from the OpenAI API.

        Returns a list of dicts with id, name, description,
        default_version, latest_version.
        """
        client = self._get_client()
        page = await client.skills.list()
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description or "",
                "default_version": s.default_version,
                "latest_version": s.latest_version,
            }
            for s in page.data
        ]

    async def create_skill(self, file_bytes: bytes, filename: str) -> dict:
        """Upload a zip file to create a new skill.

        Returns a dict with the created skill metadata.
        """
        client = self._get_client()
        skill = await client.skills.create(
            files=(filename, file_bytes),
        )
        logger.info("Created OpenAI skill: %s (%s)", skill.name, skill.id)
        return {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description or "",
            "default_version": skill.default_version,
            "latest_version": skill.latest_version,
        }

    async def update_skill(
        self, openai_id: str, file_bytes: bytes, filename: str
    ) -> dict:
        """Update an existing skill by creating a new version.

        The OpenAI skills.update() only changes the default_version,
        so to push new content we create a fresh skill and delete the
        old one.

        Returns a dict with the new skill metadata.
        """
        # Create new version with updated content
        result = await self.create_skill(file_bytes, filename)
        logger.info(
            "Created new version of skill '%s' (%s -> %s)",
            result["name"],
            openai_id,
            result["id"],
        )
        # Delete the old skill
        try:
            await self.delete_remote_skill(openai_id)
        except Exception as e:
            logger.warning("Could not delete old skill %s: %s", openai_id, e)
        return result

    async def create_or_update_skill(
        self,
        session: AsyncSession,
        file_bytes: bytes,
        filename: str,
    ) -> dict:
        """Create or update a skill on OpenAI.

        Checks remote skills by name first. If a skill with the
        same name already exists, creates a new version and deletes
        the old one. The local version counter is incremented so
        the DB reflects the upload history.

        Returns a dict with the skill metadata (versions adjusted).
        """
        remote_skills = await self.list_remote_skills()

        # Build name→id map from existing remote skills
        name_to_id: dict[str, str] = {s["name"]: s["id"] for s in remote_skills}

        # Create the skill (always creates a new one on OpenAI)
        result = await self.create_skill(file_bytes, filename)
        skill_name = result["name"]

        if skill_name in name_to_id:
            old_id = name_to_id[skill_name]

            # Look up existing DB record to get current version
            existing = await skill_repo.find_by_openai_id(session, old_id)
            old_latest = int(existing.latest_version) if existing else 1

            new_version = str(old_latest + 1)
            result["latest_version"] = new_version
            result["default_version"] = new_version

            logger.info(
                "Skill '%s' already existed (%s v%d), "
                "replacing with new version (%s v%s)",
                skill_name,
                old_id,
                old_latest,
                result["id"],
                new_version,
            )

            # Delete the old remote skill
            try:
                await self.delete_remote_skill(old_id)
            except Exception as e:
                logger.warning(
                    "Could not delete old skill %s: %s",
                    old_id,
                    e,
                )

            # Remove old local record so upsert creates a fresh one
            if existing:
                await user_skill_repo.delete_by_skill_openai_id(session, old_id)
                await skill_repo.delete_by_id(session, existing.id)

        return result

    async def retrieve_skill(self, openai_id: str) -> dict:
        """Retrieve a single skill from the OpenAI API."""
        client = self._get_client()
        skill = await client.skills.retrieve(openai_id)
        return {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description or "",
            "default_version": skill.default_version,
            "latest_version": skill.latest_version,
        }

    async def delete_remote_skill(self, openai_id: str) -> bool:
        """Delete a skill from the OpenAI API."""
        client = self._get_client()
        result = await client.skills.delete(openai_id)
        logger.info("Deleted OpenAI skill: %s", openai_id)
        return getattr(result, "deleted", True)

    # ------------------------------------------------------------------
    # Synchronisation helpers
    # ------------------------------------------------------------------

    async def sync_skill(self, session: AsyncSession, openai_id: str) -> Skill:
        """Sync a single skill from the OpenAI API into the DB."""
        remote = await self.retrieve_skill(openai_id)
        return await self._upsert_skill(session, remote)

    async def sync_all_skills(self, session: AsyncSession) -> int:
        """Sync all remote skills into the local DB.

        Returns the number of skills synced.
        """
        remote_skills = await self.list_remote_skills()
        remote_ids: set[str] = set()

        for remote in remote_skills:
            await self._upsert_skill(session, remote)
            remote_ids.add(remote["id"])

        # Deactivate local skills that no longer exist remotely
        all_local = await skill_repo.find_all_ordered_by_name(session)
        deactivated = 0
        for local in all_local:
            if local.openai_id not in remote_ids and local.active:
                local.active = False
                session.add(local)
                deactivated += 1

        await session.flush()
        total = len(remote_skills)
        logger.info(
            "Synced %d skills, deactivated %d stale",
            total,
            deactivated,
        )
        return total

    async def delete_skill_full(self, session: AsyncSession, skill_id: int) -> str:
        """Delete a skill from OpenAI and remove local DB records.

        Returns the name of the deleted skill.
        """
        skill = await skill_repo.find_by_id(session, skill_id)
        if not skill:
            raise ValueError("Skill not found in database.")

        skill_name = skill.name
        openai_id = skill.openai_id

        # Delete from OpenAI
        await self.delete_remote_skill(openai_id)

        # Cascade: remove user selections
        await user_skill_repo.delete_by_skill_openai_id(session, openai_id)

        # Delete local record
        await skill_repo.delete_by_id(session, skill_id)

        logger.info("Fully deleted skill: %s (%s)", skill_name, openai_id)
        return skill_name

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _upsert_skill(self, session: AsyncSession, remote: dict) -> Skill:
        """Insert or update a local Skill from remote data.

        OpenAI is the leading source — matches by openai_id only.
        """
        now = datetime.now(UTC)

        existing = await skill_repo.find_by_openai_id(session, remote["id"])
        if existing:
            existing.name = remote["name"]
            existing.description = remote["description"]
            existing.default_version = remote["default_version"]
            existing.latest_version = remote["latest_version"]
            existing.last_synced = now
            session.add(existing)
            await session.flush()
            await session.refresh(existing)
            return existing

        skill = Skill(
            openai_id=remote["id"],
            name=remote["name"],
            description=remote["description"],
            default_version=remote["default_version"],
            latest_version=remote["latest_version"],
            active=True,
            last_synced=now,
        )
        session.add(skill)
        await session.flush()
        await session.refresh(skill)
        return skill


def get_skill_service() -> SkillService:
    """Return a SkillService singleton."""
    return _skill_service


_skill_service = SkillService()
