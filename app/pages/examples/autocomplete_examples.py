import json

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.navbar import app_navbar


class AutocompleteState(rx.State):
    """State for autocomplete component."""

    selected_employee: str = ""

    def handle_option_submit(self, value: str) -> None:
        """Handle when an option is selected."""
        self.selected_employee = value

    def set_selected_employee(self, value: str) -> None:
        """Set the selected employee."""
        self.selected_employee = value


class LibraryState(rx.State):
    """State for library autocomplete."""

    selected_library: str = ""

    # Grouped data structure
    grouped_data = [
        {"group": "Frontend", "items": ["React", "Vue", "Svelte"]},
        {"group": "Backend", "items": ["Django", "FastAPI", "Express"]},
    ]

    def set_selected_library(self, value: str) -> None:
        """Set the selected library."""
        self.selected_library = value


class AutoState(rx.State):
    value: str = ""

    def set_value(self, v: str) -> None:
        self.value = v


def groups_example() -> rx.Component:
    grouped_data = [
        {"group": "Frontend", "items": ["React", "Vue", "Svelte"]},
        {"group": "Backend", "items": ["Django", "FastAPI", "Express"]},
    ]

    return rx.vstack(
        rx.heading("Grouped data", size="4"),
        mn.autocomplete(
            data=grouped_data,
            label="Your favorite library",
            placeholder="Pick value or enter anything",
            on_change=LibraryState.set_selected_library,
        ),
        rx.cond(
            LibraryState.selected_library != "",
            rx.text(
                f"You selected: {LibraryState.selected_library}",
                size="4",
                weight="bold",
                color="blue",
            ),
        ),
        spacing="4",
        align="stretch",
        width="100%",
        max_width="500px",
    )


def render_options_example() -> rx.Component:
    users_data = {
        "Emily Johnson": {
            "image": "https://raw.githubusercontent.com/mantinedev/mantine/master/.demo/avatars/avatar-7.png",
            "email": "emily92@gmail.com",
        },
        "Ava Rodriguez": {
            "image": "https://raw.githubusercontent.com/mantinedev/mantine/master/.demo/avatars/avatar-8.png",
            "email": "ava_rose@gmail.com",
        },
        "Olivia Chen": {
            "image": "https://raw.githubusercontent.com/mantinedev/mantine/master/.demo/avatars/avatar-4.png",
            "email": "livvy_globe@gmail.com",
        },
        "Ethan Barnes": {
            "image": "https://raw.githubusercontent.com/mantinedev/mantine/master/.demo/avatars/avatar-1.png",
            "email": "ethan_explorer@gmail.com",
        },
        "Mason Taylor": {
            "image": "https://raw.githubusercontent.com/mantinedev/mantine/master/.demo/avatars/avatar-2.png",
            "email": "mason_musician@gmail.com",
        },
    }

    render_option_js = rx.Var(
        """
        ({ option }) => {
            const usersData = """
        + json.dumps(users_data)
        + """;
            return (
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                    <img
                        src={usersData[option.value].image}
                        style={{
                            width: '36px',
                            height: '36px',
                            borderRadius: '50%'
                        }}
                        alt={option.value}
                    />
                    <div>
                        <div style={{ fontSize: '14px' }}>{option.value}</div>
                        <div style={{ fontSize: '12px', opacity: 0.5 }}>
                            {usersData[option.value].email}
                        </div>
                    </div>
                </div>
            );
        }
        """
    )

    return rx.container(
        rx.vstack(
            rx.heading("render_option Example", size="4"),
            mn.autocomplete(
                data=list(users_data),
                render_option=render_option_js,
                max_dropdown_height=300,
                label="Employee of the month",
                placeholder="Search for employee",
                on_change=AutocompleteState.set_selected_employee,
                on_option_submit=AutocompleteState.handle_option_submit,
            ),
            rx.cond(
                AutocompleteState.selected_employee != "",
                rx.text(
                    f"Selected: {AutocompleteState.selected_employee}",
                    size="4",
                    color="green",
                ),
            ),
            spacing="4",
            align="stretch",
            width="100%",
            max_width="500px",
        ),
        padding="4",
    )


@navbar_layout(
    route="/autocomplete",
    title="Autocomplete Examples",
    navbar=app_navbar(),
    with_header=False,
)
def autocomplete_examples() -> rx.Component:
    # Employees dict keyed by an id; values are dicts with name/email/avatar
    return rx.container(
        rx.color_mode.button(position="top-right"),
        rx.vstack(
            rx.heading("Autocomplete Examples", size="9"),
            rx.text(
                "Comprehensive examples of Autocomplete component",
                size="4",
                color="gray",
            ),
            rx.link(
                "← Back to Home",
                href="/",
                size="3",
            ),
            # Keep the original two example cards in a grid
            rx.grid(
                rx.card(
                    rx.heading("Basic Autocomplete", size="4"),
                    mn.autocomplete(
                        label="Search",
                        data=[
                            {"value": "React"},
                            {"value": "Angular"},
                            {"value": "Vue", "disabled": True},
                            {"value": "Svelte"},
                        ],
                        value=AutoState.value,
                        on_change=AutoState.set_value,
                    ),
                    rx.text("Value: ", AutoState.value, margin_top="12px"),
                    spacing="2",
                    width="100%",
                ),
                rx.card(
                    rx.heading(
                        "Autocomplete with clearable",
                        size="4",
                    ),
                    mn.autocomplete(
                        label="Search",
                        data=[
                            "React",
                            "Vue",
                            "Svelte",
                            "Angular",
                            "Solid",
                            "Ember",
                            "Preact",
                            "JavaScript",
                            "TypeScript",
                            "Python",
                            "Ruby",
                            "Rust",
                        ],
                        select_first_option_on_change=True,
                        clearable=True,
                        value=AutoState.value,
                        on_change=AutoState.set_value,
                    ),
                    rx.text("Value: ", AutoState.value, margin_top="12px"),
                    spacing="2",
                    width="100%",
                ),
                # New employee autocomplete example (full-width card)
                rx.card(render_options_example()),
                rx.card(groups_example()),
                columns="2",
                spacing="4",
                width="100%",
            ),
            spacing="6",
            width="100%",
            padding_y="8",
        ),
        size="3",
        width="100%",
    )
