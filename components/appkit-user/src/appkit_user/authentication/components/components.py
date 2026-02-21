import logging
from collections.abc import Callable

import reflex as rx

import appkit_mantine as mn
from appkit_commons.registry import service_registry
from appkit_user.authentication.states import LOGIN_ROUTE, LoginState, UserSession
from appkit_user.configuration import AuthenticationConfiguration

logger = logging.getLogger(__name__)
ComponentCallable = Callable[[], rx.Component]

# Get session monitor interval from configuration
_auth_config: AuthenticationConfiguration = service_registry().get(
    AuthenticationConfiguration
)
SESSION_MONITOR_INTERVAL_MS = _auth_config.session_monitor_interval_seconds * 1000
PROLONG_INTERVAL_MS = int(_auth_config.auth_token_refresh_delta * 60 * 1000)

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


def themed_logo(light: str, dark: str, **kwargs) -> rx.Component:
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
                monitor_interval_ms=SESSION_MONITOR_INTERVAL_MS,
                prolong_interval_ms=PROLONG_INTERVAL_MS,
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


def requires_role(
    *children,
    role: str,
    fallback: rx.Component | None = None,  # noqa: B008
) -> rx.Component:
    return rx.cond(
        UserSession.user.roles.contains(role),
        rx.fragment(*children),
        fallback,
    )


def requires_admin(
    *children,
    fallback: rx.Component | None = None,  # noqa: B008
) -> rx.Component:
    return rx.cond(
        UserSession.user.is_admin,
        rx.fragment(*children),
        fallback,
    )


def requires_authenticated(
    *children,
    fallback: rx.Component | None = None,  # noqa: B008
) -> rx.Component:
    return rx.cond(
        UserSession.is_authenticated,
        rx.fragment(*children),
        fallback if fallback is not None else rx.redirect(LOGIN_ROUTE),
    )
