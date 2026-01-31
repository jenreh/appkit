"""Image Gallery page with authentication wrapper.

This page provides the new image creator UI with a modern gallery interface.
"""

import reflex as rx

from appkit_imagecreator.pages import image_generator_page
from appkit_user.authentication.components.components import requires_role
from appkit_user.authentication.templates import authenticated

from app.components.navbar import app_navbar
from app.roles import IMAGE_GENERATOR_ROLE


@authenticated(
    route="/image-gallery",
    title="Image Gallery",
    description="Generate and manage AI-created images.",
    navbar=app_navbar(),
    with_header=True,
)
def image_gallery() -> rx.Component:
    """Image gallery page with role-based access control."""
    return requires_role(
        image_generator_page(),
        role=IMAGE_GENERATOR_ROLE.name,
    )
