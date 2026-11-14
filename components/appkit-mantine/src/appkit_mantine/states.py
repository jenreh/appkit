import reflex as rx


class LoadingState(rx.State):
    is_loading: bool = False
    is_loading_message: str = "Lade..."

    @rx.event
    def set_is_loading(self, is_loading: bool) -> None:
        self.is_loading = is_loading


class ThemeState(rx.State):
    """The state for the theme of the app."""

    # accent_color: str = "crimson"
    gray_color: str = "gray"
    radius: str = "large"
    scaling: str = "100%"
    appearance: str = "inherit"


def with_loading_reset(
    on_load: rx.EventHandler | list[rx.EventHandler] | None,
) -> list[rx.EventHandler]:
    """Build on_load handlers: page handlers first, then reset ``LoadingState``."""
    handlers: list[rx.EventHandler] = []
    if on_load is None:
        handlers.append(LoadingState.set_is_loading(False))
    elif isinstance(on_load, list):
        handlers.extend(on_load)
        handlers.append(LoadingState.set_is_loading(False))
    else:
        handlers.extend([on_load, LoadingState.set_is_loading(False)])
    return handlers
