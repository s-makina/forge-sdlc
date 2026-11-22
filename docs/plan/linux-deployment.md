# ForgeSDLC — Staging Server Deployment Guide

Deploy ForgeSDLC on a public staging server (Linux VM / cloud instance) and make it
reachable over HTTP(S). This guide walks you through: requirements → port checks →
clone → configure → build → start → verify.

**Assumed target:** a fresh Ubuntu 22.04 / 24.04 staging VM with root or sudo access.
**Out-of-scope:** TLS termination. If you need HTTPS, put a reverse proxy (Caddy /
Traefik / Nginx) in front of the ForgeSDLC `proxy` service on port 80/443.

---

## 1. Requirements & resource check

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Ubuntu 22.04+ (any systemd Linux) | Ubuntu 24.04 LTS |
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8 GB |
| Disk | 40 GB | 80+ GB |
| Docker | Engine 25+ + Compose v2 plugin | latest stable |
| Outbound internet | Yes (image pulls + NVIDIA NIM API) | Yes |

On your staging server, run:

```bash
lsb_release -a
nproc
free -h
df -h /
docker --version
docker compose version
```

If Docker is not installed yet:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
sudo systemctl enable --now docker
# Log out and back in (or run: newgrp docker) so you don't need sudo for docker
```

---

## 2. Port verification (critical before starting)

ForgeSDLC binds these host ports by default:

| Service | Host port | Purpose |
|---------|-----------|---------|
| proxy (nginx) | **80** (configurable via `PROXY_PORT`) | Public front door → API + dashboard |
| api | 8000 | Internal (FastAPI) |
| dashboard | 3000 | Internal (Next.js) |
| temporal | 7233 | Internal (workflow engine) |
| temporal-ui | 8080 | Internal (Temporal web UI) |
| execution-manager | 8001 | Internal |
| orchestrator | 8002 | Internal |
| postgres | 5432 | Internal (DB) |
| redis | 6379 | Internal (cache) |
| litellm | 4000 | Internal (model gateway) |

Only **port 80** (via `PROXY_PORT`) needs to be publicly reachable. Everything else
stays internal on the Docker bridge network.

### Check what's already listening

On your staging server, run:

```bash
sudo ss -tlnp | grep -E ':80|:443|:8081|:3000|:5432|:6379|:4000|:7233|:8080|:8000|:8001|:8002'
```

**If port 80 or 443 is already taken** (e.g. by an existing traefik/dokploy/Nginx
installation), set `PROXY_PORT=8081` in `.env` and access the app at
`http://<SERVER-IP>:8081`. Otherwise use `PROXY_PORT=80` and access at
`http://<SERVER-IP>/`.

Also check your cloud provider's **security group / firewall** allows inbound TCP
on whatever `PROXY_PORT` you choose (and SSH, port 22).

---

## 3. Clone the repository

```bash
git clone <YOUR-REPO-URL> forge-sdlc
cd forge-sdlc
git status            # should be clean
```

> **Line endings:** clone directly on Linux so you get correct LF endings. The
> `entrypoint.sh` scripts break with Windows CRLF endings.

---

## 4. Create the `.env` file (secrets)

Copy the example and fill in real values. **Never commit `.env`.**

```bash
cp .env.example .env
nano .env
```

A working staging `.env` (edit the values marked `CHANGE-THIS`):

