"""Package-specific fixtures for appkit-commons tests."""

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
import yaml
from faker import Faker

# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture
def temp_yaml_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary YAML file for testing configuration loading."""

    def _create_yaml(data: dict[str, Any]) -> Path:
        yaml_file = tmp_path / "test_config.yaml"
        with yaml_file.open("w") as f:
            yaml.dump(data, f)
        return yaml_file

    return _create_yaml


@pytest.fixture
def sample_yaml_config(tmp_path: Path) -> Path:
    """Create a sample YAML config file."""
    config_data = {
        "environment": "test",
        "app_name": "test-app",
        "version": "1.0.0",
        "database": {
            "host": "localhost",
            "port": 5432,
            "user": "test_user",
            "password": "test_password",
            "database": "test_db",
        },
        "logging": {
            "level": "INFO",
            "format": "json",
        },
    }

    yaml_file = tmp_path / "config.yaml"
    with yaml_file.open("w") as f:
        yaml.dump(config_data, f)

    return yaml_file


# ============================================================================
# Entity Factories
# ============================================================================


@pytest.fixture
def create_test_entity(faker_instance: Faker) -> callable:
    """Factory for creating test entities with fake data."""

    def _factory(model_class: type, **overrides: Any) -> Any:
        """Create an instance of model_class with fake data.

        Args:
            model_class: The model class to instantiate
            **overrides: Override specific fields

        Returns:
            Instance of model_class with fake/overridden data
        """
        # This is a generic factory - specific packages will extend this
        fake_data = {
            "name": faker_instance.name(),
            "email": faker_instance.email(),
            "description": faker_instance.text(max_nb_chars=200),
            "url": faker_instance.url(),
        }

        # Override with provided values
        fake_data.update(overrides)

        # Filter to only fields that exist in the model
        if hasattr(model_class, "__annotations__"):
            valid_fields = {
                k: v for k, v in fake_data.items() if k in model_class.__annotations__
            }
            return model_class(**valid_fields)

        return model_class(**fake_data)

    return _factory
