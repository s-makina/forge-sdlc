# Deploying ForgeSDLC on a Linux Host (with remote access)

This guide deploys the full ForgeSDLC stack on a dedicated Linux machine (bare
metal, VM, or cloud VM) and makes it reachable from outside that box via port
forwarding. It assumes you are coming from a Windows/WSL2 dev box and want a
proper always-on Linux environment.

---

## 0. Quick summary

```
# On the Linux host
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 git

git clone <YOUR-REPO-URL> forge-sdlc
cd forge-sdlc

cp .env.example .env            # then edit ports / credentials
docker compose -f docker-compose.yml build
docker compose -f docker-compose.yml up -d
docker compose -f docker-compose.yml ps

# From your Windows machine
curl http://<LINUX-IP>:8081/health
# open http://<LINUX-IP>:8081/login in a browser
```

---

## 1. Provision the Linux host

Recommended minimums (the Python + Next.js stack is modest):

- OS: Ubuntu 22.04 or 24.04 LTS (or any distro with Docker Engine)
- CPU: 4 cores
- RAM: 8 GB (7.6 GB was enough on WSL; give it headroom)
- Disk: 40 GB
- Outbound internet: Docker needs to pull images on first build

### Install Docker Engine + Compose plugin

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Ubuntu 24.04 (noble). Adjust codename to your release if different.
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu noble stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

# Add your user to the docker group so you don't need sudo
sudo usermod -aG docker "$USER"
# log out and back in (or: newgrp docker)
```

Verify:

```bash
docker --version
docker compose version
docker info
```

Enable Docker on boot (so the stack survives reboots):

```bash
sudo systemctl enable --now docker
```

---

## 2. Get the code

```bash
git clone <YOUR-REPO-URL> forge-sdlc
cd forge-sdlc
git status                 # optional: confirm clean checkout
```

> **Line endings:** if you clone on Linux you get correct LF endings, so the
> `entrypoint.sh` scripts work out of the box (the CRLF problem we hit on the
> Windows checkout will not occur here).

---

## 3. Configure `.env`

Create a local (gitignored) `.env`:

```bash
cp .env.example .env
nano .env
```

A working local set (no port-80 conflict on a fresh box, so you *can* use 80):

```dotenv
# Front door: set PROXY_PORT=80 to serve the app on the standard HTTP port.
PROXY_PORT=80

# App / DB credentials — CHANGE THESE for anything beyond a sandbox.
POSTGRES_USER=forgesdlc
POSTGRES_PASSWORD=change-this-strong-password
POSTGRES_DB=forgesdlc

SESSION_SECRET_KEY=replace-with-a-long-random-string

BOOTSTRAP_OPERATOR_EMAIL=operator@forgesdlc.local
BOOTSTRAP_OPERATOR_PASSWORD=change-this-operator-password
```

Notes:

- `PROXY_PORT` is the single externally-reachable port (nginx fronts the whole
  app). On a dedicated box 80 is usually free; use `8081` only if 80 is taken.
- Every other service is internal on the Docker bridge network and does **not**
  need to be exposed publicly.
- Secrets are read at container start. If you change them after first boot, the
  bootstrap operator password will not retro-update — reset it in the DB or wipe
  the `postgres_data` volume and re-migrate.

---

## 4. Build and start the stack

Use `-f docker-compose.yml` **explicitly**. The repo also ships a
`docker-compose.override.yml` that runs dev-mode live reloads (mounts source,
`pnpm dev`) which is incompatible with the production standalone dashboard image.

```bash
# Build all images (first build pulls base images; allow several minutes)
docker compose -f docker-compose.yml build

# Start everything in the background
docker compose -f docker-compose.yml up -d

# Watch it come up
docker compose -f docker-compose.yml ps
```

Expected healthy set (roughly 9 containers):

| Service          | Internal port | Notes                          |
|------------------|---------------|--------------------------------|
| postgres         | 5432          | app + temporal DB              |
| redis            | 6379          |                                |
| api              | 8000          | runs migrations on entrypoint  |
| execution-manager| 8001          |                                |
| orchestrator     | 8002          | talks to temporal              |
| temporal         | 7233          | workflow engine                |
| temporal-ui      | 8080          | internal (optional to expose)  |
| dashboard        | 3000          | Next.js standalone             |
| proxy (nginx)    | **PROXY_PORT**| the only public port           |

> The compose file sets `restart: unless-stopped`, so the stack auto-recovers if
> the host restarts or the daemon bounces.

---

## 5. Verify locally on the Linux host

```bash
# API
curl -s -o /dev/null -w "api /health -> %{http_code}\n" http://localhost:8000/health
curl -s -o /dev/null -w "api /openapi -> %{http_code}\n" http://localhost:8000/openapi.json

