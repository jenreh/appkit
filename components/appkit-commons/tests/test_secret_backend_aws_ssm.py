"""Tests for the AWS SSM Parameter Store secret backend."""

import builtins
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from appkit_commons.configuration.secret_backends.aws_ssm import (
    AwsSsmBackend,
    create_ssm_client,
    ssm_parameter_name,
)
from appkit_commons.configuration.secret_backends.base import SecretNotFoundError


class FakeClientError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeSsm:
    def __init__(self, parameters: dict[str, str]) -> None:
        self.parameters = parameters
        self.calls: list[dict[str, Any]] = []

    def get_parameter(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        name = kwargs["Name"]
        if name not in self.parameters:
            raise FakeClientError("ParameterNotFound")
        return {"Parameter": {"Name": name, "Value": self.parameters[name]}}


class TestSsmParameterName:
    @pytest.mark.parametrize(
        ("name", "namespace", "expected"),
        [
            ("db-user", None, "db-user"),
            ("db-user", "", "db-user"),
            ("db-user", "myapp", "/myapp/db-user"),
            ("db-user", "/myapp/dev/", "/myapp/dev/db-user"),
            ("db-user", "track/prod", "/track/prod/db-user"),
            ("/abs/db-user", "myapp", "/abs/db-user"),
            ("db-user", "/", "db-user"),
        ],
    )
    def test_mapping(self, name: str, namespace: str | None, expected: str) -> None:
        assert ssm_parameter_name(name, namespace) == expected


class TestAwsSsmBackend:
    def test_get_reads_decrypted_parameter_below_namespace(self) -> None:
        # Arrange
        client = FakeSsm({"/myapp/dev/db-password": "s3cret"})
        backend = AwsSsmBackend(client, "myapp/dev")

        # Act
        value = backend.get("db-password")

        # Assert
        assert value == "s3cret"
        assert client.calls == [
            {"Name": "/myapp/dev/db-password", "WithDecryption": True}
        ]

    def test_get_without_namespace_uses_bare_name(self) -> None:
        client = FakeSsm({"db-password": "plain"})
        assert AwsSsmBackend(client).get("db-password") == "plain"

    def test_missing_parameter_raises_secret_not_found(self) -> None:
        backend = AwsSsmBackend(FakeSsm({}), "myapp")

        with pytest.raises(SecretNotFoundError, match="/myapp/missing"):
            backend.get("missing")

    def test_other_client_errors_propagate(self) -> None:
        class Denied:
            def get_parameter(self, **_: Any) -> dict[str, Any]:
                raise FakeClientError("AccessDeniedException")

        with pytest.raises(FakeClientError):
            AwsSsmBackend(Denied(), "myapp").get("x")

    def test_errors_without_response_propagate(self) -> None:
        class Broken:
            def get_parameter(self, **_: Any) -> dict[str, Any]:
                raise RuntimeError("network down")

        with pytest.raises(RuntimeError, match="network down"):
            AwsSsmBackend(Broken()).get("x")


class TestCreateSsmClient:
    def test_uses_boto3_default_chain(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange
        created: list[str] = []
        fake_boto3 = ModuleType("boto3")
        fake_boto3.client = lambda service: created.append(service) or SimpleNamespace()  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

        # Act
        create_ssm_client()

        # Assert
        assert created == ["ssm"]

    def test_missing_boto3_names_the_extra(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "boto3":
                raise ImportError("no boto3")
            return real_import(name, *args, **kwargs)

        monkeypatch.delitem(sys.modules, "boto3", raising=False)
        monkeypatch.setattr(builtins, "__import__", fake_import)

        with pytest.raises(ImportError, match=r"appkit-commons\[aws\]"):
            create_ssm_client()
