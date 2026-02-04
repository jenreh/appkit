"""File manager component for assistant administration."""

import reflex as rx
from reflex.components.radix.themes.components.table import TableRow

import appkit_mantine as mn
from appkit_assistant.state.file_manager_state import (
    CleanupStats,
    FileInfo,
    FileManagerState,
    OpenAIFileInfo,
    VectorStoreInfo,
)
from appkit_ui.components.dialogs import delete_dialog


def vector_store_item(store_info: VectorStoreInfo) -> rx.Component:
    """Render a single vector store item in the list."""
    is_selected = FileManagerState.selected_vector_store_id == store_info.store_id
    is_deleting = FileManagerState.deleting_vector_store_id == store_info.store_id

    return rx.box(
        rx.hstack(
            rx.icon("database", size=16, color=rx.color("gray", 11)),
            rx.vstack(
                rx.text(
                    store_info.name,
                    size="2",
                    weight=rx.cond(is_selected, "bold", "regular"),
                    title=store_info.name,
                    style={
                        "overflow": "hidden",
                        "text_overflow": "ellipsis",
                        "white_space": "nowrap",
                        "max_width": "100%",
                    },
                ),
                rx.text(
                    store_info.store_id,
                    title=store_info.store_id,
                    size="1",
                    color="gray",
                    style={
                        "overflow": "hidden",
                        "text_overflow": "ellipsis",
                        "white_space": "nowrap",
                        "max_width": "100%",
                    },
                ),
                spacing="0",
                align="start",
                width="100%",
                min_width="0",
                flex="1",
            ),
            rx.tooltip(
                rx.button(
                    rx.icon("trash", size=13, stroke_width=1.5),
                    variant="ghost",
                    size="1",
                    color_scheme="gray",
                    loading=is_deleting,
                    on_click=FileManagerState.delete_vector_store(
                        store_info.store_id
                    ).stop_propagation,
                ),
                content="Vector Store löschen",
            ),
            spacing="2",
            align="center",
            width="100%",
        ),
        padding="10px 12px",
        cursor="pointer",
        background=rx.cond(
            is_selected,
            rx.color("blue", 3),
            "transparent",
        ),
        border_radius="6px",
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
        width="100%",
    )


def file_table_row(file_info: FileInfo) -> TableRow:
    """Render a single file row in the table."""
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.icon("file-text", size=16, color=rx.color("gray", 11)),
                rx.text(
                    file_info.filename,
                    title=file_info.filename,
                    style={
                        "overflow": "hidden",
                        "text_overflow": "ellipsis",
                        "white_space": "nowrap",
                    },
                ),
                spacing="2",
                align="center",
            ),
            style={
                "max_width": "0",
                "width": "100%",
            },
        ),
        rx.table.cell(
            rx.text(file_info.created_at, size="2"),
            white_space="nowrap",
        ),
        rx.table.cell(
            rx.text(file_info.user_name, size="2"),
            white_space="nowrap",
        ),
        rx.table.cell(
            rx.hstack(
                mn.number_formatter(
                    value=file_info.formatted_size,
                    decimal_scale=1,
                    suffix=file_info.size_suffix,
                ),
                spacing="1",
            ),
            white_space="nowrap",
        ),
        rx.table.cell(
            rx.cond(
                FileManagerState.deleting_file_id == file_info.id,
                rx.spinner(size="1"),
                delete_dialog(
                    title="Datei löschen",
                    content=file_info.filename,
                    on_click=lambda: FileManagerState.delete_file(file_info.id),
                    icon_button=True,
                    size="1",
                    variant="ghost",
                    color_scheme="red",
                ),
            ),
            white_space="nowrap",
        ),
        vertical_align="middle",
        style={"_hover": {"bg": rx.color("gray", 2)}},
    )


def empty_state(message: str) -> rx.Component:
    """Render an empty state message."""
    return rx.center(
        rx.vstack(
            rx.icon("inbox", size=48, color=rx.color("gray", 8)),
            rx.text(message, size="3", color="gray"),
            spacing="3",
            align="center",
        ),
        height="200px",
        width="100%",
    )


