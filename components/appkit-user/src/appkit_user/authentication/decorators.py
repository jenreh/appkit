import asyncio
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from appkit_user.authentication.states import LoginState

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def is_authenticated[F: Callable[..., Any]](func: F) -> F:
    """Authentication decorator with async support"""

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
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper  # type: ignore[return-value]
