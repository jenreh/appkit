"""Typography component examples — Blockquote, Highlight, Mark."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar


@navbar_layout(
    route="/typography",
    title="Typography Components",
    navbar=app_navbar(),
    with_header=False,
)
def typography_examples() -> rx.Component:
    return mn.container(
        mn.stack(
            mn.title("Typography Components", order=1, size="xl"),
            mn.text(
                "Blockquote, Highlight, and Mark components.",
                size="md",
                c="dimmed",
            ),
            # Blockquote
            mn.title("Blockquote", order=2, mt="lg"),
            mn.text(
                "Display styled quotations with optional citation and icon.",
                size="sm",
                c="dimmed",
                mb="md",
            ),
            mn.simple_grid(
                example_box(
                    "Simple Blockquote",
                    mn.blockquote(
                        "Nothing in life is to be feared, it is only to be understood.",
                        cite="— Marie Curie",
                        color="blue",
                    ),
                ),
                example_box(
                    "Blockquote with Icon",
                    mn.blockquote(
                        "The only way to do great work is to love what you do.",
                        cite="— Steve Jobs",
                        icon=rx.icon("quote", size=24),
                        color="teal",
                        radius="md",
                    ),
                ),
                cols=2,
                spacing="md",
            ),
            # Highlight
            mn.title("Highlight", order=2, mt="lg"),
            mn.text(
                "Highlights substrings within text.",
                size="sm",
                c="dimmed",
                mb="md",
            ),
            mn.simple_grid(
                example_box(
                    "Single Highlight",
                    mn.highlight(
                        "Highlight React and Reflex in this text",
                        highlight=["React", "Reflex"],
                        color="yellow",
                    ),
                ),
                example_box(
                    "Case Insensitive",
                    mn.highlight(
                        "The quick BROWN fox jumps over the lazy dog",
                        highlight=["brown", "lazy"],
                        case_insensitive=True,
                        color="orange",
                    ),
                ),
                cols=2,
                spacing="md",
            ),
            # Mark
            mn.title("Mark", order=2, mt="lg"),
            mn.text(
                "Inline text highlight.",
                size="sm",
                c="dimmed",
                mb="md",
            ),
            mn.simple_grid(
                example_box(
                    "Mark Default",
                    mn.text(
                        "This word is ",
                        mn.mark("highlighted", color="yellow"),
                        " in the sentence.",
                        span=True,
                    ),
                ),
                example_box(
                    "Mark Custom Color",
                    mn.text(
                        "Status: ",
                        mn.mark("important", color="red.2"),
                        " — please read carefully.",
                        span=True,
                    ),
                ),
                cols=2,
                spacing="md",
            ),
            gap="lg",
            w="100%",
            padding_y="lg",
        ),
        size="lg",
        w="100%",
    )
