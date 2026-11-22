#!/bin/sh
echo "=== API ==="
curl -s -o /dev/null -w "  /health   -> %{http_code}\n" http://localhost:8000/health
curl -s -o /dev/null -w "  /openapi  -> %{http_code}\n" http://localhost:8000/openapi.json
echo "=== proxy (8081) ==="
curl -s -o /dev/null -w "  /          -> %{http_code}\n" http://localhost:8081/
curl -s -o /dev/null -w "  /health    -> %{http_code}\n" http://localhost:8081/health
echo "=== execution-manager ==="
curl -s -o /dev/null -w "  /health    -> %{http_code}\n" http://localhost:8001/health
echo "=== orchestrator ==="
curl -s -o /dev/null -w "  /health    -> %{http_code}\n" http://localhost:8002/health
echo "=== temporal-ui ==="
curl -s -o /dev/null -w "  /          -> %{http_code}\n" http://localhost:8080/
echo "=== temporal frontend ==="
curl -s -o /dev/null -w "  :7233      -> %{http_code}\n" http://localhost:7233/
echo "=== containers ==="
docker ps --filter "name=forgesdlc" --format "  {{.Names}} | {{.Status}}"