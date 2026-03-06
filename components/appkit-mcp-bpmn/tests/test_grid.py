"""Tests for Grid data structure."""

import pytest

from appkit_mcp_bpmn.services.grid import Grid


class TestGridAdd:
    """Tests for Grid.add."""

    def test_add_no_position(self) -> None:
        g = Grid()
        g.add("A")
        assert g.get(0, 0) == "A"

    def test_add_with_position(self) -> None:
        g = Grid()
        g.add("A")
        g.add("B", (0, 1))
        assert g.get(0, 1) == "B"

    def test_add_expands_grid(self) -> None:
        g = Grid()
        g.add("A", (3, 5))
        assert g.get(3, 5) == "A"
        assert g.get(2, 0) is None

    def test_add_occupied_raises(self) -> None:
        g = Grid()
        g.add("A")
        g.add("B", (0, 1))
        with pytest.raises(ValueError, match="occupied"):
            g.add("C", (0, 1))

    def test_add_zero_zero_appends_row(self) -> None:
        g = Grid()
        g.add("A", (0, 0))
        g.add("B", (0, 0))
        # Both go on new rows via _add_start
        assert g.get(0, 0) == "A"
        assert g.get(1, 0) == "B"


class TestGridAddAfter:
    """Tests for Grid.add_after."""

    def test_insert_after(self) -> None:
        g = Grid()
        g.add("A")
        g.add_after("A", "B")
        assert g.get(0, 0) == "A"
        assert g.get(0, 1) == "B"

    def test_insert_after_none(self) -> None:
        g = Grid()
        g.add_after(None, "X")
        assert g.get(0, 0) == "X"


class TestGridAddBelow:
    """Tests for Grid.add_below."""

    def test_add_below_basic(self) -> None:
        g = Grid()
        g.add("A")
        g.add_below("A", "B")
        assert g.get(1, 0) == "B"

    def test_add_below_none(self) -> None:
        g = Grid()
        g.add_below(None, "X")
        assert g.get(0, 0) == "X"

    def test_add_below_occupied_inserts_row(self) -> None:
        g = Grid()
        g.add("A")
        g.add("C")  # row 1, col 0
        g.add_below("A", "B")
        assert g.get(1, 0) == "B"
        # C pushed to row 2
        assert g.get(2, 0) == "C"


class TestGridCreateRowCol:
    """Tests for create_row and create_col."""

    def test_create_row_append(self) -> None:
        g = Grid()
        g.add("A")
        g.create_row()
        rows, _ = g.get_grid_dimensions()
        assert rows == 2

    def test_create_row_after_index(self) -> None:
        g = Grid()
        g.add("A")
        g.add("B")
        g.create_row(after_index=0)
        assert g.get(0, 0) == "A"
        assert g.get(1, 0) is None
        assert g.get(2, 0) == "B"

    def test_create_col(self) -> None:
        g = Grid()
        g.add("A")
        g.add_after("A", "B")
        g.create_col(after_index=0, col_count=1)
        # A at (0,0), None inserted at (0,1), B now at (0,2)
        assert g.get(0, 0) == "A"
        assert g.get(0, 1) is None
        assert g.get(0, 2) == "B"


class TestGridFind:
    """Tests for Grid.find."""

    def test_find_existing(self) -> None:
        g = Grid()
        g.add("A")
        g.add_after("A", "B")
        assert g.find("B") == (0, 1)

    def test_find_missing_raises(self) -> None:
        g = Grid()
        g.add("A")
        with pytest.raises(ValueError, match="not found"):
            g.find("MISSING")


class TestGridGet:
    """Tests for Grid.get."""

    def test_get_out_of_bounds(self) -> None:
        g = Grid()
        assert g.get(99, 99) is None

    def test_get_negative(self) -> None:
        g = Grid()
        assert g.get(-1, 0) is None


