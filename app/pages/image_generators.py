"""Admin page for managing image generator models."""

import reflex as rx

import appkit_mantine as mn
from appkit_imagecreator.components.image_generator_table import (
    image_generators_table,
)
from appkit_ui.components.header import header
from appkit_user.authentication.components.components import (
    requires_admin,
)
from appkit_user.authentication.templates import authenticated

from app.components.navbar import app_navbar
from app.roles import IMAGE_GENERATOR_ROLE

ROLE_LABELS: dict[str, str] = {
    IMAGE_GENERATOR_ROLE.name: IMAGE_GENERATOR_ROLE.label,
}

AVAILABLE_ROLES = [
    {
        "value": IMAGE_GENERATOR_ROLE.name,
        "label": IMAGE_GENERATOR_ROLE.label,
    },
]


@authenticated(
    route="/admin/image-generators",
    title="Bildgenerator-Verwaltung",
    navbar=app_navbar(),
    admin_only=True,
)
def image_generators_page() -> rx.Component:
    """Admin page for managing image generator models."""
    return requires_admin(
        mn.stack(
            header("Bildgenerator-Verwaltung"),
            image_generators_table(
                role_labels=ROLE_LABELS,
                available_roles=AVAILABLE_ROLES,
            ),
            w="100%",
            p="2rem",
            maw="1200px",
            mx="auto",
        ),
    )
