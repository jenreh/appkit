import logging
import uuid

from appkit_assistant.backend.model_manager import ModelManager
from appkit_assistant.backend.models import (
    AssistantThread,
    Message,
    ThreadModel,
    ThreadStatus,
)
from appkit_assistant.backend.repositories import thread_repo
from appkit_commons.database.session import get_asyncdb_session

logger = logging.getLogger(__name__)


class ThreadService:
    """
    Service for managing assistant threads.
    Handles creation, loading, and persistence of threads.
    """

    def __init__(self):
        self.model_manager = ModelManager()

    def create_new_thread(
        self, current_model: str, user_roles: list[str] | None = None
    ) -> ThreadModel:
        """Create a new ephemeral thread model (not persisted)."""
        if user_roles is None:
            user_roles = []

        all_models = self.model_manager.get_all_models()

        # Validate or fallback model
        available_model_ids = [
            m.id
            for m in all_models
            if not m.requires_role or m.requires_role in user_roles
        ]

        selected_model = current_model
        if selected_model not in available_model_ids:
            selected_model = self.model_manager.get_default_model()
            if available_model_ids and selected_model not in available_model_ids:
                selected_model = available_model_ids[0]

        return ThreadModel(
            thread_id=str(uuid.uuid4()),
            title="Neuer Chat",
            prompt="",
            messages=[],
            state=ThreadStatus.NEW,
            ai_model=selected_model,
            active=True,
        )

    async def load_thread(
        self, thread_id: str, user_id: str | int
    ) -> ThreadModel | None:
        """Load a thread from the database."""
        async with get_asyncdb_session() as session:
            # Ensure user_id is correct type if needed
            user_id_val = (
                int(user_id)
                if isinstance(user_id, str) and user_id.isdigit()
                else user_id
            )

            thread_entity = await thread_repo.find_by_thread_id_and_user(
                session, thread_id, user_id_val
            )

            if not thread_entity:
                return None

            return ThreadModel(
                thread_id=thread_entity.thread_id,
                title=thread_entity.title,
                state=ThreadStatus(thread_entity.state),
                ai_model=thread_entity.ai_model,
                active=thread_entity.active,
                messages=[Message(**m) for m in thread_entity.messages],
            )

    async def save_thread(self, thread: ThreadModel, user_id: str | int) -> None:
        """Persist or update a thread in the database."""
        if not user_id:
            logger.warning("Cannot save thread: No user ID provided")
            return

        try:
            messages_dict = [m.model_dump() for m in thread.messages]
            user_id_val = (
                int(user_id)
                if isinstance(user_id, str) and user_id.isdigit()
                else user_id
            )

            async with get_asyncdb_session() as session:
                existing = await thread_repo.find_by_thread_id_and_user(
                    session, thread.thread_id, user_id_val
                )

                state_value = (
                    thread.state.value
                    if hasattr(thread.state, "value")
                    else thread.state
                )

                if existing:
                    existing.title = thread.title
                    existing.state = state_value
                    existing.ai_model = thread.ai_model
                    existing.active = thread.active
                    existing.messages = messages_dict
                    # updated_at handled by DB/SQLModel defaults,
                    # explicit save triggers it
                    await thread_repo.save(session, existing)
                else:
                    new_thread = AssistantThread(
                        thread_id=thread.thread_id,
                        user_id=user_id_val,
                        title=thread.title,
                        state=state_value,
                        ai_model=thread.ai_model,
                        active=thread.active,
                        messages=messages_dict,
                    )
                    await thread_repo.save(session, new_thread)

            logger.debug("Saved thread to DB: %s", thread.thread_id)
        except Exception as e:
            logger.exception("Error saving thread %s: %s", thread.thread_id, e)
