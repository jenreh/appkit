"""Mantine JsonViewer (``@mantine/code-highlight``, Mantine 9.7)."""

from typing import Any

from reflex.vars.base import Var

from appkit_mantine.base import MANTINE_VERSION, MantineLayoutComponentBase

CODE_HIGHLIGHT_LIBRARY = f"@mantine/code-highlight@{MANTINE_VERSION}"


class JsonViewer(MantineLayoutComponentBase):
    """Mantine JsonViewer — expandable JSON tree with copy support.

    https://mantine.dev/x/code-highlight/
    """

    library = CODE_HIGHLIGHT_LIBRARY
    tag = "JsonViewer"

    value: Var[Any] = None
    """JSON data to display."""

    root_name: Var[str | bool] = None
    default_expand_depth: Var[int] = None
    expanded_paths: Var[list[str]] = None
    max_display_length: Var[int] = None
    with_types: Var[bool] = None
    with_size: Var[bool] = None
    with_copy: Var[bool] = None
    with_copy_button: Var[bool] = None
    with_quotes: Var[bool] = None
    with_key_quotes: Var[bool] = None
    collapse_strings_after_length: Var[int | bool] = None
    sort_keys: Var[bool] = None
    group_arrays_after_length: Var[int | bool] = None
    radius: Var[str | int] = None
    font_size: Var[str | int] = None
    indent_width: Var[int] = None
    with_border: Var[bool] = None
    copy_label: Var[str] = None
    copied_label: Var[str] = None
    expand_all_label: Var[str] = None
    collapse_all_label: Var[str] = None
    with_controls: Var[bool] = None
    highlight_items: Var[dict[str, str]] = None
    """Map of serialized JSON paths to ``"added"`` or ``"removed"``."""

    all_expanded: Var[bool] = None
    with_line_numbers: Var[bool] = None
    with_chevrons: Var[bool] = None

    def _get_custom_code(self) -> str:
        return (
            "import '@mantine/core/styles.css';\n"
            "import '@mantine/code-highlight/styles.css';"
        )

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_expanded_paths_change": lambda paths: [paths],
            "on_value_select": lambda path, value: [path, value],
        }


json_viewer = JsonViewer.create
