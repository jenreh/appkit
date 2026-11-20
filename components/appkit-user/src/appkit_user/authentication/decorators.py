import asyncio
import inspect
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import reflex as rx
from reflex.event import EventSpec

from appkit_user.authentication.session_validation import (
    is_pending_approval,
    welcome_route,
)
from appkit_user.authentication.states import LoginState

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

_NOT_AUTHORIZED_MSG = "Sie haben keine Berechtigung für diese Aktion."


async def _denial(state: Any) -> tuple[bool, EventSpec | None]:
    """Whether the caller must be refused, and the event to answer with.

    Anonymous callers are sent through ``LoginState.redir`` (which may answer
    with no event at all), users awaiting admin approval to the welcome page.

    Returns:
        ``(denied, event)``; ``event`` is only meaningful when ``denied``.
    """
    login_state = await state.get_state(LoginState)
    if not await login_state.is_authenticated:
        logger.debug("User not authenticated, redirecting to login.")
        return True, await login_state.redir()
    # ``user`` is re-read by the session filter every monitor interval, so an
    # approval lifts this gate without a new login.
    if is_pending_approval(login_state.user):
        logger.debug("User awaits approval, redirecting to welcome page.")
        return True, rx.redirect(welcome_route())
    return False, None


def is_authenticated[F: Callable[..., Any]](func: F) -> F:
    """Authentication decorator with async support"""

    @wraps(func)
    async def async_gen_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        denied, event = await _denial(self)
        if denied:
            yield event
            return
        async for item in func(self, *args, **kwargs):
            yield item

    @wraps(func)
    async def async_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        denied, event = await _denial(self)
        if denied:
            return event
        return await func(self, *args, **kwargs)

    # Return appropriate wrapper based on function type
    logger.debug("Check valid authentication for: '%s'", func.__name__)

    if inspect.isasyncgenfunction(func):
        return async_gen_wrapper  # type: ignore[return-value]

    if not asyncio.iscoroutinefunction(func):
        # A synchronous handler cannot await `login_state.is_authenticated`, so
        # there is no way to enforce the check. Refuse loudly at import time
        # rather than silently wrapping it in a pass-through, which would leave
        # the handler decorated but completely unguarded.
        msg = (
            f"@is_authenticated cannot guard the synchronous handler "
            f"'{func.__name__}'. Declare it as 'async def' so the session can "
            f"be validated before the body runs."
        )
        raise TypeError(msg)

    return async_wrapper  # type: ignore[return-value]


def requires_admin[F: Callable[..., Any]](func: F) -> F:
    """Authorization decorator: allow the event only for authenticated admins.

    Enforces admin authorization server-side (over the websocket), independent
    of any render-layer gating (``rx.cond``/``admin_only`` templates only affect
    what renders, not whether an event handler runs). Unauthenticated callers are
    redirected to login; authenticated non-admins get a permission error and the
    handler body never executes.
    """

    @wraps(func)
    async def async_gen_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        login_state = await self.get_state(LoginState)
        user = await login_state.authenticated_user
        if user is None:
            logger.debug("User not authenticated, redirecting to login.")
            yield await login_state.redir()
            return
        if not user.is_admin or is_pending_approval(user):
            logger.warning(
                "Non-admin user_id=%s denied admin action '%s'",
                user.user_id,
                func.__name__,
            )
            yield rx.toast.error(_NOT_AUTHORIZED_MSG, position="top-right")
            return
        async for item in func(self, *args, **kwargs):
            yield item

    @wraps(func)
    async def async_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        login_state = await self.get_state(LoginState)
        user = await login_state.authenticated_user
        if user is None:
            logger.debug("User not authenticated, redirecting to login.")
            return await login_state.redir()
        if not user.is_admin or is_pending_approval(user):
            logger.warning(
                "Non-admin user_id=%s denied admin action '%s'",
                user.user_id,
                func.__name__,
            )
            return rx.toast.error(_NOT_AUTHORIZED_MSG, position="top-right")
        return await func(self, *args, **kwargs)

    logger.debug("Check admin authorization for: '%s'", func.__name__)

    if inspect.isasyncgenfunction(func):
        return async_gen_wrapper  # type: ignore[return-value]

    return async_wrapper  # type: ignore[return-value]
