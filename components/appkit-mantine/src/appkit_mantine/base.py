"""Base classes for Mantine UI components in Reflex.

This module provides comprehensive base classes for all Mantine UI component wrappers,
eliminating code duplication and ensuring consistency across components.

Architecture:
    MantineComponentBase - Minimal base for any Mantine component
        ↓
    MantineLayoutComponentBase - Adds common layout and style props (w, m, p, display)
        ↓
    MantineInputComponentBase - Complete base for all input-like components
        ↓
    Specific Components (PasswordInput, Textarea, DateInput, NumberInput, etc.)

Example:
    Creating a new Mantine input component:
    ```python
    from appkit_ui.components.mantine_base import MantineInputComponentBase


    class MyCustomInput(MantineInputComponentBase):
        tag = "MyCustomInput"

        # Only define component-specific props here
        custom_prop: Var[str] = None
    ```

    All common props are inherited:
    - Input.Wrapper props (label, description, error, required, with_asterisk)
    - Visual variant props (variant, size, radius)
    - State props (value, default_value, placeholder, disabled, required)
    - HTML attributes (name, id, aria_label, max_length, min_length, auto_complete)
    - Section props (left_section, right_section, widths, pointer_events)
    - Mantine style props (w, maw, miw, m, mt, mb, ml, mr, mx, my)
    - Event handlers (on_change, on_focus, on_blur, on_key_down, on_key_up, on_input)
"""

from __future__ import annotations

from typing import Any, Final, Literal

import reflex as rx
from reflex.assets import asset
from reflex.event import EventHandler
from reflex.vars.base import Var

public_provider_path = "$/public/" + asset(path="mantine_provider.js", shared=True)

MANTINE_LIBARY: Final[str] = "@mantine/core"
MANTINE_VERSION: Final[str] = "8.3.10"


MantineSize = Literal["xs", "sm", "md", "lg", "xl"]
MantineNumberSize = MantineSize | str | int
MantineDisplay = Literal[
    "none", "inline", "block", "inline-block", "flex", "inline-flex", "grid"
]
MantinePosition = Literal["static", "absolute", "relative", "fixed", "sticky"]
MantineTextAlign = Literal["left", "center", "right", "justify"]
MantineFontStyle = Literal["normal", "italic"]
MantineTextTransform = Literal["capitalize", "uppercase", "lowercase", "none"]
MantineBackgroundRepeat = Literal[
    "no-repeat", "repeat", "repeat-x", "repeat-y", "round", "space"
]
MantineBackgroundAttachment = Literal["scroll", "fixed", "local"]


class MemoizedMantineProvider(rx.Component):
    library = public_provider_path
    tag = "MemoizedMantineProvider"
    is_default = True


class MantineComponentBase(rx.Component):
    """Base class for all Mantine UI components.

    Provides the core Mantine library configuration and CSS import.
    All Mantine components should inherit from this base class or one of its subclasses.

    Example:
        ```python
        class CustomMantineComponent(MantineComponentBase):
            tag = "CustomComponent"
            # Component-specific props here
        ```
    """

    library = f"{MANTINE_LIBARY}@{MANTINE_VERSION}"

    def _get_custom_code(self) -> str:
        return """import '@mantine/core/styles.css';

// Fix: Mantine shared portal node is a block-level div appended to <body>
// that participates in document flow, breaking page layout even when
// modals/drawers are closed. Remove it from flow with position: fixed.
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.setAttribute('data-mantine-portal-fix', 'true');
  style.textContent = `
    div[data-portal="true"] {
      position: fixed !important;
      top: 0;
      left: 0;
      width: 0;
      height: 0;
      overflow: visible;
      pointer-events: none;
    }
    div[data-portal="true"] > * {
      pointer-events: auto;
    }
  `;
  if (!document.querySelector('style[data-mantine-portal-fix]')) {
    document.head.appendChild(style);
  }
}"""

    @staticmethod
    def _get_app_wrap_components() -> dict[tuple[int, str], rx.Component]:
        return {
            (44, "MantineProvider"): MemoizedMantineProvider.create(),
        }


