"""File manager component for assistant administration."""

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.state.file_manager_state import (
    CleanupStats,
    FileInfo,
    FileManagerState,
    OpenAIFileInfo,
    VectorStoreInfo,
)
from appkit_ui.components.dialogs import delete_dialog
from appkit_ui.styles import sticky_header_style


def vector_store_item(store_info: VectorStoreInfo) -> rx.Component:
    """Render a single vector store item in the list."""
    is_selected = FileManagerState.selected_vector_store_id == store_info.store_id
    is_deleting = FileManagerState.deleting_vector_store_id == store_info.store_id

    return mn.box(
        mn.group(
            rx.icon("database", size=16, color=rx.color("gray", 11)),
            mn.stack(
                mn.text(
                    store_info.name,
                    size="sm",
                    fw=rx.cond(is_selected, "bold", "normal"),
                    title=store_info.name,
                    style={
                        "overflow": "hidden",
                        "text_overflow": "ellipsis",
                        "white_space": "nowrap",
                        "max_width": "100%",
                    },
                ),
                mn.text(
                    store_info.store_id,
                    title=store_info.store_id,
                    size="xs",
                    c="dimmed",
                    style={
                        "overflow": "hidden",
                        "text_overflow": "ellipsis",
                        "white_space": "nowrap",
                        "max_width": "100%",
                    },
                ),
                gap="0",
                align="start",
                w="100%",
                style={"min_width": "0"},
                flex="1",
            ),
            rx.tooltip(
                mn.action_icon(
                    rx.icon("trash", size=13, stroke_width=1.5),
                    variant="subtle",
                    size="xs",
                    color="gray",
                    loading=is_deleting,
                    on_click=FileManagerState.delete_vector_store(
                        store_info.store_id
                    ).stop_propagation,
                ),
                content="Vector Store löschen",
            ),
            gap="sm",
            align="center",
            w="100%",
        ),
        p="md",
        style={"cursor": "pointer"},
        background=rx.cond(
            is_selected,
            rx.color("blue", 3),
            "transparent",
        ),
        br="md",
        _hover={
            "background": rx.cond(
                is_selected,
                rx.color("blue", 4),
                rx.color("gray", 3),
            ),
        },
        on_click=lambda: FileManagerState.select_vector_store(
            store_info.store_id, store_info.name
        ),
        w="100%",
    )


def file_table_row(file_info: FileInfo) -> rx.Component:
    """Render a single file row in the table."""
    return mn.table.tr(
        mn.table.td(
            mn.group(
                rx.icon("file-text", size=16, color=rx.color("gray", 11)),
                mn.text(
                    file_info.filename,
                    title=file_info.filename,
                    style={
                        "overflow": "hidden",
                        "text_overflow": "ellipsis",
                        "white_space": "nowrap",
                    },
                ),
                gap="sm",
                align="center",
            ),
            style={
                "max_width": "0",
                "width": "100%",
            },
        ),
        mn.table.td(
            mn.text(file_info.created_at, size="sm"),
            style={"whiteSpace": "nowrap"},
        ),
        mn.table.td(
            mn.text(file_info.user_name, size="sm"),
            style={"whiteSpace": "nowrap"},
        ),
        mn.table.td(
            mn.group(
                mn.number_formatter(
                    value=file_info.formatted_size,
                    decimal_scale=1,
                    suffix=file_info.size_suffix,
                ),
                gap="xs",
            ),
            style={"whiteSpace": "nowrap"},
        ),
        mn.table.td(
            rx.cond(
                FileManagerState.deleting_file_id == file_info.id,
                rx.spinner(size="1"),
                delete_dialog(
                    title="Datei löschen",
                    content=file_info.filename,
                    on_click=lambda: FileManagerState.delete_file(file_info.id),
                    icon_button=True,
                    size="1",
                    variant="surface",
                ),
            ),
            style={"whiteSpace": "nowrap"},
        ),
        style={"_hover": {"bg": rx.color("gray", 2)}},
    )


def empty_state(message: str) -> rx.Component:
    """Render an empty state message."""
    return mn.center(
        mn.stack(
            rx.icon("inbox", size=48, color=rx.color("gray", 8)),
            mn.text(message, size="md", c="dimmed"),
            gap="md",
            align="center",
        ),
        h="200px",
        w="100%",
    )


def cleanup_stat_row(label: str, value: rx.Var[int]) -> rx.Component:
    """Render a single cleanup statistic row."""
    return mn.group(
        mn.text(label, size="sm", c="dimmed"),
        mn.text(value.to_string(), size="sm", fw="bold"),
        justify="space-between",
        width="100%",
    )


