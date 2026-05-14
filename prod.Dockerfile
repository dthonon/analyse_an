# Stage 1: Build stage with Poetry
FROM python:3.12-slim-bookworm AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_HOME="/opt/poetry" \
    PATH="$POETRY_HOME/bin:$PATH"

# Install Poetry
RUN python -m pip install poetry --no-cache-dir && \
    poetry config virtualenvs.in-project true

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --without dev --no-root

# Copy the rest of the application files
COPY . .

RUN rm -f pyproject.toml poetry.lock

# Stage 2: Production stage
FROM python:3.12-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    APP_STAGE="production"

WORKDIR /app

# Copy application files and virtual environment from the builder stage
COPY --from=builder /app /app

# Entrypoint for running the application
ENTRYPOINT ["sh", "./docker/docker-entrypoint.sh"]