"""Styles for the app."""

import reflex as rx

accent_bg_color = rx.color("accent", 2)
accent_color = rx.color("accent", 3)
accent_text_color = rx.color("accent", 9)
border = f"1px solid {rx.color('gray', 5)}"
border_radius = "var(--radius-2)"
box_shadow = "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)"
box_shadow_right_light = "inset -5px -5px 15px -5px rgba(0, 0, 0, 0.1)"
box_shadow_right_dark = "inset -5px -5px 15px -5px rgba(0.9, 0.9, 0.9, 0.1)"
box_shadow_light = "0 1px 10px -0.5px rgba(0, 0, 0, 0.1)"
box_shadow_dark = "0 1px 10px -0.5px rgba(0.8, 0.8, 0.8, 0.1)"
content_max_width = "1280px"
gray_bg_color = rx.color("gray", 3)
max_width = "1480px"
sidebar_bg = rx.color("gray", 2)
text_color = rx.color("gray", 11)

markdown_style = {
    "code": lambda text: rx.code(text, color_scheme="gray"),
    "codeblock": lambda text, **props: rx.code_block(text, **props, margin_y="1em"),
    "a": lambda text, **props: rx.link(
        text,
        **props,
        font_weight="bold",
        text_decoration="underline",
        text_decoration_color=accent_text_color,
    ),
}

image_props = {
    "decoding": "auto",
    "loading": "eager",
    "vertical_align": "middle",
    "object_fit": "contain",
    "width": "100%",
    "height": ["400px", "500px", "650px", "850px"],
}

button_props = {
    "size": "2",
    "cursor": "pointer",
    "variant": "outline",
}

logo_font = {
    "font-family": "Major Mono Display",
    "font-weight": "400",
    "font-style": "normal",
}

base_stylesheets = [
    "https://fonts.googleapis.com/css2?family=Roboto+Flex:wght@400;500;600;700;800&display=swap",
    "https://fonts.googleapis.com/css2?family=Audiowide&family=Honk:SHLN@5&family=Major+Mono+Display&display=swap",
    "css/react-zoom.css",
    "css/styles.css",
    "css/arvato-theme.css",
]

base_style = {
    "font_family": "Roboto Flex",
    rx.icon: {
        "stroke_width": "1.5px",
    },
}
