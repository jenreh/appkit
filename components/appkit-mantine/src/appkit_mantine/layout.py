"""Mantine layout components."""

from typing import Literal

from reflex.vars.base import Var

from appkit_mantine.base import (
    MantineComponentBase,
    MantineLayoutComponentBase,
    MantineSize,
)


class Box(MantineLayoutComponentBase):
    """Mantine Box component."""

    tag = "Box"

    component: Var[str]


class Center(MantineLayoutComponentBase):
    """Mantine Center component."""

    tag = "Center"

    inline: Var[bool]


class Container(MantineLayoutComponentBase):
    """Mantine Container component."""

    tag = "Container"

    fluid: Var[bool]
    size: Var[MantineSize | str]


class Flex(MantineLayoutComponentBase):
    """Mantine Flex component."""

    tag = "Flex"

    gap: Var[str | int | dict]
    row_gap: Var[str | int | dict]
    column_gap: Var[str | int | dict]
    align: Var[str | dict]
    justify: Var[str | dict]
    wrap: Var[str | dict]
    direction: Var[str | dict]


class Group(MantineLayoutComponentBase):
    """Mantine Group component."""

    tag = "Group"

    justify: Var[str]
    align: Var[str]
    gap: Var[str | int]
    grow: Var[bool]
    prevent_grow_overflow: Var[bool]
    wrap: Var[str]


class Stack(MantineLayoutComponentBase):
    """Mantine Stack component."""

    tag = "Stack"

    align: Var[str]
    justify: Var[str]
    gap: Var[str | int]


class SimpleGrid(MantineLayoutComponentBase):
    """Mantine SimpleGrid component."""

    tag = "SimpleGrid"

    cols: Var[int | dict]
    spacing: Var[str | int | dict]
    vertical_spacing: Var[str | int | dict]
    type: Var[Literal["container", "media"]]


class Grid(MantineLayoutComponentBase):
    """Mantine Grid component."""

    tag = "Grid"

    columns: Var[int]
    gutter: Var[str | int | dict]
    grow: Var[bool]
    justify: Var[str]
    align: Var[str]
    overflow: Var[str]


class GridCol(MantineLayoutComponentBase):
    """Mantine Grid.Col component."""

    tag = "Grid.Col"

    span: Var[int | str | dict]
    offset: Var[int | dict]
    order: Var[int | dict]


class Space(MantineLayoutComponentBase):
    """Mantine Space component."""

    tag = "Space"


class Divider(MantineLayoutComponentBase):
    """Mantine Divider component."""

    tag = "Divider"

    color: Var[str]
    label: Var[str]
    label_position: Var[Literal["left", "center", "right"]]
    orientation: Var[Literal["horizontal", "vertical"]]
    size: Var[str | int]
    variant: Var[Literal["solid", "dashed", "dotted"]]


class Affix(MantineLayoutComponentBase):
    """Mantine Affix component."""

    tag = "Affix"

    position: Var[dict]
    within_portal: Var[bool]
    z_index: Var[int | str]


class FocusTrap(MantineComponentBase):
    """Mantine FocusTrap component."""

    tag = "FocusTrap"

    active: Var[bool]
    ref_prop: Var[str]


box = Box.create
center = Center.create
container = Container.create
flex = Flex.create
group = Group.create
stack = Stack.create
simple_grid = SimpleGrid.create
grid = Grid.create
grid_col = GridCol.create
space = Space.create
divider = Divider.create
affix = Affix.create
focus_trap = FocusTrap.create
