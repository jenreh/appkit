"""Tests for logging configuration."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from appkit_commons.configuration.logging import init_logging


class TestInitLogging:
    """Test suite for init_logging function."""

    def test_init_logging_with_yaml_file(self, tmp_path: Path) -> None:
        """init_logging loads YAML configuration when file exists."""
        # Arrange
        logging_config = tmp_path / "logging.yaml"
        config_dict = {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {},
            "root": {"level": "INFO"},
        }
        logging_config.write_text(yaml.dump(config_dict))

        mock_config = MagicMock()
        mock_config.app.logging = "logging.yaml"

        # Act & Assert
        with (
            patch("appkit_commons.configuration.logging.CONFIGURATION_PATH", tmp_path),
            patch(
                "appkit_commons.configuration.logging.logging.config.dictConfig"
            ) as mock_dict_config,
        ):
            init_logging(mock_config)
            mock_dict_config.assert_called_once()

    def test_init_logging_fallback_to_default(self) -> None:
        """init_logging logs default message when file doesn't exist."""
        # Arrange
        mock_config = MagicMock()
        mock_config.app.logging = "logging.nonexistent.yaml"

        # Act & Assert - should not raise
        with patch(
            "appkit_commons.configuration.logging.CONFIGURATION_PATH",
            Path("/nonexistent"),
        ):
            init_logging(mock_config)

    def test_init_logging_reads_yaml_with_utf8(self, tmp_path: Path) -> None:
        """init_logging reads UTF-8 encoded YAML files."""
        # Arrange
        logging_config = tmp_path / "logging.yaml"
        yaml_content = """
version: 1
disable_existing_loggers: false
root:
  level: DEBUG
"""
        logging_config.write_text(yaml_content, encoding="utf-8")

        mock_config = MagicMock()
        mock_config.app.logging = "logging.yaml"

        # Act & Assert
        with (
            patch("appkit_commons.configuration.logging.CONFIGURATION_PATH", tmp_path),
            patch(
                "appkit_commons.configuration.logging.logging.config.dictConfig"
            ) as mock_dict_config,
        ):
            init_logging(mock_config)
            assert mock_dict_config.called
            # Verify the parsed config was passed to dictConfig
            call_args = mock_dict_config.call_args[0][0]
            assert call_args["version"] == 1
            assert call_args["root"]["level"] == "DEBUG"

    def test_init_logging_parses_yaml_correctly(self, tmp_path: Path) -> None:
        """init_logging correctly parses YAML structure."""
        # Arrange
        logging_config = tmp_path / "logging.yaml"
        config_dict = {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                }
            },
            "loggers": {"test": {"level": "INFO", "handlers": ["console"]}},
            "root": {"level": "WARNING", "handlers": ["console"]},
        }
        logging_config.write_text(yaml.dump(config_dict))

        mock_config = MagicMock()
        mock_config.app.logging = "logging.yaml"

        # Act & Assert
        with (
            patch("appkit_commons.configuration.logging.CONFIGURATION_PATH", tmp_path),
            patch(
                "appkit_commons.configuration.logging.logging.config.dictConfig"
            ) as mock_dict_config,
        ):
            init_logging(mock_config)
            call_args = mock_dict_config.call_args[0][0]
            assert "handlers" in call_args
            assert "console" in call_args["handlers"]
            assert call_args["root"]["level"] == "WARNING"

    def test_init_logging_logs_info_message(self, tmp_path: Path, caplog) -> None:
        """init_logging logs info message when config exists."""
        # Arrange
        logging_config = tmp_path / "logging.yaml"
        logging_config.write_text(
            yaml.dump(
                {
                    "version": 1,
                    "disable_existing_loggers": False,
                    "handlers": {},
                    "root": {"level": "INFO"},
                }
            )
        )

        mock_config = MagicMock()
        mock_config.app.logging = "logging.yaml"

        # Act
        with (
            patch("appkit_commons.configuration.logging.CONFIGURATION_PATH", tmp_path),
            caplog.at_level(logging.INFO),
        ):
            init_logging(mock_config)

            # Assert - check that logging configuration message was logged
            found_message = any(
                "logging configuration" in record.message for record in caplog.records
            )
            assert found_message

    def test_init_logging_opens_file_in_read_text_mode(self, tmp_path: Path) -> None:
        """init_logging opens files properly with UTF-8 encoding."""
        # Arrange
        logging_config = tmp_path / "logging.yaml"
        logging_config.write_text(
            yaml.dump({"version": 1, "disable_existing_loggers": False})
        )

        mock_config = MagicMock()
        mock_config.app.logging = "logging.yaml"

        # Act & Assert - should not raise any encoding errors
        with (
            patch("appkit_commons.configuration.logging.CONFIGURATION_PATH", tmp_path),
            patch("appkit_commons.configuration.logging.logging.config.dictConfig"),
        ):
            init_logging(mock_config)
