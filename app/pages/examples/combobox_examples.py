import json

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar


class ComboboxExamplesState(rx.State):
    """State for Combobox examples."""

    # Select
    select_simple: str = ""
    select_custom: str = ""

    # MultiSelect
    multi_simple: list[str] = []
    multi_grouped: list[str] = []

    # Autocomplete
    auto_simple: str = ""
    auto_employee: str = ""

    # RichSelect
    rich_value: str = ""

    # TreeSelect / PillsInput
    tree_value: str = ""
    pills_input_value: str = ""

    def set_value(self, field: str, value: str | list[str]) -> None:
        """Generic setter for state values."""
        setattr(self, field, value)


TREE_SELECT_DATA = [
    {
        "label": "Frontend",
        "value": "frontend",
        "children": [
            {"label": "React", "value": "react"},
            {"label": "Vue", "value": "vue"},
            {"label": "Svelte", "value": "svelte"},
        ],
    },
    {
        "label": "Backend",
        "value": "backend",
        "children": [
            {"label": "FastAPI", "value": "fastapi"},
            {"label": "Django", "value": "django"},
        ],
    },
]


def _render_select_section() -> rx.Component:
    """Render Select examples."""
    # Data for custom rendering
    align_data = [
        {"value": "left", "label": "Left"},
        {"value": "center", "label": "Center"},
        {"value": "right", "label": "Right"},
        {"value": "justify", "label": "Justify"},
    ]

    # JS function for custom option rendering
    render_option_js = """
    ( { option, checked } ) => {
        const icons = { left: '⬅️', center: '↔️', right: '➡️', justify: '↕️' };
        return (
            <div style={{display: 'flex', alignItems: 'center', width: '100%'}}>
                <span style={{marginRight: 8}}>{icons[option.value]}</span>
                <span>{option.label}</span>
                {checked ? <span style={{marginLeft: 'auto'}}>✓</span> : null}
            </div>
        )
    }
    """

    return mn.stack(
        mn.title("Select", order=3),
        mn.simple_grid(
            example_box(
                "Basic Usage",
                mn.select(
                    label="Choose a framework",
                    placeholder="Pick one",
                    data=["React", "Angular", "Vue", "Svelte"],
                    value=ComboboxExamplesState.select_simple,
                    on_change=lambda v: ComboboxExamplesState.set_value(
                        "select_simple", v
                    ),
                    searchable=True,
                    clearable=True,
                ),
                ComboboxExamplesState.select_simple,
            ),
            example_box(
                "Custom Option Rendering",
                mn.select(
                    label="Text Alignment",
                    placeholder="Select alignment",
                    data=align_data,
                    value=ComboboxExamplesState.select_custom,
                    on_change=lambda v: ComboboxExamplesState.set_value(
                        "select_custom", v
                    ),
                    render_option=rx.Var(render_option_js, _var_type=str),
                ),
                ComboboxExamplesState.select_custom,
            ),
            cols=2,
            width="100%",
        ),
        width="100%",
    )


def _render_multi_select_section() -> rx.Component:
    """Render MultiSelect examples."""
    grouped_data = [
        {"group": "Frontend", "items": ["React", "Vue", "Svelte"]},
        {"group": "Backend", "items": ["Django", "FastAPI", "Express"]},
        {"group": "Mobile", "items": ["React Native", "Flutter"]},
    ]

    return mn.stack(
        mn.title("MultiSelect", order=3),
        mn.simple_grid(
            example_box(
                "Basic Usage",
                mn.multi_select(
                    label="Favorite Libraries",
                    placeholder="Select libraries",
                    data=["React", "Angular", "Vue", "Svelte", "Solid"],
                    value=ComboboxExamplesState.multi_simple,
                    on_change=lambda v: ComboboxExamplesState.set_value(
                        "multi_simple", v
                    ),
                    searchable=True,
                    clearable=True,
                ),
                ComboboxExamplesState.multi_simple,
            ),
            example_box(
                "Grouped Options",
                mn.multi_select(
                    label="Tech Stack",
                    placeholder="Select technologies",
                    data=grouped_data,
                    value=ComboboxExamplesState.multi_grouped,
                    on_change=lambda v: ComboboxExamplesState.set_value(
                        "multi_grouped", v
                    ),
                    searchable=True,
                    max_values=3,
                ),
                ComboboxExamplesState.multi_grouped,
            ),
            cols=2,
            width="100%",
        ),
        width="100%",
    )


