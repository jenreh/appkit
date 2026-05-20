"""AlertDialog component examples — mn.alert_dialog compound API.

Demonstrates:
- Basic delete confirmation (icon trigger)
- Controlled open state
- Custom labels / colors
- Compound usage (manual cancel + action)
- Footer convenience component
- Integration with delete_dialog helper from appkit_ui

Based on: components/appkit-mantine/src/appkit_mantine/alert_dialog.py
"""

import reflex as rx

import appkit_mantine as mn
from appkit_ui.components.dialogs import delete_dialog
from appkit_user.authentication.templates import navbar_layout

from app.components.navbar import app_navbar


class AlertDialogExamplesState(rx.State):
    """State for alert dialog examples."""

    last_action: str = "-"
    action_loading: bool = False

    # Controlled-mode example
    controlled_open: bool = False

    def set_controlled_open(self, value: bool) -> None:
        self.controlled_open = value

    def record_delete(self) -> None:
        self.last_action = "Datensatz gelöscht"

    def record_archive(self) -> None:
        self.last_action = "Datensatz archiviert"

    def record_reset(self) -> None:
        self.last_action = "Passwort zurückgesetzt"

    def record_cancel(self) -> None:
        self.last_action = "Abgebrochen"


def _example_card(title: str, description: str, *content: rx.Component) -> rx.Component:
    return mn.card(
        mn.stack(
            mn.text(title, fw="600", size="md"),
            mn.text(description, size="sm", c="dimmed"),
            mn.divider(my="xs"),
            *content,
            gap="sm",
        ),
        w="100%",
        with_border=True,
        radius="md",
        p="lg",
    )


def _status_badge(state_var: rx.Var) -> rx.Component:
    return mn.group(
        mn.text("Letzter Vorgang:", size="sm", c="dimmed"),
        mn.badge(state_var, variant="light", color="blue"),
        gap="xs",
        align="center",
        mt="sm",
    )


# ─── Example 1 - delete_dialog helper ────────────────────────────────────────


def delete_dialog_helper_example() -> rx.Component:
    return _example_card(
        "delete_dialog helper",
        "Drop-in replacement: appkit_ui.delete_dialog now uses mn.alert_dialog"
        " internally.",
        mn.group(
            delete_dialog(
                title="Datensatz löschen",
                content="Beispiel-Datensatz #42",
                on_click=AlertDialogExamplesState.record_delete,
                icon_button=True,
                color="red",
                variant="subtle",
            ),
            mn.text("Trash-Icon öffnet den Dialog", size="sm", c="dimmed"),
            gap="sm",
            align="center",
        ),
        _status_badge(AlertDialogExamplesState.last_action),
    )


# ─── Example 2 - footer convenience ──────────────────────────────────────────


def footer_convenience_example() -> rx.Component:
    return _example_card(
        "mn.alert_dialog.footer",
        "Convenience footer renders Cancel + Action buttons in one component. "
        "Title, description and footer accept style/class_name for custom styling.",
        mn.alert_dialog.root(
            mn.alert_dialog.trigger(
                mn.button(
                    "Archivieren",
                    left_section=rx.icon("archive", size=16),
                    variant="light",
                    color="orange",
                ),
            ),
            mn.alert_dialog.content(
                mn.alert_dialog.title(
                    "Datensatz archivieren",
                    style={"background": "var(--mantine-color-orange-0)"},
                ),
                mn.alert_dialog.description(
                    mn.text(
                        "Soll ",
                        rx.el.strong("Projekt Alpha"),
                        " wirklich archiviert werden? Der Datensatz wird in das "
                        "Archiv verschoben und ist weiterhin lesbar.",
                        size="sm",
                    ),
                ),
                mn.alert_dialog.footer(
                    action_label="Archivieren",
                    cancel_label="Abbrechen",
                    on_action=AlertDialogExamplesState.record_archive,
                    on_cancel=AlertDialogExamplesState.record_cancel,
                    action_props={"color": "orange", "variant": "filled"},
                    style={"background": "var(--mantine-color-orange-0)"},
                ),
            ),
        ),
        _status_badge(AlertDialogExamplesState.last_action),
    )


# ─── Example 3 - manual compound usage ───────────────────────────────────────