# Dashboard through the proxy
curl -s -o /dev/null -w "proxy /login -> %{http_code}\n" -L http://localhost:PROXY_PORT/login
```

When `proxy /login` returns `200`, the end-to-end path
(nginx → dashboard → api → postgres) is working.

Default login (if you kept the `.env` above):

- **Email:** `operator@forgesdlc.local`
- **Password:** `change-this-operator-password`

---

## 6. Port forwarding so it's accessible from outside

Which steps you need depends on *where* the Linux host sits.

### A. Same LAN (Windows machine → Linux box on your network)

1. Find the Linux host's LAN IP:
   ```bash
   hostname -I
   # e.g. 192.168.1.50
   ```
2. Allow the port through the host firewall:
   ```bash
   sudo ufw allow PROXY_PORT/tcp    # if ufw is enabled
   sudo ufw enable
   sudo ufw status
   ```
3. From your Windows browser open:
   ```
   http://192.168.1.50:PROXY_PORT/login
   ```

No router changes needed if both machines are on the same subnet. If you want it
available on the *standard* port 80, set `PROXY_PORT=80` in `.env` and visit
`http://192.168.1.50/`.

### B. Linux host behind your home router (expose to the internet)

1. Give the Linux box a **static** DHCP reservation in the router admin panel
   (bind its MAC to a fixed LAN IP).
2. In the router's **Port Forwarding / Virtual Server** page, forward inbound
   `PROXY_PORT` (e.g. 8081) → `<LAN-IP>:8081` (TCP). If you set `PROXY_PORT=80`,
   forward `80 → <LAN-IP>:80`.
3. Confirm the public IP (or set a dynamic-DNS hostname):
   ```bash
   curl -s ifconfig.me
   ```
4. Open `http://<PUBLIC-IP>:PROXY_PORT/login`.
5. Optionally lock it down by restricting the source IP range or putting the app
   behind a VPN/reverse proxy (see Security below).

### C. Cloud VM (AWS / GCP / Azure)

- **AWS EC2:** Security Group → Inbound rule: `TCP PROXY_PORT` (or `80`) from
  `0.0.0.0/0` (public) or your IP. Also ensure the VM's OS firewall allows it
  (see `ufw` above). A typical EC2 security group also needs your SSH port (22).
- **GCP:** VPC Firewall rule → allow `tcp:PROXY_PORT` → tagged VMs.
- **Azure:** NSG Inbound → allow `PROXY_PORT` → the NIC/subnet.

### D. SSH tunnel (no open firewall port; handy for temporary access)

From your Windows machine (needs the Linux host's SSH and your user on it):

```bash
ssh -L 8081:localhost:PROXY_PORT user@<LINUX-IP>
```

Then open `http://localhost:8081/login` on the Windows box. The tunnel forwards
through SSH, so no firewall port is opened on the host.

---

## 7. Security notes (important if exposed publicly)

The stack ships dev defaults. Before exposing to the internet, change all of:

- `BOOTSTRAP_OPERATOR_PASSWORD` and create real user accounts.
- `SESSION_SECRET_KEY` (a long random string).
- `POSTGRES_PASSWORD`.
- Do **not** publish the internal ports (5432, 7233, 8000, 3000, 4000) to the
  public interface — only the `PROXY_PORT`. In `docker-compose.yml`, internal
  services bind to `0.0.0.0` for convenience; for a hardened box change their
  `ports:` to `127.0.0.1:<port>:<port>` or drop them and rely on the nginx proxy.

Recommended: put a real reverse proxy (Caddy/Traefik/nginx) in front with TLS and
auth, or run the whole thing behind a VPN (Tailscale/WireGuard) instead of opening
a raw port.

---

## 8. Useful operational commands

```bash
# Stop / start / restart
docker compose -f docker-compose.yml down
docker compose -f docker-compose.yml up -d

# Logs
docker compose -f docker-compose.yml logs -f api
docker compose -f docker-compose.yml logs -f temporal

# Rebuild after a code change
docker compose -f docker-compose.yml build api dashboard
docker compose -f docker-compose.yml up -d

# Wipe app DB and re-migrate from scratch (destroys data)
docker compose -f docker-compose.yml down -v
docker compose -f docker-compose.yml up -d
```

---

## 9. Troubleshooting

- **`ERR_CONNECTION_REFUSED`:** the stack was briefly down (restarting or the
  daemon bounced). Wait ~30 s and retry; `restart: unless-stopped` brings it back.
- **Dashboard returns 500 / `EvalError`:** you started it *with* the dev override
  (`docker compose up` without `-f docker-compose.yml`). Always use
  `-f docker-compose.yml` in production.
- **Temporal exits with `Unsupported driver 'DB=postgresql'`:** an old tag was in
  the compose file; current code uses `DB=postgres12` and `1.29.4`.
- **API exits `exec ./entrypoint.sh: no such file`:** the checkout had CRLF line
  endings; on Linux this does not happen.