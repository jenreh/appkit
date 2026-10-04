"""Servlet-filter-style session guard for Reflex WebSocket events.

This is the primary gate. It runs as a ``reflex.middleware.Middleware`` and is
consulted *before* the event's handler is resolved, so returning a non-``None``
``StateUpdate`` short-circuits the whole pipeline: ``on_load_internal`` never
runs, a protected page's ``on_load`` handlers never fire, and no page data is
fetched or serialised into a delta.

That ordering is the security property. The redirect that accompanies the
denial is *not* atomic — an ``ssr: false`` SPA still mounts the target route for
roughly one frame before the client processes the redirect — so an empty shell
may flash. Safety comes from NOT SENDING THE DATA, not from the redirect.

THREAT MODEL — read before relying on this for authorization. The route the
filter checks is ``state.router.url.path``, which Reflex builds from the
``asPath`` field of the client's own ``router_data`` (``RouterData`` at
reflex/istate/data.py; only ``pathname`` is normalized server-side, into
``route_id``). A crafted socket client can therefore declare ``asPath:
"/login"`` and have any event treated as public.

That is not a regression — before this filter existed, directly emitted events
were not gated at all — and it does not expose page data, because
``on_load_internal`` resolves its handlers from the *same* client value, so a
spoofed public path loads the public page's handlers. But it does mean this
filter stops an unauthenticated *browser*, not a determined attacker crafting
socket frames. Per-handler authorization remains the enforcing layer: keep using
:func:`appkit_user.authentication.decorators.is_authenticated` and
:func:`~appkit_user.authentication.decorators.requires_admin` on protected event
handlers. Closing the gap properly means gating on the event's target state
class instead of on any client-declared path.

Known limitation: a short-circuit emits no delta, so the ``redirect_to`` the
denial records on :class:`LoginState` lives only server-side. That is enough for
the usual flow (the bounce to ``/login`` is a client-side navigation, which does
not re-hydrate), but a hard refresh in between makes the browser push its stale
``login_redirect_to`` back and the user lands on the homepage after logging in
instead of the page they asked for.

Wire it up once in the consumer app::

    from appkit_user.authentication.session_filter import install_session_filter

    install_session_filter(app)
"""

import logging
from typing import TYPE_CHECKING, Any, Final

import reflex as rx
from reflex.middleware import Middleware
from reflex.state import (
    BaseState,
    FrontendEventExceptionState,
    State,
    StateUpdate,
    UpdateVarsInternalState,
)
from reflex_base.event import Event

from appkit_commons.public_path import strip_public_prefix
from appkit_user.authentication.session_validation import (
    LOGIN_ROUTE,
    SessionStatus,
    SessionValidator,
    is_public_route,
    is_session_filter_enabled,
    safe_redirect_path,
)
from appkit_user.authentication.states import (
    AUTH_TOKEN_LOCAL_STORAGE_KEY,
    SESSION_COOKIE_NAME,
    LoginState,
    UserSession,
)

if TYPE_CHECKING:
    from reflex.app import App

logger = logging.getLogger(__name__)

# Reflex's generic per-state setter; never a bootstrap event on its own.
_SETVAR: Final = "setvar"
_HOME_ROUTE: Final = "/"


def _event_names(state_cls: type[BaseState], *handlers: str) -> set[str]:
    """Fully-qualified event names for handlers on a state class."""
    prefix = state_cls.get_full_name()
    return {f"{prefix}.{handler}" for handler in handlers}


def _bootstrap_events() -> frozenset[str]:
    """Internal events that must always pass the filter.

    Client-side storage — including the session cookie — reaches the backend
    *inside* the hydrate event. Blocking these would make the session
    unknowable and brick the app, so they are allowed unconditionally.
    """
    # FrontendEventExceptionState carries exactly one handler besides the
    # generic setter; read it off the class instead of hardcoding its name.
    exception_handlers = tuple(
        name for name in FrontendEventExceptionState.event_handlers if name != _SETVAR
    )
    return frozenset(
        _event_names(State, "hydrate", "set_is_hydrated")
        | _event_names(UpdateVarsInternalState, "update_vars_internal")
        | _event_names(FrontendEventExceptionState, *exception_handlers)
    )


BOOTSTRAP_EVENTS: Final = _bootstrap_events()


def _login_redirect(
    router_data: dict[str, Any], *, drop_credentials: bool = False
) -> StateUpdate:
    """Build the short-circuit update that bounces the client to the login page.

    ``set_is_hydrated(True)`` is mandatory: without it the client stays at
    ``is_hydrated == False`` forever and the loading cursor never clears.

    A short-circuit emits no delta (the processor only forwards
    ``update.delta`` when it is truthy), so clearing the token *server-side* is
    invisible to the browser. ``drop_credentials`` therefore wipes the dead
    token and cookie with explicit client-side events instead. It is off for
    :attr:`SessionStatus.ERROR`: the database is what failed, the credential is
    not known to be bad, and destroying it would turn a transient blip into a
    forced logout.

    Args:
        router_data: Router data of the event being short-circuited.
        drop_credentials: Whether to clear the browser's stored session token.

    Returns:
        The update that denies the event.
    """
    specs: list[Any] = []
    if drop_credentials:
        specs.append(rx.remove_local_storage(AUTH_TOKEN_LOCAL_STORAGE_KEY))
        specs.append(rx.remove_cookie(SESSION_COOKIE_NAME))
    specs.append(rx.redirect(LOGIN_ROUTE))
    specs.append(State.set_is_hydrated(True))
    return StateUpdate(events=Event.from_event_type(specs, router_data=router_data))


