import datetime
import json

from cryptography.fernet import Fernet
from sqlalchemy import (
    ARRAY,
    DateTime,
    String,
    TypeDecorator,
)
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)
from sqlalchemy.sql import func
from sqlalchemy.types import TypeEngine

from appkit_commons.database.configuration import DatabaseConfig
from appkit_commons.registry import service_registry


def get_cipher_key() -> str:
    """Get cipher key from database config, with lazy initialization."""
    return service_registry().get(DatabaseConfig).encryption_key.get_secret_value()


class EncryptedString(TypeDecorator):
    impl = String
    cache_ok = True  # Added to allow caching of the custom type

    def __init__(self, *args: any, **kwargs: any):
        super().__init__(*args, **kwargs)
        self.cipher_key = get_cipher_key()
        self.cipher = Fernet(self.cipher_key)

    def process_bind_param(self, value: any, dialect: Dialect) -> str | None:  # noqa: ARG002
        if value is not None:
            return self.cipher.encrypt(value.encode()).decode()
        return value

    def process_result_value(self, value: any, dialect: Dialect) -> str | None:  # noqa: ARG002
        if value is not None:
            return self.cipher.decrypt(value.encode()).decode()
        return value


class ArrayType(TypeDecorator):
    """Generic ARRAY type that works across databases.

    Uses native ARRAY type for PostgreSQL, JSON string storage for SQLite and others.
    """

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine:
        """Use native ARRAY for PostgreSQL, String for others."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String))
        return dialect.type_descriptor(String)

    def process_bind_param(self, value: any, dialect: Dialect) -> str | list | None:
        """Convert Python list to native ARRAY or JSON string."""
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value  # PostgreSQL ARRAY type handles it
        if isinstance(value, list):
            return json.dumps(value)
        return value

    def process_result_value(self, value: any, dialect: Dialect) -> list | None:
        """Convert stored ARRAY or JSON string back to Python list."""
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value  # PostgreSQL ARRAY returns list directly
        if isinstance(value, str):
            return json.loads(value)
        return value


class Base(DeclarativeBase):
    pass


class Entity:  # mixin class with default columns
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    created: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
