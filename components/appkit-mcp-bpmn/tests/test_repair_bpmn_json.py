"""Tests for BPMN JSON repair service (flat model)."""

from appkit_mcp_bpmn.services.repair_bpmn_json import (
    _ensure_step_keys,
    _repair_branches,
    repair_bpmn_json,
)


class TestEnsureStepKeys:
    """Tests for _ensure_step_keys."""

    def test_fills_missing_keys(self) -> None:
        step: dict = {"type": "task"}
        result = _ensure_step_keys(step)
        assert "id" in result
        assert result["type"] == "task"
        assert result["label"] == result["id"]  # label defaults to id
        assert result["branches"] is None
        assert result["next"] is None

    def test_preserves_existing_keys(self) -> None:
        step: dict = {
            "id": "my_task",
            "type": "userTask",
            "label": "Review",
            "branches": None,
            "next": None,
        }
        result = _ensure_step_keys(step)
        assert result["id"] == "my_task"
        assert result["label"] == "Review"

    def test_generates_unique_ids(self) -> None:
        s1 = _ensure_step_keys({"type": "task"})
        s2 = _ensure_step_keys({"type": "task"})
        assert s1["id"] != s2["id"]


class TestRepairBranches:
    """Tests for _repair_branches."""

    def test_none_returns_none(self) -> None:
        assert _repair_branches(None) is None

    def test_empty_list_returns_none(self) -> None:
        assert _repair_branches([]) is None

    def test_normalises_branch_shape(self) -> None:
        branches = [
            {"condition": "Yes", "target": "task_a"},
            {"condition": "No", "target": "task_b"},
        ]
        result = _repair_branches(branches)
        assert result == branches

    def test_maps_target_ref_to_target(self) -> None:
        branches = [{"condition": "OK", "target_ref": "task_x"}]
        result = _repair_branches(branches)
        assert result is not None
        assert result[0]["target"] == "task_x"

    def test_skips_non_dict_entries(self) -> None:
        branches = [{"condition": "A", "target": "t"}, "garbage"]
        result = _repair_branches(branches)
        assert result is not None
        assert len(result) == 1

    def test_not_list_returns_none(self) -> None:
        assert _repair_branches("not a list") is None


class TestRepairBpmnJson:
    """Tests for repair_bpmn_json."""

    def test_non_dict_returns_unchanged(self) -> None:
        assert repair_bpmn_json("not a dict") == "not a dict"

    def test_missing_steps_returns_unchanged(self) -> None:
        raw: dict = {"name": "test"}
        assert repair_bpmn_json(raw) == raw

    def test_process_key_aliased_to_steps(self) -> None:
        raw: dict = {
            "process": [
                {"id": "start", "type": "startEvent"},
                {"id": "end", "type": "endEvent"},
            ]
        }
        result = repair_bpmn_json(raw)
        assert "steps" in result
        assert "process" not in result
        assert len(result["steps"]) == 2

    def test_missing_step_keys_filled(self) -> None:
        raw: dict = {
            "steps": [{"type": "task"}],
            "lanes": None,
        }
        result = repair_bpmn_json(raw)
        step = result["steps"][0]
        assert "id" in step
        assert step["branches"] is None
        assert step["next"] is None

    def test_lanes_defaulted_to_none(self) -> None:
        raw: dict = {"steps": [{"id": "s", "type": "startEvent"}]}
        result = repair_bpmn_json(raw)
        assert result["lanes"] is None

    def test_unknown_top_level_keys_stripped(self) -> None:
        raw: dict = {
            "steps": [{"id": "s", "type": "startEvent"}],
            "lanes": None,
            "extra_key": "should be removed",
        }
        result = repair_bpmn_json(raw)
        assert "extra_key" not in result

    def test_branches_normalised(self) -> None:
        raw: dict = {
            "steps": [
                {
                    "id": "gw",
                    "type": "exclusive",
                    "branches": [
                        {
                            "condition": "Yes",
                            "target_ref": "task_a",
                        },
                    ],
                },
            ],
            "lanes": None,
        }
        result = repair_bpmn_json(raw)
        br = result["steps"][0]["branches"]
        assert br is not None
        assert br[0]["target"] == "task_a"
