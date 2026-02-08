"""Mantine layout components."""

from typing import Literal

from reflex.vars.base import Var

from appkit_mantine.base import MantineComponentBase


class MantineLayoutComponentBase(MantineComponentBase):
    """Base class for layout components with common style props."""

    # Width and Height
    w: Var[str | int]
    h: Var[str | int]
    miw: Var[str | int]
    maw: Var[str | int]
    mih: Var[str | int]
    mah: Var[str | int]

    # Margins
    m: Var[str | int]
    my: Var[str | int]
    mx: Var[str | int]
    mt: Var[str | int]
    mb: Var[str | int]
    ml: Var[str | int]
    mr: Var[str | int]

    # Paddings
    p: Var[str | int]
    py: Var[str | int]
    px: Var[str | int]
    pt: Var[str | int]
    pb: Var[str | int]
    pl: Var[str | int]
    pr: Var[str | int]

    # Display and Position
    display: Var[str]
    pos: Var[str]
    top: Var[str | int]
    left: Var[str | int]
    bottom: Var[str | int]
    right: Var[str | int]
    inset: Var[str | int]

    # Background and Color
    bg: Var[str]
    c: Var[str]
    opacity: Var[str | int]


class Center(MantineLayoutComponentBase):
    """Mantine Center component."""

    tag = "Center"

    inline: Var[bool]


class Container(MantineLayoutComponentBase):
    """Mantine Container component."""

    tag = "Container"

    fluid: Var[bool]
    size: Var[str | int]


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


center = Center.create
container = Container.create
flex = Flex.create
group = Group.create
stack = Stack.create
simple_grid = SimpleGrid.create
grid = Grid.create
grid_col = GridCol.create
space = Space.create
