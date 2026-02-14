from pydantic import SecretStr

from appkit_commons.configuration import BaseConfig


class FileUploadConfig(BaseConfig):
    """Configuration for file upload and vector store management."""

    vector_store_expiration_days: int = 2
    max_file_size_mb: int = 50
    max_files_per_thread: int = 10
    cleanup_interval_minutes: int = 60
    files_expiration_days: int = 30


class AssistantConfig(BaseConfig):
    azure_api_key: SecretStr | None = None
    azure_ai_projects_endpoint: str | None = None
    openai_is_azure: bool = False

    openai_base_url: str | None = None
    openai_api_key: SecretStr | None = None

    claude_base_url: str | None = None
    claude_api_key: SecretStr | None = None

    google_api_key: SecretStr | None = None
    perplexity_api_key: SecretStr | None = None

    file_upload: FileUploadConfig = FileUploadConfig()
