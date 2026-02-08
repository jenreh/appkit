"""Data display component examples."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar


@navbar_layout(
    route="/data-display",
    title="Data Display",
    navbar=app_navbar(),
    with_header=False,
)
def data_display_examples() -> rx.Component:
    """Consolidated data display components examples page."""
    return mn.container(
        mn.stack(
            mn.title("Data Display", order=1, size="xl"),
            mn.text(
                "Components for displaying data and content.",
                size="md",
                c="dimmed",
            ),
            example_box(
                "Basic Accordion",
                mn.accordion(
                    mn.accordion.item(
                        mn.accordion.control("Section 1"),
                        mn.accordion.panel("Content for section 1"),
                        value="1",
                    ),
                    mn.accordion.item(
                        mn.accordion.control("Section 2"),
                        mn.accordion.panel("Content for section 2"),
                        value="2",
                    ),
                    mn.accordion.item(
                        mn.accordion.control("Section 3"),
                        mn.accordion.panel("Content for section 3"),
                        value="3",
                    ),
                    default_value="1",
                    variant="separated",
                    radius="md",
                ),
            ),
            mn.simple_grid(
                example_box(
                    "Basic Avatars",
                    mn.group(
                        mn.avatar(
                            src="https://avatars.githubusercontent.com/u/10353856?s=200&v=4",
                            radius="xl",
                        ),
                        mn.avatar(name="JS", color="blue", radius="xl"),
                        mn.avatar(radius="xl"),
                    ),
                ),
                example_box(
                    "Avatar Group",
                    mn.avatar.group(
                        mn.avatar(
                            src="https://avatars.githubusercontent.com/u/10353856?s=200&v=4",
                            radius="xl",
                        ),
                        mn.avatar(name="AB", color="red", radius="xl"),
                        mn.avatar(name="+5", color="gray", radius="xl"),
                    ),
                ),
                cols=2,
                spacing="md",
            ),
            mn.simple_grid(
                example_box(
                    "Card with Image",
                    mn.card(
                        mn.card.section(
                            mn.image(
                                src="https://raw.githubusercontent.com/mantinedev/mantine/master/.demo/images/bg-8.png",
                                h=160,
                                alt="Norway",
                            )
                        ),
                        mn.group(
                            rx.text("Norway Fjord Adventures", weight="medium"),
                            mn.button(
                                "On Sale", variant="light", color="blue", size="xs"
                            ),
                            justify="space-between",
                            mt="md",
                            mb="xs",
                        ),
                        rx.text(
                            "With Fjord Tours you can explore more of the magical "
                            "fjord landscapes...",
                            size="2",
                            color="gray",
                        ),
                        mn.button(
                            "Book classic tour now",
                            variant="light",
                            color="blue",
                            full_width=True,
                            mt="md",
                            radius="md",
                        ),
                        radius="md",
                        with_border=True,
                        w="350px",
                    ),
                ),
                # Timeline
                example_box(
                    "Activity Timeline",
                    mn.timeline(
                        mn.timeline.item(
                            rx.text("Git repository created", size="2"),
                            title="New Branch",
                            bullet=rx.icon("git-branch", size=12),
                        ),
                        mn.timeline.item(
                            rx.text("Commited changes", size="2"),
                            title="Commit",
                            bullet=rx.icon("git-commit-horizontal", size=12),
                        ),
                        mn.timeline.item(
                            rx.text("Pull request created", size="2"),
                            title="Pull Request",
                            bullet=rx.icon("git-pull-request", size=12),
                            line_variant="dashed",
                        ),
                        mn.timeline.item(
                            rx.text("Deployed to production", size="2"),
                            title="Deployment",
                            bullet=rx.icon("rocket", size=12),
                        ),
                        active=1,
                        bullet_size=24,
                        line_width=2,
                    ),
                ),
                cols=2,
                spacing="md",
            ),
            mn.simple_grid(
                example_box(
                    "Standard Image",
                    mn.image(
                        src="https://raw.githubusercontent.com/mantinedev/mantine/master/.demo/images/bg-8.png",
                        radius="md",
                        caption="My Image",
                    ),
                ),
                example_box(
                    "With Fallback",
                    mn.image(
                        src="invalid-src",
                        h=200,
                        fallback_src="https://placehold.co/200x200?text=Placeholder",
                        radius="md",
                    ),
                ),
                cols=2,
                spacing="md",
            ),
            mn.simple_grid(
                example_box(
                    "Processing",
                    mn.center(
                        mn.indicator(
                            mn.avatar(
                                radius="xl",
                                size="lg",
                                src="https://avatars.githubusercontent.com/u/10353856?s=200&v=4",
                            ),
                            inline=True,
                            size=16,
                            processing=True,
                            color="red",
                        ),
                        p="md",
                    ),
                ),
                example_box(
                    "With Label",
                    mn.center(
                        mn.indicator(
                            mn.avatar(
                                radius="xl",
                                size="lg",
                                src="https://avatars.githubusercontent.com/u/10353856?s=200&v=4",
                            ),
                            inline=True,
                            label="New",
                            size=16,
                            color="blue",
                        ),
                        p="md",
                    ),
                ),
                cols=2,
                spacing="md",
            ),
            spacing="md",
            w="100%",
            mb="6rem",
        ),
        size="lg",
        w="100%",
    )