class MantineProvider(MantineComponentBase):
    """Mantine Provider - Required wrapper for all Mantine components.

    MantineProvider must be rendered at the root of your application.
    It provides theme context and manages color scheme.

    This component automatically respects Reflex's color mode system.

    Example:
        ```python
        def index():
            return mantine_provider(
                mantine_input(placeholder="Search..."),
                theme={"primaryColor": "blue"},
            )
        ```
    """

    # Use the custom provider that respects color mode
    library = public_provider_path
    tag = "MantineProvider"
    is_default = True

    # Theme configuration
    theme: Var[dict]

    # Color scheme settings - Note: forceColorScheme is managed automatically
    # default_color_scheme: Var[Literal["light", "dark", "auto"]]

    # CSS variables
    css_variables_selector: Var[str]
    with_css_variables: Var[bool]

    # Class names
    class_names_prefix: Var[str]
    with_static_classes: Var[bool]
    with_global_classes: Var[bool]


class MantineLayoutComponentBase(MantineComponentBase):
    """Base class for layout components with common style props."""

    # Width and Height
    w: Var[MantineNumberSize] = None
    h: Var[MantineNumberSize] = None
    miw: Var[MantineNumberSize] = None
    maw: Var[MantineNumberSize] = None
    mih: Var[MantineNumberSize] = None
    mah: Var[MantineNumberSize] = None

    # Margins
    m: Var[MantineNumberSize] = None
    my: Var[MantineNumberSize] = None
    mx: Var[MantineNumberSize] = None
    mt: Var[MantineNumberSize] = None
    mb: Var[MantineNumberSize] = None
    ml: Var[MantineNumberSize] = None
    mr: Var[MantineNumberSize] = None

    # Paddings
    p: Var[MantineNumberSize] = None
    py: Var[MantineNumberSize] = None
    px: Var[MantineNumberSize] = None
    pt: Var[MantineNumberSize] = None
    pb: Var[MantineNumberSize] = None
    pl: Var[MantineNumberSize] = None
    pr: Var[MantineNumberSize] = None

    # Display and Position
    display: Var[MantineDisplay] = None
    pos: Var[MantinePosition] = None
    top: Var[MantineNumberSize] = None
    left: Var[MantineNumberSize] = None
    bottom: Var[MantineNumberSize] = None
    right: Var[MantineNumberSize] = None
    inset: Var[MantineNumberSize] = None

    # Background and Color
    bg: Var[str] = None
    c: Var[str] = None
    opacity: Var[str | int] = None

    # Typography
    ff: Var[str] = None
    fz: Var[MantineNumberSize] = None
    fw: Var[str | int] = None
    lts: Var[MantineNumberSize] = None
    ta: Var[MantineTextAlign] = None
    lh: Var[MantineNumberSize] = None
    fs: Var[MantineFontStyle] = None
    tt: Var[MantineTextTransform] = None
    td: Var[str] = None

    # Border
    bd: Var[str] = None

    # Background (Extended)
    bgsz: Var[MantineNumberSize] = None
    bgp: Var[str] = None
    bgr: Var[MantineBackgroundRepeat] = None
    bga: Var[MantineBackgroundAttachment] = None

    # Other
    flex: Var[str | int] = None
    hidden_from: Var[MantineSize] = None
    visible_from: Var[MantineSize] = None


