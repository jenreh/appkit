"""Mantine Tree wrapper for Reflex."""

from __future__ import annotations

from typing import Any

from reflex import asset
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MantineComponentBase

_TREE_WRAPPER = asset(path="tree_advanced.jsx", shared=True)
# importable_path omits the ?v= content hash, which Vite would treat as an
# optimized-dep URL and cache immutably, pinning a stale React instance.
_TREE_WRAPPER_IMPORT = _TREE_WRAPPER.importable_path


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

    # Controller (useTree) options handled by the wrapper
    initial_selected_state: Var[list[str]] = None
    initial_checked_state: Var[list[str]] = None
    initial_expanded_state: Var[dict[str, bool]] = None
    check_strictly: Var[bool] = None

    # Enhanced wrapper properties
    search: Var[str] = None
    with_checkbox: Var[bool] = None
    with_custom_node: Var[bool] = None

    on_select: EventHandler[lambda values: [values]] = None
    """Called with the selected node values (``list[str]``)."""

    on_check: EventHandler[lambda values: [values]] = None
    """Called with the checked node values (``list[str]``)."""

    on_expand: EventHandler[lambda value: [value]] = None
    """Called with the value of the expanded node."""

    on_collapse: EventHandler[lambda value: [value]] = None
    """Called with the value of the collapsed node."""


tree = Tree.create
