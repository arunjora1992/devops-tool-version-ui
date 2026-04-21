# DevOps Tools Version Dashboard

A self-hosted web dashboard that tracks the **latest stable** and **N-1 (previous stable)** versions of 21 popular DevOps tools. Version data is fetched live from GitHub Releases, GitHub Tags, and Docker Hub APIs with a 1-hour cache. Export the full list to **CSV** or **PDF** in one click.

---

## Features

- **21 DevOps tools** across 10 categories — container orchestration, databases, messaging, IaC, monitoring, and more
- **Live version data** fetched from GitHub and Docker Hub APIs (no manual updates needed)
- **N-1 tracking** — see both the current stable release and the previous one side by side
- **Category filter pills** — click to narrow the table by tool category
- **Full-text search** — search by tool name, category, or version string
- **Column sorting** — click any header to sort ascending/descending
- **Export to CSV** — download a spreadsheet of all versions
- **Export to PDF** — download a formatted report
- **1-hour TTL cache** — all 21 tools fetched in parallel, cached to avoid hitting API rate limits
- **Force refresh** — manual refresh button bypasses the cache on demand
- **Docker Compose** deployment — single command to start the full stack

---

## Tools Tracked

| Tool | Category | Data Source |
|------|----------|-------------|
| Kubernetes | Container Orchestration | GitHub Releases |
| OpenShift OKD | Container Orchestration | GitHub Releases |
| Docker Engine | Containerization | GitHub Releases |
| Docker Compose | Containerization | GitHub Releases |
| Helm | Package Manager | GitHub Releases |
| Apache Kafka | Message Streaming | GitHub Tags |
| RabbitMQ | Message Broker | GitHub Releases |
| Apache NiFi | Data Integration | GitHub Tags |
| Redis | Cache / Database | GitHub Releases |
| MySQL Community | Database | Docker Hub |
| PostgreSQL | Database | GitHub Tags |
| Elasticsearch | Search Engine | GitHub Releases |
| JupyterLab | Data Science IDE | GitHub Releases |
| Terraform | IaC | GitHub Releases |
| Ansible | Config Management | GitHub Releases |
| ArgoCD | GitOps | GitHub Releases |
| Prometheus | Monitoring | GitHub Releases |
| Grafana | Visualization | GitHub Releases |
| Jenkins | CI/CD | GitHub Releases |
| Nginx | Web Server | GitHub Tags |
| VMware vSphere | Virtualization | Static (manually maintained) |

---

## Architecture

```
┌─────────────────────────────────────┐
│         Browser (port 3000)         │
│    Vanilla JS + Tailwind CSS         │
└──────────────┬──────────────────────┘
               │ /api/*
┌──────────────▼──────────────────────┐
│      nginx (frontend container)     │
│       Reverse proxy + static        │
└──────────────┬──────────────────────┘
               │ proxy_pass
┌──────────────▼──────────────────────┐
│    FastAPI backend (port 8000)      │
│  Async fetcher · Cache · Exporter  │
└──────────┬──────────────────────────┘
           │
    ┌──────┴────────┐
    │               │
GitHub API     Docker Hub API
(20 tools)     (MySQL)
```

**Stack:**
- **Backend:** Python 3.11 · FastAPI · httpx (async) · ReportLab (PDF)
- **Frontend:** Vanilla JS · Tailwind CSS CDN · Font Awesome CDN
- **Server:** nginx:alpine serving static files + proxying `/api/*`
- **Deployment:** Docker Compose

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 20.10+
- [Docker Compose](https://docs.docker.com/compose/install/) v2+
- A GitHub Personal Access Token *(recommended — free, no scopes needed)*

---

## Quick Start

```bash
# 1. Clone the repo
git clone git@github.com:arunjora1992/devops-tool-version-ui.git
cd devops-tool-version-ui

# 2. Configure environment
cp .env.example .env
# Edit .env and add your GITHUB_TOKEN (see below)

# 3. Start the stack
docker compose up -d

# 4. Open the dashboard
open http://localhost:3000
```

---

## Configuration

Copy `.env.example` to `.env` and set the values:

```env
# GitHub Personal Access Token — STRONGLY recommended
# Without it, GitHub allows only 60 API requests/hour per IP.
# With it: 5,000 requests/hour. No scopes needed (reads public repos only).
# Create one at: https://github.com/settings/tokens
GITHUB_TOKEN=ghp_your_token_here

# Port exposed by the dashboard (default: 3000)
DASHBOARD_PORT=3000

# How often to re-fetch version data in seconds (default: 3600 = 1 hour)
CACHE_TTL_SECONDS=3600

# Corporate proxy — leave empty if not needed
# HTTP_PROXY=http://proxy.corp.example.com:8080
# HTTPS_PROXY=http://proxy.corp.example.com:8080
```

### GitHub Token Setup

1. Go to [https://github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **"Generate new token (classic)"**
3. Give it a name (e.g., `devops-dashboard`)
4. **Select no scopes** — the dashboard only reads public repo data
5. Click **Generate token** and copy it to `GITHUB_TOKEN` in your `.env`

> Without a token the dashboard still works, but the GitHub API rate limit (60 req/hr per IP) may be hit when all 21 tools are fetched simultaneously.

---

## API Endpoints

The backend exposes these endpoints (also accessible via nginx proxy at port 3000):

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/versions` | All tool versions (uses cache) |
| `GET` | `/api/versions/refresh` | Force-refresh cache and return fresh data |
| `GET` | `/api/export/csv` | Download versions as CSV |
| `GET` | `/api/export/pdf` | Download versions as PDF |
| `GET` | `/health` | Backend health check |

---

## Project Structure

```
devops-tool-version-ui/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py          # FastAPI routes
│   ├── tools.py         # Tool definitions (21 tools, repos, categories)
│   ├── fetcher.py       # Async GitHub + Docker Hub fetcher with TTL cache
│   └── exporter.py      # CSV and PDF generation (ReportLab)
└── frontend/
    ├── Dockerfile
    ├── nginx.conf        # Static serving + /api/* reverse proxy
    ├── index.html
    ├── style.css         # Dark theme with CSS custom properties
    └── app.js            # Fetch, render, filter, sort, export
```

---

## Docker Compose Commands

```bash
# Start in background
docker compose up -d

# View logs
docker compose logs -f

# Rebuild after code changes
docker compose up -d --build

# Stop
docker compose down

# Stop and remove volumes
docker compose down -v
```

---

## Updating VMware vSphere Versions

VMware does not provide a public API for version data. Update the static entries manually in `backend/tools.py`:

```python
{
    "name": "VMware vSphere",
    "source": "static",
    "versions": [
        {"version": "8.0 Update 3", "release_date": "2024-07-02"},
        {"version": "8.0 Update 2", "release_date": "2023-12-14"},
    ],
}
```

After editing, rebuild the backend:

```bash
docker compose up -d --build backend
```

---

## Adding New Tools

Add an entry to the `TOOLS` list in `backend/tools.py`:

```python
{
    "name": "My Tool",
    "category": "My Category",
    "icon": "🔧",
    "source": "github_releases",   # github_releases | github_tags | dockerhub | static
    "repo": "owner/repo",
    "homepage": "https://mytool.io/releases",
}
```

Available `source` types:

| Source | Description |
|--------|-------------|
| `github_releases` | Fetches from GitHub Releases API (stable only, skips pre-releases) |
| `github_tags` | Fetches from GitHub Tags API (filters rc/alpha/beta by name) |
| `dockerhub` | Fetches from Docker Hub tags, sorted by semver descending |
| `static` | Hardcoded `versions` list (for tools without a public API) |

---

## License

MIT
