# Hotel Management System — single container: Django + Gunicorn + PostgreSQL.

FROM python:3.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    DATA_DIR=/var/lib/hotel \
    PGDATA=/var/lib/hotel/postgres \
    MEDIA_ROOT=/var/lib/hotel/media \
    DJANGO_DEBUG=0 \
    DJANGO_ALLOWED_HOSTS=* \
    DEMO_DATA=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql tini curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --create-home --home-dir /home/app --shell /usr/sbin/nologin app

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies first so they are cached between code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN chmod +x docker/entrypoint.sh scripts/*.sh

VOLUME ["/var/lib/hotel"]
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/ > /dev/null || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/app/docker/entrypoint.sh"]
