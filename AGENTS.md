# AGENTS.md

## Project Overview

AppKit is a production-ready Reflex application and component workspace that packages Mantine UI wrappers, AI assistant tooling (MCP, multi-model chat), enterprise authentication, and supporting infrastructure (database, logging, Docker, CI). The repo contains both the demo app in `app/` and six publishable Python packages under `components/` that can be installed independently via `uv`/PyPI. Core stack: Python 3.13 (repo pins 3.13 via `.python-version`), Reflex 0.8.26, React 18, Mantine 8.3.3, SQLAlchemy/Alembic, FastAPI, uv as the package manager, and PostgreSQL/pgvector.

## Architecture Snapshot

- `app/`: Reflex application with authenticated pages (`app/pages/`), Mantine-based layouts, and AI assistant/image creator demos. Configuration is loaded through `app/configuration.py` which pulls structured settings via `appkit_commons`.
- `components/`: Workspace packages loaded via `[tool.uv.workspace]`.
  - `appkit-commons`: configuration/secret providers, logging bootstrap, database settings.
  - `appkit-user`: OAuth2 auth, RBAC, `authenticated()` decorator & `requires_role()` gate.
  - `appkit-assistant`: Model Manager, LLM processors (OpenAI, Perplexity, Lorem Ipsum fallback), MCP server management.
  - `appkit-imagecreator`: multi-provider image generation workflows.
  - `appkit-mantine`: Mantine UI component wrappers + Tailwind/Mantine providers.
  - `appkit-ui`: shared layouts, dialogs, headers, navigation.
- `configuration/`: YAML profiles (`config.yaml`, `config.local.yaml`, `config.devcontainer.yaml`, etc.), logging configs.
- `alembic/`: database migrations (PostgreSQL + pgvector) driven by `alembic.ini`.
- `assets/`, `docs/`, `.github/`: static assets, deep-dive docs, Copilot/agent instructions, CI workflows.
- `rxconfig.py`: Reflex config wiring TailwindV4Plugin, ports, DB URLs from the service registry.

## Setup & Tooling

### Prerequisites

