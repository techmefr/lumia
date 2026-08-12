FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock* ./
RUN uv sync --no-dev --no-install-project

COPY backend/ ./
RUN uv sync --no-dev

ENV PATH="/app/.venv/bin:${PATH}"

EXPOSE 8000