def cleanup_progress_modal() -> rx.Component:
    """Render the cleanup progress modal with live statistics."""
    stats: CleanupStats = FileManagerState.cleanup_stats
    is_running = FileManagerState.cleanup_running
    is_completed = stats.status == "completed"
    is_error = stats.status == "error"

    # Status message based on current state
    status_message = rx.match(
        stats.status,
        ("idle", "Bereit zur Bereinigung"),
        ("starting", "Starte Bereinigung..."),
        ("checking", "Prüfe Vector Stores..."),
        ("deleting", "Lösche abgelaufene Stores..."),
        ("completed", "Bereinigung abgeschlossen"),
        ("error", "Fehler bei der Bereinigung"),
        "Unbekannter Status",
    )

    return mn.modal.root(
        mn.modal.overlay(),
        mn.modal.content(
            mn.modal.header(
                mn.group(
                    rx.icon(
                        rx.cond(is_error, "circle-alert", "trash-2"),
                        size=23,
                        color=rx.cond(
                            is_error,
                            rx.color("red", 11),
                            rx.cond(
                                is_completed,
                                rx.color("green", 11),
                                rx.color("blue", 11),
                            ),
                        ),
                        margin_right="1rem",
                    ),
                    mn.modal.title(
                        rx.cond(
                            FileManagerState.selected_file_model_name,
                            f"Bereinigung - "
                            f"{FileManagerState.selected_file_model_name}",
                            "Bereinigung",
                        ),
                    ),
                    gap="2",
                    align="center",
                ),
                mn.modal.close_button(),
            ),
            mn.modal.body(
                mn.stack(
                    # Status message
                    mn.group(
                        rx.cond(
                            is_running,
                            rx.spinner(size="1"),
                            rx.fragment(),
                        ),
                        mn.text(status_message, size="sm"),
                        gap="md",
                        align="center",
                    ),
                    # Error message
                    rx.cond(
                        is_error,
                        mn.alert(
                            stats.error,
                            icon="triangle-alert",
                            color="red",
                            title="Fehler",
                            size="sm",
                        ),
                        rx.fragment(),
                    ),
                    # Progress indicator
                    mn.stack(
                        mn.progress(
                            value=rx.cond(
                                stats.total_vector_stores > 0,
                                (stats.vector_stores_checked * 100)
                                / stats.total_vector_stores,
                                100,
                            ),
                            width="100%",
                        ),
                        mn.text(
                            f"Geprüft: {stats.vector_stores_checked} / "
                            f"{stats.total_vector_stores}",
                            size="xs",
                            c="dimmed",
                        ),
                        gap="sm",
                        width="100%",
                    ),
                    # Current processing
                    rx.cond(
                        stats.current_vector_store.is_not_none(),
                        mn.text(
                            f"Aktuell: {stats.current_vector_store}",
                            size="xs",
                            c="dimmed",
                            style={
                                "overflow": "hidden",
                                "text_overflow": "ellipsis",
                                "white_space": "nowrap",
                                "max_width": "100%",
                            },
                        ),
                        rx.fragment(),
                    ),
                    mn.stack(
                        cleanup_stat_row(
                            "Abgelaufene Stores:", stats.vector_stores_expired
                        ),
                        cleanup_stat_row(
                            "Gelöschte Stores:", stats.vector_stores_deleted
                        ),
                        cleanup_stat_row("Gefundene Dateien:", stats.files_found),
                        cleanup_stat_row("Gelöschte Dateien:", stats.files_deleted),
                        cleanup_stat_row(
                            "Aktualisierte Threads:", stats.threads_updated
                        ),
                        gap="xs",
                        width="100%",
                    ),
                    # Footer
                    mn.group(
                        mn.button(
                            "Schließen",
                            variant="light",
                            disabled=is_running,
                            on_click=FileManagerState.close_cleanup_modal,
                        ),
                        justify="flex-end",
                        gap="md",
                        mt="16px",
                    ),
                    gap="md",
                    width="100%",
                ),
            ),
            size="400px",
        ),
        opened=FileManagerState.cleanup_modal_open,
        on_close=FileManagerState.close_cleanup_modal,
        centered=True,
    )


def cleanup_button() -> rx.Component:
    """Render the cleanup button."""
    return mn.button(
        "Vector Stores aufräumen",
        left_section=rx.icon("trash-2", size=14),
        variant="light",
        color="red",
        size="sm",
        # w="270px",
        disabled=FileManagerState.cleanup_running,
        loading=FileManagerState.cleanup_running,
        on_click=[
            FileManagerState.open_cleanup_modal,
            FileManagerState.start_cleanup,
        ],
    )