def compound_example() -> rx.Component:
    return _example_card(
        "Compound API (manual cancel + action)",
        "Full control: compose Title, Description, Cancel and Action individually.",
        mn.alert_dialog.root(
            mn.alert_dialog.trigger(
                mn.button(
                    "Passwort zurücksetzen",
                    left_section=rx.icon("key-round", size=16),
                    variant="outline",
                ),
            ),
            mn.alert_dialog.content(
                mn.alert_dialog.title("Passwort zurücksetzen"),
                mn.alert_dialog.description(
                    mn.stack(
                        mn.text(
                            "Eine E-Mail wird an den Benutzer gesendet mit einem "
                            "Link zum Zurücksetzen des Passworts.",
                            size="sm",
                        ),
                        mn.alert(
                            "Der Benutzer wird über diesen Vorgang informiert.",
                            title="Hinweis",
                            color="yellow",
                            variant="light",
                            icon=rx.icon("info", size=16),
                        ),
                        gap="sm",
                    ),
                ),
                mn.group(
                    mn.alert_dialog.cancel(
                        "Abbrechen",
                        on_cancel=AlertDialogExamplesState.record_cancel,
                    ),
                    mn.alert_dialog.action(
                        "E-Mail senden",
                        color="blue",
                        on_action=AlertDialogExamplesState.record_reset,
                    ),
                    justify="flex-end",
                    mt="md",
                    p="16px",
                    border_top="1px solid var(--mantine-color-default-border)",
                ),
            ),
        ),
        _status_badge(AlertDialogExamplesState.last_action),
    )


# ─── Example 4 - controlled open state ───────────────────────────────────────


def controlled_example() -> rx.Component:
    return _example_card(
        "Controlled open state",
        "Pass open + on_open_change to manage dialog state from Reflex.",
        mn.group(
            mn.button(
                "Dialog öffnen",
                on_click=AlertDialogExamplesState.set_controlled_open(True),
            ),
            gap="sm",
        ),
        mn.alert_dialog.root(
            mn.alert_dialog.content(
                mn.alert_dialog.title("Aktion bestätigen"),
                mn.alert_dialog.description(
                    mn.text(
                        "Dieser Dialog wird durch Reflex-State gesteuert "
                        "(kein Trigger-Sub-Component).",
                        size="sm",
                    ),
                ),
                mn.alert_dialog.footer(
                    on_action=AlertDialogExamplesState.record_delete,
                    on_cancel=AlertDialogExamplesState.record_cancel,
                    action_props={"color": "red"},
                ),
            ),
            open=AlertDialogExamplesState.controlled_open,
            on_open_change=AlertDialogExamplesState.set_controlled_open,
        ),
        _status_badge(AlertDialogExamplesState.last_action),
    )


# ─── Example 5 - custom size & centered ──────────────────────────────────────


def size_example() -> rx.Component:
    return _example_card(
        "Benutzerdefinierte Größe",
        "Passe size und centered des Dialogs an.",
        mn.group(
            mn.alert_dialog.root(
                mn.alert_dialog.trigger(
                    mn.button("Größe: xs", variant="default", size="sm"),
                ),
                mn.alert_dialog.content(
                    mn.alert_dialog.title("Kleiner Dialog"),
                    mn.alert_dialog.description(
                        mn.text("size='xs' - kompakter Dialog.", size="sm"),
                    ),
                    mn.alert_dialog.footer(
                        on_action=AlertDialogExamplesState.record_delete
                    ),
                ),
                size="xs",
            ),
            mn.alert_dialog.root(
                mn.alert_dialog.trigger(
                    mn.button("Größe: md", variant="default", size="sm"),
                ),
                mn.alert_dialog.content(
                    mn.alert_dialog.title("Mittlerer Dialog"),
                    mn.alert_dialog.description(
                        mn.text("size='md' - Standard-Größe.", size="sm"),
                    ),
                    mn.alert_dialog.footer(
                        on_action=AlertDialogExamplesState.record_delete
                    ),
                ),
                size="md",
            ),
            mn.alert_dialog.root(
                mn.alert_dialog.trigger(
                    mn.button("Größe: lg", variant="default", size="sm"),
                ),
                mn.alert_dialog.content(
                    mn.alert_dialog.title("Großer Dialog"),
                    mn.alert_dialog.description(
                        mn.text("size='lg' - breiter Dialog.", size="sm"),
                    ),
                    mn.alert_dialog.footer(
                        on_action=AlertDialogExamplesState.record_delete
                    ),
                ),
                size="lg",
            ),
            gap="sm",
            wrap="wrap",
        ),
    )


# ─── Page ─────────────────────────────────────────────────────────────────────


@navbar_layout(
    route="/alert-dialog",
    title="AlertDialog Examples",
    navbar=app_navbar(),
    with_header=False,
)
def alert_dialog_examples() -> rx.Component:
    return mn.container(
        mn.stack(
            mn.title("AlertDialog Examples", order=1),
            mn.text(
                "mn.alert_dialog — Mantine-basierter AlertDialog mit Radix-kompatiblem "
                "Compound API. Kein externer State nötig; der Trigger"
                " öffnet den Dialog automatisch.",
                size="md",
                c="dimmed",
            ),
            mn.divider(my="md"),
            delete_dialog_helper_example(),
            footer_convenience_example(),
            compound_example(),
            controlled_example(),
            size_example(),
            gap="xl",
        ),
        size="md",
        py="xl",
    )
