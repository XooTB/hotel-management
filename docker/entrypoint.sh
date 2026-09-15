#!/usr/bin/env bash
# Starts PostgreSQL and the Django app inside one container.
set -euo pipefail

PG_BIN="$(ls -d /usr/lib/postgresql/*/bin | sort -V | tail -n1)"
PG_SOCKET_DIR=/var/run/postgresql
POSTGRES_DB="${POSTGRES_DB:-hotel}"
POSTGRES_USER="${POSTGRES_USER:-hotel}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-hotel}"

as_postgres() { runuser -u postgres -- "$@"; }
psql_admin() { as_postgres "$PG_BIN/psql" -h "$PG_SOCKET_DIR" -d postgres -v ON_ERROR_STOP=1 "$@"; }

APP_PID=""
cleanup() {
  echo "==> Stopping services"
  if [ -n "$APP_PID" ]; then
    kill -TERM "$APP_PID" 2>/dev/null || true
    wait "$APP_PID" 2>/dev/null || true
  fi
  as_postgres "$PG_BIN/pg_ctl" -D "$PGDATA" -m fast -w stop > /dev/null 2>&1 || true
}
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

# --- persistent data (single volume) -----------------------------------------
mkdir -p "$PGDATA" "$MEDIA_ROOT" "$PG_SOCKET_DIR"
chown -R postgres:postgres "$PGDATA" "$PG_SOCKET_DIR"
chmod 700 "$PGDATA"
chown -R app:app "$MEDIA_ROOT"

if [ -z "${DJANGO_SECRET_KEY:-}" ]; then
  if [ ! -s "$DATA_DIR/secret_key" ]; then
    python -c "import secrets; print(secrets.token_urlsafe(50))" > "$DATA_DIR/secret_key"
    chmod 600 "$DATA_DIR/secret_key"
  fi
  DJANGO_SECRET_KEY="$(cat "$DATA_DIR/secret_key")"
  export DJANGO_SECRET_KEY
fi

# --- PostgreSQL ----------------------------------------------------------------
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo "==> Initialising PostgreSQL cluster"
  as_postgres "$PG_BIN/initdb" -D "$PGDATA" --username=postgres --encoding=UTF8 \
    --auth-local=peer --auth-host=scram-sha-256 > /dev/null
fi

echo "==> Starting PostgreSQL"
if ! as_postgres "$PG_BIN/pg_ctl" -D "$PGDATA" -w -t 60 -l "$PGDATA/server.log" \
    -o "-c listen_addresses=127.0.0.1 -c unix_socket_directories=$PG_SOCKET_DIR" start > /dev/null; then
  cat "$PGDATA/server.log"
  exit 1
fi

if [ -z "$(psql_admin -tAc "SELECT 1 FROM pg_roles WHERE rolname = '$POSTGRES_USER'")" ]; then
  psql_admin -c "CREATE ROLE \"$POSTGRES_USER\" LOGIN" > /dev/null
fi
psql_admin -c "ALTER ROLE \"$POSTGRES_USER\" PASSWORD '$POSTGRES_PASSWORD'" > /dev/null
if [ -z "$(psql_admin -tAc "SELECT 1 FROM pg_database WHERE datname = '$POSTGRES_DB'")" ]; then
  as_postgres "$PG_BIN/createdb" -h "$PG_SOCKET_DIR" -O "$POSTGRES_USER" "$POSTGRES_DB"
fi
export DATABASE_URL="postgres://$POSTGRES_USER:$POSTGRES_PASSWORD@127.0.0.1:5432/$POSTGRES_DB"

# --- Django --------------------------------------------------------------------
echo "==> Applying migrations"
python manage.py migrate --noinput

if [ "${DEMO_DATA:-1}" = "1" ]; then
  python manage.py seed_demo
fi
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ]; then
  python manage.py createsuperuser --noinput > /dev/null 2>&1 \
    && echo "==> Created superuser $DJANGO_SUPERUSER_USERNAME" || true
fi

echo "==> Starting Gunicorn on 0.0.0.0:8000"
setpriv --reuid=app --regid=app --init-groups \
  gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --graceful-timeout 5 \
    --access-logfile - --error-logfile - &
APP_PID=$!
wait "$APP_PID"
