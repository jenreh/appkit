"""Notify admins when a new user awaits approval."""

import asyncio
import logging
from typing import Final

from appkit_commons.database.session import get_asyncdb_session
from appkit_commons.registry import service_registry
from appkit_user.authentication.backend.database import user_repo
from appkit_user.authentication.backend.models import User
from appkit_user.authentication.backend.services.email_service import (
    get_email_service,
)
from appkit_user.configuration import AuthenticationConfiguration

logger = logging.getLogger(__name__)

# Strong references to fire-and-forget tasks: the event loop only keeps weak
# ones, so an unreferenced task may be garbage collected mid-flight.
_BACKGROUND_TASKS: Final[set[asyncio.Task[int]]] = set()


def _admin_url() -> str:
    config: AuthenticationConfiguration = service_registry().get(
        AuthenticationConfiguration
    )
    return f"{config.public_base_url}{config.user_admin_route}"


async def notify_admins_of_pending_user(user: User) -> int:
    """Email every active admin that ``user`` awaits approval.

    Never raises: a missing email provider or a failing send must not affect
    the login that triggered the notification.

    Returns:
        The number of admins the email was sent to.
    """
    email_service = get_email_service()
    if email_service is None:
        logger.debug("No email provider, skipping pending-approval notification")
        return 0

    try:
        async with get_asyncdb_session() as db:
            admins = [
                (admin.email, admin.name or admin.email)
                for admin in await user_repo.find_active_admins(db)
                if admin.email
            ]
    except Exception as e:
        logger.warning("Could not load admins for approval notification: %s", e)
        return 0

    admin_url = _admin_url()
    sent = 0
    for email, name in admins:
        if await email_service.send_new_user_pending_email(
            to_email=email,
            admin_name=name,
            user_name=user.name,
            user_email=user.email,
            admin_url=admin_url,
        ):
            sent += 1

    logger.info(
        "Pending-approval notification for user_id=%s sent to %d admin(s)",
        user.user_id,
        sent,
    )
    return sent


def schedule_pending_user_notification(user: User) -> None:
    """Send the admin notification in the background, off the login path."""
    task = asyncio.create_task(notify_admins_of_pending_user(user))
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)