def openai_file_table_row(file_info: OpenAIFileInfo) -> rx.Component:
    """Render a single OpenAI file row in the table."""
    return mn.table.tr(
        mn.table.td(
            mn.group(
                rx.icon("file-text", size=16, color=rx.color("gray", 11)),
                mn.text(
                    file_info.filename,
                    title=file_info.filename,
                    style={
                        "overflow": "hidden",
                        "text_overflow": "ellipsis",
                        "white_space": "nowrap",
                    },
                ),
                gap="sm",
                align="center",
            ),
            style={
                "max_width": "0",
                "width": "100%",
            },
        ),
        mn.table.td(
            mn.text(file_info.purpose, size="sm"),
            style={"whiteSpace": "nowrap"},
        ),
        mn.table.td(
            mn.text(file_info.created_at, size="sm"),
            style={"whiteSpace": "nowrap"},
        ),
        mn.table.td(
            mn.text(file_info.expires_at, size="sm"),
            style={"whiteSpace": "nowrap"},
        ),
        mn.table.td(
            mn.group(
                mn.number_formatter(
                    value=file_info.formatted_size,
                    decimal_scale=1,
                    suffix=file_info.size_suffix,
                ),
                gap="xs",
            ),
            style={"whiteSpace": "nowrap"},
        ),
        mn.table.td(
            rx.cond(
                FileManagerState.deleting_openai_file_id == file_info.openai_id,
                rx.spinner(size="1"),
                delete_dialog(
                    title="Datei löschen",
                    content=file_info.filename,
                    on_click=lambda: FileManagerState.delete_openai_file(
                        file_info.openai_id
                    ),
                    icon_button=True,
                    size="1",
                    variant="surface",
                ),
            ),
            style={"whiteSpace": "nowrap"},
        ),
        style={"_hover": {"bg": rx.color("gray", 2)}},
    )


