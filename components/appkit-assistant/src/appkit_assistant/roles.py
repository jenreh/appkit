from typing import Final

from appkit_commons.roles import Role

ASSISTANT_GROUP: Final[str] = "Assistent"

ASSISTANT_USER_ROLE: Final[Role] = Role(
    name="assistant", label="Chat", group=ASSISTANT_GROUP
)
ASSISTANT_ADMIN_ROLE: Final[Role] = Role(
    name="assistant-admin", label="Administration", group=ASSISTANT_GROUP
)

ASSISTANT_BASIC_MODELS_ROLE: Final[Role] = Role(
    name="assistant-basic_models", label="Basis-Modelle", group=ASSISTANT_GROUP
)
ASSISTANT_ADVANCED_MODELS_ROLE: Final[Role] = Role(
    name="assistant-advanced_models", label="Erweiterte Modelle", group=ASSISTANT_GROUP
)
ASSISTANT_PERPLEXITY_MODEL_ROLE = Role(
    id=10001,
    name="perplexity_models",
    label="Perplexity Modelle",
    description="Berechtigung für Perplexity KI-Modelle",
    group=ASSISTANT_GROUP,
)
ASSISTANT_WEB_SEARCH_ROLE: Final[Role] = Role(
    name="assistant-web_search", label="Websuche", group=ASSISTANT_GROUP
)
ASSISTANT_FILE_UPLOAD_ROLE: Final[Role] = Role(
    name="file_upload", label="Datei-Upload", group=ASSISTANT_GROUP
)

ASSISTANT_ROLES: Final[list[Role]] = [
    ASSISTANT_USER_ROLE,
    ASSISTANT_BASIC_MODELS_ROLE,
    ASSISTANT_ADVANCED_MODELS_ROLE,
    ASSISTANT_PERPLEXITY_MODEL_ROLE,
    ASSISTANT_WEB_SEARCH_ROLE,
    ASSISTANT_FILE_UPLOAD_ROLE,
    ASSISTANT_ADMIN_ROLE,
]
