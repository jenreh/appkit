import reflex as rx

splash_container: dict[str, str] = {
    "background": (
        f"linear-gradient(99deg, {rx.color('blue', 4)},"
        f" {rx.color('pink', 3)}, {rx.color('mauve', 3)})"
    ),
    "background_size": "cover",
    "background_position": "center",
    "background_repeat": "no-repeat",
    "min_height": "100vh",
    "width": "100%",
}

dialog_styles = {
    "max_width": "540px",
    "padding": "1.5em",
    "border": f"2px solid {rx.color('accent', 9)}",
    "border_radius": "25px",
}

label_styles = {
    "align": "center",
    "spacing": "1",
    "margin_bottom": "3px",
}
