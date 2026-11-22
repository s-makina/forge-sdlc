#!/bin/sh
set -e
cd ./ || exit 1
echo "=== forge-sdlc containers ==="
docker ps -a | grep forgesdlc
echo "=== litellm container ==="
docker ps -a | grep litellm || echo "no litellm container"
echo "=== all containers status ==="
docker ps -a --format "{{.Names}} | {{.Status}}" | grep -E "forgesdlc|litellm|temporal"
