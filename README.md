# Family AI Companion Monorepo

Arabic-first parenting assistant MVP with a FastAPI backend, Next.js web app, RAG knowledge base, and production-ready Docker Compose deployment for a single VM (Lightsail / EC2). Designed to keep operating costs low while enabling an easy migration to managed services (Amazon RDS, App Runner) later.

## Repository layout
```
family-ai/
  docker-compose.yml           # Production-ready stack (nginx, certbot, web, server, postgres, backup)
  .env.example                 # Copy to .env and fill in secrets
  ops/                         # Deployment, nginx, certbot, backup assets
  server/                      # FastAPI application, RAG pipeline, tests
  web/                         # Next.js 14 frontend (TypeScript, App Router)
  shared/                      # Shared OpenAPI + TypeScript contract
  sample_corpus/               # Example bilingual parenting docs
```

## Prerequisites
- Docker Engine 24+
- Docker Compose plugin
- Node.js 20+ (only if running the frontend outside Docker)
- Python 3.11+ (only if you prefer running the API without Docker)

## Quick start (local Docker)
1. `cp .env.example .env` and update secrets (OpenAI key, JWT secret, domain, AWS credentials if using backups).
2. For local iterations set in `.env`:
   - `VECTOR_BACKEND=chroma`
   - `DATABASE_URL=sqlite:////app/data/app.db`
   - (Chromadb currently requires NumPy < 2.0; this pin is already handled in `server/pyproject.toml`.)
   - `CHAT_MODEL=gpt-4o-mini` (or another OpenAI chat model you have access to).
   - `NGINX_HTTP_PORT` / `NGINX_HTTPS_PORT` if your host already uses 80/443 (e.g. `8080` / `8443`).
   - `NGINX_CONF_PATH=./ops/nginx/nginx.conf` for the HTTP-only proxy.
3. `docker compose build`
4. `docker compose up -d`
5. Open `http://localhost:NGINX_HTTP_PORT`.

For production TLS, switch to `NGINX_CONF_PATH=./ops/nginx/nginx.prod.conf`, run `docker compose up -d`, then follow the certbot steps to obtain certificates before exposing port 443.

Useful commands:
- `docker compose logs -f server` — API logs
- `docker compose logs -f nginx` — reverse proxy + TLS logs
- `docker compose exec server pytest` — run backend tests (retrieval and safety heuristics)
- `docker compose exec server alembic upgrade head` — run database migrations
- `curl -s http://localhost/api/admin/households | jq` — list recent households (DEV helper)
- `python tools/list_households.py --base-url http://127.0.0.1:8080/api` — same as above, formatted table (add `--json` for raw output). If the script cannot reach Docker (some shells block the socket), run `docker compose exec server python tools/list_households.py --base-url http://nginx/api` instead.
- `docker compose exec db psql -U family -d familyai -c "SELECT id, name, language_preference, country, created_at FROM households ORDER BY created_at DESC LIMIT 20;"` — inspect households via psql

### Household chat secrets

Household login in the chat UI uses a shared secret stored in the database. Set or rotate it with the helper script (run inside the server container so it has the right environment):

```bash
docker compose exec server python -m app.scripts.set_household_secret HOUSEHOLD_ID NEW_SECRET

# example
docker compose exec server python -m app.scripts.set_household_secret aousabdo_family family-2024
```

Share the chosen secret with that household; after logging in via the modal the app will claim any guest threads created from the same browser.


## Sample corpus ingestion
Populate the vector store with the provided bilingual parenting corpus:
```bash
docker compose exec server python -m app.scripts.seed_sample
```
The script parses Markdown front matter for metadata (topic, age_range, tone, country, language) and stores embeddings using the configured backend (`VECTOR_BACKEND`).

## Switching vector backends
- **pgvector (default)**: Runs on the `pgvector/pgvector:pg16` image. Ensure `DATABASE_URL` points to Postgres and `VECTOR_BACKEND=pgvector`.
- **Chroma (ultra-lean dev)**: Set `VECTOR_BACKEND=chroma` and `DATABASE_URL=sqlite:///data/app.db`. The `server` container mounts `chroma_data` for persistence. Backups automatically archive `/data/chroma` when Chroma is active.

## Auth & safety
- JWT tokens generated via `/api/profile` include `is_admin` claims for admin routes (`/api/admin/upload`).
- `app/core/safety.py` implements pre/post lexical guardrails; failing checks mark responses with `needs_human` and short-circuit high-risk user prompts.

## Backups
- Nightly cron inside the `backup` service runs `/opt/backup/backup_to_s3.sh`, taking a compressed `pg_dump` and optionally archiving Chroma vectors.
- Trigger ad-hoc backup: `docker compose exec backup /opt/backup/backup_to_s3.sh`
- Restoring Postgres: `docker compose exec db pg_restore -d $POSTGRES_DB /path/to/dump`

## TLS and nginx
- `ops/certbot/init_renew.sh` bootstraps and renews certificates using HTTP-01. Ensure `DOMAIN` and `LETSENCRYPT_EMAIL` are set before the first run.
- Local development uses `ops/nginx/nginx.conf` (HTTP only); for HTTPS in production set `NGINX_CONF_PATH=./ops/nginx/nginx.prod.conf` and update the domain inside that file.
- After obtaining certificates (`docker compose run --rm certbot`), reload nginx with `docker compose exec nginx nginx -s reload`.

## Deployment checklist (single VM)
1. Provision Ubuntu Lightsail/EC2, attach static IP, configure DNS A record.
2. Secure the box (updates, UFW) and install Docker (see `ops/deploy/provision.md`).
3. Copy repo to `/opt/family-ai`, provide `.env`, make backup/certbot scripts executable.
4. `docker compose pull && docker compose build && docker compose up -d`
5. Run certbot once: `docker compose run --rm certbot` then reload nginx.
6. Enable systemd unit (`ops/deploy/systemd-family-ai.service`) for auto-start on boot.

## Frontend notes
- Next.js App Router with Arabic-first layout, persona + dialect toggles, admin upload form, and profile management.
- API base URL configured via `NEXT_PUBLIC_API_BASE_URL` to support future App Runner or external API deployments.

### Chat memory & household login
- Each conversation thread is persisted (guest = browser-scoped, logged-in = household-scoped) and automatically replayed when you reopen it.
- The chat UI stores a `browser_id` per tab and calls `/api/chat/new`, `/api/chat/history`, `/api/chat/threads`, and `/api/chat/claim` to manage threads.
- Household members can log in via the chat modal using the shared secret set with `set_household_secret.py`; after login the app claims guest threads for that household so they are available across devices.

## Backend notes
- FastAPI modular routers: chat, profile CRUD, tips, admin upload.
- RAG abstraction supports pgvector or Chroma; ingestion pipeline stores metadata + embeddings.
- OpenAPI schema shared at `shared/openapi/schema.json`, generated typings in `shared/types/api.d.ts` and consumed by the web client.

## Testing & linting
```bash
# Backend
cd server && poetry install && pytest
poetry run ruff check app

# Frontend
cd web && npm install
npm run lint
npm run build
```

## REST to managed services
- **Amazon RDS**: provision a Postgres instance, set `DATABASE_URL`, and remove the `db` service from `docker-compose.yml`.
- **AWS App Runner**: build & push the `ops/docker/Dockerfile.server` image to ECR, deploy to App Runner, and update `NEXT_PUBLIC_API_BASE_URL` for the frontend.
- `ops/deploy/provision.md` covers the VM path today and notes the migration steps for tomorrow.
