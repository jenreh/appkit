from pydantic import SecretStr

from appkit_commons.configuration import BaseConfig


class AssistantConfig(BaseConfig):
    perplexity_api_key: SecretStr | None = None
    openai_base_url: str | None = None
    openai_api_key: SecretStr | None = None
    google_api_key: SecretStr | None = None
    azure_ai_projects_endpoint: str | None = None
