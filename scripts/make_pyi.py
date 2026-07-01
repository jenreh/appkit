#!/usr/bin/env python
"""Generate ``.pyi`` stub files for AppKit's Reflex component packages.

AppKit components are Reflex component wrappers built with the Reflex prop DSL
(``prop: Var[T] = default`` declarations plus dynamic ``Component.create`` /
factory functions). A ``py.typed`` marker alone is not enough: type checkers and
IDEs cannot see component props through the dynamic ``create`` signature. Reflex
solves this by shipping generated ``.pyi`` stubs with explicit, fully-typed
``create`` signatures — this script does the same for AppKit so the published
wheels give downstream users autocomplete and type checking.

The heavy lifting is done by Reflex's own generator
(``reflex_base.utils.pyi_generator``). Module names are derived relative to the
working directory, so the generator must run with each package's ``src`` dir as
the CWD; we therefore spawn one subprocess per package.

Usage::

    python scripts/make_pyi.py            # regenerate stubs for every package
    python scripts/make_pyi.py mantine ui # regenerate stubs for named packages
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Component packages whose modules define Reflex ``Component`` subclasses and
# therefore benefit from generated stubs. Keyed by a short alias for CLI use;
# the value is the importable top-level package name under ``components/<dist>/src``.
COMPONENT_PACKAGES: dict[str, str] = {
    "mantine": "appkit_mantine",
    "ui": "appkit_ui",
    "user": "appkit_user",
    "assistant": "appkit_assistant",
    "imagecreator": "appkit_imagecreator",
}


def _src_dir(package: str) -> Path:
    """Return the ``src`` directory that contains ``package``."""
    dist = package.replace("_", "-")
    return REPO_ROOT / "components" / dist / "src"


def generate(package: str) -> int:
    """Generate stubs for a single package, returning the subprocess exit code."""
    src = _src_dir(package)
    if not (src / package).is_dir():
        print(f"  ! skipping {package}: {src / package} not found")
        return 0

    print(f"==> generating stubs for {package} (cwd={src})")
    # The generator emits .pyi next to each .py and lints them; long generated
    # docstrings produce ruff warnings but do not affect the written output, so a
    # non-zero return code here is expected and not treated as failure.
    result = subprocess.run(
        [sys.executable, "-m", "reflex_base.utils.pyi_generator", package],
        cwd=src,
        check=False,
    )

    # Importing component modules makes Reflex copy shared assets to
    # "<cwd>/assets/external"; that copy is a build artifact, not source, so
    # drop it to keep the working tree clean.
    shutil.rmtree(src / "assets", ignore_errors=True)
    return result.returncode


def main(argv: list[str]) -> int:
    aliases = argv or list(COMPONENT_PACKAGES)
    unknown = [a for a in aliases if a not in COMPONENT_PACKAGES]
    if unknown:
        print(f"Unknown package(s): {', '.join(unknown)}")
        print(f"Available: {', '.join(COMPONENT_PACKAGES)}")
        return 2

    for alias in aliases:
        generate(COMPONENT_PACKAGES[alias])

    print("Done. Stubs generated; remember to commit the .pyi files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
