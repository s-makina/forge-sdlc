#!/bin/sh
set -e
cd /mnt/c/Users/Salvation/Documents/workspace/forge-sdlc || exit 1
echo "=== litellm container ==="
docker ps -a | grep litellm || echo "no litellm container"
echo "=== litellm image ==="
docker images | grep litellm || echo "no litellm image"
echo "=== ghcr.io reachability ==="
curl -s -o /dev/null -w "ghcr.io -> %{http_code}\n" https://ghcr.io 2>&1 || echo "ghcr.io curl failed"
echo "=== docker hub reachability ==="
curl -s -o /dev/null -w "docker.io -> %{http_code}\n" https://registry-1.docker.io 2>&1 || echo "docker.io curl failed"
echo "=== docker system disk ==="
docker system df 2>&1 | head -10