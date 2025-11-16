"""Helper to include Mermaid zoom script for markdown preview."""

import reflex as rx
from reflex.assets import asset
from reflex.components.component import Component


class MermaidZoomScript(Component):
    """React component wrapper that loads the Mermaid zoom script."""

    tag = "MermaidZoomLoader"
    library = "$/public/" + asset(
        path="mermaid_zoom_loader.js",
        shared=True,
    )
    is_default = False


def mermaid_zoom_script() -> rx.Component:
    """Include the Mermaid SVG zoom JavaScript.

    Add this component to any page that uses markdown preview or renders images
    that should support click-to-zoom behaviour.
    """

    return MermaidZoomScript.create()