```dotenv
# ============================================================
# ForgeSDLC staging environment
# ============================================================

# --- Postgres ---
POSTGRES_USER=forgesdlc
POSTGRES_PASSWORD=CHANGE-THIS-STRONG-DB-PASSWORD
POSTGRES_DB=forgesdlc
POSTGRES_PORT=5432

# --- Redis ---
REDIS_PORT=6379

# --- Dashboard (Next.js) ---
DASHBOARD_PORT=3000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1

# --- Reverse proxy (nginx) ---
# Use 80 if free; otherwise 8081 (if traefik/dokploy already owns 80/443).
PROXY_PORT=80

# --- API (FastAPI) ---
API_PORT=8000
ENVIRONMENT=staging
DATABASE_URL=postgresql+psycopg://forgesdlc:CHANGE-THIS-STRONG-DB-PASSWORD@postgres:5432/forgesdlc
REDIS_URL=redis://redis:6379/0

# --- Security ---
SESSION_SECRET_KEY=CHANGE-THIS-LONG-RANDOM-STRING-AT-LEAST-32-CHARS
SESSION_COOKIE_NAME=forgesdlc_session

# --- Bootstrap operator (first admin login) ---
BOOTSTRAP_OPERATOR_EMAIL=admin@yourdomain.com
BOOTSTRAP_OPERATOR_PASSWORD=CHANGE-THIS-OPERATOR-PASSWORD

# --- Temporal ---
TEMPORAL_PORT=7233
TEMPORAL_UI_PORT=8080

# --- Ollama (DISABLED) ---
OLLAMA_PORT=11434

# --- Model gateway (LiteLLM) ---
LITELLM_PORT=4000
LITELLM_MASTER_KEY=sk-litellm-staging-CHANGE-THIS

# --- External OpenAI-compatible provider (NVIDIA NIM default) ---
EXTERNAL_MODEL_BASE_URL=https://integrate.api.nvidia.com/v1
EXTERNAL_MODEL_API_KEY=CHANGE-THIS-NVIDIA-API-KEY

# --- Execution manager ---
EXECUTION_MANAGER_PORT=8001
```

Save and exit. The `.env` file is gitignored — it will not be committed.

---

## 5. Build the images

Use `-f docker-compose.yml` **explicitly**. Do **not** use
`docker-compose.override.yml` on staging — it mounts local source and runs dev
commands (`pnpm dev`, `uvicorn --reload`) which are incompatible with the
production standalone dashboard image.

```bash
docker compose -f docker-compose.yml build
```

This builds: `api`, `dashboard`, `execution-manager`, `orchestrator`. The
dashboard build takes a few minutes (Next.js compile). Pulls for `postgres`,
`redis`, `temporalio/*`, `litellm`, `nginx` happen automatically at startup.

---

## 6. Start the stack

```bash
docker compose -f docker-compose.yml up -d
```

Watch it come up:

```bash
docker compose -f docker-compose.yml ps
```

Expected result — all `forgesdlc-*` containers `Up` and `healthy`:

```
forgesdlc-postgres-1    Up (healthy)
forgesdlc-redis-1       Up (healthy)
forgesdlc-api-1         Up (healthy)
forgesdlc-dashboard-1   Up (healthy)
forgesdlc-proxy-1       Up
forgesdlc-temporal-1    Up (healthy)
forgesdlc-temporal-ui-1 Up
forgesdlc-litellm-1     Up (healthy)
forgesdlc-execution-manager-1 Up (healthy)
forgesdlc-orchestrator-1 Up (healthy)
```

> If the daemon restarts mid-startup, services with `restart: unless-stopped`
> (all of them) will come back automatically. Just re-run the `ps` check after
> ~30 seconds.

---

## 7. Verify every endpoint

Run these from the staging server itself (replace `80` with `8081` if you set
`PROXY_PORT=8081`):

```bash
# --- API ---
curl -s -o /dev/null -w "api /health     -> %{http_code}\n" http://localhost:8000/health
curl -s -o /dev/null -w "api /openapi    -> %{http_code}\n" http://localhost:8000/openapi.json

# --- Execution manager ---
curl -s -o /dev/null -w "exec-mgr /health -> %{http_code}\n" http://localhost:8001/health

# --- Orchestrator ---
curl -s -o /dev/null -w "orchestrator /health -> %{http_code}\n" http://localhost:8002/health

# --- Temporal ---
curl -s -o /dev/null -w "temporal :7233   -> %{http_code}\n" http://localhost:7233/

# --- Temporal UI ---
curl -s -o /dev/null -w "temporal-ui :8080 -> %{http_code}\n" http://localhost:8080/

# --- LiteLLM ---
curl -s -o /dev/null -w "litellm :4000   -> %{http_code}\n" http://localhost:4000/health/liveliness

# --- Proxy (public front door) ---
curl -s -o /dev/null -w "proxy /health   -> %{http_code}\n" http://localhost:80/health
curl -s -o /dev/null -w "proxy /login    -> %{http_code}\n" -L http://localhost:80/login
curl -s -o /dev/null -w "proxy / (dash)  -> %{http_code}\n" -L http://localhost:80/
```

You should see `200` for everything. The dashboard root (`/`) returns `307`
(redirect to `/login`) — follow the redirect (`-L`) and you'll get `200` on the
login page.