def file_manager() -> rx.Component:
    """File manager component with tabs for vector stores and OpenAI files."""
    return rx.fragment(
        cleanup_progress_modal(),
        mn.stack(
            # Top bar: model selector + cleanup button
            rx.flex(
                mn.select(
                    data=FileManagerState.file_model_options,
                    value=FileManagerState.selected_file_model_id,
                    on_change=FileManagerState.set_selected_file_model,
                    placeholder="Abonnement auswählen...",
                    size="sm",
                    w="16rem",
                    disabled=~FileManagerState.has_file_models,
                ),
                rx.spacer(),
                cleanup_button(),
                width="100%",
                gap="12px",
                align="center",
            ),
            mn.tabs(
                mn.tabs.list(
                    mn.tabs.tab("Vector Store Dateien", value="vector_stores"),
                    mn.tabs.tab("OpenAI Dateien", value="openai_files"),
                ),
                mn.tabs.panel(
                    mn.group(
                        # Left column: Vector stores list
                        mn.box(
                            mn.stack(
                                rx.cond(
                                    FileManagerState.vector_stores.length() > 0,
                                    mn.scroll_area(
                                        mn.stack(
                                            rx.foreach(
                                                FileManagerState.vector_stores,
                                                vector_store_item,
                                            ),
                                            gap="xs",
                                            width="100%",
                                        ),
                                        height="calc(100vh - 350px)",
                                        width="100%",
                                        scrollbars="y",
                                        type="auto",
                                    ),
                                    empty_state("Keine Vector Stores vorhanden."),
                                ),
                                gap="md",
                                width="100%",
                                align="start",
                            ),
                            w="280px",
                            miw="280px",
                            p="md",
                            style={"border_right": f"1px solid {rx.color('gray', 5)}"},
                            h="calc(100vh - 280px)",
                        ),
                        # Right column: Files table
                        mn.box(
                            mn.stack(
                                rx.cond(
                                    FileManagerState.selected_vector_store_id == "",
                                    empty_state("Wähle einen Vector Store aus."),
                                    rx.cond(
                                        FileManagerState.loading,
                                        mn.center(
                                            mn.stack(
                                                rx.spinner(size="3"),
                                                mn.text(
                                                    "Dateien werden geladen...",
                                                    size="sm",
                                                    c="dimmed",
                                                ),
                                                gap="md",
                                                align="center",
                                            ),
                                            h="200px",
                                            w="100%",
                                        ),
                                        rx.cond(
                                            FileManagerState.files.length() > 0,
                                            mn.scroll_area(
                                                mn.table(
                                                    mn.table.thead(
                                                        mn.table.tr(
                                                            mn.table.th(
                                                                mn.text(
                                                                    "Dateiname",
                                                                    size="sm",
                                                                    fw="700",
                                                                ),
                                                                width="auto",
                                                            ),
                                                            mn.table.th(
                                                                mn.text(
                                                                    "Erstellt am",
                                                                    size="sm",
                                                                    fw="700",
                                                                ),
                                                                width="140px",
                                                            ),
                                                            mn.table.th(
                                                                mn.text(
                                                                    "Benutzer",
                                                                    size="sm",
                                                                    fw="700",
                                                                ),
                                                                width="150px",
                                                            ),
                                                            mn.table.th(
                                                                mn.text(
                                                                    "Größe",
                                                                    size="sm",
                                                                    fw="700",
                                                                ),
                                                                width="100px",
                                                            ),
                                                            mn.table.th(
                                                                mn.text("", size="sm"),
                                                                width="50px",
                                                            ),
                                                            style=sticky_header_style,
                                                        ),
                                                    ),
                                                    mn.table.tbody(
                                                        rx.foreach(
                                                            FileManagerState.files,
                                                            file_table_row,
                                                        )
                                                    ),
                                                    sticky_header=True,
                                                    sticky_header_offset="0px",
                                                    striped=False,
                                                    highlight_on_hover=True,
                                                    highlight_on_hover_color=rx.color_mode_cond(
                                                        light="gray.0",
                                                        dark="dark.8",
                                                    ),
                                                    w="100%",
                                                ),
                                                height="calc(100vh - 350px)",
                                                width="100%",
                                                scrollbars="y",
                                                type="auto",
                                            ),
                                            empty_state("Keine Dateien vorhanden."),
                                        ),
                                    ),
                                ),
                                gap="md",
                                width="100%",
                                align="start",
                            ),
                            flex="1",
                            p="md",
                            h="calc(100vh - 280px)",
                        ),
                        gap="0",
                        width="100%",
                        align="start",
                    ),
                    value="vector_stores",
                ),
                mn.tabs.panel(
                    mn.box(
                        mn.stack(
                            rx.cond(
                                FileManagerState.loading,
                                mn.center(
                                    mn.stack(
                                        rx.spinner(size="3"),
                                        mn.text(
                                            "Dateien werden geladen...",
                                            size="sm",
                                            c="dimmed",
                                        ),
                                        gap="md",
                                        align="center",
                                    ),
                                    h="200px",
                                    w="100%",
                                ),
                                rx.cond(
                                    FileManagerState.openai_files.length() > 0,
                                    mn.scroll_area(
                                        mn.table(
                                            mn.table.thead(
                                                mn.table.tr(
                                                    mn.table.th(
                                                        mn.text(
                                                            "Dateiname",
                                                            size="sm",
                                                            fw="700",
                                                        ),
                                                        width="auto",
                                                    ),
                                                    mn.table.th(
                                                        mn.text(
                                                            "Zweck", size="sm", fw="700"
                                                        ),
                                                        width="120px",
                                                        style={"whiteSpace": "nowrap"},
                                                    ),
                                                    mn.table.th(
                                                        mn.text(
                                                            "Erstellt am",
                                                            size="sm",
                                                            fw="700",
                                                        ),
                                                        width="140px",
                                                        style={"whiteSpace": "nowrap"},
                                                    ),
                                                    mn.table.th(
                                                        mn.text(
                                                            "Läuft ab",
                                                            size="sm",
                                                            fw="700",
                                                        ),
                                                        width="140px",
                                                        style={"whiteSpace": "nowrap"},
                                                    ),
                                                    mn.table.th(
                                                        mn.text(
                                                            "Größe", size="sm", fw="700"
                                                        ),
                                                        width="100px",
                                                    ),
                                                    mn.table.th(
                                                        mn.text("", size="sm"),
                                                        width="50px",
                                                    ),
                                                    style=sticky_header_style,
                                                ),
                                            ),
                                            mn.table.tbody(
                                                rx.foreach(
                                                    FileManagerState.openai_files,
                                                    openai_file_table_row,
                                                )
                                            ),
                                            sticky_header=True,
                                            sticky_header_offset="0px",
                                            striped=False,
                                            highlight_on_hover=True,
                                            highlight_on_hover_color=rx.color_mode_cond(
                                                light="gray.0",
                                                dark="dark.8",
                                            ),
                                            w="100%",
                                        ),
                                        height="calc(100vh - 350px)",
                                        width="100%",
                                        scrollbars="y",
                                        type="auto",
                                    ),
                                    empty_state("Keine OpenAI-Dateien vorhanden."),
                                ),
                            ),
                            gap="md",
                            width="100%",
                            align="start",
                        ),
                        flex="1",
                        p="md",
                        h="calc(100vh - 280px)",
                    ),
                    value="openai_files",
                ),
                default_value="vector_stores",
                on_change=FileManagerState.on_tab_change,
                w="100%",
            ),
            gap="xs",
            w="100%",
            align="end",
            on_mount=FileManagerState.load_file_models,
        ),
    )
