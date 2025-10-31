# syntax=docker/dockerfile:1

# =========================================
# Stage 1: Build Dependencies
# =========================================
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS builder

# Prevents Python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Create virtual environment
RUN python -m venv /app/venv

# Activate virtual environment
ENV PATH="/app/venv/bin:$PATH"

# Install dependencies
# Use cache mount to speed up subsequent builds
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=central/requirements.txt,target=requirements.txt \
    pip install --no-cache-dir -r requirements.txt

# =========================================
# Stage 2: Runtime
# =========================================
FROM python:${PYTHON_VERSION}-slim AS runtime

# Prevents Python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Create a non-privileged user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Copy virtual environment from builder
COPY --from=builder /app/venv /app/venv

# Set PATH to use virtual environment
ENV PATH="/app/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appuser central/app ./app
COPY --chown=appuser:appuser central/main.py ./main.py

# Copy shared code if exists (optional)
# COPY --chown=appuser:appuser shared /app/shared

# Switch to non-privileged user
USER appuser

# Expose the port that the application listens on
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
