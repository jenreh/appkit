from __future__ import annotations

from typing import Literal

import reflex as rx
from reflex.constants.colors import Color
from reflex.vars.base import Var

from appkit_mantine.base import MantineComponentBase


class Table(MantineComponentBase):
    """Mantine Table wrapper for Reflex.

    Mirrors Mantine's Table props where sensible. Avoids re-declaring props
    provided by the base classes.
    """

    tag = "Table"

    # Visual helpers

    border_color: Var[str | Color | None] = None
    caption_side: Var[Literal["top", "bottom"]] = "bottom"
    data: Var[dict | None] = None
    highlight_on_hover: Var[bool] = True
    highlight_on_hover_color: Var[str | Color | None] = None
    horizontal_spacing: Var[Literal["xs", "sm", "md", "lg", "xl"]] = "xs"
    layout: Var[str] = "auto"
    sticky_header_offset: Var[int | str] = 0
    sticky_header: Var[bool] = False
    striped: Var[bool] = False
    striped_color: Var[str | Color | None] = None
    tabular_nums: Var[bool] = False
    vertical_spacing: Var[Literal["xs", "sm", "md", "lg", "xl"]] = "xs"
    with_column_borders: Var[bool] = False
    with_row_borders: Var[bool] = True
    with_table_border: Var[bool] = False


class Thead(MantineComponentBase):
    """Table.Thead sub-component."""

    tag = "Table.Thead"


class Tbody(MantineComponentBase):
    """Table.Tbody sub-component."""

    tag = "Table.Tbody"


class Tfoot(MantineComponentBase):
    """Table.Tfoot sub-component."""

    tag = "Table.Tfoot"


class Tr(MantineComponentBase):
    """Table.Tr sub-component."""

    tag = "Table.Tr"


class Th(MantineComponentBase):
    """Table.Th sub-component."""

    tag = "Table.Th"


class Td(MantineComponentBase):
    """Table.Td sub-component."""

    tag = "Table.Td"


class Caption(MantineComponentBase):
    """Table.Caption sub-component."""

    tag = "Table.Caption"


class ScrollContainer(MantineComponentBase):
    """Table.ScrollContainer helper component.

    Mirrors Mantine's Table.ScrollContainer which wraps the table in a scroll area.
    """

    tag = "Table.ScrollContainer"


class TableNamespace(rx.ComponentNamespace):
    """Namespace for Table and its subcomponents."""

    __call__ = staticmethod(Table.create)
    thead = staticmethod(Thead.create)
    tbody = staticmethod(Tbody.create)
    tfoot = staticmethod(Tfoot.create)
    tr = staticmethod(Tr.create)
    th = staticmethod(Th.create)
    td = staticmethod(Td.create)
    caption = staticmethod(Caption.create)
    scroll_container = staticmethod(ScrollContainer.create)


table = TableNamespace()
