#!/bin/sh
set -e
echo "=== any running docker pulls ==="
ps aux | grep -E "docker|pull|litellm" | grep -v grep || echo "none running"
echo "=== litellm container ==="
docker ps -a | grep litellm || echo "no litellm container"
echo "=== litellm image ==="
docker images | grep litellm || echo "no litellm image"
echo "=== any stopped/exited forge containers ==="
docker ps -a | grep forgesdlc || echo "none"