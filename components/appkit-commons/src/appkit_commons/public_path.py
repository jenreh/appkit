"""Path prefix of an app served below the site root, e.g. ``/knai``.

The single source is Reflex's ``frontend_path`` (``ReflexConfig.frontend_path``
via rxconfig.py, or ``REFLEX_FRONTEND_PATH``). It must be the same at export
time and in the backend. appkit-commons does not depend on Reflex, so it is
imported lazily.
"""

import re
from urllib.parse import urlsplit


def public_prefix() -> str:
    """Path prefix of this app: "" when it is served at the site root."""
    try:
        from reflex.config import get_config  # noqa: PLC0415
    except ImportError:
        return ""
    stripped = (get_config().frontend_path or "").strip("/")
    return f"/{stripped}" if stripped else ""


def app_slug() -> str:
    """The prefix as an identifier: ``/apps/my-app`` -> ``apps_my_app``."""
    return re.sub(r"[^A-Za-z0-9]+", "_", public_prefix()).strip("_")


def default_session_cookie_name() -> str:
    """``knai_session`` under ``/knai``, ``reflex_session`` at the site root."""
    slug = app_slug()
    return f"{slug}_session" if slug else "reflex_session"


def public_path(path: str) -> str:
    """Absolute app path with the app prefix; other values unchanged."""
    if not path.startswith("/") or path.startswith("//"):
        return path
    prefix = public_prefix()
    if not prefix or path == prefix or path.startswith(f"{prefix}/"):
        return path
    return f"{prefix}{path}"


def strip_public_prefix(path: str) -> str:
    """App relative route of a browser path, e.g. ``/knai/login`` -> ``/login``.

    Reflex's ``router.url.path`` and single-port page requests carry the
    ``frontend_path`` prefix; route checks and redirect targets must not.
    """
    prefix = public_prefix()
    if prefix and (path == prefix or path.startswith(f"{prefix}/")):
        return path[len(prefix) :] or "/"
    return path


def public_url(base_url: str, path: str = "") -> str:
    """``base_url`` plus the app prefix plus the app relative ``path``.

    The prefix is not added when ``base_url`` already ends with it, so a
    configured URL like ``https://x/knai`` keeps working.
    """
    base = base_url.rstrip("/")
    prefix = public_prefix()
    if prefix and not urlsplit(base).path.endswith(prefix):
        base = f"{base}{prefix}"
    return f"{base}{path}"
