from collections.abc import Callable

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.backend.schemas import UploadedFile
from appkit_assistant.components.tools_modal import tools_popover
from appkit_assistant.state.thread_state import ThreadState


def render_model_option(model: dict) -> rx.Component:
    return rx.hstack(
        rx.cond(
            model.icon,
            rx.image(
                src=rx.color_mode_cond(
                    light=f"/icons/{model.icon}.svg",
                    dark=f"/icons/{model.icon}_dark.svg",
                ),
                width="13px",
                margin_right="8px",
            ),
            None,
        ),
        rx.text(model.text),
        align="center",
        spacing="0",
    )


def composer_input(placeholder: str = "Frage etwas...") -> rx.Component:
    return rx.text_area(
        id="composer-area",
        name="composer_prompt",
        placeholder=placeholder,
        value=ThreadState.prompt,
        auto_height=True,
        enter_key_submit=True,
        # stil
        border="0",
        outline="none",
        variant="soft",
        background_color=rx.color("white", 1, alpha=False),
        padding="9px 3px",
        size="3",
        min_height="24px",
        max_height="244px",
        resize="none",
        rows="1",
        width="100%",
        on_change=ThreadState.set_prompt,
    )


def submit() -> rx.Component:
    return rx.cond(
        ThreadState.processing,
        rx.tooltip(
            rx.button(
                rx.icon("square", size=14, fill="currentColor"),
                on_click=ThreadState.request_cancellation,
                color_scheme="red",
                variant="solid",
                type="button",
                cursor="pointer",
                loading=ThreadState.cancellation_requested,
            ),
            content="Stoppen",
        ),
        rx.tooltip(
            rx.button(
                rx.icon("arrow-right", size=18),
                id="composer-submit",
                name="composer_submit",
                type="submit",
            ),
            content="Absenden",
        ),
    )


def _uploaded_file_thumbnail(file: UploadedFile) -> rx.Component:
    """Render a thumbnail for an uploaded file with a remove button."""
    return rx.box(
        rx.hstack(
            rx.icon("file", size=16, color=rx.color("gray", 9)),
            rx.text(
                file.filename,
                size="1",
                max_width="100px",
                overflow="hidden",
                text_overflow="ellipsis",
                white_space="nowrap",
            ),
            spacing="1",
            align="center",
            padding="4px 8px",
            background=rx.color("gray", 3),
            border_radius="6px",
        ),
        rx.icon_button(
            rx.icon("x", size=10),
            width="16px",
            height="16px",
            variant="solid",
            color_scheme="gray",
            position="absolute",
            top="-6px",
            right="-6px",
            border_radius="12px",
            padding="0px",
            cursor="pointer",
            on_click=lambda: ThreadState.remove_file_from_prompt(file.file_path),
        ),
        position="relative",
    )


def selected_files_row() -> rx.Component:
    """Render the row of selected file thumbnails (only visible when files exist)."""
    return rx.cond(
        ThreadState.uploaded_files.length() > 0,
        rx.hstack(
            rx.foreach(
                ThreadState.uploaded_files,
                _uploaded_file_thumbnail,
            ),
            spacing="2",
            flex_wrap="wrap",
            margin_top="6px",
            margin_left="12px",
        ),
        rx.fragment(),
    )


def file_upload(show: bool = False) -> rx.Component:
    """File upload button with drag-and-drop support."""
    return rx.cond(
        show & ThreadState.selected_model_supports_attachments,
        rx.tooltip(
            rx.upload.root(
                rx.tooltip(
                    rx.button(
                        rx.icon("paperclip", size=17),
                        cursor="pointer",
                        variant="ghost",
                        padding="8px",
                    ),
                    content=(
                        "Dateien hochladen (max. "
                        f"{ThreadState.max_files_per_thread}, "
                        f"{ThreadState.max_file_size_mb}MB pro Datei)"
                    ),
                ),
                id="composer_file_upload",
                accept={
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [  # noqa: E501
                        ".xlsx"
                    ],
                    "text/csv": [".csv"],
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document": [".docx"],
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation": [".pptx"],
                    "text/markdown": [".md"],
                    "application/pdf": [".pdf"],
                    "image/png": [".png"],
                    "image/jpeg": [".jpg", ".jpeg"],
                },
                multiple=True,
                max_size=ThreadState.max_file_size_mb * 1024 * 1024,
                on_drop=ThreadState.handle_upload(
                    rx.upload_files(upload_id="composer_file_upload")
                ),
            ),
            content=f"Dateien hochladen (max. {ThreadState.max_files_per_thread}, {ThreadState.max_file_size_mb}MB pro Datei)",
        ),
        rx.fragment(),
    )


def choose_model(show: bool = False) -> rx.Component | None:
    if not show:
        return None

    return rx.cond(
        ThreadState.ai_models,
        mn.rich_select(
            mn.rich_select.map(
                ThreadState.ai_models,
                renderer=render_model_option,
                value=lambda model: model.id,
            ),
            placeholder="Wähle ein Modell",
            value=ThreadState.selected_model,
            on_change=ThreadState.set_selected_model,
            name="model-select",
            width="252px",
            position="top",
        ),
        None,
    )


def web_search_toggle() -> rx.Component:
    """Render web search toggle button."""
    return rx.cond(
        ThreadState.selected_model_supports_search,
        rx.tooltip(
            rx.button(
                rx.icon("globe", size=17),
                cursor="pointer",
                variant=rx.cond(ThreadState.web_search_enabled, "solid", "ghost"),
                color_scheme=rx.cond(ThreadState.web_search_enabled, "blue", "accent"),
                padding="8px",
                margin_right=rx.cond(
                    ThreadState.selected_model_supports_attachments, "6px", "14px"
                ),
                margin_left="-6px",
                on_click=ThreadState.toggle_web_search,
                type="button",
            ),
            content="Websuche aktivieren",
        ),
        rx.fragment(),
    )


def tools(show: bool = False) -> rx.Component:
    """Render tools button with conditional visibility."""
    return rx.cond(
        show,
        rx.hstack(
            tools_popover(),
            spacing="1",
            align="center",
        ),
        rx.fragment(),  # Empty fragment when hidden
    )


def clear(show: bool = True) -> rx.Component | None:
    if not show:
        return None

    return rx.tooltip(
        rx.button(
            rx.icon("paintbrush", size=17),
            cursor="pointer",
            variant="ghost",
            padding="8px",
            on_click=ThreadState.clear,
        ),
        content="Chatverlauf löschen",
    )


def composer(*children, on_submit: Callable, **kwargs) -> rx.Component:
    return rx.vstack(
        rx.form.root(
            *children,
            on_submit=on_submit,
        ),
        **kwargs,
    )


class ComposerComponent(rx.ComponentNamespace):
    __call__ = staticmethod(composer)
    choose_model = staticmethod(choose_model)
    clear = staticmethod(clear)
    file_upload = staticmethod(file_upload)
    web_search_toggle = staticmethod(web_search_toggle)
    input = staticmethod(composer_input)
    selected_files_row = staticmethod(selected_files_row)
    submit = staticmethod(submit)
    tools = staticmethod(tools)


composer = ComposerComponent()
