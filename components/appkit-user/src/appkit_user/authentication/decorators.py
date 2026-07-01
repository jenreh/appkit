import asyncio
import inspect
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import reflex as rx

from appkit_user.authentication.states import LoginState

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

_NOT_AUTHORIZED_MSG = "Sie haben keine Berechtigung für diese Aktion."


def is_authenticated[F: Callable[..., Any]](func: F) -> F:
    """Authentication decorator with async support"""

    @wraps(func)
    async def async_gen_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        login_state = await self.get_state(LoginState)
        if not await login_state.is_authenticated:
            logger.debug("User not authenticated, redirecting to login.")
            yield await login_state.redir()
            return
        async for item in func(self, *args, **kwargs):
            yield item

    @wraps(func)
    async def async_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        login_state = await self.get_state(LoginState)
        if not await login_state.is_authenticated:
            logger.debug("User not authenticated, redirecting to login.")
            return await login_state.redir()
        return await func(self, *args, **kwargs)

    @wraps(func)
    def sync_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        return func(self, *args, **kwargs)

    # Return appropriate wrapper based on function type
    logger.debug("Check valid authentication for: '%s'", func.__name__)

    if inspect.isasyncgenfunction(func):
        return async_gen_wrapper  # type: ignore[return-value]

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper  # type: ignore[return-value]


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
        if not user.is_admin:
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
        if not user.is_admin:
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
