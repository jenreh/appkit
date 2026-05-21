"""Mantine Modals Manager extension components."""

from typing import Any

from reflex.vars.base import Var

from appkit_mantine.base import MANTINE_VERSION, MantineComponentBase

MODALS_LIBRARY = f"@mantine/modals@{MANTINE_VERSION}"


class ModalsProvider(MantineComponentBase):
    """Mantine ModalsProvider — wraps app for programmatic modal management.

    https://mantine.dev/x/modals/

    Usage:
        Wrap your app (or a subtree) with this component. Then open modals
        imperatively from state using rx.call_script with the modals API.
    """

    library = MODALS_LIBRARY

    tag = "ModalsProvider"
    is_default = False

    modal_props: Var[dict[str, Any]] = None
    """Default props passed to all modals."""

    labels: Var[dict[str, Any]] = None
    """Default confirm/cancel button labels: {confirm: str, cancel: str}."""


modals_provider = ModalsProvider.create
