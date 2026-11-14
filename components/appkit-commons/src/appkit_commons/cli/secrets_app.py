"""`appkit-secrets`: manage secrets in the macOS Keychain or Windows Credential
Manager so that `SECRET_PROVIDER=macos|windows` can resolve `secret:` values.
"""

import os
import re
import shlex
import sys
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from appkit_commons.cli.secret_check import parse_profiles, required_secret_names
from appkit_commons.configuration.secret_backends import (
    LOCAL_STORE_PROVIDERS,
    SecretNotFoundError,
    SecretStore,
    SecretStoreError,
    create_local_store,
    settings,
)

NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,126}$")
_PLATFORM_PROVIDERS = {"darwin": "macos", "win32": "windows"}

PROG_NAME = "appkit-secrets"
COMPLETE_VAR = "_APPKIT_SECRETS_COMPLETE"

app = typer.Typer(
    name=PROG_NAME,
    help=(
        "Manage appkit secrets in the macOS Keychain or the Windows Credential "
        "Manager. Values are never printed except by `env`."
    ),
    no_args_is_help=True,
    add_completion=True,
)


class Shell(StrEnum):
    posix = "posix"
    powershell = "powershell"


class CompletionShell(StrEnum):
    bash = "bash"
    zsh = "zsh"
    fish = "fish"
    powershell = "powershell"
    pwsh = "pwsh"


def resolve_provider(explicit: str | None, platform: str = sys.platform) -> str:
    """--provider, else a local SECRET_PROVIDER, else the platform's store."""
    if explicit:
        provider = explicit.strip().lower()
        if provider not in LOCAL_STORE_PROVIDERS:
            raise SecretStoreError(
                f"appkit-secrets only manages local stores (macos, windows), "
                f"not '{provider}'. Manage cloud secrets with az / aws."
            )
        return provider
    configured = settings.provider_name()
    if configured in LOCAL_STORE_PROVIDERS:
        return configured
    if platform in _PLATFORM_PROVIDERS:
        return _PLATFORM_PROVIDERS[platform]
    raise SecretStoreError(
        "No local secret store on this platform; use --provider macos|windows."
    )


def env_var_name(name: str) -> str:
    return re.sub(r"[-.]", "_", name).upper()


def export_line(name: str, value: str, shell: Shell) -> str:
    variable = env_var_name(name)
    if shell is Shell.powershell:
        return f"$env:{variable} = '{value.replace("'", "''")}'"
    return f"export {variable}={shlex.quote(value)}"


def _default_shell() -> Shell:
    return Shell.powershell if sys.platform == "win32" else Shell.posix


@contextmanager
def _cli_errors() -> Iterator[None]:
    try:
        yield
    except (SecretStoreError, SecretNotFoundError, ImportError, OSError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc


def _validate_name(name: str) -> str:
    if not NAME_PATTERN.match(name):
        raise typer.BadParameter(
            "use letters, digits, '.', '_' and '-' (max 127 characters), "
            "starting with a letter or digit"
        )
    return name


def _open_store(ctx: typer.Context) -> SecretStore:
    """Store from the global --provider/--namespace options, opened on demand."""
    params = ctx.find_root().params
    return create_local_store(
        resolve_provider(params.get("provider")),
        settings.local_namespace(params.get("namespace")),
    )


def _read_value(from_stdin: bool) -> str:
    if from_stdin:
        value = sys.stdin.read().removesuffix("\n").removesuffix("\r")
    else:
        value = typer.prompt("Value", hide_input=True, confirmation_prompt=True)
    if not value:
        raise SecretStoreError("The secret value must not be empty.")
    return value


def _default_config_dir() -> Path:
    return Path(os.getcwd()) / "configuration"  # noqa: PTH109


# --- Shell completion --------------------------------------------------------
# Completion callbacks run inside the user's shell on every <TAB>: they must
# never raise, never prompt and never print values, so all errors become [].


def _matching(candidates: Iterable[str], incomplete: str) -> list[str]:
    return sorted(name for name in set(candidates) if name.startswith(incomplete))


def complete_provider(incomplete: str) -> list[str]:
    return _matching(LOCAL_STORE_PROVIDERS, incomplete)


def complete_stored_names(ctx: typer.Context, incomplete: str) -> list[str]:
    """Names in the store, minus those already on the command line."""
    try:
        names = _open_store(ctx).list_names()
    except Exception:  # noqa: BLE001
        return []
    given = set(ctx.params.get("names") or [])
    return _matching([name for name in names if name not in given], incomplete)


def complete_missing_names(ctx: typer.Context, incomplete: str) -> list[str]:
    """Names referenced by any configuration file but not yet in the store."""
    try:
        needed = required_secret_names(_default_config_dir(), [], all_profiles=True)
        stored = set(_open_store(ctx).list_names())
    except Exception:  # noqa: BLE001
        return []
    return _matching(needed - stored, incomplete)


def complete_profiles(ctx: typer.Context, incomplete: str) -> list[str]:
    """Profiles from config.<profile>.yaml; completes the part after the last comma."""
    directory = ctx.params.get("config_dir") or _default_config_dir()
    try:
        profiles = {
            file.name.removeprefix("config.").removesuffix(".yaml")
            for file in Path(directory).glob("config.*.yaml")
        }
    except OSError:
        return []
    done, _, current = incomplete.rpartition(",")
    prefix = f"{done}," if done else ""
    chosen = set(parse_profiles(done))
    return [prefix + name for name in _matching(profiles - chosen, current)]


StdinOption = Annotated[
    bool, typer.Option("--stdin", help="Read the value from stdin.")
]


@app.callback()
def main(
    provider: Annotated[
        str | None,
        typer.Option(
            "--provider",
            "-p",
            help="macos or windows (default: SECRET_PROVIDER or this platform).",
            autocompletion=complete_provider,
        ),
    ] = None,
    namespace: Annotated[
        str | None,
        typer.Option(
            "--namespace",
            "-n",
            envvar=settings.SECRET_NAMESPACE_ENV,
            help="Keychain account / credential prefix (default: appkit).",
        ),
    ] = None,
) -> None:
    """Global options; commands open the store when they need it."""


@app.command()
def add(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Argument(callback=_validate_name, autocompletion=complete_missing_names),
    ],
    stdin: StdinOption = False,
) -> None:
    """Add a new secret. Fails if it already exists."""
    with _cli_errors():
        store = _open_store(ctx)
        if store.exists(name):
            raise SecretStoreError(f"Secret '{name}' already exists; use update.")
        store.set(name, _read_value(stdin))
        typer.echo(f"Added {name}")


