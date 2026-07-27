#!/usr/bin/env sh
set -eu

COMPOSE_FILE="${ASIE_COMPOSE_FILE:-docker-compose.production.yml}"
ENV_FILE="${ASIE_ENV_FILE:-.env.production}"

if [ ! -f "$ENV_FILE" ]; then
  echo "missing deployment environment: $ENV_FILE" >&2
  exit 1
fi

chmod 600 "$ENV_FILE"

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config --quiet
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build --pull
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --remove-orphans

echo "Waiting for ASIE services..."
count=0
while [ "$count" -lt 40 ]; do
  if docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps --format json | grep -q '"Health":"healthy"'; then
    break
  fi
  count=$((count + 1))
  sleep 3
done

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

domain=$(sed -n 's/^ASIE_DOMAIN=//p' "$ENV_FILE" | tail -n 1)
if [ -n "$domain" ]; then
  echo "ASIE deployment target: https://$domain"
else
  echo "ASIE_DOMAIN is missing from $ENV_FILE" >&2
  exit 1
fi
