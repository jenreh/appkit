---
name: multi-stage-dockerfile
description: Creates optimized multi-stage Dockerfiles for any language or framework. Use when building, reviewing, or refactoring Dockerfiles, container images, or Docker Compose configurations. Covers stage structure, base image selection, layer caching, security hardening, and healthchecks.
license: MIT
metadata:
  author: jens-rehpoehler
  version: "1.0"
---

# Multi-Stage Dockerfiles

## Quick reference

- **Multi-stage builds** — separate builder from runtime; copy only artifacts.
- **Pin versions** — use exact image tags (`python:3.13-slim-bookworm`, not `python`).
- **Minimize layers** — combine `RUN` commands with `&&`; order from least→most changing.
- **Non-root user** — always set `USER` in the final stage.
- **Cache mounts** — use `--mount=type=cache` for package manager caches.
- **Healthchecks** — add `HEALTHCHECK` for production readiness.

## Stage structure

```
dependencies → build → (test) → runtime
```

Use meaningful stage names with the `AS` keyword.

```dockerfile
# ── Stage 1: Builder ──
FROM python:3.13-slim-bookworm AS builder
# install build deps, compile, fetch packages

# ── Stage 2: Runtime ──
FROM python:3.13-slim-bookworm AS runtime
# copy only runtime artifacts from builder
COPY --from=builder /app /app
```

### Key rules

- **Builder stage** — install compilers, dev headers, build tools. Run `pip install`, `npm ci`, `cargo build`, etc.
- **Runtime stage** — start from a minimal base; copy only the built output, virtual env, or binary.
- Never install build-only tools (`gcc`, `make`, `node-gyp`) in the runtime stage.

## Base image selection

| Goal | Recommended base | Notes |
|---|---|---|
| Smallest possible | `distroless` / `alpine` | No shell; harder to debug |
| Balance size + compat | `*-slim` variants | Good default for Python, Node |
| Full tooling needed | `*-bookworm` / `*-bullseye` | Use only in builder stage |

- Always pin to a specific tag: `python:3.13-slim-bookworm`, `node:22-alpine3.20`.
- Match builder and runtime base OS family when possible to avoid glibc mismatches.

## Layer optimization

### Order: stable → volatile

```dockerfile
# 1. System deps (rarely change)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Dependency manifests (change occasionally)
COPY pyproject.toml uv.lock ./

# 3. Install deps (cached unless manifests change)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# 4. Application code (changes frequently)
COPY . .
```

### Cache mounts

Use BuildKit cache mounts to persist package manager caches across builds:

```dockerfile
# Python (uv / pip)
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen

# Node.js (npm)
RUN --mount=type=cache,target=/root/.npm npm ci --omit=dev

# Go
RUN --mount=type=cache,target=/root/.cache/go-build go build -o /app
```

### Combine RUN commands

```dockerfile
# ✅ Single layer — fewer layers, smaller image
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ❌ Multiple layers — bloats image
RUN apt-get update
RUN apt-get install -y curl
RUN rm -rf /var/lib/apt/lists/*
```

## Security practices

### Non-root user

```dockerfile
# Create a non-root user in the runtime stage
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/false appuser

# Set ownership
COPY --from=builder --chown=appuser:appuser /app /app

WORKDIR /app
USER appuser
```

### Secrets handling

- Never `COPY` `.env` files or secret files into the image.
- Use `--mount=type=secret` for build-time secrets:

```dockerfile
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci
```

- Use runtime env vars or secret managers (Vault, Key Vault) at container start.

### Minimal attack surface

- Remove package caches: `rm -rf /var/lib/apt/lists/*`
- Avoid installing `sudo`, `ssh`, `vim` in runtime images.
- Set `ENV PYTHONDONTWRITEBYTECODE=1` to skip `.pyc` files.
- Set `ENV PYTHONUNBUFFERED=1` for proper log streaming.

## Healthchecks

```dockerfile
# HTTP-based
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# TCP-based (when curl is unavailable)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')"
```

## Build arguments & env vars

```dockerfile
# Build-time configuration
ARG PYTHON_VERSION=3.13
ARG APP_ENV=production

# Runtime environment
ENV NODE_ENV=production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
```

- Use `ARG` for values that vary between build environments.
- Use `ENV` for runtime configuration with sensible defaults.
- `ARG` values are not persisted in the final image (security-safe).

## .dockerignore

Always create a `.dockerignore` to exclude unnecessary files:

```
.git
.github
.venv
__pycache__
*.pyc
node_modules
.env
.env.*
*.md
tests/
htmlcov/
.mypy_cache/
.ruff_cache/
.pytest_cache/
```

## Complete example (Python / uv)

```dockerfile
# ── Stage 1: Builder ──
ARG PYTHON_VERSION=3.13-slim-bookworm
FROM python:${PYTHON_VERSION} AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --all-extras

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-extras

# ── Stage 2: Runtime ──
FROM python:${PYTHON_VERSION} AS runtime

ARG PORT=8000
ENV PORT=${PORT} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/false appuser

WORKDIR /app
COPY --from=builder --chown=appuser:appuser /app /app

USER appuser
EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')"

CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "${PORT}"]
```

## Decision tree

- **Need build tools (gcc, make)?** → Put them in the builder stage only.
- **Python project?** → Use `uv sync` with cache mounts; copy `.venv` to runtime.
- **Node.js project?** → `npm ci --omit=dev` in builder; copy `node_modules` to runtime.
- **Go / Rust?** → Build static binary in builder; use `distroless` or `scratch` for runtime.
- **Need shell access for debugging?** → Use `*-slim` over `distroless`.
- **Multi-arch build?** → Use `docker buildx build --platform linux/amd64,linux/arm64`.

## Pre-commit checklist

- [ ] Multi-stage build separates builder from runtime
- [ ] Base image tags are pinned to specific versions
- [ ] Layers ordered from stable to volatile for cache efficiency
- [ ] Cache mounts used for package managers
- [ ] Non-root user in the final stage
- [ ] No secrets baked into the image
- [ ] `.dockerignore` excludes unnecessary files
- [ ] `HEALTHCHECK` defined for production images
- [ ] `EXPOSE` matches the actual application port
- [ ] Image scanned for vulnerabilities (`docker scout`, `trivy`)
