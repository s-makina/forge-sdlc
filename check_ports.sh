#!/bin/sh
set -e
cd ./ || exit 1
echo "=== Checking candidate ports ==="
for p in 8082 8090 9000 9090 8443 3000 8000 4000 7233 5432 6379; do
  r=$(sudo ss -tlnp 2>/dev/null | grep -c ":$p ")
  echo "port $p: $r listener(s)"
done
echo "=== All listening ports ==="
sudo ss -tlnp 2>/dev/null | awk '{print $4}' | grep -oE ':[0-9]+$' | sort -u | tr '\n' ' '
echo