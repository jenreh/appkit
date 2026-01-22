from appkit_user.authentication.backend.models import Role

ASSISTANT_GROUP = "Assistent"
IMAGE_GENERATOR_GROUP = "Bildgenerator"

ASSISTANT_ROLE = Role(
    id=1,
    name="assistant",
    label="Assistent",
    description="Berechtigung für den Chat-Assistenten",
    group=ASSISTANT_GROUP,
)
IMAGE_GENERATOR_ROLE = Role(
    id=2,
    name="image_generator",
    label="Bildgenerator",
    description="Berechtigung für die Bildgenerierung",
    group=IMAGE_GENERATOR_GROUP,
)

BASIC_MODEL_ROLE = Role(
    id=3,
    name="basic_model",
    label="Basis Modelle",
    description="Berechtigung für Basis-KI-Modelle",
    group=ASSISTANT_GROUP,
)
ADVANCED_MODEL_ROLE = Role(
    id=4,
    name="advanced_model",
    label="Advanced Modelle",
    description="Berechtigung für fortgeschrittene KI-Modelle",
    group=ASSISTANT_GROUP,
)
PERPLEXITY_MODEL_ROLE = Role(
    id=10001,
    name="perplexity_models",
    label="Perplexity Modelle",
    description="Berechtigung für Perplexity KI-Modelle",
    group=ASSISTANT_GROUP,
)

ALL_ROLES: list[Role] = [
    ASSISTANT_ROLE,
    BASIC_MODEL_ROLE,
    ADVANCED_MODEL_ROLE,
    PERPLEXITY_MODEL_ROLE,
    IMAGE_GENERATOR_ROLE,
]
