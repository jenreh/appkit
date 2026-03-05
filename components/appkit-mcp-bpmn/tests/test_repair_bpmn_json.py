"""Tests for BPMN JSON repair service."""

from appkit_mcp_bpmn.services.repair_bpmn_json import (
    _collect_ids_from_raw_process,
    _mk_noop_task,
    repair_bpmn_json,
)


class TestMkNoopTask:
    """Tests for _mk_noop_task."""

    def test_creates_task_with_unique_id(self) -> None:
        ids: set[str] = set()
        task = _mk_noop_task(ids)
        assert task["type"] == "task"
        assert task["id"].startswith("Task_NoOp_")
        assert task["label"] == "Continue"
        assert task["has_join"] is False

    def test_avoids_collisions(self) -> None:
        ids: set[str] = set()
        t1 = _mk_noop_task(ids)
        t2 = _mk_noop_task(ids)
        assert t1["id"] != t2["id"]
        assert t1["id"] in ids
        assert t2["id"] in ids

    def test_custom_prefix(self) -> None:
        ids: set[str] = set()
        task = _mk_noop_task(ids, prefix="Custom")
        assert task["id"].startswith("Custom_")


class TestCollectIds:
    """Tests for _collect_ids_from_raw_process."""

    def test_flat_process(self) -> None:
        process = [
            {"id": "Start_1", "type": "startEvent"},
            {"id": "Task_1", "type": "task"},
        ]
        ids = _collect_ids_from_raw_process(process)
        assert ids == {"Start_1", "Task_1"}

    def test_nested_branches(self) -> None:
        process = [
            {
                "id": "GW_1",
                "type": "exclusiveGateway",
                "branches": [
                    {
                        "condition": "yes",
                        "path": [
                            {"id": "Task_A", "type": "task"},
                        ],
                    },
                    {
                        "condition": "no",
                        "path": [
                            {"id": "Task_B", "type": "task"},
                        ],
                    },
                ],
            },
        ]
        ids = _collect_ids_from_raw_process(process)
        assert "GW_1" in ids
        assert "Task_A" in ids
        assert "Task_B" in ids

    def test_missing_id_skipped(self) -> None:
        process = [{"type": "task"}]
        ids = _collect_ids_from_raw_process(process)
        assert len(ids) == 0

    def test_empty_process(self) -> None:
        assert _collect_ids_from_raw_process([]) == set()


class TestRepairBpmnJson:
    """Tests for repair_bpmn_json."""

    def test_non_dict_returns_unchanged(self) -> None:
        assert repair_bpmn_json("not a dict") == "not a dict"

    def test_missing_process_returns_unchanged(self) -> None:
        raw = {"name": "test"}
        assert repair_bpmn_json(raw) == raw

    def test_non_list_process_returns_unchanged(self) -> None:
        raw = {"process": "not a list"}
        assert repair_bpmn_json(raw) == raw

    def test_empty_branch_gets_noop(self) -> None:
        raw = {
            "process": [
                {
                    "id": "GW_1",
                    "type": "exclusiveGateway",
                    "branches": [
                        {"condition": "yes", "path": []},
                        {
                            "condition": "no",
                            "path": [
                                {"id": "T1", "type": "task"},
                            ],
                        },
                    ],
                },
            ],
        }
        result = repair_bpmn_json(raw)
        yes_branch = result["process"][0]["branches"][0]
        assert len(yes_branch["path"]) == 1
        assert yes_branch["path"][0]["type"] == "task"
        assert yes_branch["path"][0]["label"] == "Continue"

    def test_non_empty_branch_unchanged(self) -> None:
        raw = {
            "process": [
                {
                    "id": "GW_1",
                    "type": "exclusiveGateway",
                    "branches": [
                        {
                            "condition": "yes",
                            "path": [
                                {"id": "T1", "type": "task"},
                            ],
                        },
                    ],
                },
            ],
        }
        result = repair_bpmn_json(raw)
        assert len(result["process"][0]["branches"][0]["path"]) == 1
        assert result["process"][0]["branches"][0]["path"][0]["id"] == "T1"

    def test_null_path_gets_fixed(self) -> None:
        raw = {
            "process": [
                {
                    "id": "GW_1",
                    "type": "exclusiveGateway",
                    "branches": [
                        {"condition": "yes", "path": None},
                    ],
                },
            ],
        }
        result = repair_bpmn_json(raw)
        path = result["process"][0]["branches"][0]["path"]
        assert isinstance(path, list)
        assert len(path) == 1
        assert path[0]["type"] == "task"

    def test_nested_gateway_branches_repaired(self) -> None:
        raw = {
            "process": [
                {
                    "id": "GW_Outer",
                    "type": "exclusiveGateway",
                    "branches": [
                        {
                            "condition": "a",
                            "path": [
                                {
                                    "id": "GW_Inner",
                                    "type": "exclusiveGateway",
                                    "branches": [
                                        {
                                            "condition": "x",
                                            "path": [],
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
        }
        result = repair_bpmn_json(raw)
        inner_gw = result["process"][0]["branches"][0]["path"][0]
        assert len(inner_gw["branches"][0]["path"]) == 1

    def test_no_branches_element_unchanged(self) -> None:
        raw = {
            "process": [
                {
                    "id": "Task_1",
                    "type": "task",
                    "branches": None,
                },
            ],
        }
        result = repair_bpmn_json(raw)
        assert result["process"][0]["id"] == "Task_1"