@app.command()
def update(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Argument(callback=_validate_name, autocompletion=complete_stored_names),
    ],
    stdin: StdinOption = False,
) -> None:
    """Replace the value of an existing secret."""
    with _cli_errors():
        store = _open_store(ctx)
        if not store.exists(name):
            raise SecretNotFoundError(f"Secret '{name}' does not exist; use add.")
        store.set(name, _read_value(stdin))
        typer.echo(f"Updated {name}")


@app.command()
def delete(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Argument(callback=_validate_name, autocompletion=complete_stored_names),
    ],
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Do not ask for confirmation.")
    ] = False,
) -> None:
    """Delete a secret."""
    with _cli_errors():
        store = _open_store(ctx)
        if not yes:
            typer.confirm(f"Delete secret '{name}'?", abort=True)
        store.delete(name)
        typer.echo(f"Deleted {name}")


@app.command("list")
def list_secrets(ctx: typer.Context) -> None:
    """List the secret names in the namespace (never values)."""
    with _cli_errors():
        for name in _open_store(ctx).list_names():
            typer.echo(name)


@app.command()
def env(
    ctx: typer.Context,
    names: Annotated[
        list[str] | None,
        typer.Argument(
            help="Secrets to export (default: all in the namespace).",
            autocompletion=complete_stored_names,
        ),
    ] = None,
    shell: Annotated[
        Shell | None,
        typer.Option(help="posix (export) or powershell ($env:)."),
    ] = None,
) -> None:
    """
    Print the secrets as shell exports for SECRET_PROVIDER=local.

        eval "$(appkit-secrets env)"
    """
    with _cli_errors():
        store = _open_store(ctx)
        selected = [_validate_name(name) for name in names or store.list_names()]
        chosen_shell = shell or _default_shell()
        for name in selected:
            typer.echo(export_line(name, store.get(name), chosen_shell))


@app.command()
def check(
    ctx: typer.Context,
    profiles: Annotated[
        str | None,
        typer.Option(
            envvar="PROFILES",
            help="Comma separated profiles (default: PROFILES).",
            autocompletion=complete_profiles,
        ),
    ] = None,
    config_dir: Annotated[
        Path | None,
        typer.Option(help="Configuration directory (default: ./configuration)."),
    ] = None,
    all_profiles: Annotated[
        bool,
        typer.Option(
            "--all-profiles", help="Check config.yaml and every config.*.yaml."
        ),
    ] = False,
) -> None:
    """Check that every secret:<name> of the configuration exists in the store."""
    with _cli_errors():
        directory = config_dir or _default_config_dir()
        needed = sorted(
            required_secret_names(directory, parse_profiles(profiles), all_profiles)
        )
        if not needed:
            typer.echo(f"No secret: references found in {directory}")
            return

        store = _open_store(ctx)
        missing = [name for name in needed if not store.exists(name)]
        for name in needed:
            typer.echo(f"{'missing' if name in missing else 'ok':<8} {name}")
        typer.echo(f"{len(needed) - len(missing)} of {len(needed)} secrets present")
        if missing:
            raise typer.Exit(1)


@app.command()
def completion(
    shell: Annotated[
        CompletionShell | None,
        typer.Argument(help="Target shell (default: from $SHELL)."),
    ] = None,
) -> None:
    """
    Print the shell completion script for appkit-secrets.

    Load it from your shell start-up file (after compinit for zsh):

        eval "$(appkit-secrets completion zsh)"      # ~/.zshrc
        eval "$(appkit-secrets completion bash)"     # ~/.bashrc
        appkit-secrets completion fish | source      # config.fish
        appkit-secrets completion powershell | Out-String | Invoke-Expression
    """
    # Typer has no public API for the script; --show-completion uses the same.
    from typer._completion_shared import get_completion_script  # noqa: PLC0415

    with _cli_errors():
        chosen = shell or detect_completion_shell()
        typer.echo(
            get_completion_script(
                prog_name=PROG_NAME, complete_var=COMPLETE_VAR, shell=chosen.value
            )
        )


def detect_completion_shell(
    shell_path: str | None = None, platform: str = sys.platform
) -> CompletionShell:
    """Shell named by $SHELL; PowerShell on Windows."""
    if platform == "win32" and shell_path is None and not os.getenv("SHELL"):
        return CompletionShell.powershell
    path = shell_path or os.getenv("SHELL", "")
    name = re.split(r"[\\/]", path)[-1].lower().removesuffix(".exe")
    try:
        return CompletionShell(name)
    except ValueError:
        raise SecretStoreError(
            "Cannot detect the shell; pass one of: "
            + ", ".join(shell.value for shell in CompletionShell)
        ) from None
