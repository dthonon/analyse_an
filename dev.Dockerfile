# Stage 1: Build stage with Poetry
FROM python:3.12-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_HOME="/opt/poetry" \
    PATH="$POETRY_HOME/bin:$PATH"

# Install Poetry
RUN apt-get update && apt-get install -y make && \
    python -m pip install poetry --no-cache-dir && \
    poetry config virtualenvs.in-project true

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --no-root

# Copy the rest of the application files
COPY . .

ENV PATH="/app/.venv/bin:$PATH" \
    APP_STAGE="development"

# Entrypoint for running the application
CMD ["sh", "./docker/docker-entrypoint.sh"]
