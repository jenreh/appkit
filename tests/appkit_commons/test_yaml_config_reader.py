"""Tests for YamlConfigReader and YamlConfigSettingsSource."""

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import Field
from pydantic_settings import BaseSettings

from appkit_commons.configuration.yaml import (
    YamlConfigReader,
    YamlConfigSettingsSource,
)


class TestYamlConfigReader:
    """Test suite for YamlConfigReader."""

    def test_read_file_success(self, tmp_path: Path) -> None:
        """Reading a valid YAML file returns parsed data."""
        # Arrange
        config_data = {"key": "value", "number": 42, "nested": {"item": "data"}}
        yaml_file = tmp_path / "config.yaml"
        with yaml_file.open("w") as f:
            yaml.dump(config_data, f)

        # Act
        result = YamlConfigReader.read_file(yaml_file)

        # Assert
        assert result == config_data

    def test_read_file_not_found_returns_empty_dict(self, tmp_path: Path) -> None:
        """Reading a non-existent file returns empty dict and logs warning."""
        # Arrange
        nonexistent = tmp_path / "missing.yaml"

        # Act
        result = YamlConfigReader.read_file(nonexistent)

        # Assert
        assert result == {}

    def test_read_file_empty_yaml_returns_empty_dict(self, tmp_path: Path) -> None:
        """Reading an empty YAML file returns empty dict."""
        # Arrange
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        # Act
        result = YamlConfigReader.read_file(yaml_file)

        # Assert
        assert result == {}

    def test_read_file_only_comments_returns_empty_dict(self, tmp_path: Path) -> None:
        """Reading a YAML file with only comments returns empty dict."""
        # Arrange
        yaml_file = tmp_path / "comments.yaml"
        yaml_file.write_text("# Just a comment\n# Another comment\n")

        # Act
        result = YamlConfigReader.read_file(yaml_file)

        # Assert
        assert result == {}

    def test_read_file_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Reading invalid YAML raises YAMLError."""
        # Arrange
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("key: value\n  invalid indentation\n")

        # Act & Assert
        with pytest.raises(yaml.YAMLError):
            YamlConfigReader.read_file(yaml_file)

    def test_read_and_merge_files_no_profiles(self, tmp_path: Path) -> None:
        """Reading without profiles returns base config only."""
        # Arrange
        base_config = {"env": "base", "value": 1}
        config_file = tmp_path / "config.yaml"
        with config_file.open("w") as f:
            yaml.dump(base_config, f)

        reader = YamlConfigReader(yaml_file_path=tmp_path)

        # Act
        result = reader.read_and_merge_files(profiles=None)

        # Assert
        assert result == base_config

    def test_read_and_merge_files_with_single_profile(self, tmp_path: Path) -> None:
        """Reading with a profile merges profile config into base config."""
        # Arrange
        base_config = {"env": "base", "shared": "base_value", "value": 1}
        profile_config = {"env": "dev", "value": 2, "dev_only": "dev_data"}

        config_file = tmp_path / "config.yaml"
        with config_file.open("w") as f:
            yaml.dump(base_config, f)

        dev_file = tmp_path / "config.dev.yaml"
        with dev_file.open("w") as f:
            yaml.dump(profile_config, f)

        reader = YamlConfigReader(yaml_file_path=tmp_path)

        # Act
        result = reader.read_and_merge_files(profiles=["dev"])

        # Assert
        assert result["env"] == "dev"
        assert result["shared"] == "base_value"
        assert result["value"] == 2
        assert result["dev_only"] == "dev_data"

    def test_read_and_merge_files_with_multiple_profiles(
        self, tmp_path: Path
    ) -> None:
        """Reading with multiple profiles merges in order."""
        # Arrange
        base_config = {"env": "base", "value": 1}
        dev_config = {"env": "dev", "value": 2, "dev_key": "dev"}
        prod_config = {"env": "prod", "value": 3, "prod_key": "prod"}

        config_file = tmp_path / "config.yaml"
        with config_file.open("w") as f:
            yaml.dump(base_config, f)

        dev_file = tmp_path / "config.dev.yaml"
        with dev_file.open("w") as f:
            yaml.dump(dev_config, f)

        prod_file = tmp_path / "config.prod.yaml"
        with prod_file.open("w") as f:
            yaml.dump(prod_config, f)

        reader = YamlConfigReader(yaml_file_path=tmp_path)

        # Act - prod should override dev
        result = reader.read_and_merge_files(profiles=["dev", "prod"])

        # Assert
        assert result["env"] == "prod"
        assert result["value"] == 3
        assert result["dev_key"] == "dev"
        assert result["prod_key"] == "prod"

    def test_read_and_merge_files_nested_merge(self, tmp_path: Path) -> None:
        """Nested dictionaries are deep merged, not replaced."""
        # Arrange
        base_config = {"database": {"host": "localhost", "port": 5432}}
        dev_config = {"database": {"host": "dev-db", "user": "dev_user"}}

        config_file = tmp_path / "config.yaml"
        with config_file.open("w") as f:
            yaml.dump(base_config, f)

        dev_file = tmp_path / "config.dev.yaml"
        with dev_file.open("w") as f:
            yaml.dump(dev_config, f)

        reader = YamlConfigReader(yaml_file_path=tmp_path)

        # Act
        result = reader.read_and_merge_files(profiles=["dev"])

        # Assert
        assert result["database"]["host"] == "dev-db"
        assert result["database"]["port"] == 5432  # Not overwritten
        assert result["database"]["user"] == "dev_user"

    def test_read_and_merge_files_missing_profile_ignored(
        self, tmp_path: Path
    ) -> None:
        """Missing profile file is ignored without error."""
        # Arrange
        base_config = {"env": "base"}
        config_file = tmp_path / "config.yaml"
        with config_file.open("w") as f:
            yaml.dump(base_config, f)

        reader = YamlConfigReader(yaml_file_path=tmp_path)

        # Act - nonexistent profile should be ignored
        result = reader.read_and_merge_files(profiles=["nonexistent"])

        # Assert
        assert result == base_config

    def test_merge_handles_none_master(self) -> None:
        """Merge handles None master dict."""
        # Arrange
        updates = {"key": "value"}

        # Act
        result = YamlConfigReader._YamlConfigReader__merge(None, updates)

        # Assert
        assert result == updates

    def test_merge_handles_none_updates(self) -> None:
        """Merge handles None updates dict."""
        # Arrange
        master = {"key": "value"}

        # Act
        result = YamlConfigReader._YamlConfigReader__merge(master, None)

        # Assert
        assert result == master

    def test_custom_yaml_file_name(self, tmp_path: Path) -> None:
        """YamlConfigReader works with custom file names."""
        # Arrange
        config_data = {"custom": "config"}
        custom_file = tmp_path / "my_config.yaml"
        with custom_file.open("w") as f:
            yaml.dump(config_data, f)

        reader = YamlConfigReader(
            yaml_file_path=tmp_path, yaml_file=Path("my_config.yaml")
        )

        # Act
        result = reader.read_and_merge_files(profiles=None)

        # Assert
        assert result == config_data


class TestYamlConfigSettingsSource:
    """Test suite for YamlConfigSettingsSource Pydantic integration."""

    def test_settings_source_loads_yaml(self, tmp_path: Path) -> None:
        """YamlConfigSettingsSource loads YAML into Pydantic settings."""

        # Arrange
        class TestSettings(BaseSettings):
            app_name: str = "default"
            port: int = 8000

        config_data = {"app_name": "test-app", "port": 9000}
        config_file = tmp_path / "config.yaml"
        with config_file.open("w") as f:
            yaml.dump(config_data, f)

        # Act
        source = YamlConfigSettingsSource(
            TestSettings, yaml_file_path=tmp_path, profiles=None
        )
        settings = TestSettings(_settings_source=source)

        # Assert
        assert settings.app_name == "test-app"
        assert settings.port == 9000

    def test_settings_source_filters_invalid_fields(self, tmp_path: Path) -> None:
        """YamlConfigSettingsSource filters out fields not in Pydantic model."""

        # Arrange
        class TestSettings(BaseSettings):
            valid_field: str = "default"

        config_data = {"valid_field": "value", "invalid_field": "ignored"}
        config_file = tmp_path / "config.yaml"
        with config_file.open("w") as f:
            yaml.dump(config_data, f)

        # Act
        source = YamlConfigSettingsSource(
            TestSettings, yaml_file_path=tmp_path, profiles=None
        )

        # Assert - yaml_data contains both, but init_kwargs only has valid field
        assert "valid_field" in source.yaml_data
        assert "invalid_field" in source.yaml_data
        assert source.init_kwargs == {"valid_field": "value"}

    def test_settings_source_with_profiles(self, tmp_path: Path) -> None:
        """YamlConfigSettingsSource merges profiles correctly."""

        # Arrange
        class TestSettings(BaseSettings):
            env: str = "base"
            value: int = 0

        base_config = {"env": "base", "value": 1}
        dev_config = {"env": "dev", "value": 2}

        config_file = tmp_path / "config.yaml"
        with config_file.open("w") as f:
            yaml.dump(base_config, f)

        dev_file = tmp_path / "config.dev.yaml"
        with dev_file.open("w") as f:
            yaml.dump(dev_config, f)

        # Act
        source = YamlConfigSettingsSource(
            TestSettings, yaml_file_path=tmp_path, profiles=["dev"]
        )
        settings = TestSettings(_settings_source=source)

        # Assert
        assert settings.env == "dev"
        assert settings.value == 2

    def test_settings_source_repr(self, tmp_path: Path) -> None:
        """YamlConfigSettingsSource has proper repr."""

        # Arrange
        class TestSettings(BaseSettings):
            key: str = "value"

        config_data = {"key": "test"}
        config_file = tmp_path / "config.yaml"
        with config_file.open("w") as f:
            yaml.dump(config_data, f)

        # Act
        source = YamlConfigSettingsSource(
            TestSettings, yaml_file_path=tmp_path, profiles=None
        )

        # Assert
        assert "YamlConfigSettingsSource" in repr(source)
        assert "yaml_data" in repr(source)
