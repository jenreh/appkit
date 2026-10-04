"""Style preview paths carry the app's public path prefix."""

import os
import subprocess
import sys
import textwrap
from types import SimpleNamespace

import pytest

from appkit_commons.testing import set_public_path_prefix
from appkit_imagecreator.configuration import prefixed_styles, styles_preset
from appkit_imagecreator.state import ImageGalleryState

_CV = ImageGalleryState.__dict__


@pytest.fixture(autouse=True)
def _knai_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    set_public_path_prefix(monkeypatch, "/knai")


def test_prefixed_styles() -> None:
    result = prefixed_styles(styles_preset)

    assert result["Photographic"]["path"] == "/knai/styles/photographic.webp"
    assert result["Photographic"]["prompt"] == styles_preset["Photographic"]["prompt"]
    assert all(info["path"].startswith("/knai/styles/") for info in result.values())
    # The shared configuration dict stays unprefixed.
    assert styles_preset["Photographic"]["path"] == "/styles/photographic.webp"


def test_prefixed_styles_tolerates_missing_path() -> None:
    presets = {"plain": {"prompt": "x"}}
    assert prefixed_styles(presets) == presets


def test_prefixed_styles_keeps_external_urls() -> None:
    presets = {"web": {"path": "https://x/a.webp", "prompt": ""}}
    assert prefixed_styles(presets) == presets


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/styles/anime.webp", "/knai/styles/anime.webp"),
        ("styles/anime.webp", "/knai/styles/anime.webp"),
        ("/knai/styles/anime.webp", "/knai/styles/anime.webp"),
        ("https://x/a.webp", "https://x/a.webp"),
    ],
)
def test_selected_style_path(path: str, expected: str) -> None:
    state = SimpleNamespace(
        selected_style="Anime", styles_preset={"Anime": {"path": path, "prompt": ""}}
    )
    assert _CV["selected_style_path"].fget(state) == expected


def test_state_default_carries_prefix() -> None:
    """The state var default is fixed at import, so check a fresh interpreter."""
    script = textwrap.dedent(
        """
        import appkit_commons.testing  # registers the test configs
        from appkit_imagecreator.state import ImageGalleryState

        field = ImageGalleryState.get_fields()["styles_preset"]
        default = field.default_factory()
        print(default["Photographic"]["path"])
        """
    )
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PYTHONWARNINGS": "ignore", "REFLEX_FRONTEND_PATH": "/knai"},
        timeout=120,
    )
    assert result.stdout.strip().splitlines()[-1] == "/knai/styles/photographic.webp"