---

## 8. Access from your browser

Get your staging server's public IP:

```bash
curl -s ifconfig.me
```

Open in your browser:

```
http://<PUBLIC-IP>:80/login        # if PROXY_PORT=80
http://<PUBLIC-IP>:8081/login      # if PROXY_PORT=8081
```

**Default login** (from `.env` bootstrap operator):

| Field | Value |
|-------|-------|
| Email | `admin@yourdomain.com` (or whatever you set) |
| Password | `CHANGE-THIS-OPERATOR-PASSWORD` (whatever you set) |

⚠️ Change these immediately after first login.

---

## 9. LiteLLM + NVIDIA NIM (AI model access)

Ollama is **disabled** by default. The platform uses LiteLLM with the NVIDIA NIM
endpoint `https://integrate.api.nvidia.com/v1` as the default external provider.

To actually route model calls through NVIDIA NIM, set a real API key:

```bash
nano .env
# Set: EXTERNAL_MODEL_API_KEY=your-nvidia-nim-api-key
docker compose -f docker-compose.yml up -d litellm
```

Then enable specific models in
`infrastructure/litellm/config.yaml` (uncomment the `model_list` example and
fill in model names), or render the gateway config from the API:

```bash
curl -s http://localhost:8000/api/v1/models/gateway/config.yaml
```

---

## 10. Operational commands

```bash
# View logs
docker compose -f docker-compose.yml logs -f api
docker compose -f docker-compose.yml logs -f temporal
docker compose -f docker-compose.yml logs -f litellm

# Restart a single service
docker compose -f docker-compose.yml restart api

# Stop everything
docker compose -f docker-compose.yml down

# Start everything again
docker compose -f docker-compose.yml up -d

# Full wipe (DANGER: deletes Postgres data volume)
docker compose -f docker-compose.yml down -v
docker compose -f docker-compose.yml up -d

# Rebuild after code changes
docker compose -f docker-compose.yml build api dashboard
docker compose -f docker-compose.yml up -d
```

---

## 11. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `ERR_CONNECTION_REFUSED` on port 80 | Stack still starting / daemon bounced | Wait ~30 s, then `docker compose -f docker-compose.yml ps` |
| Port 80 already in use | Another service (traefik/dokploy) owns 80 | Set `PROXY_PORT=8081` in `.env`, rebuild, restart |
| Dashboard returns 500 / `EvalError` | Started with `docker-compose.override.yml` (dev mode) | Always use `-f docker-compose.yml` on staging |
| API exits `exec ./entrypoint.sh: no such file` | CRLF line endings in checkout | Re-clone on Linux (LF endings) |
| Litellm health failing | `EXTERNAL_MODEL_API_KEY` empty or NVIDIA NIM unreachable | Set key in `.env`, restart litellm, check outbound HTTPS |
| Temporal exits `Unsupported driver` | Old `DB=postgresql` value | Already fixed to `DB=postgres12` in compose |

---

## 12. Security notes (before going public)

- Change `SESSION_SECRET_KEY`, `POSTGRES_PASSWORD`, `BOOTSTRAP_OPERATOR_PASSWORD`,
  `EXTERNAL_MODEL_API_KEY`, `LITELLM_MASTER_KEY` from the defaults.
- Do **not** publish internal ports (5432, 7233, 8000, 3000, 4000, 8001, 8002)
  to the public interface — only `PROXY_PORT`. In `docker-compose.yml`, internal
  services bind to `0.0.0.0`; on a hardened host, restrict their `ports:` to
  `127.0.0.1:<port>:<port>` or remove the `ports:` blocks entirely and rely on
  the nginx proxy.
- For HTTPS, put Caddy / Traefik / Nginx in front of `PROXY_PORT` with TLS.

---

## Quick one-liner summary (after Docker is installed)

```bash
git clone <REPO> forge-sdlc && cd forge-sdlc
cp .env.example .env && nano .env          # edit secrets + PROXY_PORT
docker compose -f docker-compose.yml build
docker compose -f docker-compose.yml up -d
docker compose -f docker-compose.yml ps
curl -s -o /dev/null -w "proxy login -> %{http_code}\n" -L http://localhost:80/login
```

Then open `http://<PUBLIC-IP>:80/login` and log in with your bootstrap operator
credentials.

Saved to: `docs/plan/linux-deployment.md`