"""Mantine Tree wrapper for Reflex."""

from __future__ import annotations

from typing import Any

from reflex import asset
from reflex.vars.base import Var

from appkit_mantine.base import MantineComponentBase

_TREE_WRAPPER = asset(path="tree_advanced.jsx", shared=True)
_TREE_WRAPPER_IMPORT = f"$/public/{_TREE_WRAPPER}"


class Tree(MantineComponentBase):
    """Mantine Tree wrapper for Reflex."""

    tag = "EnhancedTree"
    library = _TREE_WRAPPER_IMPORT
    lib_dependencies: list[str] = ["lucide-react"]

    # Properties
    allow_drop: Var[bool] = None
    allow_range_selection: Var[bool] = None
    check_on_space: Var[bool] = None
    clear_selection_on_outside_click: Var[bool] = None
    data: Var[list[dict]] = None
    expand_on_click: Var[bool] = None
    expand_on_space: Var[bool] = None
    keep_mounted: Var[bool] = None
    level_offset: Var[int | str] = None
    multiple: Var[bool] = None
    render_node: Var[Any] = None
    select_on_click: Var[bool] = None
    tree: Var[str] = None
    value: Var[str] = None
    with_drag_handle: Var[bool] = None
    with_lines: Var[bool] = None

    # Enhanced wrapper properties
    search: Var[str] = None
    with_checkbox: Var[bool] = None
    with_custom_node: Var[bool] = None


tree = Tree.create
