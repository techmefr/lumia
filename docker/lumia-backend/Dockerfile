FROM python:3.14.7-slim AS base

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

# The image is published, so it has to be useful without the compose file that used to carry
# every command. This one serves the API; the worker overrides it with the arq command.
RUN useradd --system --no-create-home --uid 10001 lumia \
    && chown -R lumia:lumia /app

USER lumia

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
