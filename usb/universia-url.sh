#!/usr/bin/env bash
# Levanta Universia Control con el túnel y mantiene actualizado el link público.
# El link se guarda en URL-ACTUAL.txt y se muestra en la pantalla de login de la consola.
set -u
cd "$(dirname "$0")/.."
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.usb.yml)

until docker info >/dev/null 2>&1; do sleep 3; done
"${COMPOSE[@]}" up -d --build

last=""
while true; do
  url=$("${COMPOSE[@]}" logs --no-color cloudflared 2>/dev/null | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | tail -1)
  if [ -n "$url" ] && [ "$url" != "$last" ]; then
    last="$url"
    echo "$url" > URL-ACTUAL.txt
    mkdir -p /etc/issue.d
    printf '\n  Universia Control  ->  %s\n  (panel local: http://localhost:5173)\n\n' "$url" > /etc/issue.d/universia.issue
    echo "Universia Control disponible en: $url"
  fi
  sleep 20
done
