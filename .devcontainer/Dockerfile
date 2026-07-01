ARG VARIANT=3.13-bookworm
FROM mcr.microsoft.com/devcontainers/python:${VARIANT} AS base

ENV PATH="/root/.local/bin/:$PATH" \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# The base image ships a yarn apt source whose signing key has rotated,
# which breaks `apt-get update` during dev container feature installs
# (NO_PUBKEY 62D54FD4003F6525). Remove any yarn apt source; the node
# feature provides yarn instead.
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && grep -rl 'dl.yarnpkg.com' /etc/apt/sources.list.d/ /etc/apt/sources.list 2>/dev/null | xargs -r rm -f

# Stage 1: Install UV separately to optimize caching
#RUN curl -LsSf https://astral.sh/uv/install.sh | sh
