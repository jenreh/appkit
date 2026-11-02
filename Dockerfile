# ────────────────────────────  Stage 1 ─ Builder  ────────────────────────────
ARG VARIANT=3.14-slim-bookworm
FROM python:${VARIANT} AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get -y install --no-install-recommends postgresql-client libpq-dev unzip curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pinned tool images instead of piping an installer script into a shell.
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/
COPY --from=oven/bun:1.4.4 /usr/local/bin/bun /usr/local/bin/bun
RUN ln -s /usr/local/bin/bun /usr/local/bin/bunx

# ───────────────────────────  Stage 2 ─ Runtime  ────────────────────────────
FROM builder AS final

ARG PORT=80
ARG BACKEND_PORT=3030
ENV PORT=$PORT BACKEND_PORT=$BACKEND_PORT

ENV WORK=/reflexapp
# The app runs unprivileged. Ports below 1024 (the default PORT=80) are bindable
# because Docker lowers net.ipv4.ip_unprivileged_port_start for containers; set
# PORT to 1024 or higher on platforms that do not.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app \
    && mkdir -p ${WORK} \
    && chown app:app ${WORK}
WORKDIR ${WORK}
USER app

COPY --chown=app:app pyproject.toml uv.lock README.md .python-version ${WORK}/
COPY --chown=app:app components ${WORK}/components

RUN --mount=type=cache,target=/home/app/.cache/uv,uid=10001,gid=10001 \
    uv sync --frozen --no-install-project --all-extras

COPY --chown=app:app alembic.ini start.sh rxconfig.py ${WORK}/
COPY --chown=app:app configuration ${WORK}/configuration
COPY --chown=app:app assets ${WORK}/assets
COPY --chown=app:app alembic ${WORK}/alembic
COPY --chown=app:app app ${WORK}/app

RUN --mount=type=cache,target=/home/app/.cache/uv,uid=10001,gid=10001 \
    uv sync --frozen --all-extras && \
    chmod +x ${WORK}/start.sh

EXPOSE $PORT $BACKEND_PORT

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/ping' % os.environ['PORT'], timeout=4)"]

CMD ["./start.sh"]
