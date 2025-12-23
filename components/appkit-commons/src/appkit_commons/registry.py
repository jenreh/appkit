import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Any, TypeVar, cast

if TYPE_CHECKING:
    from appkit_commons.configuration.configuration import (
        ApplicationConfig,
        Configuration,
    )

logger = logging.getLogger(__name__)

T = TypeVar("T")
ConfigT = TypeVar("ConfigT", bound="ApplicationConfig")


class ServiceRegistry:
    """Registry for storing and retrieving initialized instances by their class type."""

    def __init__(self) -> None:
        self._instances: dict[type[Any], Any] = {}

    def _register_config_recursively(  # noqa: PLR0912
        self, obj: Any, visited: set[int] | None = None
    ) -> None:
        """Recursively register configuration objects and their attributes."""
        if visited is None:
            visited = set()

        # Avoid infinite recursion by tracking visited objects
        obj_id = id(obj)
        if obj_id in visited:
            return
        visited.add(obj_id)

        # Use __dict__ to get instance attributes directly
        if hasattr(obj, "__dict__"):
            for attr_name, attr_value in obj.__dict__.items():
                # Skip private attributes and None values
                if attr_name.startswith("_") or attr_value is None:
                    continue

                try:
                    # Check if this is a configuration object (not a basic type)
                    if hasattr(attr_value, "__class__"):
                        attr_class = attr_value.__class__

                        # Skip built-in types, pydantic types, and already registered
                        if (
                            attr_class.__module__ != "builtins"
                            and attr_class.__name__ not in ("SecretStr", "StrEnum")
                            and not self.has(attr_class)
                        ):
                            self.register_as(attr_class, attr_value)
                            logger.debug(
                                "Registered service configuration: %s from attribute %s",  # noqa: E501
                                attr_class.__name__,
                                attr_name,
                            )

                            # Recursively register nested configurations
                            self._register_config_recursively(attr_value, visited)

                except Exception as e:
                    logger.warning(
                        "Failed to process attribute %s: %s", attr_name, str(e)
                    )

        # Also check class annotations to handle properties/descriptors
        if hasattr(obj.__class__, "__annotations__"):
            for attr_name in obj.__class__.__annotations__:
                if attr_name.startswith("_"):
                    continue

                try:
                    attr_value = getattr(obj, attr_name, None)
                    if attr_value is not None and hasattr(attr_value, "__class__"):
                        attr_class = attr_value.__class__

                        if (
                            attr_class.__module__ != "builtins"
                            and attr_class.__name__ not in ("SecretStr", "StrEnum")
                            and not self.has(attr_class)
                        ):
                            self.register_as(attr_class, attr_value)
                            logger.debug(
                                "Registered service configuration: %s from annotated attribute %s",  # noqa: E501
                                attr_class.__name__,
                                attr_name,
                            )

                            # Recursively register nested configurations
                            self._register_config_recursively(attr_value, visited)

                except Exception as e:
                    logger.warning(
                        "Failed to access annotated attribute %s: %s", attr_name, str(e)
                    )

    def configure(
        self, app_config_class: type[ConfigT], env_file: str = ".env"
    ) -> "Configuration[ConfigT]":
        """Configure and register the application configuration."""
        from appkit_commons.configuration.configuration import (  # noqa: PLC0415
            Configuration,
        )

        logger.debug(
            "Configuring application with config class: %s", app_config_class.__name__
        )

        # Create the configuration instance
        configuration = Configuration[app_config_class](_env_file=env_file)

        # Register the configuration instance
        self.register_as(Configuration, configuration)
        self._register_config_recursively(configuration)

        logger.info("Application configuration initialized and registered")
        logger.info("Total registered instances: %d", len(self._instances))
        for registered_type in self.list_registered():
            logger.debug("Registered: %s", registered_type.__name__)

        return configuration

    def register(self, instance: object) -> None:
        """Register an initialized instance using its class type as the key."""
        instance_type = type(instance)

        if instance_type in self._instances:
            logger.warning(
                "Overwriting existing instance of type: %s", instance_type.__name__
            )

        self._instances[instance_type] = instance
        logger.debug("Registered instance of type %s", instance_type.__name__)

    def register_as(self, instance_type: type[T], instance: T) -> None:
        """Register an initialized instance with a specific type as the key."""
        if instance_type in self._instances:
            logger.warning(
                "Overwriting existing instance of type: %s", instance_type.__name__
            )

        self._instances[instance_type] = instance
        logger.debug("Registered instance as type %s", instance_type.__name__)

    def get(self, instance_type: type[T]) -> T:
        """Retrieve an instance by its class type, returning None if not found."""
        instance: type[T] | None = self._instances.get(instance_type)
        if instance is None:
            logger.error(
                "Instance of type %s not found in registry", instance_type.__name__
            )
            raise KeyError(
                f"Instance of type {instance_type.__name__} not found in registry"
            )
        return cast(T, instance)

    def unregister(self, instance_type: type[T]) -> None:
        """Remove an instance from the registry by its class type."""
        if instance_type in self._instances:
            del self._instances[instance_type]
            logger.debug("Unregistered instance of type: %s", instance_type.__name__)
        else:
            logger.warning(
                "Attempted to unregister non-existent type: %s", instance_type.__name__
            )

    def list_registered(self) -> list[type[Any]]:
        """Get a list of all registered class types."""
        return list(self._instances)

    def has(self, instance_type: type[T]) -> bool:
        """Check if an instance is registered for the given class type."""
        return instance_type in self._instances

    def clear(self) -> None:
        """Clear all registered instances."""
        count = len(self._instances)
        self._instances.clear()
        logger.debug("Cleared %d instances from registry", count)


@lru_cache(maxsize=1)
def service_registry() -> ServiceRegistry:
    logger.debug("Creating the service registry instance")
    return ServiceRegistry()
