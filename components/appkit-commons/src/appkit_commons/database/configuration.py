from typing import Literal
from urllib.parse import quote

from pydantic import SecretStr, computed_field
from pydantic_settings import SettingsConfigDict

from appkit_commons.configuration.base import BaseConfig


class DatabaseConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="app_database_", env_file=".env")

    type: str = "postgresql"
    username: str = "postgres"
    password: SecretStr = SecretStr("postgres")
    host: str = "localhost"
    port: int = 5432
    name: str = "postgres"
    encryption_key: SecretStr = SecretStr("")
    pool_size: int = 10
    max_overflow: int = 30
    pool_recycle: int = 1800  # seconds, recycle connections to prevent stale SSL
    echo: bool = False
    testing: bool = False
    # SSL mode: disable, allow, prefer, require, verify-ca, verify-full
    ssl_mode: Literal[
        "disable", "allow", "prefer", "require", "verify-ca", "verify-full"
    ] = "disable"

    @computed_field(repr=False)  # type: ignore
    @property
    def url(self) -> str:
        if self.type == "sqlite":
            return f"sqlite:///{self.name}"

        if self.type == "postgresql":
            # URL encode the password to handle special characters
            encoded_password = quote(self.password.get_secret_value(), safe="")
            base_url = (
                f"postgresql+psycopg://{self.username}:{encoded_password}"
                f"@{self.host}:{self.port}/{self.name}"
            )

            # Add SSL parameters if specified
            if self.ssl_mode != "disable":
                base_url += f"?sslmode={self.ssl_mode}"

            return base_url

        raise ValueError(f"Unsupported database type: {self.type}")
