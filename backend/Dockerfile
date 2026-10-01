FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /bin/
RUN groupadd --system app && useradd --system --gid app --home-dir /app app
WORKDIR /app

# --- Faqat production bog'liqliklari ---
FROM base AS deps
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# --- Local ishlab chiqish: dev bog'liqliklari, kod volume orqali ulanadi ---
FROM base AS dev
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project
ENTRYPOINT ["sh", "/app/scripts/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# --- Production ---
FROM base AS runtime
COPY --from=deps /opt/venv /opt/venv
COPY --chown=app:app . .
RUN mkdir -p /app/staticfiles && chown app:app /app/staticfiles
USER app
EXPOSE 8000
ENTRYPOINT ["sh", "/app/scripts/entrypoint.sh"]
CMD ["gunicorn", "config.asgi:application", \
     "--worker-class", "uvicorn_worker.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--access-logfile", "-"]

# --- Video worker: ffmpeg bilan ---
FROM runtime AS video
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
USER app
CMD ["celery", "-A", "config", "worker", "-l", "INFO", "-Q", "video", "--concurrency", "1"]

# --- Local ishlab chiqish uchun video worker (kod volume orqali ulanadi) ---
FROM dev AS video-dev
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
CMD ["celery", "-A", "config", "worker", "-l", "INFO", "-Q", "video", "--concurrency", "1"]
