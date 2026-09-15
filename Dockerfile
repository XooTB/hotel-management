# Hotel Management System — single container: Django + Gunicorn + PostgreSQL.

# ---- Stage 1: compile Tailwind CSS --------------------------------------------
# Uses the standalone Tailwind CLI (no Node) and runs natively on the build machine.
# The CLI download is its own layer, so it is cached and not repeated on code changes.
FROM --platform=$BUILDPLATFORM debian:trixie-slim AS css
ARG TAILWIND_VERSION=4.3.3
ARG BUILDARCH
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN arch="${BUILDARCH:-$(dpkg --print-architecture)}" \
    && case "$arch" in amd64) cli=x64 ;; arm64) cli=arm64 ;; *) echo "Unsupported architecture: $arch" >&2; exit 1 ;; esac \
    && curl -fsSL --retry 3 -o /usr/local/bin/tailwindcss \
       "https://github.com/tailwindlabs/tailwindcss/releases/download/v${TAILWIND_VERSION}/tailwindcss-linux-${cli}" \
    && chmod +x /usr/local/bin/tailwindcss
WORKDIR /build
COPY assets ./assets
COPY templates ./templates
COPY apps ./apps
RUN tailwindcss --input assets/tailwind.css --output static/css/app.css --minify

# ---- Stage 2: runtime ------------------------------------------------------------
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
    && useradd --system --home-dir /app --shell /usr/sbin/nologin app

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies first so they are cached between code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
COPY --from=css /build/static/css/app.css static/css/app.css
RUN python manage.py collectstatic --noinput \
    && chmod +x docker/entrypoint.sh scripts/*.sh

VOLUME ["/var/lib/hotel"]
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/ > /dev/null || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/app/docker/entrypoint.sh"]
