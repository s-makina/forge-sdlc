#!/bin/sh
set -e
cd /mnt/c/Users/Salvation/Documents/workspace/forge-sdlc || exit 1
echo "Starting litellm (image pull may take a minute)..."
docker compose -f docker-compose.yml up -d --no-build litellm
echo "Done. Status:"
docker ps -a | grep litellm || echo "litellm not found"