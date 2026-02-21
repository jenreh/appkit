import logging

import reflex as rx

import appkit_mantine as mn
from appkit_ui.components.header import header
from appkit_user.authentication.components.components import password_rule
from appkit_user.authentication.states import UserSession
from appkit_user.user_management.states.profile_states import (
    MIN_PASSWORD_LENGTH,
    ProfileState,
)

logger = logging.getLogger(__name__)


def _status_row(label: str, active: bool = False) -> rx.Component:
    """Render a single status row with icon."""
    return mn.group(
        mn.text(label, w=120, size="sm", style={"whiteSpace": "nowrap"}),
        rx.cond(
            active,
            rx.icon(
                "circle-check",
                class_name="w-5 h-5 text-teal-500",
                stroke_width=2,
            ),
            rx.icon(
                "circle-x",
                class_name="w-5 h-5 text-red-400",
                stroke_width=2,
            ),
        ),
        w="100%",
        align="center",
        gap="xs",
    )


def _status_section() -> rx.Component:
    """Render the user status section."""
    return mn.stack(
        mn.group(
            rx.icon("shield", class_name="w-4 h-4", stroke_width=1.5),
            mn.text("Status", size="sm", fw=500),
            w="100%",
            align="center",
            gap="xs",
        ),
        rx.cond(
            UserSession.user,
            mn.stack(
                _status_row("Administrator", UserSession.user.is_admin),
                _status_row("Aktiv", UserSession.user.is_active),
                _status_row("Verifiziert", UserSession.user.is_verified),
                gap="xs",
            ),
            mn.stack(
                _status_row("Administrator", False),
                _status_row("Aktiv", False),
                _status_row("Verifiziert", False),
                gap="xs",
            ),
        ),
        w="100%",
        gap="xs",
    )


def _personal_info_section() -> rx.Component:
    """Render the personal information form section."""
    return mn.grid(
        mn.grid_col(
            mn.stack(
                mn.group(
                    rx.icon("square-user-round", size=20),
                    mn.title("Persönliche Informationen", size="h4"),
                    align="center",
                    gap="sm",
                ),
                mn.text(
                    "Aktualisiere deine persönlichen Informationen.",
                    size="sm",
                    c="dimmed",
                ),
            ),
            span={"base": 12, "md": 5},
        ),
        mn.grid_col(
            rx.form(
                mn.stack(
                    mn.text_input(
                        label="Name",
                        left_section=rx.icon("user", size=16),
                        placeholder="Dein Name",
                        name="lastname",
                        default_value=UserSession.user.name,
                        read_only=True,
                    ),
                    mn.text_input(
                        label="E-Mail / Benutzername",
                        left_section=rx.icon("at-sign", size=16),
                        placeholder="Deine E-Mail-Adresse",
                        default_value=UserSession.user.email,
                        name="mail",
                        read_only=True,
                    ),
                    _status_section(),
                    gap="md",
                ),
                class_name="w-full",
            ),
            span={"base": 12, "md": 7},
        ),
        gutter="xl",
        w="100%",
    )


def _password_change_section() -> rx.Component:
    """Render the password change form section."""
    return mn.grid(
        mn.grid_col(
            mn.stack(
                mn.group(
                    rx.icon("key-round", size=20),
                    mn.title("Passwort ändern", size="h4"),
                    align="center",
                    gap="sm",
                ),
                mn.text(
                    "Aktualisiere dein Passwort. Ein neues Passwort muss der "
                    "Passwort-Richtlinie entsprechen:",
                    size="sm",
                    c="dimmed",
                ),
                mn.stack(
                    password_rule(
                        ProfileState.has_length,
                        f"Mindestens {MIN_PASSWORD_LENGTH} Zeichen",
                    ),
                    password_rule(
                        ProfileState.has_upper, "Mindestens ein Großbuchstabe"
                    ),
                    password_rule(
                        ProfileState.has_lower, "Mindestens ein Kleinbuchstabe"
                    ),
                    password_rule(ProfileState.has_digit, "Mindestens eine Zahl"),
                    password_rule(
                        ProfileState.has_special, "Mindestens ein Sonderzeichen"
                    ),
                    gap="xs",
                    mt="md",
                ),
            ),
            span={"base": 12, "md": 5},
        ),
        mn.grid_col(
            rx.form(
                mn.stack(
                    mn.password_input(
                        label="Aktuelles Passwort",
                        left_section=rx.icon("lock", size=16),
                        placeholder="dein aktuelles Passwort",
                        name="current_password",
                        value=ProfileState.current_password,
                        on_change=ProfileState.set_current_password,
                        required=True,
                    ),
                    mn.password_input(
                        label="Neues Passwort",
                        left_section=rx.icon("lock-keyhole-open", size=16),
                        placeholder="Dein neues Passwort...",
                        value=ProfileState.new_password,
                        on_change=ProfileState.set_new_password,
                        required=True,
                    ),
                    rx.cond(
                        ProfileState.strength_value > 0,
                        mn.progress(
                            value=ProfileState.strength_value,
                            size="sm",
                            radius="xl",
                        ),
                    ),
                    mn.password_input(
                        label="Passwort bestätigen",
                        left_section=rx.icon("lock-keyhole", size=16),
                        placeholder="bestätige dein neues Passwort",
                        error=ProfileState.password_error,
                        name="confirm_password",
                        value=ProfileState.confirm_password,
                        on_change=ProfileState.set_confirm_password,
                        required=True,
                    ),
                    mn.button(
                        "Passwort aktualisieren",
                        type="submit",
                        full_width=True,
                    ),
                    gap="md",
                ),
                on_submit=ProfileState.handle_password_update,
                reset_on_submit=True,
                class_name="w-full",
            ),
            span={"base": 12, "md": 7},
        ),
        gutter="xl",
        w="100%",
    )


def user_profile_view(**kwargs) -> rx.Component:
    """Render the user profile view content."""
    return mn.stack(
        header("Profil"),
        _personal_info_section(),
        mn.divider(my="md"),
        _password_change_section(),
        **kwargs,
    )
