import datetime
import json
from typing import Any

from cryptography.fernet import Fernet
from sqlalchemy import (
    DateTime,
    Dialect,
    String,
    TypeDecorator,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)
from sqlalchemy.sql import func

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


class EncryptedJSON(EncryptedString):
    """Custom type for storing encrypted JSON data."""

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        if value is not None:
            value = json.dumps(value)
        return super().process_bind_param(value, dialect)

    def process_result_value(self, value: Any, dialect: Dialect) -> Any | None:
        value = super().process_result_value(value, dialect)
        if value is not None:
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
