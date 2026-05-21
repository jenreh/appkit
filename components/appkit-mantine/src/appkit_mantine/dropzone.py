"""Mantine Dropzone extension components."""

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MANTINE_VERSION, MantineLayoutComponentBase

DROPZONE_LIBRARY = f"@mantine/dropzone@{MANTINE_VERSION}"
REACT_DROPZONE_LIBRARY = "react-dropzone@^14.2.3"


class MantineDropzoneBase(MantineLayoutComponentBase):
    """Base class for Dropzone components."""

    library = DROPZONE_LIBRARY
    lib_dependencies: list[str] = [REACT_DROPZONE_LIBRARY]

    def _get_custom_code(self) -> str:
        return """import '@mantine/core/styles.css';
import '@mantine/dropzone/styles.css';"""


class Dropzone(MantineDropzoneBase):
    """Mantine Dropzone — file drag-and-drop zone.

    https://mantine.dev/x/dropzone/
    """

    tag = "Dropzone"

    _rename_props = {
        "accept_color": "acceptColor",
        "activate_on_click": "activateOnClick",
        "activate_on_drag": "activateOnDrag",
        "activate_on_keyboard": "activateOnKeyboard",
        "auto_focus": "autoFocus",
        "drag_events_bubbling": "dragEventsBubbling",
        "enable_pointer_events": "enablePointerEvents",
        "get_files_from_event": "getFilesFromEvent",
        "input_props": "inputProps",
        "loader_props": "loaderProps",
        "max_files": "maxFiles",
        "max_size": "maxSize",
        "on_drag_enter": "onDragEnter",
        "on_drag_leave": "onDragLeave",
        "on_drag_over": "onDragOver",
        "on_drop": "onDrop",
        "on_drop_any": "onDropAny",
        "on_file_dialog_cancel": "onFileDialogCancel",
        "on_file_dialog_open": "onFileDialogOpen",
        "on_reject": "onReject",
        "prevent_drop_on_document": "preventDropOnDocument",
        "reject_color": "rejectColor",
        "use_fs_access_api": "useFsAccessApi",
    }

    accept: Var[list[str] | dict] = None
    """Accepted MIME types or react-dropzone Accept object."""

    multiple: Var[bool] = None
    max_files: Var[int] = None
    max_size: Var[int] = None
    disabled: Var[bool] = None
    loading: Var[bool] = None
    name: Var[str] = None
    auto_focus: Var[bool] = None
    activate_on_click: Var[bool] = None
    activate_on_drag: Var[bool] = None
    activate_on_keyboard: Var[bool] = None
    drag_events_bubbling: Var[bool] = None
    enable_pointer_events: Var[bool] = None
    prevent_drop_on_document: Var[bool] = None
    use_fs_access_api: Var[bool] = None
    radius: Var[str | int] = None
    accept_color: Var[str] = None
    reject_color: Var[str] = None
    loader_props: Var[dict] = None

    on_drop: EventHandler[lambda files: [files]] = None
    on_reject: EventHandler[lambda file_rejections: [file_rejections]] = None
    on_drop_any: EventHandler[lambda files, rejections: [files, rejections]] = None
    on_drag_enter: EventHandler[rx.event.no_args_event_spec] = None
    on_drag_leave: EventHandler[rx.event.no_args_event_spec] = None
    on_file_dialog_open: EventHandler[rx.event.no_args_event_spec] = None
    on_file_dialog_cancel: EventHandler[rx.event.no_args_event_spec] = None


class DropzoneAccept(MantineDropzoneBase):
    """Mantine Dropzone.Accept — shown when dragging accepted files."""

    tag = "Dropzone.Accept"


class DropzoneReject(MantineDropzoneBase):
    """Mantine Dropzone.Reject — shown when dragging rejected files."""

    tag = "Dropzone.Reject"


class DropzoneIdle(MantineDropzoneBase):
    """Mantine Dropzone.Idle — shown in the default state."""

    tag = "Dropzone.Idle"


class DropzoneFullScreen(MantineDropzoneBase):
    """Mantine Dropzone.FullScreen — captures drops anywhere in browser."""

    tag = "Dropzone.FullScreen"

    _rename_props = {
        "portal_props": "portalProps",
        "within_portal": "withinPortal",
        "z_index": "zIndex",
    }

    active: Var[bool] = None
    within_portal: Var[bool] = None
    z_index: Var[str | int] = None
    portal_props: Var[dict] = None


class DropzoneNamespace(rx.ComponentNamespace):
    """Namespace for Dropzone components."""

    __call__ = staticmethod(Dropzone.create)
    accept = staticmethod(DropzoneAccept.create)
    reject = staticmethod(DropzoneReject.create)
    idle = staticmethod(DropzoneIdle.create)
    full_screen = staticmethod(DropzoneFullScreen.create)


dropzone = DropzoneNamespace()
