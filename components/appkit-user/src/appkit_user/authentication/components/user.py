import logging

import reflex as rx

import appkit_mantine as mn
from appkit_ui.components.header import header
from appkit_user.authentication.components.components import password_rule
from appkit_user.authentication.states import UserSession
from appkit_user.user_management.components.user_profile import profile_roles
from appkit_user.user_management.states.profile_states import (
    MIN_PASSWORD_LENGTH,
    ProfileState,
)

logger = logging.getLogger(__name__)


def user_profile_view(**kwargs) -> rx.Component:
    """Render the user profile view content."""
    return mn.stack(
        header("Profil"),
        mn.grid(
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
                    rx.form(
                        mn.stack(
                            rx.cond(
                                UserSession.user.avatar_url,
                                mn.avatar(
                                    src=UserSession.user.avatar_url,
                                    size="xl",
                                    radius="xl",
                                    mb="xs",
                                ),
                            ),
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
                            rx.cond(
                                UserSession.user,
                                profile_roles(
                                    is_admin=UserSession.user.is_admin,
                                    is_active=UserSession.user.is_active,
                                    is_verified=UserSession.user.is_verified,
                                ),
                                profile_roles(
                                    is_admin=False,
                                    is_active=False,
                                    is_verified=False,
                                ),
                            ),
                            gap="md",
                        ),
                        class_name="w-full",
                    ),
                    gap="md",
                ),
                span={"base": 12, "md": 6},
            ),
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
                    ),
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
                    gap="md",
                ),
                span={"base": 12, "md": 6},
            ),
            gutter="xl",
        ),
        gap="xl",
        **kwargs,
    )
