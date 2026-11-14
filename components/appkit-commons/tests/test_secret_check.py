"""Tests for collecting secret: references from YAML configuration."""

from pathlib import Path
from typing import Any

import yaml

from appkit_commons.cli.secret_check import (
    collect_secret_names,
    parse_profiles,
    required_secret_names,
)


def write(directory: Path, file: str, data: dict[str, Any]) -> None:
    (directory / file).write_text(yaml.safe_dump(data), encoding="utf-8")


class TestCollectSecretNames:
    def test_nested_dicts_and_lists(self) -> None:
        data = {
            "app": {
                "database": {"user": "secret:db-user", "port": 5432},
                "providers": [
                    {"client_id": "secret:gh-id"},
                    "secret:in-list",
                    "plain",
                ],
            }
        }

        assert collect_secret_names(data) == {"db-user", "gh-id", "in-list"}

    def test_empty_name_uses_key(self) -> None:
        assert collect_secret_names({"api_key": "secret:"}) == {"api_key"}

    def test_empty_name_in_list_uses_parent_key(self) -> None:
        assert collect_secret_names({"keys": ["secret:", "secret:x"]}) == {
            "keys",
            "x",
        }

    def test_prefix_is_case_insensitive(self) -> None:
        assert collect_secret_names({"a": "SECRET:Mixed-Case"}) == {"Mixed-Case"}

    def test_top_level_value_without_key_is_ignored(self) -> None:
        assert collect_secret_names("secret:") == set()
        assert collect_secret_names(None) == set()


class TestParseProfiles:
    def test_parse(self) -> None:
        assert parse_profiles(" local, prod ,,") == ["local", "prod"]
        assert parse_profiles(None) == []
        assert parse_profiles("") == []


class TestRequiredSecretNames:
    def test_merged_profiles_replace_values(self, tmp_path: Path) -> None:
        write(tmp_path, "config.yaml", {"db": {"host": "secret:base-host"}})
        write(tmp_path, "config.prod.yaml", {"db": {"host": "secret:prod-host"}})

        assert required_secret_names(tmp_path, []) == {"base-host"}
        assert required_secret_names(tmp_path, ["prod"]) == {"prod-host"}

    def test_all_profiles_scans_every_config_file(self, tmp_path: Path) -> None:
        write(tmp_path, "config.yaml", {"db": {"host": "secret:base-host"}})
        write(tmp_path, "config.prod.yaml", {"db": {"host": "secret:prod-host"}})
        write(tmp_path, "config.local.yaml", {"key": "secret:local-key"})
        write(tmp_path, "logging.yaml", {"x": "secret:not-a-config"})

        names = required_secret_names(tmp_path, [], all_profiles=True)

        assert names == {"base-host", "prod-host", "local-key"}

    def test_missing_directory_finds_nothing(self, tmp_path: Path) -> None:
        assert required_secret_names(tmp_path / "missing", ["local"]) == set()
