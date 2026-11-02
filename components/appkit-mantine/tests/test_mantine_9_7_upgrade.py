"""Tests for the Mantine 9.7.3 upgrade — version pin, new props and components."""

from __future__ import annotations

import json

import reflex as rx

import appkit_mantine as mn
from appkit_mantine.base import MANTINE_VERSION, MantineComponentBase


def _props(component) -> set[str]:
    return {e.split(":", 1)[0] for e in component.render().get("props", [])}


def _tag(component) -> str:
    return component.render().get("name", "")


def test_version_pin() -> None:
    assert MANTINE_VERSION == "9.7.3"
    assert MantineComponentBase().library == "@mantine/core@9.7.3"
    assert mn.schedule.day_view(events=[]).library == "@mantine/schedule@9.7.3"


def test_json_viewer_library_and_props() -> None:
    comp = mn.json_viewer(value={"a": 1}, with_copy_button=True, default_expand_depth=2)
    assert comp.library == "@mantine/code-highlight@9.7.3"
    assert _tag(comp) == "JsonViewer"
    assert {"withCopyButton", "defaultExpandDepth"} <= _props(comp)


def test_toggle_props() -> None:
    comp = mn.toggle(default_active=True, auto_width=True, aria_label="Bold")
    assert _tag(comp) == "Toggle"
    assert {"defaultActive", "autoWidth"} <= _props(comp)


def test_toolbar_tree() -> None:
    comp = mn.toolbar(
        mn.toolbar.toggle_group(
            mn.toolbar.toggle_item("B", value="bold"),
            type="multiple",
            default_value=["bold"],
        ),
        mn.toolbar.divider(),
        orientation="vertical",
    )
    assert _tag(comp) == "Toolbar"
    assert "orientation" in _props(comp)
    group = mn.toolbar.toggle_group(type="single")
    assert _tag(group) == "Toolbar.ToggleGroup"
    assert "on_change" in group.get_event_triggers()
    assert _tag(mn.toolbar.toggle_item(value="x")) == "Toolbar.ToggleItem"


def test_tour_tree() -> None:
    comp = mn.tour(
        mn.tour.step("Hello", target="#a", title="One"),
        active=True,
        mode="beacon",
        default_step=-1,
    )
    assert _tag(comp) == "Tour"
    assert {"active", "mode", "defaultStep"} <= _props(comp)
    assert _tag(mn.tour.step(target="#a")) == "Tour.Step"
    triggers = comp.get_event_triggers()
    assert {"on_close", "on_step_change"} <= set(triggers)


def test_checkbox_radio_light_variant() -> None:
    assert "variant" in _props(mn.checkbox(variant="light"))
    assert "variant" in _props(mn.radio(variant="light"))


def test_tooltip_hide_detached_and_hover_card() -> None:
    assert "hideDetached" in _props(mn.tooltip(hide_detached=False))
    hc = mn.hover_card(interactive=True, close_on_escape=False, return_focus=True)
    assert {"interactive", "closeOnEscape", "returnFocus"} <= _props(hc)
    assert "on_dismiss" in hc.get_event_triggers()


def test_schedule_overlap_and_validation_props() -> None:
    week = mn.schedule.week_view(
        events=[],
        event_overlap_mode="cascade",
        event_overlap_raise_delay=300,
        prevent_event_overlap=True,
    )
    assert {"eventOverlapMode", "eventOverlapRaiseDelay"} <= _props(week)
    assert "preventEventOverlap" in _props(week)
    assert "on_event_placement_rejected" in week.get_event_triggers()


def test_tree_select_render_pill() -> None:
    pill = rx.Var("(node) => node.label")
    assert "renderPill" in _props(mn.tree_select(data=[], render_pill=pill))


# ---------------------------------------------------------------------------
# Notifications, AppShell resize, RichTextEditor image upload
# ---------------------------------------------------------------------------


def _script(event) -> str:
    return json.loads(str(event.args[0][1]))


def test_notifications_provider() -> None:
    comp = mn.notifications_provider(
        position="top-right", with_auto_close_progress=True
    )
    assert comp.library == "@mantine/notifications@9.7.3"
    assert _tag(comp) == "Notifications"
    assert {"position", "withAutoCloseProgress"} <= _props(comp)
    assert "window.mantineNotifications" in comp._get_custom_code()


def test_notifications_show_payload_is_camel_cased() -> None:
    script = _script(
        mn.notifications.show(
            "Saved", title="Done", with_auto_close_progress=True, auto_close=2000
        )
    )
    assert script.startswith("window.mantineNotifications.show(")
    assert '"withAutoCloseProgress": true' in script
    assert '"autoClose": 2000' in script
    assert '"message": "Saved"' in script


def test_notifications_update_hide_clean_promise() -> None:
    assert "update(" in _script(
        mn.notifications.update(
            "n1", message="x", loading=False, with_close_button=True
        )
    )
    assert 'hide("n1")' in _script(mn.notifications.hide("n1"))
    assert "clean()" in _script(mn.notifications.clean())
    assert "cleanQueue()" in _script(mn.notifications.clean_queue())
    script = _script(
        mn.notifications.promise(
            "fetch('/ping')",
            loading={"message": "wait"},
            success={"message": "ok"},
            error={"message": "bad"},
            id="p1",
        )
    )
    assert "promise((fetch('/ping'))," in script
    assert '"id": "p1"' in script


def test_app_shell_resizable() -> None:
    comp = mn.app_shell.resizable(
        navbar={"width": 280, "breakpoint": "sm"},
        resize_options={"navbar": {"min": 200, "max": 480}},
        initial_sizes={"navbar": 320},
    )
    assert _tag(comp) == "AppShellResizable"
    assert "app_shell_resizable_wrapper" in comp.library
    assert {"resizeOptions", "initialSizes", "navbar"} <= _props(comp)
    triggers = comp.get_event_triggers()
    assert {"on_resize", "on_resize_end", "on_collapse_change"} <= set(triggers)


def test_rich_text_editor_image_upload() -> None:
    comp = mn.rich_text_editor(
        image_upload_url="/upload",
        image_upload_field="file",
        control_groups=[["bold", "imageUpload"]],
    )
    assert {"imageUploadUrl", "imageUploadField", "controlGroups"} <= _props(comp)
    assert "on_image_upload_error" in comp.get_event_triggers()
    from appkit_mantine.tiptap import ToolbarControlGroup

    assert ToolbarControlGroup.UPLOAD.value == ["imageUpload"]


def test_portal_fix_does_not_override_component_pointer_events() -> None:
    """Tour's root sets pointer-events: none; the portal fix must not beat it."""
    code = MantineComponentBase()._get_custom_code()
    assert ':where(div[data-portal="true"]) > :where(*)' in code
    assert 'div[data-portal="true"] > *' not in code
