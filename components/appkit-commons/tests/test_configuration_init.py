"""Tests for configuration module lazy loading."""

import pytest

import appkit_commons.configuration as config_module


class TestConfigurationLazyLoading:
    """Test suite for configuration module lazy loading."""

    def test_configuration_in_all(self) -> None:
        """Configuration is in __all__."""
        # Assert
        assert "Configuration" in config_module.__all__

    def test_application_config_in_all(self) -> None:
        """ApplicationConfig is in __all__."""
        # Assert
        assert "ApplicationConfig" in config_module.__all__

    def test_database_config_in_all(self) -> None:
        """DatabaseConfig is in __all__."""
        # Assert
        assert "DatabaseConfig" in config_module.__all__

    def test_server_config_in_all(self) -> None:
        """ServerConfig is in __all__."""
        # Assert
        assert "ServerConfig" in config_module.__all__

    def test_worker_config_in_all(self) -> None:
        """WorkerConfig is in __all__."""
        # Assert
        assert "WorkerConfig" in config_module.__all__

    def test_base_config_in_all(self) -> None:
        """BaseConfig is in __all__."""
        # Assert
        assert "BaseConfig" in config_module.__all__

    def test_secret_provider_in_all(self) -> None:
        """SecretProvider is in __all__."""
        # Assert
        assert "SecretProvider" in config_module.__all__

    def test_secret_not_found_error_in_all(self) -> None:
        """SecretNotFoundError is in __all__."""
        # Assert
        assert "SecretNotFoundError" in config_module.__all__

    def test_get_secret_in_all(self) -> None:
        """get_secret is in __all__."""
        # Assert
        assert "get_secret" in config_module.__all__

    def test_init_logging_in_all(self) -> None:
        """init_logging is in __all__."""
        # Assert
        assert "init_logging" in config_module.__all__

    def test_lazy_map_configuration_module(self) -> None:
        """Configuration is lazy loaded from configuration module."""
        # Act
        attr = config_module.__getattr__("Configuration")

        # Assert
        assert attr is not None
        assert attr.__name__ == "Configuration"

    def test_lazy_map_application_config_module(self) -> None:
        """ApplicationConfig is lazy loaded from configuration module."""
        # Act
        attr = getattr(config_module, "ApplicationConfig", None)

        # Assert
        assert attr is not None
        assert attr.__name__ == "ApplicationConfig"

    def test_lazy_map_init_logging_module(self) -> None:
        """init_logging is lazy loaded from logging module."""
        # Act
        attr = getattr(config_module, "init_logging", None)

        # Assert
        assert attr is not None
        assert attr.__name__ == "init_logging"

    def test_getattr_returns_module_attribute(self) -> None:
        """__getattr__ returns module attributes."""
        # Act
        base_config = getattr(config_module, "BaseConfig", None)

        # Assert
        assert base_config is not None
        assert base_config.__name__ == "BaseConfig"

    def test_getattr_loads_from_correct_module(self) -> None:
        """__getattr__ loads attributes from correct module."""
        # Act
        get_secret = getattr(config_module, "get_secret", None)

        # Assert
        assert get_secret is not None
        assert "secret_provider" in get_secret.__module__

    def test_getattr_raises_attribute_error_for_unknown(self) -> None:
        """__getattr__ raises AttributeError for unknown attributes."""
        # Act & Assert
        with pytest.raises(AttributeError, match="has no attribute 'NonExistent'"):
            config_module.__getattr__("NonExistent")

    def test_backward_compatibility_all_caps(self) -> None:
        """__ALL__ backward compatibility constant exists."""
        # Assert
        assert config_module.__ALL__ == config_module.__all__

    def test_direct_getattr_base_config(self) -> None:
        """BaseConfig can be accessed via getattr."""
        # Act
        base_config = getattr(config_module, "BaseConfig", None)

        # Assert
        assert base_config is not None
        assert base_config.__name__ == "BaseConfig"

    def test_direct_getattr_get_secret(self) -> None:
        """get_secret can be accessed via getattr."""
        # Act
        get_secret = getattr(config_module, "get_secret", None)

        # Assert
        assert get_secret is not None
        assert callable(get_secret)

    def test_lazy_import_configuration_class(self) -> None:
        """Configuration class can be lazy imported."""
        # Act
        configuration_class = getattr(config_module, "Configuration", None)

        # Assert
        assert configuration_class is not None
        assert configuration_class.__name__ == "Configuration"

    def test_lazy_import_from_logging_module(self) -> None:
        """init_logging can be lazy imported from logging module."""
        # Act
        init_logging_func = getattr(config_module, "init_logging", None)

        # Assert
        assert init_logging_func is not None
        assert init_logging_func.__name__ == "init_logging"

    def test_getattr_verifies_module_source(self) -> None:
        """__getattr__ loads from correct module."""
        # Act - get init_logging which should come from logging module
        init_logging_func = getattr(config_module, "init_logging", None)

        # Assert
        assert init_logging_func.__module__ == ("appkit_commons.configuration.logging")
