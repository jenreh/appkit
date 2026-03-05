import logging
from functools import lru_cache

from appkit_assistant.configuration import AssistantConfig
from appkit_commons.configuration.configuration import (
    ApplicationConfig,
    Configuration,
)
from appkit_commons.registry import service_registry
from appkit_imagecreator.configuration import ImageGeneratorConfig
from appkit_mcp_bpmn.configuration import BPMNConfig
from appkit_mcp_image.configuration import MCPImageGeneratorConfig
from appkit_mcp_user.configuration import McpUserConfig
from appkit_user.configuration import AuthenticationConfiguration

logger = logging.getLogger(__name__)


class AppConfig(ApplicationConfig):
    authentication: AuthenticationConfiguration
    imagegenerator: ImageGeneratorConfig | None = None
    assistant: AssistantConfig | None = None
    mcp_user: McpUserConfig | None = None
    mcp_bpmn: BPMNConfig | None = None
    mcp_image: MCPImageGeneratorConfig | None = None


@lru_cache(maxsize=1)
def configure() -> Configuration[AppConfig]:
    logger.debug("--- Configuring application settings ---")
    return service_registry().configure(
        AppConfig,
        env_file="/.env",
    )
