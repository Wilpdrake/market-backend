# syntax=docker/dockerfile:1.7

# ---- Base for dependency resolution (uv) -----------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS dependencies

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install only third-party dependencies first so this layer is cached across
# source changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# ---- Development image ------------------------------------------------------
FROM dependencies AS development
COPY . ./
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---- Production dependency build (no dev extras) ----------------------------
FROM dependencies AS production-build
COPY . ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ---- Lean production runtime ------------------------------------------------
FROM python:3.12-slim-bookworm AS production

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Run as a dedicated non-root user.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app app

WORKDIR /app

# Copy only what the runtime needs: the venv, application source, and the
# alembic migration setup. No tests, docs, git history, or dev tooling.
COPY --from=production-build --chown=app:app /app/.venv /app/.venv
COPY --from=production-build --chown=app:app /app/app /app/app
COPY --from=production-build --chown=app:app /app/alembic /app/alembic
COPY --from=production-build --chown=app:app /app/alembic.ini /app/alembic.ini

# Writable upload dir, seeded with an app-owned placeholder so that a freshly
# created named volume inherits app ownership (Docker copies the mount point's
# contents/permissions into an empty volume on first mount). This removes the
# need for a root chown init-container in compose.
RUN install -d -o app -g app -m 0755 /app/uploads \
    && install -o app -g app -m 0644 /dev/null /app/uploads/.dockerkeep

USER app

EXPOSE 8000
STOPSIGNAL SIGTERM

# Self-contained liveness probe (compose may override this).
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=10 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/health/live').status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
