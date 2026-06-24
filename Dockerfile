# syntax=docker/dockerfile:1

# --- Build stage ---
FROM python:3.12-slim AS build
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

# Build the wheel from source.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip build && python -m build --wheel --outdir /dist

# --- Runtime stage ---
FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# Install the package from the built wheel.
COPY --from=build /dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm -rf /tmp/*.whl

# Bundle the synthetic fixtures so `run` works out of the box.
COPY fixtures ./fixtures

# Run as a non-root user.
RUN useradd --create-home appuser
USER appuser

ENTRYPOINT ["llm-extract"]
CMD ["run", "--dry-run"]
