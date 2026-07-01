import functools
import logging
from collections.abc import Callable
from typing import Any

import reflex as rx

import appkit_mantine as mn
from appkit_commons.registry import service_registry
from appkit_user.authentication.states import LOGIN_ROUTE, LoginState, UserSession
from appkit_user.configuration import AuthenticationConfiguration

logger = logging.getLogger(__name__)
ComponentCallable = Callable[[], rx.Component]


@functools.lru_cache(maxsize=1)
def _auth_config() -> AuthenticationConfiguration:
    """Resolve the authentication configuration lazily and cache it."""
    return service_registry().get(AuthenticationConfiguration)


def _session_monitor_interval_ms() -> int:
    """Session monitor poll interval in milliseconds, resolved lazily."""
    return _auth_config().session_monitor_interval_seconds * 1000


def _prolong_interval_ms() -> int:
    """Session prolong interval in milliseconds, resolved lazily."""
    return int(_auth_config().auth_token_refresh_delta * 60 * 1000)


### components ###


_SESSION_MONITOR_JS = """
(function() {{
    const monitorId = 'session-monitor-trigger';
    const prolongId = 'session-prolong-trigger';
    const monitorIntervalMs = {monitor_interval_ms};
    const prolongIntervalMs = {prolong_interval_ms};
    const events = ['click', 'keydown', 'mousemove', 'scroll', 'touchstart'];

    // Cleanup previous instances to prevent leaks and duplicate listeners
    if (window._sessionMonitorInterval) {{
        clearInterval(window._sessionMonitorInterval);
    }}
    if (window._sessionMonitorHandler) {{
        events.forEach(e => document.removeEventListener(
            e, window._sessionMonitorHandler
        ));
    }}

    let lastActivity = Date.now();
    let lastProlong = Date.now(); // Start fresh to avoid immediate prolong on reload

    const updateActivity = (e) => {{
        // Only trust real user events, ignore script-generated events
        // (like our own clicks)
        if (e.isTrusted) {{
            lastActivity = Date.now();
        }}
    }};

    // Store handler globally for cleanup
    window._sessionMonitorHandler = updateActivity;

    events.forEach(e => document.addEventListener(
        e, updateActivity, {{ passive: true }}
    ));

    window._sessionMonitorInterval = setInterval(() => {{
        const checkBtn = document.getElementById(monitorId);
        const prolongBtn = document.getElementById(prolongId);

        const now = Date.now();
        const idle = now - lastActivity;
        const timeSinceProlong = now - lastProlong;

        // 1. Prolong session if active since last prolong AND enough time passed
        if (lastActivity > lastProlong
            && timeSinceProlong > prolongIntervalMs
            && prolongBtn) {{
            prolongBtn.click();
            lastProlong = now;
        }}
        // 2. Otherwise check authentication (redirect if expired)
        else if (checkBtn) {{
            checkBtn.click();
        }}
    }}, monitorIntervalMs);
}})();
"""


def themed_logo(light: str, dark: str, **kwargs: Any) -> rx.Component:
    """Helper to render a logo that changes with color mode."""
    return rx.color_mode_cond(
        mn.image(src=light, **kwargs),
        mn.image(src=dark, **kwargs),
    )


def default_fallback(
    message: str = "Du hast nicht die notwendigen Rechte, um diese Inhalte zu sehen!",
) -> rx.Component:
    """Fallback component to show when the user is not authenticated."""
    return mn.center(
        mn.card(
            mn.title(message, size="h3"),
            mn.text(
                "Melde dich an, um fortzufahren. ",
                rx.link("Anmelden", href="/login", text_decoration="underline"),
            ),
            padding="xl",
            with_border=True,
            maw=400,
        ),
        h="80vh",
    )


def session_monitor() -> rx.Component:
    """Frontend-only component that periodically checks session validity.

    Tracks user activity and extends session if active.
    """
    return rx.fragment(
        rx.el.button(
            id="session-monitor-trigger",
            on_click=LoginState.check_auth,
            style={"display": "none"},
        ),
        rx.el.button(
            id="session-prolong-trigger",
            on_click=UserSession.prolong_session,
            style={"display": "none"},
        ),
        rx.script(
            _SESSION_MONITOR_JS.format(
                monitor_interval_ms=_session_monitor_interval_ms(),
                prolong_interval_ms=_prolong_interval_ms(),
            )
        ),
    )


def password_rule(check: bool, message: str) -> rx.Component:
    return mn.group(
        rx.cond(
            check,
            rx.icon("circle-check", size=18, color="green"),
            rx.icon("circle-x", size=18, color="red"),
        ),
        mn.text(message, size="xs", c="dimmed"),
        gap="xs",
    )


def password_rules_checklist(
    *,
    has_length: bool,
    has_upper: bool,
    has_lower: bool,
    has_digit: bool,
    has_special: bool,
    length_label: str,
    upper_label: str = "Ein Großbuchstabe",
    lower_label: str = "Ein Kleinbuchstabe",
    digit_label: str = "Eine Ziffer",
    special_label: str = "Ein Sonderzeichen",
) -> rx.Component:
    """Render the five password-policy checklist rows.

    Labels are parameterized (callers may use slightly different wording); the
    caller owns the surrounding container/spacing.
    """
    return rx.fragment(
        password_rule(has_length, length_label),
        password_rule(has_upper, upper_label),
        password_rule(has_lower, lower_label),
        password_rule(has_digit, digit_label),
        password_rule(has_special, special_label),
    )


def requires_role(
    *children: Any,
    role: str,
    fallback: rx.Component | None = None,  # noqa: B008
) -> rx.Component:
    return rx.cond(
        UserSession.user.roles.contains(role),
        rx.fragment(*children),
        fallback,
    )


def requires_admin(
    *children: Any,
    fallback: rx.Component | None = None,  # noqa: B008
) -> rx.Component:
    return rx.cond(
        UserSession.user.is_admin,
        rx.fragment(*children),
        fallback,
    )


def requires_authenticated(
    *children: Any,
    fallback: rx.Component | None = None,  # noqa: B008
) -> rx.Component:
    return rx.cond(
        UserSession.is_authenticated,
        rx.fragment(*children),
        fallback if fallback is not None else rx.redirect(LOGIN_ROUTE),
    )