def cleanup_stat_row(label: str, value: rx.Var[int]) -> rx.Component:
    """Render a single cleanup statistic row."""
    return rx.hstack(
        rx.text(label, size="2", color="gray"),
        rx.text(value.to_string(), size="2", weight="bold"),
        justify="between",
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

    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon(
                        rx.cond(is_error, "alert-circle", "trash-2"),
                        size=20,
                        color=rx.cond(
                            is_error,
                            rx.color("red", 11),
                            rx.cond(
                                is_completed,
                                rx.color("green", 11),
                                rx.color("blue", 11),
                            ),
                        ),
                    ),
                    rx.text("Bereinigung"),
                    spacing="2",
                    align="center",
                ),
            ),
            rx.dialog.description(
                rx.vstack(
                    # Status message
                    rx.hstack(
                        rx.cond(
                            is_running,
                            rx.spinner(size="1"),
                            rx.fragment(),
                        ),
                        rx.text(status_message, size="2"),
                        spacing="2",
                        align="center",
                    ),
                    # Error message
                    rx.cond(
                        is_error,
                        rx.callout(
                            stats.error,
                            icon="triangle-alert",
                            color="red",
                            size="1",
                        ),
                        rx.fragment(),
                    ),
                    # Progress indicator
                    rx.cond(
                        stats.total_vector_stores > 0,
                        rx.vstack(
                            rx.progress(
                                value=rx.cond(
                                    stats.total_vector_stores > 0,
                                    (stats.vector_stores_checked * 100)
                                    / stats.total_vector_stores,
                                    0,
                                ),
                                width="100%",
                            ),
                            rx.text(
                                f"Geprüft: {stats.vector_stores_checked} / "
                                f"{stats.total_vector_stores}",
                                size="1",
                                color="gray",
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        rx.fragment(),
                    ),
                    # Current processing
                    rx.cond(
                        stats.current_vector_store.is_not_none(),
                        rx.text(
                            f"Aktuell: {stats.current_vector_store}",
                            size="1",
                            color="gray",
                            style={
                                "overflow": "hidden",
                                "text_overflow": "ellipsis",
                                "white_space": "nowrap",
                                "max_width": "100%",
                            },
                        ),
                        rx.fragment(),
                    ),
                    # Statistics
                    rx.divider(),
                    rx.vstack(
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
                        spacing="1",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                    padding_y="2",
                ),
            ),
            rx.flex(
                rx.button(
                    "Schließen",
                    variant="soft",
                    disabled=is_running,
                    on_click=FileManagerState.close_cleanup_modal,
                ),
                justify="end",
                spacing="2",
                margin_top="16px",
            ),
            max_width="400px",
        ),
        open=FileManagerState.cleanup_modal_open,
        on_open_change=FileManagerState.set_cleanup_modal_open,
    )


def cleanup_button() -> rx.Component:
    """Render the cleanup button."""
    return rx.button(
        rx.icon("trash-2", size=14),
        rx.text("Vector Stores aufräumen"),
        variant="soft",
        color_scheme="red",
        size="2",
        disabled=FileManagerState.cleanup_running,
        loading=FileManagerState.cleanup_running,
        on_click=[
            FileManagerState.open_cleanup_modal,
            FileManagerState.start_cleanup,
        ],
    )


def openai_file_table_row(file_info: OpenAIFileInfo) -> TableRow:
    """Render a single OpenAI file row in the table."""
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.icon("file-text", size=16, color=rx.color("gray", 11)),
                rx.text(
                    file_info.filename,
                    title=file_info.filename,
                    style={
                        "overflow": "hidden",
                        "text_overflow": "ellipsis",
                        "white_space": "nowrap",
                    },
                ),
                spacing="2",
                align="center",
            ),
            style={
                "max_width": "0",
                "width": "100%",
            },
        ),
        rx.table.cell(
            rx.text(file_info.purpose, size="2"),
            white_space="nowrap",
        ),
        rx.table.cell(
            rx.text(file_info.created_at, size="2"),
            white_space="nowrap",
        ),
        rx.table.cell(
            rx.text(file_info.expires_at, size="2"),
            white_space="nowrap",
        ),
        rx.table.cell(
            rx.hstack(
                mn.number_formatter(
                    value=file_info.formatted_size,
                    decimal_scale=1,
                    suffix=file_info.size_suffix,
                ),
                spacing="1",
            ),
            white_space="nowrap",
        ),
        rx.table.cell(
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
                    variant="ghost",
                    color_scheme="red",
                ),
            ),
            white_space="nowrap",
        ),
        vertical_align="middle",
        style={"_hover": {"bg": rx.color("gray", 2)}},
    )