class MantineOverlayComponentBase(MantineLayoutComponentBase):
    """Base class for overlay components (Modal, Drawer).

    Provides common props for overlay-based components:
    - Visibility state (opened, on_close)
    - Behavior (close_on_click_outside, close_on_escape, lock_scroll, trap_focus)
    - Visuals (overlay_props, transition_props, radius, shadow)
    """

    # Core Props
    opened: Var[bool] = None
    """Controls overlay visibility (required)."""

    keep_mounted: Var[bool] = None
    """Whether to keep overlay mounted in DOM when closed."""

    title: Var[str] = None
    """Title text displayed in header."""

    # Behavior
    close_on_click_outside: Var[bool] = None
    """Whether to close overlay on click outside."""

    close_on_escape: Var[bool] = None
    """Whether to close overlay on Escape key."""

    lock_scroll: Var[bool] = None
    """Whether to lock body scroll when open."""

    trap_focus: Var[bool] = None
    """Whether to trap focus inside overlay."""

    return_focus: Var[bool] = None
    """Whether to return focus to trigger element on close."""

    within_portal: Var[bool] = None
    """Whether to render inside portal."""

    # Visual/Content
    with_overlay: Var[bool] = None
    """Whether to show overlay."""

    with_close_button: Var[bool] = None
    """Whether to show close button."""

    # Styling
    radius: Var[MantineNumberSize] = None
    """Border radius."""

    shadow: Var[MantineNumberSize] = None
    """Box shadow."""

    size: Var[MantineNumberSize] = None
    """Size (width for Modal/Drawer)."""

    padding: Var[MantineNumberSize] = None
    """Content padding."""

    z_index: Var[int | str] = None
    """CSS z-index."""

    id: Var[str] = None
    """Element ID."""

    # Configuration Props
    overlay_props: Var[dict[str, Any]] = None
    """Props for Overlay component."""

    transition_props: Var[dict[str, Any]] = None
    """Props for Transition component."""

    close_button_props: Var[dict[str, Any]] = None
    """Props for CloseButton component."""

    portal_props: Var[dict[str, Any]] = None
    """Props for Portal component."""

    remove_scroll_props: Var[dict[str, Any]] = None
    """Props for react-remove-scroll."""

    scroll_area_component: Var[Any] = None
    """Custom scroll area component."""

    # Events
    on_close: EventHandler[rx.event.no_args_event_spec] = None
    """Called when overlay should close."""

    on_enter_transition_end: EventHandler[rx.event.no_args_event_spec] = None
    """Called when enter transition finishes."""

    on_exit_transition_end: EventHandler[rx.event.no_args_event_spec] = None
    """Called when exit transition finishes."""

    _rename_props = {
        "close_on_click_outside": "closeOnClickOutside",
        "close_on_escape": "closeOnEscape",
        "keep_mounted": "keepMounted",
        "lock_scroll": "lockScroll",
        "trap_focus": "trapFocus",
        "return_focus": "returnFocus",
        "within_portal": "withinPortal",
        "with_overlay": "withOverlay",
        "with_close_button": "withCloseButton",
        "overlay_props": "overlayProps",
        "transition_props": "transitionProps",
        "close_button_props": "closeButtonProps",
        "portal_props": "portalProps",
        "remove_scroll_props": "removeScrollProps",
        "scroll_area_component": "scrollAreaComponent",
        "on_close": "onClose",
        "on_enter_transition_end": "onEnterTransitionEnd",
        "on_exit_transition_end": "onExitTransitionEnd",
        "z_index": "zIndex",
    }


