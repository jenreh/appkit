"""Lightbox examples (Mantine 9.6)."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar

_DEMO_IMAGES = (
    "https://raw.githubusercontent.com/mantinedev/mantine/master/.demo/images"
)
IMAGES = [f"{_DEMO_IMAGES}/bg-{i}.png" for i in range(1, 6)]
SLIDES = [
    {"src": src, "alt": f"Landscape {i}", "caption": f"Landscape {i}"}
    for i, src in enumerate(IMAGES, start=1)
]
VIDEO_SLIDES = [
    {
        "type": "video",
        "src": "https://www.w3schools.com/html/mov_bbb.mp4",
        "poster": IMAGES[1],
        "label": "Big Buck Bunny",
        "caption": "Video slides pause automatically when you navigate away",
    },
    SLIDES[0],
    SLIDES[2],
]


class LightboxExamplesState(rx.State):
    """State for Lightbox examples."""

    opened: bool = False
    index: int = 0

    @rx.event
    def open_at(self, index: int) -> None:
        self.index = index
        self.opened = True

    @rx.event
    def close(self) -> None:
        self.opened = False

    @rx.event
    def set_index(self, index: int) -> None:
        self.index = index

    @rx.event
    def open_store(self, start_index: int = 0) -> rx.event.EventSpec:
        return mn.lightbox_api.open(SLIDES, start_index=start_index)

    @rx.event
    def open_videos(self) -> rx.event.EventSpec:
        return mn.lightbox_api.open(VIDEO_SLIDES)


def _thumbnail(src: str, index: int) -> rx.Component:
    return mn.image(
        src=src,
        radius="md",
        h=120,
        fit="cover",
        style={"cursor": "pointer"},
        on_click=LightboxExamplesState.open_at(index),
    )


@navbar_layout(
    route="/examples/lightbox",
    title="Lightbox",
    navbar=app_navbar(),
    with_header=False,
)
def lightbox_examples() -> rx.Component:
    """Lightbox examples page."""
    return mn.container(
        mn.stack(
            mn.title("Lightbox", order=1, size="xl"),
            mn.text(
                "Full-screen media viewer with zoom, thumbnails and keyboard "
                "shortcuts (arrows, F fullscreen, T thumbnails, Z zoom).",
                size="md",
                c="dimmed",
            ),
            example_box(
                "Controlled gallery",
                mn.stack(
                    mn.simple_grid(
                        *[_thumbnail(src, i) for i, src in enumerate(IMAGES)],
                        cols=3,
                    ),
                    mn.text(
                        "Current slide: "
                        + (LightboxExamplesState.index + 1).to_string(),
                        size="sm",
                        c="dimmed",
                    ),
                ),
            ),
            example_box(
                "Store API",
                mn.group(
                    mn.button(
                        "Open lightbox",
                        on_click=LightboxExamplesState.open_store(0),
                    ),
                    mn.button(
                        "Open at slide 3",
                        variant="default",
                        on_click=LightboxExamplesState.open_store(2),
                    ),
                    mn.button(
                        "Video slides",
                        variant="light",
                        on_click=LightboxExamplesState.open_videos,
                    ),
                ),
            ),
            mn.lightbox(
                opened=LightboxExamplesState.opened,
                on_close=LightboxExamplesState.close,
                slides=SLIDES,
                current_index=LightboxExamplesState.index,
                on_index_change=LightboxExamplesState.set_index,
                with_thumbnails=True,
                with_fullscreen=True,
                loop=True,
            ),
            mn.lightbox.provider(with_thumbnails=True, with_download=True),
            spacing="md",
            w="100%",
            mb="6rem",
        ),
        size="lg",
        w="100%",
    )
