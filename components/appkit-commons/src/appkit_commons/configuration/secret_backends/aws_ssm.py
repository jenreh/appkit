import logging
from typing import Any

from appkit_commons.configuration.secret_backends.base import SecretNotFoundError

logger = logging.getLogger(__name__)


def create_ssm_client() -> Any:
    """SSM client using the default AWS credential chain (aws login, profiles)."""
    try:
        import boto3  # noqa: PLC0415  # ty: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "Optional AWS dependencies are required to use SecretProvider.AWS_SSM. "
            "Install 'appkit-commons[aws]' ('boto3')."
        ) from exc
    return boto3.client("ssm")


def ssm_parameter_name(name: str, namespace: str | None) -> str:
    """`/<namespace>/<name>`; absolute names and an unset namespace stay as is."""
    if name.startswith("/"):
        return name
    prefix = (namespace or "").strip("/")
    return f"/{prefix}/{name}" if prefix else name


def _error_code(exc: Exception) -> str | None:
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return None
    return response.get("Error", {}).get("Code")


class AwsSsmBackend:
    def __init__(self, client: Any, namespace: str | None = None) -> None:
        self._client = client
        self._namespace = namespace

    def get(self, name: str) -> str:
        parameter = ssm_parameter_name(name, self._namespace)
        logger.debug("Reading parameter %s from AWS SSM", parameter)
        try:
            response = self._client.get_parameter(Name=parameter, WithDecryption=True)
        except Exception as exc:
            if _error_code(exc) == "ParameterNotFound":
                raise SecretNotFoundError(
                    f"Secret '{name}' not found in AWS SSM (parameter '{parameter}')"
                ) from exc
            raise
        return str(response["Parameter"]["Value"])
