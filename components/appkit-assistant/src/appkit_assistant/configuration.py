from appkit_commons.configuration import BaseConfig


class FileUploadConfig(BaseConfig):
    """Configuration for file upload and vector store management."""

    vector_store_expiration_days: int = 2
    max_file_size_mb: int = 50
    max_files_per_thread: int = 10
    cleanup_interval_minutes: int = 60
    files_expiration_days: int = 30


class AssistantConfig(BaseConfig):
    file_upload: FileUploadConfig = FileUploadConfig()
