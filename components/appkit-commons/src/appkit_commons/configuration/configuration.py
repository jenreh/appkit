from __future__ import annotations

from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import Field

from appkit_commons.configuration.base import BaseConfig
from appkit_commons.database.configuration import DatabaseConfig


class ConfigurationError(ValueError):
    pass


class Environment(StrEnum):
    devcontainer = "devcontainer"
    development = "development"
    production = "production"
    testing = "test"
    staging = "stage"
    docker = "docker"
    local = "local"
    ci = "ci"


class WorkerConfig(StrEnum):
    multiprocessing = "multiprocessing"
    webconcurrency = "webconcurrency"


class Protocol(StrEnum):
    http = "http"
    https = "https"


class ServerConfig(BaseConfig):
    host: str
    port: int
    docker_port: int
    protocol: Protocol = Protocol.http
    reload: bool = False
    workers: int | WorkerConfig = WorkerConfig.webconcurrency


class ReflexConfig(BaseConfig):
    deploy_url: str | None = None
    api_url: str | None = None
    frontend_port: int = 80
    backend_port: int = 3030
    workers: int = 3
    default_timeout: int = 300  # seconds
    backend_timeout: int = 180  # seconds
    single_port: bool = False


class ApplicationConfig(BaseConfig):
    version: str
    name: str
    logging: str
    environment: Environment | None = Environment.local
    database: DatabaseConfig | None = Field(..., alias="database")


T = TypeVar("T", bound=ApplicationConfig)


class Configuration(BaseConfig, Generic[T]):  # noqa: UP046
    profile: str
    server: ServerConfig | None = Field(default=None, alias="server")
    reflex: ReflexConfig | None = Field(default=None, alias="reflex")
    app: T