class MantineInputComponentBase(MantineLayoutComponentBase):
    """Comprehensive base class for all Mantine input-like components.

    This base class includes all common properties shared across Mantine input
    components:
    - Input.Wrapper props for labels, descriptions, and error messages
    - Visual variant props for styling (variant, size, radius)
    - State management props (value, default_value, placeholder, disabled)
    - HTML input attributes (name, id, aria-label, etc.)
    - Left and right section props for icons or controls
    - Mantine style system props (width, margin)
    - Standard input event handlers

    Components inheriting from this base only need to define their unique props.

    Supported components:
    - PasswordInput (adds visible, on_visibility_change)
    - Textarea (adds autosize, min_rows, max_rows, resize)
    - DateInput (adds value_format, date_parser, min_date, max_date, clearable)
    - NumberInput (adds min, max, step, decimal_scale, prefix, suffix)
    - And more...

    Example:
        ```python
        class PasswordInput(MantineInputComponentBase):
            tag = "PasswordInput"

            # Only password-specific props
            visible: Var[bool] = None
            on_visibility_change: EventHandler[lambda visible: [visible]]
        ```

    Prop Aliasing:
        Python snake_case props are automatically converted to React camelCase:
        - default_value → defaultValue
        - with_asterisk → withAsterisk
        - left_section → leftSection
        - right_section → rightSection
        - left_section_width → leftSectionWidth
        - right_section_width → rightSectionWidth
        - left_section_pointer_events → leftSectionPointerEvents
        - right_section_pointer_events → rightSectionPointerEvents
        - max_length → maxLength
        - min_length → minLength
        - auto_complete → autoComplete
        - aria_label → aria-label
    """

    # Prop aliasing for camelCase React props
    _rename_props = {
        "default_value": "defaultValue",
        "with_asterisk": "withAsterisk",
        "left_section": "leftSection",
        "right_section": "rightSection",
        "left_section_width": "leftSectionWidth",
        "right_section_width": "rightSectionWidth",
        "left_section_pointer_events": "leftSectionPointerEvents",
        "right_section_pointer_events": "rightSectionPointerEvents",
        "max_length": "maxLength",
        "min_length": "minLength",
        "auto_complete": "autoComplete",
        "aria_label": "aria-label",
    }

    # ========================================================================
    # Input.Wrapper Props - Label, description, error handling
    # ========================================================================

    label: Var[str] = None
    """Label text displayed above the input."""

    description: Var[str] = None
    """Description text displayed below the label."""

    error: Var[bool | str] = None
    """Error state (boolean) or error message (string) displayed below input."""

    required: Var[bool] = None
    """If true, adds asterisk to label and sets aria-required."""

    with_asterisk: Var[bool] = None
    """If true, adds asterisk to label without setting required attribute."""

    # ========================================================================
    # Visual Variant Props - Styling and appearance
    # ========================================================================

    variant: Var[Literal["default", "filled", "unstyled"]] = None
    """Input visual variant: default (bordered), filled (background),
    unstyled (no styles)."""

    size: Var[MantineSize] = None
    """Input size affecting height, padding, and font size."""

    radius: Var[MantineNumberSize] = None
    """Border radius size."""

    pointer: Var[bool]
    """Changes cursor to pointer"""

    # ========================================================================
    # State Props - Value, placeholder, disabled state
    # ========================================================================

    value: Var[str | int | float | list | None] = None
    """Current input value (controlled component)."""

    default_value: Var[str | float | int | list | None] = None
    """Default input value (uncontrolled component)."""

    placeholder: Var[str] = None
    """Placeholder text when input is empty."""

    disabled: Var[bool] = None
    """If true, input is disabled and cannot be edited."""

    read_only: Var[bool] = None
    """If true, input is read-only (can be focused but not edited)."""

    # ========================================================================
    # HTML Input Attributes - Standard input element attributes
    # ========================================================================

    name: Var[str] = None
    """HTML name attribute for form submission."""

    id: Var[str] = None
    """HTML id attribute."""

    aria_label: Var[str] = None
    """Accessibility label for screen readers."""

    maxlength: Var[int | str] = None
    """Maximum number of characters allowed."""

    minlength: Var[int | str] = None
    """Minimum number of characters required."""

    autocapitalize: Var[str] = None
    """HTML autocapitalize attribute (none, sentences, words, characters)."""

    autocomplete: Var[str] = None
    """HTML autocomplete attribute (e.g., 'off', 'email', 'current-password')."""

    type: Var[str] = None
    """HTML input type (text, email, tel, url, password, etc.)."""

    pattern: Var[str] = None
    """HTML5 pattern validation regex."""

    input_mode: Var[str] = None
    """Input mode for mobile keyboards (text, numeric, decimal, tel, email, url)."""

    # ========================================================================
    # Section Props - Left and right sections for icons or controls
    # ========================================================================

    left_section: Var[Any] = None
    """Content displayed on the left side of input (icons, text, etc.)."""

    right_section: Var[Any] = None
    """Content displayed on the right side of input (icons, buttons, etc.)."""

    left_section_width: Var[int | str] = None
    """Width of the left section (px or rem)."""

    right_section_width: Var[int | str] = None
    """Width of the right section (px or rem)."""

    left_section_pointer_events: Var[str] = None
    """CSS pointer-events for left section (none, auto, all)."""

    right_section_pointer_events: Var[str] = None
    """CSS pointer-events for right section (none, auto, all)."""

    # ========================================================================
    # Event Handlers - Standard input events
    # ========================================================================

    on_change: EventHandler[rx.event.input_event] = None
    """Called when input value changes (receives event with event.target.value)."""

    on_focus: EventHandler[rx.event.input_event] = None
    """Called when input receives focus."""

    on_blur: EventHandler[rx.event.input_event] = None
    """Called when input loses focus."""

    on_key_down: EventHandler[rx.event.key_event] = None
    """Called when key is pressed down."""

    on_key_up: EventHandler[rx.event.key_event] = None
    """Called when key is released."""

    on_input: EventHandler[rx.event.input_event] = None
    """Called on input event (fires before on_change)."""
