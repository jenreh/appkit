from typing import Literal

import reflex as rx
from reflex.vars.base import Var

from appkit_mantine.base import MantineLayoutComponentBase, MantineNumberSize


class Text(MantineLayoutComponentBase):
    """Mantine Text component.

    Display text and links with theme styles.
    https://mantine.dev/core/text/
    """

    tag = "Text"

    # Text props
    size: Var[MantineNumberSize] = None
    variant: Var[Literal["text", "gradient"]] = None
    gradient: Var[dict] = None
    truncate: Var[Literal["end", "start"] | bool] = None
    line_clamp: Var[int] = None
    inline: Var[bool] = None
    inherit: Var[bool] = None
    span: Var[bool] = None

    _rename_props = {
        "line_clamp": "lineClamp",
    }


class Title(MantineLayoutComponentBase):
    """Mantine Title component.

    h1-h6 headings.
    https://mantine.dev/core/title/
    """

    tag = "Title"

    # Title props
    order: Var[int] = None
    size: Var[MantineNumberSize] = None
    text_wrap: Var[Literal["wrap", "nowrap", "balance", "pretty", "stable"]] = None
    line_clamp: Var[int] = None

    _rename_props = {
        "text_wrap": "textWrap",
        "line_clamp": "lineClamp",
    }


class Code(MantineLayoutComponentBase):
    """Mantine Code component.

    Inline and block code.
    https://mantine.dev/core/code/
    """

    tag = "Code"

    # Code props
    block: Var[bool] = None
    """If set, code is rendered in pre element."""

    color: Var[str] = None
    """Key of theme.colors or any valid CSS color, controls background-color."""


class TypographyStylesProvider(MantineLayoutComponentBase):
    """Mantine TypographyStylesProvider component.

    Apply Mantine typography styles to HTML content.
    https://mantine.dev/core/typography/
    """

    tag = "TypographyStylesProvider"

    # No specific props, just renders children with Mantine styles
    # Inherits layout and system props


class List(MantineLayoutComponentBase):
    """Mantine List component.

    Display ordered or unordered lists with customizable styling.
    https://mantine.dev/core/list/
    """

    tag = "List"

    # List props
    type: Var[Literal["ordered", "unordered"]] = None
    size: Var[MantineNumberSize] = None
    spacing: Var[MantineNumberSize] = None
    center: Var[bool] = None
    icon: Var[any] = None
    list_style_type: Var[str] = None
    with_padding: Var[bool] = None

    _rename_props = {
        "list_style_type": "listStyleType",
        "with_padding": "withPadding",
    }


class ListItem(MantineLayoutComponentBase):
    """Mantine List.Item component.

    Item within a List component.
    https://mantine.dev/core/list/
    """

    tag = "List.Item"

    # List.Item props
    icon: Var[any] = None


# ============================================================================
# List Namespace
# ============================================================================


class ListNamespace(rx.ComponentNamespace):
    """Namespace for List components.

    Provides convenient access to List and ListItem components.

    Usage:
        ```python
        import appkit_mantine as mn

        # Using namespace
        mn.list(
            mn.list.item("First item"),
            mn.list.item("Second item"),
            type="ordered",
        )

        # Or using direct imports
        mn.list_item("Item")
        ```
    """

    __call__ = staticmethod(List.create)
    item = staticmethod(ListItem.create)


list_ = ListNamespace()  # noqa: A001
code = Code.create
text = Text.create
title = Title.create
typography_styles_provider = TypographyStylesProvider.create
