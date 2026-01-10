from appkit_user.authentication.backend.models import Role

ASSISTANT_ROLE = Role(
    id=1,
    name="assistant",
    label="Assistent",
    description="Berechtigung für den Chat-Assistenten",
)
IMAGE_GENERATOR_ROLE = Role(
    id=2,
    name="image_generator",
    label="Bildgenerator",
    description="Berechtigung für die Bildgenerierung",
)

BASIC_MODEL_ROLE = Role(
    id=3,
    name="basic_model",
    label="Basis-Modelle",
    description="Berechtigung für Basis-KI-Modelle",
)
ADVANCED_MODEL_ROLE = Role(
    id=4,
    name="advanced_model",
    label="Advanced-Modelle",
    description="Berechtigung für fortgeschrittene KI-Modelle",
)
PERPLEXITY_MODEL_ROLE = Role(
    id=10001,
    name="perplexity_models",
    label="Perplexity-Modelle",
    description="Berechtigung für Perplexity KI-Modelle",
)

ALL_ROLES: list[Role] = [
    ASSISTANT_ROLE,
    IMAGE_GENERATOR_ROLE,
    BASIC_MODEL_ROLE,
    ADVANCED_MODEL_ROLE,
    PERPLEXITY_MODEL_ROLE,
]
