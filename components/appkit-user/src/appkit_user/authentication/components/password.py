import logging

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.components.components import password_rule, themed_logo
from appkit_user.authentication.password_reset_states import (
    PasswordResetConfirmState,
    PasswordResetRequestState,
)
from appkit_user.user_management.states.profile_states import (
    MIN_PASSWORD_LENGTH,
)

logger = logging.getLogger(__name__)


def password_reset_request_form(
    logo: str,
    logo_dark: str,
) -> rx.Component:
    """Render the password reset request form (email entry)."""
    return mn.center(
        mn.card(
            mn.stack(
                mn.group(
                    themed_logo(
                        light=logo,
                        dark=logo_dark,
                        h=60,
                        w="auto",
                        style={"objectFit": "contain"},
                    ),
                    align="center",
                    justify="flex-start",
                    mb="xs",
                ),
                mn.stack(
                    mn.title("Passwort zurücksetzen", size="h3"),
                    mn.text(
                        "Geben Sie Ihre E-Mail-Adresse ein, um einen "
                        "Link zum Zurücksetzen Ihres Passworts zu erhalten.",
                        c="dimmed",
                        size="sm",
                    ),
                    gap="xs",
                ),
                rx.cond(
                    PasswordResetRequestState.email_error,
                    mn.alert(
                        PasswordResetRequestState.email_error,
                        color="red",
                        variant="filled",
                        p="6px",
                    ),
                ),
                rx.cond(
                    PasswordResetRequestState.is_submitted,
                    mn.alert(
                        PasswordResetRequestState.success_message,
                        color="green",
                        variant="filled",
                        p="6px",
                    ),
                ),
                rx.form(
                    mn.stack(
                        mn.text_input(
                            placeholder="E-Mail-Adresse",
                            value=PasswordResetRequestState.email,
                            on_change=PasswordResetRequestState.set_email,
                            type="email",
                            size="md",
                            left_section=rx.icon("mail", size=16),
                            required=True,
                        ),
                        mn.button(
                            "Link senden",
                            type="submit",
                            size="md",
                            full_width=True,
                            loading=PasswordResetRequestState.is_loading,
                        ),
                        mn.group(
                            rx.link(
                                mn.text(
                                    "Zurück zur Anmeldung",
                                    size="sm",
                                    c="blue",
                                ),
                                href="/login",
                            ),
                            justify="flex-end",
                            w="100%",
                        ),
                        gap="md",
                    ),
                    on_submit=PasswordResetRequestState.request_password_reset,
                    class_name="w-full",
                ),
                gap="lg",
            ),
            padding="lg",
            radius="md",
            with_border=True,
            w=400,
        ),
        h="100vh",
    )


def password_reset_confirm_form(
    logo: str,
    logo_dark: str,
) -> rx.Component:
    """Render the password reset confirm form (new password entry)."""
    return mn.center(
        mn.card(
            mn.stack(
                mn.group(
                    themed_logo(
                        light=logo,
                        dark=logo_dark,
                        h=60,
                        w="auto",
                        style={"objectFit": "contain"},
                    ),
                    align="center",
                    justify="flex-start",
                    mb="xs",
                ),
                rx.cond(
                    PasswordResetConfirmState.token_error,
                    mn.alert(
                        PasswordResetConfirmState.token_error,
                        title="Token",
                        color="red",
                        variant="filled",
                        p="6px",
                    ),
                ),
                rx.cond(
                    PasswordResetConfirmState.password_error,
                    mn.alert(
                        PasswordResetConfirmState.password_error,
                        color="red",
                        variant="filled",
                        p="6px",
                    ),
                ),
                rx.cond(
                    PasswordResetConfirmState.password_history_error,
                    mn.alert(
                        PasswordResetConfirmState.password_history_error,
                        title="Passwortverlauf",
                        color="red",
                        variant="filled",
                        p="6px",
                    ),
                ),
                mn.grid(
                    mn.grid_col(
                        mn.stack(
                            rx.form(
                                mn.stack(
                                    mn.password_input(
                                        placeholder="Neues Passwort",
                                        label="Geben Sie Ihr neues Passwort ein.",
                                        description=(
                                            "Für "
                                            + PasswordResetConfirmState.user_email
                                        ),
                                        value=PasswordResetConfirmState.new_password,
                                        on_change=PasswordResetConfirmState.set_new_password,
                                        size="md",
                                        left_section=rx.icon("lock", size=16),
                                        required=True,
                                    ),
                                    mn.password_input(
                                        placeholder="Passwort bestätigen",
                                        value=PasswordResetConfirmState.confirm_password,
                                        on_change=PasswordResetConfirmState.set_confirm_password,
                                        size="md",
                                        left_section=rx.icon("lock", size=16),
                                        required=True,
                                    ),
                                    mn.button(
                                        "Passwort zurücksetzen",
                                        type="submit",
                                        size="md",
                                        full_width=True,
                                        loading=PasswordResetConfirmState.is_loading,
                                    ),
                                    mn.group(
                                        rx.link(
                                            mn.text(
                                                "Zurück zur Anmeldung",
                                                size="sm",
                                                c="blue",
                                            ),
                                            href="/login",
                                        ),
                                        justify="flex-end",
                                        w="100%",
                                    ),
                                    gap="md",
                                ),
                                on_submit=PasswordResetConfirmState.confirm_password_reset,
                                class_name="w-full",
                            ),
                            gap="lg",
                        ),
                        span=7,
                    ),
                    mn.grid_col(
                        mn.stack(
                            mn.stack(
                                password_rule(
                                    PasswordResetConfirmState.has_length,
                                    f"Mindestens {MIN_PASSWORD_LENGTH} Zeichen",
                                ),
                                password_rule(
                                    PasswordResetConfirmState.has_upper,
                                    "Ein Großbuchstabe",
                                ),
                                password_rule(
                                    PasswordResetConfirmState.has_lower,
                                    "Ein Kleinbuchstabe",
                                ),
                                password_rule(
                                    PasswordResetConfirmState.has_digit,
                                    "Eine Ziffer",
                                ),
                                password_rule(
                                    PasswordResetConfirmState.has_special,
                                    "Ein Sonderzeichen",
                                ),
                                gap="xs",
                            ),
                            mt="3rem",
                            h="100%",
                            p="0",
                        ),
                        span=5,
                    ),
                    gutter="xl",
                ),
                gap="lg",
            ),
            padding="lg",
            radius="md",
            with_border=True,
            w=564,
        ),
        h="100vh",
    )