- Python 3.13 (match `.python-version`).
- `uv` CLI (`pip install uv` or see <https://docs.astral.sh/uv/>).
- Node is bundled via Reflex; no manual install required. PostgreSQL 15+ required locally (or use Docker Compose).

### Install dependencies

```bash
# From repo root
task init                 # installs python, syncs deps, installs pre-commit hooks
```

`Taskfile.dist.yml` defines the workflow commands, replacing `Makefile`:

- `task init` → install python, sync deps, setup pre-commit, run migrations
- `task sync` → `uv sync`
- `task clean` → clean cache and build artifacts

### Environment configuration

- Copy `configuration/config.local.yaml` if you need new overrides. Set `APP_ENV=local` (loads `config.local.yaml`) before running Reflex.
- Secrets use the `secret:<key>` pattern. Provide those keys via `.env`, shell vars, or Azure Key Vault (see *Secrets & Configuration* below).
- Optional envs:
  - `APP_ENV=local|prod|docker_test`
  - `SECRET_PROVIDER=local|azure`
  - `AZURE_KEY_VAULT_URL=<https://...>` when using Key Vault.

### Database & migrations

```bash
task db:upgrade                  # run alembic upgrade head
task db:history                  # show migration history
task db:revision -- "message"    # create new migration (manual)
task db:current                  # check current revision
```

Aliases in `Taskfile.dist.yml` under `db:*` namespace.
PostgreSQL defaults come from `configuration/config*.yaml`; Docker Compose (see below) starts `pgvector/pgvector:pg15` with matching creds.

### Run the app (hot reload)

```bash
task run                         # reflex run
task run:debug                   # reflex run --loglevel=debug
APP_ENV=local task run           # manual invocation with env
```

Reflex serves the frontend on `http://localhost:3000` and backend API on port `3031` (configurable via `configuration/*`). Tailwind styles are applied via the plugin registered in `rxconfig.py`.

### Docker & Compose

- Build image: `task docker:build`
- Run stack: `docker compose up` (or `task docker:test`). Uses `docker-compose.yml`, `.env.docker`, exposes app on 3030/8080 and Postgres on 5433.
- Container entrypoint `start.sh` runs migrations, performs `reflex export --env prod --frontend-only --no-zip`, moves build artifacts to `/srv`, starts Caddy (serving static bundle via `Caddyfile`), then launches the Reflex backend (`uv run reflex run --env prod --backend-only`).

## Secrets & Configuration

- Config loader (`app/configuration.py`) calls `service_registry().configure(...)`, merging YAML profiles and env vars, then resolving secrets via `appkit_commons.configuration.secret_provider`.
- `secret:<name>` references search env vars in multiple casings; set them in your shell or `.env`. To use Azure Key Vault set `SECRET_PROVIDER=azure` and `AZURE_KEY_VAULT_URL`.
- Core config locations:
  - `configuration/config.yaml` – production defaults (ports, DB, authentication, assistant/image generator keys).
  - `configuration/config.local.yaml` – sets `environment: local`, enables DB echo, configures OAuth redirect to localhost.
  - Logging configs: `configuration/logging.yaml` (dev) and `configuration/logging.prod.yaml`.
- Toggle profiles with `APP_ENV=<profile>` (e.g., `local`, `docker_test`); Reflex picks ports/worker counts from the chosen profile via `rxconfig.py`.

## Development Workflow

1. `task init` (first time) or `task sync`.
2. `task run` to launch the app with auto-reload.
3. Edit Reflex pages/components under `app/` or package sources under `components/<package>/src/...`.
4. Use `task test`, `task lint`, `task format` before committing.
5. For stateful flows (assistant, image creator, user management) seed data or authenticate via `appkit_user` components; RBAC relies on entries in `app/roles.py`.
6. Keep `.github/copilot-instructions.md` handy for architectural guardrails (inheritance pattern for Mantine inputs, logging rules, SOPs).

## Monorepo & Workspace Guidance

- uv workspace members (`components/*`) are installed in editable mode. To work on a specific package:

  ```bash
  cd components/appkit-mantine
  uv run pytest  # package-specific tests (add tests under tests/)
  uv build --package appkit-mantine
  ```

- When adding a package, update `[tool.setuptools.packages.find]`, `[tool.hatch.build.targets.wheel]`, and `[tool.uv.workspace]` in `pyproject.toml`.
- CI publishes packages listed in `.github/workflows/02_publish_to_pypi.yml`. Keep `pyproject` versions in sync (root + each component) and run `task release:build` (uses `bump-my-version`).

## Testing & Quality Gates

- Tests live under `tests/` (root) or beside packages. Run `task test` (runs pytest with coverage).
- Targeted runs: `uv run pytest tests -k assistant`, `uv run pytest components/appkit-user/tests -k oauth`.
- Coverage config (`[tool.coverage.run]`) requires ≥80% (`fail_under = 80`).
- Type checking: `uv run mypy .` (configured for py313, `ignore_errors = true` but tighten when touching critical paths).

## Linting & Formatting

- Ruff handles lint + format (configured in `pyproject.toml` with line length 88, double quotes, Py313 target, import sorting).

  ```bash
  task format  # ruff check --fix . && ruff format .
  task lint    # ruff check .
  ```

- Use `task format` before committing.
- Follow logging rule from `.github/copilot-instructions.md`: never use f-strings in logger calls; use parameterized logging.

## Build & Deployment

- **Local prod export**: Use `task run:prod` to test production mode locally, or `reflex export` for static build.
- **Docker**: `Dockerfile` is multi-stage (builder installs Postgres client, Caddy, uv; final image copies workspace code). Ports `PORT`/`BACKEND_PORT` default to `80`/`3030`.
- **Compose**: `docker-compose.yml` starts `appkit-app` and `pgvector` on a shared bridge network.
- **CI/CD**:
  - `.github/workflows/01_build_and_publish_docker_image.yml`: builds multi-arch images and pushes to `ghcr.io/jenreh/appkit-app` on release tags.
  - `.github/workflows/02_publish_to_pypi.yml`: `uv build` + `uv publish` for each Python package.
  - `.github/workflows/publish_to_aca.yml`: mirrors GHCR images into Azure Container Registry and deploys to Azure Container Apps using OIDC login.

## Security Notes

- Secrets must never be hard-coded; rely on `secret:` indirection and environment variables or Azure Key Vault.
- Authentication helpers (`appkit_user`) enforce RBAC via `requires_role` (e.g., `ASSISTANT_ROLE` for the assistant page). Page decorators such as `authenticated()` wrap routes; ensure new pages respect this pattern.
- MCP server headers and OAuth credentials are encrypted via `appkit_assistant` configs; treat `AssistantConfig` secret fields as sensitive.
- Use SSL/TLS for database connections in production (`configuration/config.yaml`), and keep `logging.prod.yaml` sanitized (PII-free logs).

## Pull Request Routine

- Follow the SOP in `.github/copilot-instructions.md` (plan → tests → minimal diff). Conventional commits (`feat:`, `fix:`, etc.).
- Before opening a PR:
  - `task format && task lint && task test`
  - Ensure coverage stays ≥80%.
  - Update docs (`README.md`, relevant component README, or `docs/`) plus `AGENTS.md` if instructions change.
  - Document DB migrations (include Alembic revision ID + rationale in the PR body).
  - If you touched secrets or config, describe required env changes.

## Debugging & Troubleshooting

- **`SecretNotFoundError`**: confirm the key exists in your env (`export mn-db-user=...`) or switch `SECRET_PROVIDER=local`. For Azure, install `azure-identity` & `azure-keyvault-secrets` and set `AZURE_KEY_VAULT_URL`.
- **Database connection refused**: ensure Postgres is running (Docker on port 5433) and that `configuration/config.local.yaml` points at the right host (`DATABASE_HOST=db` inside Compose, `localhost` outside). Run `task db:current` to verify connectivity.
- **Reflex port conflicts**: override `reflex.frontend_port` / `backend_port` in `configuration/config.local.yaml` or export `REFLEX_FRONTEND_PORT`. Re-run `task run` after cleaning `.web`.
- **uv sync issues**: install the interpreter listed in `.python-version` (3.13) and clear caches via `task clean && rm -rf .venv`. uv stores caches under `.cache/uv_cache` per `pyproject`.
- **Docker export missing files**: the container expects `.web/build/client`. If `reflex export` moved paths in newer versions, adjust `start.sh` accordingly and keep Caddy root synced.
- **Assistant models unavailable**: `app/pages/assitant/assistant.py` registers processors conditionally. Ensure `AssistantConfig` contains OpenAI & Perplexity keys; otherwise only the Lorem Ipsum processor is enabled.

## Reference Docs & Entry Points

- `README.md` – high-level product overview and quick start.
- `Taskfile.dist.yml` - definitive source of build/run commands.
- `.github/copilot-instructions.md` – authoritative architecture/guideline file for agents.
- `llms.txt` – condensed AI-focused project summary.
- Component READMEs (`components/appkit-*/README.md`) – per-package APIs and design patterns.
- `.github/workflows/` – release pipelines (Docker, package publish, ACA deployment).
- `configuration/` – environment/logging YAMLs.
- `alembic/versions/` – migration history.

Keep this file updated whenever setup commands, workflows, or architecture constraints change so future agents can bootstrap quickly.
