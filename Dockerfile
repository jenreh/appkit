# ────────────────────────────  Stage 1 ─ Builder  ────────────────────────────
ARG VARIANT=3.13-slim-bookworm
FROM python:${VARIANT} AS builder

# Stage 1: Install required libraries
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y upgrade \
    && apt-get -y install --no-install-recommends postgresql-client libpq-dev unzip curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy uv and bun from official images (simpler than curl install)
RUN export UV_INSTALL_DIR=/bin && curl -LsSf https://astral.sh/uv/install.sh | sh
RUN export BUN_INSTALL=/usr/local && curl -fsSL https://bun.sh/install | bash

# ───────────────────────────  Stage 2 ─ Runtime  ────────────────────────────
FROM builder AS final

ARG PORT=80
ARG BACKEND_PORT=3030
ARG API_URL
ENV PORT=$PORT REFLEX_API_URL=${API_URL:-http://localhost:$PORT}

ENV WORK=/reflexapp
WORKDIR ${WORK}

COPY pyproject.toml uv.lock README.md .python-version ${WORK}/
COPY components ${WORK}/components

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --all-extras

COPY alembic.ini start.sh rxconfig.py ${WORK}/
COPY configuration ${WORK}/configuration
COPY assets ${WORK}/assets
COPY alembic ${WORK}/alembic
COPY app ${WORK}/app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-extras && \
    chmod +x ${WORK}/start.sh

EXPOSE $PORT $BACKEND_PORT

CMD ["./start.sh"]
