#!/bin/bash
cd /reflexapp/

# apply database migrations
uv run alembic upgrade head
# start server
uv run reflex run --env prod --single-port &
BACKEND_PID=$!
# Keep the container active
wait
