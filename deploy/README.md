# Server Deployment Guide

> **Target**: Linux ARM64 server running Podman + podman-compose

---

## Prerequisites

Install Podman and podman-compose on the server:

```bash
# Debian/Ubuntu ARM64
sudo apt-get update && sudo apt-get install -y podman

# Install podman-compose
pip3 install podman-compose
```

---

## First-Time Setup

### 1. Authenticate with GHCR

```bash
# Use a GitHub Personal Access Token with read:packages scope
echo $GHCR_TOKEN | podman login ghcr.io -u <github-username> --password-stdin
```

### 2. Create the project directory and env file

```bash
mkdir -p ~/tradekub
cd ~/tradekub
```

Create `~/tradekub/api.env`:

```env
DATABASE_HOSTNAME=postgres
DATABASE_PORT=5432
DATABASE_USERNAME=tradekub
DATABASE_PASSWORD=<strong-password>
DATABASE_NAME=tradekub
SECRET_KEY=<generate-with: openssl rand -hex 32>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
NEWS_DATA_API_KEY=<your-newsdata-api-key>
GUNICORN_WORKERS=2
```

### 3. Copy the compose file to the server

```bash
scp podman-compose.yml user@server:~/tradekub/
```

### 4. Pull images and start services

```bash
cd ~/tradekub
podman-compose -f podman-compose.yml pull
podman-compose -f podman-compose.yml up -d
```

### 5. Run initial DB migrations

```bash
podman run --rm \
  --env-file ~/tradekub/api.env \
  ghcr.io/bukharney/tradekub_api:latest \
  alembic upgrade head
```

---

## GitHub Actions Secrets Required

Add these in the GitHub repo → **Settings → Secrets and variables → Actions**:

| Secret | Value |
|---|---|
| `SSH_HOST` | Server IP or hostname |
| `SSH_USER` | SSH login username (e.g. `ubuntu`) |
| `SSH_KEY` | Contents of your private SSH key (`~/.ssh/id_ed25519`) |
| `SSH_PORT` | SSH port (default `22`, can omit) |

---

## Updating / Rolling Deployments

On every push to `main`, GitHub Actions will:
1. Run tests
2. Build & push a new `linux/arm64` image to GHCR
3. SSH into the server, pull the new image, run `alembic upgrade head`, restart the `api` container

**Manual update** (if needed):

```bash
cd ~/tradekub
podman pull ghcr.io/bukharney/tradekub_api:latest
podman run --rm --env-file api.env ghcr.io/bukharney/tradekub_api:latest alembic upgrade head
podman-compose -f podman-compose.yml up -d --pull=never api
```

---

## Logs & Monitoring

```bash
# Live API logs
podman-compose -f podman-compose.yml logs -f api

# Postgres logs
podman-compose -f podman-compose.yml logs -f postgres

# Container status
podman ps
```

---

## Reverse Proxy (nginx on host)

Point your host nginx to the API container:

```nginx
server {
    listen 443 ssl;
    server_name api.tradekub.me;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
