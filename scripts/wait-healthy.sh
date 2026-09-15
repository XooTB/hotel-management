#!/usr/bin/env bash
# Wait for the compose service's Docker health check to report "healthy".
set -euo pipefail
service="${1:-hotel}"
timeout="${2:-180}"

container="$(docker compose ps -q "$service")"
if [ -z "$container" ]; then
  echo "Service '$service' is not running" >&2
  exit 1
fi

for ((elapsed = 0; elapsed < timeout; elapsed += 3)); do
  status="$(docker inspect -f '{{.State.Health.Status}}' "$container" 2>/dev/null || echo unknown)"
  case "$status" in
    healthy) echo "✔ $service is healthy after ${elapsed}s"; exit 0 ;;
    unhealthy) echo "✘ $service is unhealthy" >&2; docker compose logs --tail 50 "$service" >&2; exit 1 ;;
  esac
  sleep 3
done
echo "✘ Timed out after ${timeout}s waiting for $service (last status: $status)" >&2
docker compose logs --tail 50 "$service" >&2
exit 1
