"""Mantine CodeHighlight extension components."""

from typing import Any, Literal

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MANTINE_VERSION, MantineLayoutComponentBase

CODE_HIGHLIGHT_LIBRARY = f"@mantine/code-highlight@{MANTINE_VERSION}"


class MantineCodeHighlightBase(MantineLayoutComponentBase):
    """Base class for CodeHighlight components."""

    library = CODE_HIGHLIGHT_LIBRARY

    def _get_custom_code(self) -> str:
        return """import '@mantine/core/styles.css';
import '@mantine/code-highlight/styles.css';"""


class CodeHighlight(MantineCodeHighlightBase):
    """Mantine CodeHighlight — syntax-highlighted code block.

    https://mantine.dev/x/code-highlight/
    """

    tag = "CodeHighlight"

    _rename_props = {
        "code_color_scheme": "codeColorScheme",
        "collapse_code_label": "collapseCodeLabel",
        "copied_label": "copiedLabel",
        "copy_label": "copyLabel",
        "default_expanded": "defaultExpanded",
        "expand_code_label": "expandCodeLabel",
        "max_collapsed_height": "maxCollapsedHeight",
        "on_expanded_change": "onExpandedChange",
        "with_border": "withBorder",
        "with_copy_button": "withCopyButton",
        "with_expand_button": "withExpandButton",
    }

    code: Var[str] = None
    language: Var[str] = None
    background: Var[str] = None
    radius: Var[str | int] = None
    with_border: Var[bool] = None
    with_copy_button: Var[bool] = None
    with_expand_button: Var[bool] = None
    default_expanded: Var[bool] = None
    expanded: Var[bool] = None
    max_collapsed_height: Var[str | int] = None
    copy_label: Var[str] = None
    copied_label: Var[str] = None
    expand_code_label: Var[str] = None
    collapse_code_label: Var[str] = None
    code_color_scheme: Var[Literal["dark", "light"]] = None
    controls: Var[list[Any]] = None

    on_expanded_change: EventHandler[lambda expanded: [expanded]] = None


class CodeHighlightTabs(MantineCodeHighlightBase):
    """Mantine CodeHighlightTabs — tabbed code blocks.

    https://mantine.dev/x/code-highlight/
    """

    tag = "CodeHighlightTabs"

    _rename_props = {
        "active_tab": "activeTab",
        "code_color_scheme": "codeColorScheme",
        "collapse_code_label": "collapseCodeLabel",
        "default_active_tab": "defaultActiveTab",
        "get_file_icon": "getFileIcon",
        "max_collapsed_height": "maxCollapsedHeight",
        "on_expanded_change": "onExpandedChange",
        "on_tab_change": "onTabChange",
        "with_border": "withBorder",
        "with_copy_button": "withCopyButton",
        "with_expand_button": "withExpandButton",
    }

    code: Var[list[dict[str, Any]]] = None
    """List of {code: str, language: str, fileName?: str}"""

    active_tab: Var[int] = None
    default_active_tab: Var[int] = None
    background: Var[str] = None
    radius: Var[str | int] = None
    with_border: Var[bool] = None
    with_copy_button: Var[bool] = None
    with_expand_button: Var[bool] = None
    max_collapsed_height: Var[str | int] = None
    code_color_scheme: Var[str] = None

    on_tab_change: EventHandler[lambda tab: [tab]] = None
    on_expanded_change: EventHandler[lambda expanded: [expanded]] = None


class InlineCodeHighlight(MantineCodeHighlightBase):
    """Mantine InlineCodeHighlight — inline syntax-highlighted snippet."""

    tag = "InlineCodeHighlight"

    code: Var[str] = None
    language: Var[str] = None


class CodeHighlightNamespace(rx.ComponentNamespace):
    """Namespace for CodeHighlight components."""

    __call__ = staticmethod(CodeHighlight.create)
    tabs = staticmethod(CodeHighlightTabs.create)
    inline = staticmethod(InlineCodeHighlight.create)


code_highlight = CodeHighlightNamespace()
