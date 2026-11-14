"""Entry point of `appkit-secrets`; typer is an optional dependency."""

import sys


def main() -> None:
    try:
        from appkit_commons.cli.secrets_app import app  # noqa: PLC0415
    except ModuleNotFoundError as exc:
        if exc.name != "typer":
            raise
        sys.stderr.write("appkit-secrets needs typer. Install 'appkit-commons[cli]'.\n")
        raise SystemExit(1) from exc
    app()


if __name__ == "__main__":
    main()