class TestGridQueries:
    """Tests for query methods."""

    def _populated_grid(self) -> Grid:
        g = Grid()
        g.add("A")
        g.add_after("A", "B")
        g.add("C")
        return g

    def test_get_all_elements(self) -> None:
        g = self._populated_grid()
        assert set(g.get_all_elements()) == {"A", "B", "C"}

    def test_get_grid_dimensions(self) -> None:
        g = self._populated_grid()
        rows, cols = g.get_grid_dimensions()
        assert rows == 2
        assert cols == 2

    def test_elements_by_position(self) -> None:
        g = self._populated_grid()
        pos = g.elements_by_position()
        assert len(pos) == 3
        lookup = {p["element"]: (p["row"], p["col"]) for p in pos}
        assert lookup["A"] == (0, 0)
        assert lookup["B"] == (0, 1)
        assert lookup["C"] == (1, 0)

    def test_get_elements_total(self) -> None:
        g = self._populated_grid()
        assert g.get_elements_total() == 3

    def test_get_elements_in_range(self) -> None:
        g = self._populated_grid()
        elems = g.get_elements_in_range((0, 0), (0, 1))
        assert set(elems) == {"A", "B"}

    def test_get_elements_in_range_reversed(self) -> None:
        g = self._populated_grid()
        elems = g.get_elements_in_range((0, 1), (0, 0))
        assert set(elems) == {"A", "B"}

    def test_empty_grid_dimensions(self) -> None:
        g = Grid()
        assert g.get_grid_dimensions() == (0, 0)


class TestGridAdjust:
    """Tests for adjustment helpers."""

    def test_adjust_grid_position(self) -> None:
        g = Grid()
        g.add("A")
        g.add_after("A", "B")
        g.add_after("B", "X")  # 3 cols
        g.add("C")
        g.adjust_grid_position("C")
        # max_col = 3 (len of longest row), C placed at index 3
        assert g.get(1, 0) is None
        assert g.get(1, 3) == "C"

    def test_adjust_row_multiple_incoming(self) -> None:
        g = Grid()
        g.add("A")  # row 0, col 0
        g.add_after("A", "B")  # row 0, col 1
        g.add("C")  # row 1, col 0
        g.add("D", (2, 1))  # row 2, col 1
        # Move D to lowest row (0) if col 1 is free at that row
        # But B is at (0,1) so it won't move
        # Use elements at different rows: A(0,0), C(1,0)
        g2 = Grid()
        g2.add("X")  # row 0, col 0
        g2.add("Y")  # row 1, col 0
        g2.add("Z", (2, 1))  # row 2, col 1
        g2.adjust_row_for_multiple_incoming(["X", "Y"], "Z")
        # Lowest row = 0; col 1 at row 0 is None → Z moves
        assert g2.get(0, 1) == "Z"

    def test_adjust_column_multiple_incoming(self) -> None:
        g = Grid()
        g.add("A")
        g.add_after("A", "B")
        g.add("C")
        g.adjust_column_for_multiple_incoming(["A", "B"], "C")
        # C moves to col after rightmost (B at col 1) → col 2
        assert g.find("C")[1] == 2

    def test_from_positions_empty(self) -> None:
        g = Grid.from_positions([])
        assert g.get_elements_total() == 0

    def test_from_positions_basic(self) -> None:
        g = Grid.from_positions([("A", 0, 0), ("B", 0, 1), ("C", 1, 0)])
        assert g.get(0, 0) == "A"
        assert g.get(0, 1) == "B"
        assert g.get(1, 0) == "C"
        assert g.get_elements_total() == 3

    def test_from_positions_sparse(self) -> None:
        g = Grid.from_positions([("X", 0, 2), ("Y", 2, 0)])
        assert g.get(0, 2) == "X"
        assert g.get(2, 0) == "Y"
        assert g.get(0, 0) is None
        assert g.get(1, 1) is None
        assert g.get_grid_dimensions() == (3, 3)
