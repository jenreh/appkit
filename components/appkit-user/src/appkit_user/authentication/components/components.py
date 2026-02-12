import logging
from collections.abc import Callable

import reflex as rx

from appkit_commons.registry import service_registry
from appkit_user.authentication.states import LOGIN_ROUTE, LoginState, UserSession
from appkit_user.configuration import AuthenticationConfiguration, OAuthProvider

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


def _themed_logo(light: str, dark: str, **kwargs) -> rx.Component:
    """Helper to render a logo that changes with color mode."""
    return rx.color_mode_cond(
        rx.image(light, **kwargs),
        rx.image(dark, **kwargs),
    )


def _oauth_button(
    provider: OAuthProvider,
    text: str,
    icon_light: str,
    enabled_var: rx.Var[bool],
    icon_dark: str | None = None,
) -> rx.Component:
    """Helper to render an OAuth login button."""
    icon_class = "absolute left-[30px] top-1/2 -translate-y-1/2 w-5 h-5"
    if icon_dark:
        icon = _themed_logo(icon_light, icon_dark, class_name=icon_class)
    else:
        icon = rx.image(icon_light, class_name=icon_class)

    return rx.cond(
        enabled_var,
        rx.button(
            icon,
            text,
            variant="outline",
            size="3",
            class_name="relative flex w-full",
            loading=LoginState.is_loading,
            on_click=[LoginState.login_with_provider(provider)],
        ),
    )


def _form_inline_field(icon: str, **kwargs) -> rx.Component:
    """Helper to render an inline form field."""
    class_name = kwargs.pop("class_name", "")
    return rx.form.field(
        rx.input(
            rx.input.slot(rx.icon(icon)),
            class_name=f"{class_name} w-full",
            size=kwargs.pop("size", "3"),
            **kwargs,
        ),
        class_name="form-group w-full",
    )


def default_fallback(
    message: str = "Du hast nicht die notwendigen Rechte, um diese Inhalte zu sehen!",
) -> rx.Component:
    """Fallback component to show when the user is not authenticated."""
    return rx.center(
        rx.card(
            rx.heading(message, class_name="w-full", size="3"),
            rx.text(
                "Melde dich an, um fortzufahren. ",
                rx.link("Anmelden", href="/login", text_decoration="underline"),
                class_name="w-full",
            ),
            class_name="w-[380px] p-8",
        ),
        class_name="w-full h-[80vh]",
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


def login_form(
    header: str, logo: str, logo_dark: str, margin_left: str = "0px"
) -> rx.Component:
    return rx.center(
        rx.card(
            rx.vstack(
                rx.hstack(
                    _themed_logo(
                        logo,
                        logo_dark,
                        class_name="h-[60px]",
                        style={"marginLeft": margin_left},
                    ),
                    rx.heading(header, size="8", margin_left="9px", margin_top="24px"),
                    align="center",
                    justify="start",
                    margin_bottom="0.5em",
                ),
                rx.form(
                    rx.vstack(
                        rx.cond(
                            LoginState.error_message,
                            rx.callout(
                                "Fehler: " + LoginState.error_message,
                                icon="triangle_alert",
                                color_scheme="red",
                                role="alert",
                            ),
                        ),
                        _form_inline_field(
                            name="username",
                            icon="user",
                            placeholder="Deine E-Mail-Adresse",
                            auto_focus=True,
                        ),
                        _form_inline_field(
                            name="password",
                            icon="lock",
                            placeholder="Dein Passwort",
                            type="password",
                        ),
                        rx.button(
                            "Anmelden",
                            type="submit",
                            size="3",
                            class_name="w-full mt-3",
                            loading=LoginState.is_loading,
                        ),
                        class_name="justify-start w-full gap-2",
                    ),
                    on_submit=[
                        LoginState.login_with_password,
                    ],
                ),
                rx.hstack(
                    rx.divider(margin="0"),
                    rx.text(
                        "oder",
                        class_name="whitespace-nowrap font-medium",
                    ),
                    rx.divider(margin="0"),
                    class_name="items-center w-full",
                ),
                rx.vstack(
                    _oauth_button(
                        OAuthProvider.GITHUB,
                        "Mit Github anmelden",
                        "/icons/GitHub_light.svg",
                        LoginState.enable_github_oauth,
                        icon_dark="/icons/GitHub_dark.svg",
                    ),
                    _oauth_button(
                        OAuthProvider.AZURE,
                        "Mit Microsoft anmelden",
                        "/icons/microsoft.svg",
                        LoginState.enable_azure_oauth,
                    ),
                    class_name="w-full gap-1",
                ),
                rx.hstack(
                    rx.spacer(),
                    rx.color_mode.button(style={"opacity": "0.8", "scale": "0.95"}),
                    class_name="w-full",
                ),
                class_name="w-full gap-5",
            ),
            size="4",
            class_name="min-w-[26em] max-w-[26em] w-full",
            variant="surface",
            appearance="dark",
        ),
    )


def oauth_login_splash(
    provider: OAuthProvider,
    message: str = "Anmeldung mit {provider}...",
    logo: str = "/img/logo.svg",
    logo_dark: str = "/img/logo_dark.svg",
) -> rx.Component:
    """Render a splash screen while handling OAuth callback."""
    return rx.card(
        rx.vstack(
            _themed_logo(logo, logo_dark, class_name="w-[70%]"),
            rx.hstack(
                rx.text(message.format(provider=provider)),
                rx.spinner(),
                class_name="w-full gap-5",
            ),
        ),
        size="4",
        class_name="min-w-[26em] max-w-[26em] w-full",
        variant="surface",
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
