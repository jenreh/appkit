"""Data display component examples."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.navbar import app_navbar


@navbar_layout(
    route="/accordion",
    title="Accordion Examples",
    navbar=app_navbar(),
    with_header=False,
)
def accordion_examples() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Accordion", size="8"),
            rx.text("Expand and collapse content sections", size="3", color="gray"),
            mn.card(
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
                with_border=True,
                shadow="sm",
                padding="lg",
                radius="md",
                w="100%",
            ),
            spacing="6",
            width="100%",
            padding_y="8",
        ),
        size="3",
        width="100%",
    )


@navbar_layout(
    route="/avatar",
    title="Avatar Examples",
    navbar=app_navbar(),
    with_header=False,
)
def avatar_examples() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Avatar", size="8"),
            rx.text("User profile images and initials", size="3", color="gray"),
            mn.card(
                mn.stack(
                    rx.heading("Basic Avatars", size="4"),
                    rx.hstack(
                        mn.avatar(
                            src="https://avatars.githubusercontent.com/u/10353856?s=200&v=4",
                            radius="xl",
                        ),
                        mn.avatar(name="JS", color="blue", radius="xl"),
                        mn.avatar(radius="xl"),
                        spacing="4",
                    ),
                    rx.heading("Avatar Group", size="4"),
                    mn.avatar.group(
                        mn.avatar(
                            src="https://avatars.githubusercontent.com/u/10353856?s=200&v=4",
                            radius="xl",
                        ),
                        mn.avatar(name="AB", color="red", radius="xl"),
                        mn.avatar(name="+5", color="gray", radius="xl"),
                        spacing="sm",
                    ),
                    spacing="4",
                    width="100%",
                ),
                with_border=True,
                shadow="sm",
                padding="lg",
                radius="md",
                w="100%",
            ),
            spacing="6",
            width="100%",
            padding_y="8",
        ),
        size="3",
        width="100%",
    )


@navbar_layout(
    route="/card",
    title="Card Examples",
    navbar=app_navbar(),
    with_header=False,
)
def card_examples() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Card", size="8"),
            rx.text("Content container with shadow and border", size="3", color="gray"),
            mn.card(
                mn.card.section(
                    mn.image(
                        src="https://raw.githubusercontent.com/mantinedev/mantine/master/.demo/images/bg-8.png",
                        h=160,
                        alt="Norway",
                    ),
                ),
                mn.group(
                    rx.text("Norway Fjord Adventures", weight="medium"),
                    mn.button("On Sale", variant="light", color="blue", size="xs"),
                    justify="space-between",
                    mt="md",
                    mb="xs",
                ),
                rx.text(
                    "With Fjord Tours you can explore more of the magical fjord "
                    "landscapes with tours and activities on and around the "
                    "fjords of Norway",
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
                shadow="sm",
                padding="lg",
                radius="md",
                with_border=True,
                w="350px",
            ),
            spacing="6",
            width="100%",
            padding_y="8",
        ),
        size="3",
        width="100%",
    )


@navbar_layout(
    route="/image",
    title="Image Examples",
    navbar=app_navbar(),
    with_header=False,
)
def image_examples() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Image", size="8"),
            rx.text("Image with optional fallback", size="3", color="gray"),
            mn.card(
                mn.group(
                    mn.image(
                        src="https://raw.githubusercontent.com/mantinedev/mantine/master/.demo/images/bg-8.png",
                        w=200,
                        radius="md",
                        caption="My Image",
                    ),
                    mn.image(
                        src="invalid-src",
                        h=200,
                        w=200,
                        fallback_src="https://placehold.co/200x200?text=Placeholder",
                        radius="md",
                    ),
                    spacing="4",
                ),
                with_border=True,
                shadow="sm",
                padding="lg",
                radius="md",
                w="100%",
            ),
            spacing="6",
            width="100%",
            padding_y="8",
        ),
        size="3",
        width="100%",
    )


@navbar_layout(
    route="/indicator",
    title="Indicator Examples",
    navbar=app_navbar(),
    with_header=False,
)
def indicator_examples() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Indicator", size="8"),
            rx.text(
                "Display element at corner of another element", size="3", color="gray"
            ),
            mn.card(
                mn.group(
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
                    spacing="8",
                ),
                with_border=True,
                shadow="sm",
                padding="lg",
                radius="md",
                w="100%",
            ),
            spacing="6",
            width="100%",
            padding_y="8",
        ),
        size="3",
        width="100%",
    )


@navbar_layout(
    route="/timeline",
    title="Timeline Examples",
    navbar=app_navbar(),
    with_header=False,
)
def timeline_examples() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Timeline", size="8"),
            rx.text("Visual list of events", size="3", color="gray"),
            mn.card(
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
                with_border=True,
                shadow="sm",
                padding="lg",
                radius="md",
                w="100%",
            ),
            spacing="6",
            width="100%",
            padding_y="8",
        ),
        size="3",
        width="100%",
    )
