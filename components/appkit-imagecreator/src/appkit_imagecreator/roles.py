from typing import Final

from appkit_commons.roles import Role

IMAGE_GENERATOR_GROUP = "Bildgenerator"

IMAGE_GEN_USER_ROLE = Role(
    name="image_generator",
    label="Bildgenerator",
    description="Berechtigung für die Bildgenerierung",
    group=IMAGE_GENERATOR_GROUP,
)

IMAGE_GEN_ADMIN_ROLE = Role(
    name="image_gen_admin",
    label="Admininistration",
    description="Admin-Berechtigung für die Verwaltung von Bildgeneratoren",
    group=IMAGE_GENERATOR_GROUP,
)

# === Provider-specific roles ===

IMAGE_GEN_GOOGLE_ROLE = Role(
    name="image_gen_google",
    label="Google Modelle",
    description="Berechtigung für die Nutzung von Google Bildgeneratoren",
    group=IMAGE_GENERATOR_GROUP,
)

IMAGE_GEN_AZURE_ROLE = Role(
    name="image_gen_azure",
    label="Azure Modelle",
    description="Berechtigung für die Nutzung von Azure Bildgeneratoren",
    group=IMAGE_GENERATOR_GROUP,
)

# === Role Collections ===

IMAGE_GENERATOR_ROLES: Final[list[Role]] = [
    IMAGE_GEN_USER_ROLE,
    IMAGE_GEN_ADMIN_ROLE,
    IMAGE_GEN_GOOGLE_ROLE,
    IMAGE_GEN_AZURE_ROLE,
]
