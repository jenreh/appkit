import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.navbar import app_navbar


@navbar_layout(
    route="/",
    title="Home",
    description="A demo page for the appkit components",
    navbar=app_navbar(),
    with_header=False,
)
def index() -> rx.Component:
    return mn.container(
        mn.stack(
            mn.title("Welcome to appkit!", order=1, size="xl"),
            mn.text(
                "A component library for ",
                rx.link("Reflex.dev", href="https://reflex.dev/", is_external=True),
                " based on ",
                rx.link("Mantine UI", href="https://mantine.dev/", is_external=True),
                mb="lg",
            ),
            mn.simple_grid(
                # Left column
                mn.stack(
                    mn.text("AI Tools:", fw="bold", size="md"),
                    mn.list_(
                        mn.list_.item(rx.link("Assistant", href="/assistant")),
                        mn.list_.item(
                            rx.link("Image Generator", href="/image-gallery")
                        ),
                        list_style_type="disc",
                        type="unordered",
                    ),
                    mn.text("Inputs:", fw="bold", size="md"),
                    mn.list_(
                        mn.list_.item(rx.link("Buttons & Icons", href="/buttons")),
                        mn.list_.item(rx.link("Input Components", href="/inputs")),
                        mn.list_.item(rx.link("Comboboxes", href="/comboboxes")),
                        mn.list_.item(
                            rx.link("Rich Text Editor (Tiptap)", href="/tiptap")
                        ),
                        list_style_type="disc",
                        type="unordered",
                    ),
                    mn.text("Data Display:", fw="bold", size="md"),
                    mn.list_(
                        mn.list_.item(rx.link("Data Display", href="/data-display")),
                        type="unordered",
                        list_style_type="disc",
                    ),
                ),
                # Right column
                mn.stack(
                    mn.text("Navigation:", fw="bold", size="md"),
                    mn.list_(
                        mn.list_.item(rx.link("Navigation", href="/navigation")),
                        mn.list_.item(
                            rx.link("Navigation Progress", href="/nprogress")
                        ),
                        mn.list_.item(rx.link("Nav Link", href="/nav-link")),
                        type="unordered",
                        list_style_type="disc",
                    ),
                    mn.text("Overlay:", fw="bold", size="md"),
                    mn.list_(
                        mn.list_.item(rx.link("HoverCard", href="/hover-card")),
                        mn.list_.item(rx.link("Tooltip", href="/tooltip")),
                        type="unordered",
                        list_style_type="disc",
                    ),
                    mn.text("Others:", fw="bold", size="md"),
                    mn.list_(
                        mn.list_.item(rx.link("Feedback Components", href="/feedback")),
                        mn.list_.item(
                            rx.link("Markdown Preview", href="/markdown-preview")
                        ),
                        mn.list_.item(rx.link("Modal", href="/modal")),
                        mn.list_.item(
                            rx.link("Navigation Progress", href="/nprogress")
                        ),
                        mn.list_.item(rx.link("Nav Link", href="/nav-link")),
                        mn.list_.item(
                            rx.link("Number Formatter", href="/number-formatter")
                        ),
                        mn.list_.item(rx.link("ScrollArea", href="/scroll-area")),
                        mn.list_.item(rx.link("Table", href="/table")),
                        type="unordered",
                        list_style_type="disc",
                    ),
                ),
                cols=2,
                spacing="md",
            ),
            spacing="md",
            mt="0",
            w="100%",
        ),
        size="lg",
        w="100%",
    )
