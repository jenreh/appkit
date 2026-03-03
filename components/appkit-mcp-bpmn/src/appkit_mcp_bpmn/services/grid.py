"""Grid data structure for BPMN auto-layout.

Ported from bpmn-io/bpmn-auto-layout (MIT License).
"""

from __future__ import annotations

from typing import Any


class Grid:
    """2D grid for positioning BPMN elements during layout.

    Each cell can hold a single element (or ``None``).  Elements are
    placed during the depth-first traversal and the grid is later used
    to compute pixel coordinates.
    """

    def __init__(self) -> None:
        self._grid: list[list[Any]] = []

    # -- Mutation --------------------------------------------------------

    def add(
        self,
        element: Any,
        position: tuple[int, int] | None = None,
    ) -> None:
        """Add *element* at ``(row, col)`` or on a new row at column 0."""
        if position is None:
            self._add_start(element)
            return

        row, col = position
        if row == 0 and col == 0:
            self._add_start(element)
            return

        while len(self._grid) <= row:
            self._grid.append([])
        while len(self._grid[row]) <= col:
            self._grid[row].append(None)

        if self._grid[row][col] is not None:
            raise ValueError("Grid position is already occupied")

        self._grid[row][col] = element

    def _add_start(self, element: Any) -> None:
        self._grid.append([element])

    def add_after(self, element: Any, new_element: Any) -> None:
        """Insert *new_element* immediately after *element* in the same row."""
        if element is None:
            self._add_start(new_element)
            return
        row, col = self.find(element)
        self._grid[row].insert(col + 1, new_element)

    def add_below(self, element: Any, new_element: Any) -> None:
        """Place *new_element* below *element* in the grid."""
        if element is None:
            self._add_start(new_element)
            return

        row, col = self.find(element)
        target_row = row + 1

        if target_row >= len(self._grid):
            self._grid.append([])

        # Ensure column exists in target row
        while len(self._grid[target_row]) <= col:
            self._grid[target_row].append(None)

        # If occupied, insert a fresh row
        if self._grid[target_row][col] is not None:
            self._grid.insert(target_row, [])
            while len(self._grid[target_row]) <= col:
                self._grid[target_row].append(None)

        self._grid[target_row][col] = new_element

    def create_row(self, after_index: int | None = None) -> None:
        """Insert an empty row after *after_index*, or append one."""
        if after_index is None:
            self._grid.append([])
        else:
            self._grid.insert(after_index + 1, [])

    def create_col(self, after_index: int, col_count: int = 1) -> None:
        """Insert *col_count* empty columns after *after_index* in every row."""
        for row_idx in range(len(self._grid)):
            self._expand_row(row_idx, after_index, col_count)

    # -- Querying --------------------------------------------------------

    def find(self, element: Any) -> tuple[int, int]:
        """Return ``(row, col)`` of *element*."""
        for row_idx, row in enumerate(self._grid):
            for col_idx, el in enumerate(row):
                if el is element:
                    return (row_idx, col_idx)
        raise ValueError("Element not found in grid")

    def get(self, row: int, col: int) -> Any:
        """Return element at ``(row, col)`` or ``None``."""
        if 0 <= row < len(self._grid):
            grid_row = self._grid[row]
            if 0 <= col < len(grid_row):
                return grid_row[col]
        return None

    def get_elements_in_range(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
    ) -> list[Any]:
        """Return all elements inside the rectangular *start*-*end* range."""
        sr, sc = start
        er, ec = end
        if sr > er:
            sr, er = er, sr
        if sc > ec:
            sc, ec = ec, sc

        elements: list[Any] = []
        for r in range(sr, er + 1):
            for c in range(sc, ec + 1):
                el = self.get(r, c)
                if el is not None:
                    elements.append(el)
        return elements

    def get_all_elements(self) -> list[Any]:
        """Return a flat list of all non-``None`` elements."""
        return [el for row in self._grid for el in row if el is not None]

    def get_grid_dimensions(self) -> tuple[int, int]:
        """Return ``(num_rows, max_cols)``."""
        num_rows = len(self._grid)
        max_cols = max((len(r) for r in self._grid), default=0)
        return (num_rows, max_cols)

    def elements_by_position(
        self,
    ) -> list[dict[str, Any]]:
        """Return ``[{element, row, col}, ...]`` for every occupied cell."""
        result: list[dict[str, Any]] = []
        for row_idx, row in enumerate(self._grid):
            for col_idx, el in enumerate(row):
                if el is not None:
                    result.append({"element": el, "row": row_idx, "col": col_idx})
        return result

    def get_elements_total(self) -> int:
        """Count unique elements (by identity)."""
        seen: set[int] = set()
        for row in self._grid:
            for el in row:
                if el is not None:
                    seen.add(id(el))
        return len(seen)

    # -- Adjustment helpers ----------------------------------------------

    def adjust_grid_position(self, element: Any) -> None:
        """Move *element* to the last column of its row."""
        row, col = self.find(element)
        _, max_col = self.get_grid_dimensions()

        if col < max_col - 1:
            while len(self._grid[row]) <= max_col:
                self._grid[row].append(None)
            self._grid[row][max_col] = element
            self._grid[row][col] = None

    def adjust_row_for_multiple_incoming(
        self,
        elements: list[Any],
        current_element: Any,
    ) -> None:
        """Move *current_element* to the lowest row occupied by *elements*."""
        positions = [self.find(el) for el in elements]
        lowest_row = min(r for r, _ in positions if r >= 0)

        row, col = self.find(current_element)
        if lowest_row < row and self.get(lowest_row, col) is None:
            while len(self._grid[lowest_row]) <= col:
                self._grid[lowest_row].append(None)
            self._grid[lowest_row][col] = current_element
            self._grid[row][col] = None

    def adjust_column_for_multiple_incoming(
        self,
        elements: list[Any],
        current_element: Any,
    ) -> None:
        """Move *current_element* to the column after the rightmost source."""
        positions = [self.find(el) for el in elements]
        max_col = max(c for _, c in positions if c >= 0)

        row, col = self.find(current_element)
        if max_col + 1 > col:
            while len(self._grid[row]) <= max_col + 1:
                self._grid[row].append(None)
            self._grid[row][max_col + 1] = current_element
            self._grid[row][col] = None

    # -- Internal --------------------------------------------------------

    def _expand_row(
        self,
        row_index: int,
        after_index: int,
        col_count: int = 1,
    ) -> None:
        if row_index < 0 or row_index >= len(self._grid):
            return
        count = max(1, col_count) if col_count else 1
        row = self._grid[row_index]
        insert_at = (after_index + 1) if after_index is not None else len(row)
        for i in range(count):
            row.insert(insert_at + i, None)

    @property
    def row_count(self) -> int:
        """Number of rows."""
        return len(self._grid)
