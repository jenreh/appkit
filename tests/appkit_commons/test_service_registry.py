"""Tests for ServiceRegistry dependency injection container."""

import pytest

from appkit_commons.registry import ServiceRegistry, service_registry


class DummyService:
    """Dummy service for testing."""

    def __init__(self, name: str = "test") -> None:
        self.name = name


class DummyConfig:
    """Dummy configuration for testing."""

    def __init__(self, value: str = "config_value") -> None:
        self.value = value


class NestedConfig:
    """Configuration with nested attributes."""

    def __init__(self) -> None:
        self.database = DatabaseConfig()
        self.api = ApiConfig()
        self.name = "nested"


class DatabaseConfig:
    """Database configuration."""

    def __init__(self) -> None:
        self.host = "localhost"
        self.port = 5432


class ApiConfig:
    """API configuration."""

    def __init__(self) -> None:
        self.base_url = "https://api.example.com"
        self.timeout = 30


class TestServiceRegistry:
    """Test suite for ServiceRegistry DI container."""

    def test_register_and_get(self, clean_service_registry: ServiceRegistry) -> None:
        """Registering an instance allows retrieval by type."""
        # Arrange
        service = DummyService("my-service")

        # Act
        clean_service_registry.register(service)
        retrieved = clean_service_registry.get(DummyService)

        # Assert
        assert retrieved is service
        assert retrieved.name == "my-service"

    def test_register_as_specific_type(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """Registering with a specific type key works."""
        # Arrange
        service = DummyService("specific")

        # Act
        clean_service_registry.register_as(DummyService, service)
        retrieved = clean_service_registry.get(DummyService)

        # Assert
        assert retrieved is service

    def test_get_nonexistent_raises_key_error(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """Getting a non-registered type raises KeyError."""
        # Act & Assert
        with pytest.raises(KeyError, match="DummyService not found"):
            clean_service_registry.get(DummyService)

    def test_register_overwrites_warning(
        self, clean_service_registry: ServiceRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Re-registering a type logs a warning."""
        # Arrange
        service1 = DummyService("first")
        service2 = DummyService("second")

        # Act
        clean_service_registry.register(service1)
        clean_service_registry.register(service2)

        # Assert
        assert "Overwriting existing instance" in caplog.text
        retrieved = clean_service_registry.get(DummyService)
        assert retrieved is service2

    def test_has_returns_true_for_registered(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """has() returns True for registered types."""
        # Arrange
        service = DummyService()
        clean_service_registry.register(service)

        # Act & Assert
        assert clean_service_registry.has(DummyService) is True

    def test_has_returns_false_for_unregistered(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """has() returns False for unregistered types."""
        # Act & Assert
        assert clean_service_registry.has(DummyService) is False

    def test_unregister_removes_instance(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """Unregistering a type removes it from the registry."""
        # Arrange
        service = DummyService()
        clean_service_registry.register(service)

        # Act
        clean_service_registry.unregister(DummyService)

        # Assert
        assert clean_service_registry.has(DummyService) is False

    def test_unregister_nonexistent_logs_warning(
        self, clean_service_registry: ServiceRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Unregistering a non-existent type logs a warning."""
        # Act
        clean_service_registry.unregister(DummyService)

        # Assert
        assert "Attempted to unregister non-existent type" in caplog.text

    def test_list_registered(self, clean_service_registry: ServiceRegistry) -> None:
        """list_registered() returns all registered types."""
        # Arrange
        service = DummyService()
        config = DummyConfig()
        clean_service_registry.register(service)
        clean_service_registry.register(config)

        # Act
        registered = clean_service_registry.list_registered()

        # Assert
        assert DummyService in registered
        assert DummyConfig in registered
        assert len(registered) == 2

    def test_clear_removes_all_instances(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """clear() removes all registered instances."""
        # Arrange
        service = DummyService()
        config = DummyConfig()
        clean_service_registry.register(service)
        clean_service_registry.register(config)

        # Act
        clean_service_registry.clear()

        # Assert
        assert len(clean_service_registry.list_registered()) == 0
        assert clean_service_registry.has(DummyService) is False
        assert clean_service_registry.has(DummyConfig) is False

    def test_register_config_recursively_simple(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """_register_config_recursively registers nested config objects."""
        # Arrange
        config = NestedConfig()

        # Act
        clean_service_registry._register_config_recursively(config)

        # Assert
        assert clean_service_registry.has(DatabaseConfig) is True
        assert clean_service_registry.has(ApiConfig) is True
        db_config = clean_service_registry.get(DatabaseConfig)
        assert db_config.host == "localhost"

    def test_register_config_recursively_avoids_circular_refs(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """_register_config_recursively handles circular references."""

        # Arrange
        class CircularA:
            def __init__(self) -> None:
                self.name = "A"
                self.ref_b: CircularB | None = None

        class CircularB:
            def __init__(self) -> None:
                self.name = "B"
                self.ref_a: CircularA | None = None

        a = CircularA()
        b = CircularB()
        a.ref_b = b
        b.ref_a = a

        # Act - should not raise RecursionError
        clean_service_registry._register_config_recursively(a)

        # Assert
        assert clean_service_registry.has(CircularB) is True

    def test_register_config_recursively_skips_private_attrs(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """_register_config_recursively skips private attributes."""

        # Arrange
        class ConfigWithPrivate:
            def __init__(self) -> None:
                self.public = DummyConfig()
                self._private = DummyConfig()

        config = ConfigWithPrivate()

        # Act
        clean_service_registry._register_config_recursively(config)

        # Assert
        # Should register the public DummyConfig, but not try to register
        # ConfigWithPrivate itself (it's not a known config type)
        assert clean_service_registry.has(DummyConfig) is True

    def test_register_config_recursively_skips_builtins(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """_register_config_recursively skips built-in types."""

        # Arrange
        class ConfigWithBuiltins:
            def __init__(self) -> None:
                self.number = 42
                self.text = "hello"
                self.items = [1, 2, 3]

        config = ConfigWithBuiltins()

        # Act - should not raise
        clean_service_registry._register_config_recursively(config)

        # Assert - no built-in types should be registered
        registered = clean_service_registry.list_registered()
        assert int not in registered
        assert str not in registered
        assert list not in registered

    def test_service_registry_singleton(self) -> None:
        """service_registry() returns a singleton instance."""
        # Act
        registry1 = service_registry()
        registry2 = service_registry()

        # Assert
        assert registry1 is registry2

    def test_multiple_instances_same_base_type(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """Registering with different keys allows multiple instances."""

        # Arrange
        class ServiceA(DummyService):
            pass

        class ServiceB(DummyService):
            pass

        service_a = ServiceA("A")
        service_b = ServiceB("B")

        # Act
        clean_service_registry.register(service_a)
        clean_service_registry.register(service_b)

        # Assert
        assert clean_service_registry.get(ServiceA).name == "A"
        assert clean_service_registry.get(ServiceB).name == "B"

    def test_register_as_allows_interface_registration(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """register_as() allows registering implementations as interfaces."""

        # Arrange
        class IService:
            def do_work(self) -> str:
                raise NotImplementedError

        class ConcreteService(IService):
            def do_work(self) -> str:
                return "working"

        service = ConcreteService()

        # Act
        clean_service_registry.register_as(IService, service)

        # Assert
        retrieved = clean_service_registry.get(IService)
        assert isinstance(retrieved, ConcreteService)
        assert retrieved.do_work() == "working"