class SessionFilter(Middleware):
    """Denies WebSocket events that arrive without a currently valid session."""

    def __init__(self, validator: SessionValidator | None = None) -> None:
        """Create the filter.

        Args:
            validator: Session validator to use; a default one is created when
                omitted. Injectable for tests.
        """
        self._validator = validator or SessionValidator()

    async def preprocess(
        self,
        app: "App",  # noqa: ARG002 - part of the Middleware contract
        state: BaseState,
        event: Event,
    ) -> StateUpdate | None:
        """Gate an incoming event.

        Args:
            app: The Reflex app (unused).
            state: The session root state.
            event: The event about to be processed.

        Returns:
            ``None`` to let the event through, or a ``StateUpdate`` that
            short-circuits it with a redirect to the login page.
        """
        try:
            return await self._evaluate(state, event)
        except Exception as e:
            # Fail closed: an unexpected error must not become an
            # authorization bypass, and must not escape into the event loop.
            logger.error("Session filter failed for event=%s: %s", event.name, e)
            return _login_redirect(event.router_data)

    async def _evaluate(self, state: BaseState, event: Event) -> StateUpdate | None:
        """Apply the filter rules to one event."""
        if not is_session_filter_enabled():
            return None

        if event.name in BOOTSTRAP_EVENTS:
            return None

        # Gated by ROUTE, not by state class: that is what lets the login
        # page's own events (login_with_password, handle_oauth_callback) run
        # while the visitor is still unauthenticated. NOTE this path comes from
        # the client's own `asPath` and is therefore spoofable — see the THREAT
        # MODEL section of the module docstring.
        path = strip_public_prefix(state.router.url.path)
        if is_public_route(path):
            return None

        user_session = await state.get_state(UserSession)
        # Cookie first, LocalStorage as fallback so sessions created before the
        # cookie existed keep working.
        token = user_session.session_cookie or user_session.auth_token

        # preprocess holds the exclusive per-session state lock, so a DB round
        # trip per event would serialize the session's whole event stream. A
        # cached expiry that has not been reached yet is authoritative.
        if token and user_session._has_unexpired_cache():  # noqa: SLF001 - backend var helper, underscore is required by Reflex
            return None

        result = await self._validator.validate(
            session_id=token, user_id=user_session.user_id
        )
        if result.is_valid:
            user_session._cache_session(result)  # noqa: SLF001 - see above
            return None

        return await self._deny(state, user_session, path, result.status, event)

    async def _deny(
        self,
        state: BaseState,
        user_session: UserSession,
        path: str,
        status: SessionStatus,
        event: Event,
    ) -> StateUpdate:
        """Log, tear the session down and short-circuit to the login page."""
        logger.warning(
            "Session filter denied path=%s status=%s user_id=%s",
            path,
            status.value,
            user_session.user_id,
        )
        session_is_known_bad = status is not SessionStatus.ERROR
        try:
            await self._clear_session(user_session, session_is_known_bad)
            await self._remember_path(state, path)
        except Exception as e:
            # The denial itself must never raise.
            logger.warning("Session teardown after denial failed: %s", e)
        return _login_redirect(event.router_data, drop_credentials=session_is_known_bad)

    async def _clear_session(
        self, user_session: UserSession, session_is_known_bad: bool
    ) -> None:
        """Drop the session, but only when it is known to be gone.

        On :attr:`SessionStatus.ERROR` the database is what failed, so the
        session was never *shown* to be invalid. Access is still denied
        (fail-closed), but the credential is left intact so a retry can
        succeed once the database recovers — the same stance
        :meth:`LoginState.check_auth` takes. Tearing it down here would let a
        single transient error log every active user out.

        Args:
            user_session: The session state to clear.
            session_is_known_bad: Whether validation actually proved the
                session absent or expired.
        """
        if not session_is_known_bad:
            return
        await user_session.terminate_session()  # type: ignore[operator]  # rx.event handler invoked directly

    async def _remember_path(self, state: BaseState, path: str) -> None:
        """Record the attempted path so login can send the user back to it.

        The path is client-supplied, so it is sanitised first: an unchecked
        value makes the post-login redirect an open redirect.
        """
        target = safe_redirect_path(path)
        if not target or target == _HOME_ROUTE:
            return
        login_state = await state.get_state(LoginState)
        login_state.redirect_to = target


def install_session_filter(app: rx.App) -> None:
    """Register the session filter on a Reflex app. Consumer apps call this once.

    Args:
        app: The Reflex app to guard.
    """
    app.add_middleware(SessionFilter())
