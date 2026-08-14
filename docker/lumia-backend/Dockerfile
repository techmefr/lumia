FROM python:3.12-slim AS base

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock* ./
RUN uv sync --no-dev --no-install-project

COPY backend/ ./
RUN uv sync --no-dev

ENV PATH="/app/.venv/bin:${PATH}"

# Adds ruff, mypy and pytest on top of the runtime image, so the gate runs against exactly the
# dependency versions the app ships with. Used by the lumia-backend-tests service.
FROM base AS dev

RUN uv sync

# Kept last so a build without an explicit target produces the runtime image, not the dev one.
FROM base AS runtime

EXPOSE 8000