def file_manager() -> rx.Component:
    """File manager component with tabs for vector stores and OpenAI files."""
    return rx.fragment(
        cleanup_progress_modal(),
        rx.tabs.root(
            rx.hstack(
                rx.tabs.list(
                    rx.tabs.trigger("Vector Store Dateien", value="vector_stores"),
                    rx.tabs.trigger("OpenAI Dateien", value="openai_files"),
                    width="100%",
                ),
                rx.spacer(),
                cleanup_button(),
                width="100%",
                align="center",
                padding_right="16px",
            ),
            rx.tabs.content(
                rx.hstack(
                    # Left column: Vector stores list
                    rx.box(
                        rx.vstack(
                            rx.cond(
                                FileManagerState.vector_stores.length() > 0,
                                mn.scroll_area(
                                    rx.vstack(
                                        rx.foreach(
                                            FileManagerState.vector_stores,
                                            vector_store_item,
                                        ),
                                        spacing="1",
                                        width="100%",
                                    ),
                                    height="calc(100vh - 350px)",
                                    width="100%",
                                    scrollbars="y",
                                    type="auto",
                                ),
                                empty_state("Keine Vector Stores vorhanden."),
                            ),
                            spacing="2",
                            width="100%",
                            align="start",
                        ),
                        width="280px",
                        min_width="280px",
                        padding="16px",
                        border_right=f"1px solid {rx.color('gray', 5)}",
                        height="calc(100vh - 280px)",
                    ),
                    # Right column: Files table
                    rx.box(
                        rx.vstack(
                            rx.cond(
                                FileManagerState.selected_vector_store_id == "",
                                empty_state("Wähle einen Vector Store aus."),
                                rx.cond(
                                    FileManagerState.loading,
                                    rx.center(
                                        rx.vstack(
                                            rx.spinner(size="3"),
                                            rx.text(
                                                "Dateien werden geladen...",
                                                size="2",
                                                color="gray",
                                            ),
                                            spacing="3",
                                            align="center",
                                        ),
                                        height="200px",
                                        width="100%",
                                    ),
                                    rx.cond(
                                        FileManagerState.files.length() > 0,
                                        mn.scroll_area(
                                            rx.table.root(
                                                rx.table.header(
                                                    rx.table.row(
                                                        rx.table.column_header_cell(
                                                            "Dateiname", width="auto"
                                                        ),
                                                        rx.table.column_header_cell(
                                                            "Erstellt am", width="140px"
                                                        ),
                                                        rx.table.column_header_cell(
                                                            "Benutzer", width="150px"
                                                        ),
                                                        rx.table.column_header_cell(
                                                            "Größe", width="100px"
                                                        ),
                                                        rx.table.column_header_cell(
                                                            "", width="50px"
                                                        ),
                                                    ),
                                                ),
                                                rx.table.body(
                                                    rx.foreach(
                                                        FileManagerState.files,
                                                        file_table_row,
                                                    )
                                                ),
                                                size="2",
                                                width="100%",
                                                table_layout="fixed",
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
                            spacing="2",
                            width="100%",
                            align="start",
                        ),
                        flex="1",
                        padding="16px",
                        height="calc(100vh - 280px)",
                    ),
                    spacing="0",
                    width="100%",
                    align="start",
                ),
                value="vector_stores",
            ),
            rx.tabs.content(
                rx.box(
                    rx.vstack(
                        rx.cond(
                            FileManagerState.loading,
                            rx.center(
                                rx.vstack(
                                    rx.spinner(size="3"),
                                    rx.text(
                                        "Dateien werden geladen...",
                                        size="2",
                                        color="gray",
                                    ),
                                    spacing="3",
                                    align="center",
                                ),
                                height="200px",
                                width="100%",
                            ),
                            rx.cond(
                                FileManagerState.openai_files.length() > 0,
                                mn.scroll_area(
                                    rx.table.root(
                                        rx.table.header(
                                            rx.table.row(
                                                rx.table.column_header_cell(
                                                    "Dateiname", width="auto"
                                                ),
                                                rx.table.column_header_cell(
                                                    "Zweck",
                                                    width="120px",
                                                    white_space="nowrap",
                                                ),
                                                rx.table.column_header_cell(
                                                    "Erstellt am",
                                                    width="140px",
                                                    white_space="nowrap",
                                                ),
                                                rx.table.column_header_cell(
                                                    "Läuft ab",
                                                    width="140px",
                                                    white_space="nowrap",
                                                ),
                                                rx.table.column_header_cell(
                                                    "Größe", width="100px"
                                                ),
                                                rx.table.column_header_cell(
                                                    "", width="50px"
                                                ),
                                            ),
                                        ),
                                        rx.table.body(
                                            rx.foreach(
                                                FileManagerState.openai_files,
                                                openai_file_table_row,
                                            )
                                        ),
                                        size="2",
                                        width="100%",
                                        table_layout="fixed",
                                    ),
                                    height="calc(100vh - 350px)",
                                    width="100%",
                                    scrollbars="y",
                                    type="auto",
                                ),
                                empty_state("Keine OpenAI-Dateien vorhanden."),
                            ),
                        ),
                        spacing="2",
                        width="100%",
                        align="start",
                    ),
                    flex="1",
                    padding="16px",
                    height="calc(100vh - 280px)",
                ),
                value="openai_files",
            ),
            default_value="vector_stores",
            width="100%",
            on_change=FileManagerState.on_tab_change,
            on_mount=FileManagerState.load_vector_stores,
        ),
    )
