from collections.abc import Callable

import reflex as rx

import appkit_mantine as mn
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
    return rx.fragment(
        rx.button(
            rx.icon("arrow-right", size=18),
            id="composer-submit",
            name="composer_submit",
            type="submit",
            loading=ThreadState.processing,
        ),
    )


def add_attachment(show: bool = False) -> rx.Component | None:
    if not show:
        return None

    return rx.tooltip(
        rx.button(
            rx.icon("paperclip", size=18),
            rx.text("2 files", size="1", color="gray.2"),
            id="composer-attachment",
            variant="ghost",
            padding="8px",
            access_key="s",
        ),
        content="Manage Attachments…",
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
    add_attachment = staticmethod(add_attachment)
    choose_model = staticmethod(choose_model)
    clear = staticmethod(clear)
    input = staticmethod(composer_input)
    submit = staticmethod(submit)
    tools = staticmethod(tools)


composer = ComposerComponent()