def _render_autocomplete_section() -> rx.Component:
    """Render Autocomplete examples."""
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
    }

    render_option_js = f"""
    ({{ option }}) => {{
        const usersData = {json.dumps(users_data)};
        const user = usersData[option.value];
        if (!user) return option.value;
        return (
            <div style={{{{ display: 'flex', gap: '12px', alignItems: 'center' }}}}>
                <img
                    src={{user.image}}
                    style={{{{ width: '36px', height: '36px', borderRadius: '50%' }}}}
                    alt={{option.value}}
                />
                <div>
                    <div style={{{{ fontSize: '14px' }}}}>{{option.value}}</div>
                    <div style={{{{ fontSize: '12px', opacity: 0.5 }}}}>
                        {{user.email}}
                    </div>
                </div>
            </div>
        );
    }}
    """

    return mn.stack(
        mn.title("Autocomplete", order=3),
        mn.simple_grid(
            example_box(
                "Basic Usage",
                mn.autocomplete(
                    label="Framework",
                    placeholder="Start typing...",
                    data=["React", "Angular", "Vue", "Svelte"],
                    value=ComboboxExamplesState.auto_simple,
                    on_change=lambda v: ComboboxExamplesState.set_value(
                        "auto_simple", v
                    ),
                ),
                ComboboxExamplesState.auto_simple,
            ),
            example_box(
                "Custom Option Rendering",
                mn.autocomplete(
                    label="Employee Search",
                    placeholder="Search employee...",
                    data=list(users_data.keys()),
                    value=ComboboxExamplesState.auto_employee,
                    on_change=lambda v: ComboboxExamplesState.set_value(
                        "auto_employee", v
                    ),
                    render_option=rx.Var(render_option_js, _var_type=str),
                    max_dropdown_height=300,
                ),
                ComboboxExamplesState.auto_employee,
            ),
            cols=2,
            width="100%",
        ),
        spacing="4",
        width="100%",
    )


def _render_rich_select_section() -> rx.Component:
    """Render RichSelect examples."""
    data = [
        {
            "value": "apples",
            "emoji": "🍎",
            "label": "Apples",
            "description": "Crisp and refreshing fruit",
        },
        {
            "value": "bananas",
            "emoji": "🍌",
            "label": "Bananas",
            "description": "Naturally sweet and potassium-rich fruit",
        },
        {
            "value": "broccoli",
            "emoji": "🥦",
            "label": "Broccoli",
            "description": "Nutrient-packed green vegetable",
            "disabled": True,
        },
    ]

    def render_row(row: dict) -> rx.Component:
        return mn.group(
            mn.text(row.get("emoji", ""), width="24px"),
            mn.stack(
                mn.text(row["label"], fw="bold"),
                mn.text(row.get("description", ""), c="gray"),
                align_items="start",
                spacing="1",
            ),
            spacing="3",
        )

    return mn.stack(
        mn.title("Rich Select", order=3),
        mn.simple_grid(
            example_box(
                "Rich Option Content",
                mn.rich_select(
                    mn.rich_select.map(
                        data,
                        renderer=render_row,
                    ),
                    value=ComboboxExamplesState.rich_value,
                    on_change=lambda v: ComboboxExamplesState.set_value(
                        "rich_value", v
                    ),
                    placeholder="Pick a food",
                    searchable=True,
                    clearable=True,
                ),
                ComboboxExamplesState.rich_value,
            ),
            cols=2,  # Only one complex example needed for rich select
            width="100%",
        ),
        width="100%",
    )


def _render_tree_and_pills_section() -> rx.Component:
    """Render TreeSelect, Pill, and PillsInput examples."""
    return mn.stack(
        mn.title("TreeSelect & Pills", order=3),
        mn.simple_grid(
            example_box(
                "TreeSelect",
                mn.tree_select(
                    label="Project area",
                    placeholder="Pick a nested option",
                    data=TREE_SELECT_DATA,
                    value=ComboboxExamplesState.tree_value,
                    on_change=lambda v: ComboboxExamplesState.set_value(
                        "tree_value", v
                    ),
                    searchable=True,
                    clearable=True,
                    with_lines=True,
                    default_expand_all=True,
                ),
                ComboboxExamplesState.tree_value,
            ),
            example_box(
                "Pill Group",
                mn.pill.group(
                    mn.pill("Design", with_remove_button=True),
                    mn.pill("Build", color="blue"),
                    mn.pill("Review", disabled=True),
                ),
            ),
            example_box(
                "PillsInput",
                mn.pills_input(
                    mn.pill.group(
                        mn.pill("React", with_remove_button=True),
                        mn.pill("FastAPI", with_remove_button=True),
                        mn.pills_input.field(
                            placeholder="Add tag",
                            value=ComboboxExamplesState.pills_input_value,
                            on_change=lambda v: ComboboxExamplesState.set_value(
                                "pills_input_value", v
                            ),
                        ),
                    ),
                    label="Technology tags",
                    description="Pills can be mixed with an input field.",
                ),
                ComboboxExamplesState.pills_input_value,
            ),
            cols=2,
            width="100%",
        ),
        width="100%",
    )


@navbar_layout(
    route="/comboboxes",
    title="Combobox Examples",
    navbar=app_navbar(),
    with_header=False,
)
def combobox_examples() -> rx.Component:
    """Consolidated page for Combobox-like components."""
    return mn.container(
        mn.stack(
            mn.title("Combobox Examples", order=1),
            mn.text(
                "Combined examples for Select, MultiSelect, "
                "Autocomplete, and RichSelect.",
                size="lg",
                c="gray",
            ),
            rx.link(
                "← Back to Home",
                href="/",
                size="3",
            ),
            _render_select_section(),
            _render_multi_select_section(),
            _render_autocomplete_section(),
            _render_rich_select_section(),
            _render_tree_and_pills_section(),
            w="100%",
            p="9px",
        ),
        size="lg",
        w="100%",
        mb="6rem",
    )
