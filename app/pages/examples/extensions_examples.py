"""Extension component examples — Carousel, Dropzone, CodeHighlight."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_mantine.carousel import carousel
from appkit_mantine.code_highlight import code_highlight
from appkit_mantine.dropzone import dropzone
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar

EXAMPLE_CODE_PY = """import appkit_mantine as mn

def my_page() -> rx.Component:
    return mn.stack(
        mn.title("Hello Mantine", order=1),
        mn.button("Click me", on_click=State.handle_click),
    )
"""

EXAMPLE_CODE_TS = """import { Button, Stack, Title } from '@mantine/core';

function MyPage() {
  return (
    <Stack>
      <Title order={1}>Hello Mantine</Title>
      <Button onClick={handleClick}>Click me</Button>
    </Stack>
  );
}
"""


@navbar_layout(
    route="/extensions",
    title="Extension Components",
    navbar=app_navbar(),
    with_header=False,
)
def extensions_examples() -> rx.Component:
    return mn.container(
        mn.stack(
            mn.title("Extension Components", order=1, size="xl"),
            mn.text(
                "Carousel, Dropzone, and CodeHighlight — separate @mantine packages.",
                size="md",
                c="dimmed",
            ),
            # Carousel
            mn.title("Carousel", order=2, mt="lg"),
            mn.text(
                "Slide show with navigation controls.",
                size="sm",
                c="dimmed",
                mb="md",
            ),
            example_box(
                "Basic Carousel",
                carousel(
                    carousel.slide(
                        mn.center(
                            mn.title("Slide 1", order=3, c="white"),
                            h="100%",
                        ),
                        bg="blue.6",
                    ),
                    carousel.slide(
                        mn.center(
                            mn.title("Slide 2", order=3, c="white"),
                            h="100%",
                        ),
                        bg="teal.6",
                    ),
                    carousel.slide(
                        mn.center(
                            mn.title("Slide 3", order=3, c="white"),
                            h="100%",
                        ),
                        bg="violet.6",
                    ),
                    height=200,
                    with_controls=True,
                    with_indicators=True,
                    slide_size="100%",
                ),
            ),
            # Code Highlight
            mn.title("Code Highlight", order=2, mt="lg"),
            mn.text(
                "Syntax-highlighted code blocks.",
                size="sm",
                c="dimmed",
                mb="md",
            ),
            mn.simple_grid(
                example_box(
                    "Python Block",
                    code_highlight(
                        code=EXAMPLE_CODE_PY,
                        language="python",
                        with_copy_button=True,
                        with_border=True,
                        radius="md",
                    ),
                ),
                example_box(
                    "Tabbed Code",
                    code_highlight.tabs(
                        code=[
                            {
                                "code": EXAMPLE_CODE_PY,
                                "language": "python",
                                "fileName": "page.py",
                            },
                            {
                                "code": EXAMPLE_CODE_TS,
                                "language": "tsx",
                                "fileName": "page.tsx",
                            },
                        ],
                        with_copy_button=True,
                        with_border=True,
                        radius="md",
                    ),
                ),
                cols=2,
                spacing="md",
            ),
            # Dropzone
            mn.title("Dropzone", order=2, mt="lg"),
            mn.text(
                "Drag-and-drop file upload zone.",
                size="sm",
                c="dimmed",
                mb="md",
            ),
            example_box(
                "File Drop Zone",
                dropzone(
                    dropzone.idle(
                        mn.stack(
                            rx.icon("upload", size=40),
                            mn.text(
                                "Drop files here or click to select",
                                size="lg",
                                fw="500",
                            ),
                            mn.text(
                                "PDF, PNG, JPG up to 5MB",
                                size="sm",
                                c="dimmed",
                            ),
                            align="center",
                            gap="xs",
                        ),
                    ),
                    dropzone.accept(
                        mn.stack(
                            rx.icon("check", size=40, color="green"),
                            mn.text("Drop to upload!", size="lg", fw="500", c="green"),
                            align="center",
                            gap="xs",
                        ),
                    ),
                    dropzone.reject(
                        mn.stack(
                            rx.icon("x", size=40, color="red"),
                            mn.text("File not accepted", size="lg", fw="500", c="red"),
                            align="center",
                            gap="xs",
                        ),
                    ),
                    accept=["image/png", "image/jpeg", "application/pdf"],
                    max_size=5 * 1024 * 1024,
                    radius="md",
                    p="xl",
                ),
            ),
            gap="lg",
            w="100%",
            padding_y="lg",
        ),
        size="lg",
        w="100%",
    )
