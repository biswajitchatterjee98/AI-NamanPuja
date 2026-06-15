# NamanPuja AI Content Pipeline

Agentic content pipeline for generating, reviewing, and uploading SEO-optimized puja service pages to NamanPuja.com.

## Features

- LangGraph multi-agent pipeline (Content → Image → Humanizer → QC)
- Batch-level human review (approve / reject)
- Redis + RQ background workers for generation and upload
- MongoDB for pages, batches, and rejection feedback
- React admin dashboard
- Production-ready Docker deployment, health checks, API key auth, rate limiting

---

## Prerequisites

| Tool | Version | Used for |
|------|---------|----------|
| Docker + Docker Compose | Latest | Recommended local & prod deploy |
| Python | 3.11+ | Backend (local dev without Docker) |
| Node.js | 20+ | Frontend (local dev without Docker) |
| MongoDB | 7+ | Data store (or use Docker `mongo` service) |
| Redis | 7+ | Job queue + rate limiting (or use Docker `redis` service) |

**External accounts (production / real AI generation):**

| Service | Where to get it | Needed when |
|---------|-----------------|-------------|
| [Groq](https://console.groq.com/keys) | API key from Groq console | `LLM_PROVIDER=groq`, `USE_MOCK_LLM=false` |
| [Google Gemini](https://aistudio.google.com/apikey) | API key from Google AI Studio | Image generation; content fallback when Groq fails |
| [OpenAI](https://platform.openai.com/api-keys) | API key from OpenAI dashboard | `LLM_PROVIDER=openai` |
| NamanPuja CMS | Your website/backend team | `CMS_UPLOAD_ENABLED=true` |
| [AWS S3](https://aws.amazon.com/s3/) + CloudFront | AWS Console | `USE_S3_STORAGE=true` |

---

## Quick start

**Docker Desktop must be running** before you use Option A.

```bash
cd namanpuja
cp backend/.env.example backend/.env   # first time only
make dev
```

| Service | URL |
|---------|-----|
| Admin UI | http://localhost:5173 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Health | http://localhost:8000/api/v1/health/ready |

Stop: `Ctrl+C`, then `docker compose down`.

> **Do not mix Docker approaches.** If you use `make dev`, do **not** also run standalone `docker run` containers for MongoDB/Redis on ports `27017` / `6379` — that causes `port is already allocated` errors. Pick one method below.

---

## How to run

### Option A — Docker (recommended)

Starts API, worker, MongoDB, Redis, and frontend in one command. No local Python or Node install required.

```bash
make dev
```

Edit `backend/.env` before starting if you want real AI generation (Groq + Gemini keys). By default `.env.example` uses mock LLM.

Detached mode (runs in background):

```bash
docker compose up --build -d
docker compose logs -f    # follow logs
docker compose down       # stop
```

---

### Option B — Local development (no Docker for app code)

Use this when you want to run Python/Node directly on your machine. You still need MongoDB and Redis reachable on `localhost`.

**1. Install Python dependencies** (once):

```bash
make backend-install
# equivalent to:
# cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt
```

Or from the repo root:

```bash
pip install -r requirements.txt          # production deps only
pip install -r backend/requirements-dev.txt   # + pytest (recommended)
```

**2. Start MongoDB and Redis** — install locally, or run only these two in Docker:

```bash
docker run -d --name namanpuja-mongo -p 27017:27017 mongo:7
docker run -d --name namanpuja-redis -p 6379:6379 redis:7-alpine
```

Do **not** run `make dev` if you use this approach.

**3. Configure environment:**

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

**4. Run three processes** (three terminals):

Terminal 1 — API:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 — worker (required for batch generation):

```bash
cd backend
source .venv/bin/activate
python worker.py
```

Terminal 3 — frontend:

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to the backend.

---

### Option C — Production (Docker)

```bash
cp backend/.env.production.example backend/.env
# Edit backend/.env — see Environment variables section below
make prod
```

| Service | Default port |
|---------|----------------|
| API | http://localhost:8000 |
| Admin (nginx) | http://localhost:8080 |

Build frontend with API key for production:

```bash
cd frontend
docker build \
  --build-arg VITE_API_BASE_URL=/api/v1 \
  --build-arg VITE_API_KEY=your-production-api-key \
  -t namanpuja-admin .
```

See [infra/PRODUCTION.md](infra/PRODUCTION.md) for Atlas, managed Redis, TLS, and monitoring.

---

## Python dependencies

| File | Purpose |
|------|---------|
| `backend/requirements.txt` | **Canonical** production list — used by the API/worker Docker image |
| `backend/requirements-dev.txt` | Dev extras (`pytest`, etc.); includes production deps via `-r requirements.txt` |
| `requirements.txt` (repo root) | Convenience alias — points to `backend/requirements.txt` so you can run `pip install -r requirements.txt` from the project root |

Install for local backend development:

```bash
make backend-install
```

Or manually:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

> **Note:** There is no separate `pip-install.txt`. Install steps live in this README to avoid duplicating the same instructions in two places.

---

## Environment setup

You need **two** env files:

| File | Purpose |
|------|---------|
| `backend/.env` | API + workers (main configuration) |
| `frontend/.env` | Admin UI (API URL + optional API key) |

Copy from examples:

```bash
cp backend/.env.example backend/.env              # development
cp backend/.env.production.example backend/.env   # production
cp frontend/.env.example frontend/.env
```

---

## Backend environment variables

### Required by scenario

| Scenario | Must set |
|----------|----------|
| **Local dev (Docker, default)** | Nothing — `.env.example` works as-is (mock LLM) |
| **Local dev (real AI)** | `GROQ_API_KEY` and/or `GEMINI_API_KEY`, `LLM_PROVIDER=groq`, `USE_MOCK_LLM=false` |
| **Production** | Valid LLM keys, `API_KEYS` (32+ chars), `ENFORCE_AUTH=true` |
| **Production + CMS upload** | Above + `CMS_BASE_URL`, `CMS_API_KEY`, `CMS_UPLOAD_ENABLED=true` |
| **Production + S3 images** | Above + `S3_BUCKET`, `S3_PUBLIC_BASE_URL`, `USE_S3_STORAGE=true` |

---

### Application

| Variable | Default | Required | Where to get / what to set |
|----------|---------|----------|----------------------------|
| `APP_ENV` | `development` | Yes (prod) | `development` for local; `production` for live deploy. Controls secret validation and security headers. |
| `APP_HOST` | `0.0.0.0` | No | Bind address inside the container/process. Keep `0.0.0.0` for Docker. |
| `APP_PORT` | `8000` | No | API port. Match your reverse proxy / Docker port mapping. |

---

### MongoDB

| Variable | Default | Required | Where to get / what to set |
|----------|---------|----------|----------------------------|
| `MONGODB_URI` | `mongodb://localhost:27017` | Yes | **Docker dev:** `mongodb://mongo:27017` (set automatically in `docker-compose.yml`). **Local:** `mongodb://localhost:27017`. **Production:** [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) → Connect → connection string, e.g. `mongodb+srv://user:pass@cluster.mongodb.net` |
| `MONGODB_DATABASE` | `namanpuja` | No | Database name. Use one per environment (`namanpuja_dev`, `namanpuja_prod`). |

---

### LLM (content generation)

| Variable | Default | Required | Where to get / what to set |
|----------|---------|----------|----------------------------|
| `LLM_PROVIDER` | `mock` | No | `mock` \| `groq` \| `openai` |
| `USE_MOCK_LLM` | `true` | No | `true` = fake content (dev/CI). `false` = real AI; requires provider keys below. |
| `GROQ_API_KEY` | *(empty)* | If `LLM_PROVIDER=groq` | [console.groq.com/keys](https://console.groq.com/keys) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | No | Groq model ID for content generation |
| `GEMINI_API_KEY` | *(empty)* | For images + fallback | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `GEMINI_CONTENT_MODEL` | `gemini-2.0-flash` | No | Gemini model for content fallback |
| `GEMINI_IMAGE_MODEL` | `gemini-2.0-flash-preview-image-generation` | No | Primary image generation model |
| `OPENAI_API_KEY` | *(empty)* | If `LLM_PROVIDER=openai` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `OPENAI_MODEL` | `gpt-4o-mini` | No | OpenAI model ID |

---

### Redis (job queue)

| Variable | Default | Required | Where to get / what to set |
|----------|---------|----------|----------------------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Yes | **Docker dev:** `redis://redis:6379/0`. **Local:** `redis://localhost:6379/0`. **Production:** [Upstash](https://upstash.com/), AWS ElastiCache, or Redis Cloud URL, e.g. `redis://:password@host:6379/0` |
| `WORKER_QUEUE` | `batch_generation` | No | Queue name for generation jobs. Do not change unless you customize workers. |
| `JOB_MAX_RETRIES` | `3` | No | How many times failed generation/upload jobs retry (30s → 2m → 5m backoff). |

---

### CMS (upload to NamanPuja.com)

| Variable | Default | Required | Where to get / what to set |
|----------|---------|----------|----------------------------|
| `CMS_BASE_URL` | *(empty)* | Yes if upload enabled | Base URL of your CMS API from your web team, e.g. `https://cms.namanpuja.com/api` or WordPress REST `https://namanpuja.com/wp-json/wp/v2` |
| `CMS_API_KEY` | *(empty)* | Yes if upload enabled | Bearer token or API key from CMS admin / your backend team. Used as `Authorization: Bearer <key>`. |
| `CMS_UPLOAD_ENABLED` | `false` | No | `false` = generate & review only, no live upload (safe for dev). `true` = approved batches POST to `{CMS_BASE_URL}/pages`. |

---

### Image storage

| Variable | Default | Required | Where to get / what to set |
|----------|---------|----------|----------------------------|
| `USE_S3_STORAGE` | `false` | No | `false` = save images under `LOCAL_IMAGE_DIR`. `true` = upload to S3 (production). |
| `AWS_REGION` | `us-east-1` | If S3 | AWS region where bucket lives, e.g. `us-east-1`, `ap-south-1`. |
| `S3_BUCKET` | *(empty)* | If S3 | [AWS S3 Console](https://s3.console.aws.amazon.com/) → Create bucket, e.g. `namanpuja-production-assets`. |
| `S3_PUBLIC_BASE_URL` | *(empty)* | If S3 | Public URL for images — usually [CloudFront](https://aws.amazon.com/cloudfront/) distribution, e.g. `https://cdn.namanpuja.com`. Page docs store `{CDN}/pages/{filename}`. |
| `LOCAL_IMAGE_DIR` | `../frontend/public/images` | If not S3 | **Docker:** `/app/images` (mounted volume). **Local:** `../frontend/public/images` so Vite serves them at `/images/...`. |

**AWS credentials:** The API uses the default AWS credential chain (env vars `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`, or IAM role on EC2/ECS). Not in `.env.example` but required for S3 in production.

---

### Security & CORS

| Variable | Default | Required | Where to get / what to set |
|----------|---------|----------|----------------------------|
| `ALLOWED_ORIGINS` | `http://localhost:5173` | Yes (prod) | Comma-separated admin UI origins for CORS. Dev: `http://localhost:5173`. Prod: `https://admin.namanpuja.com` |
| `API_KEYS` | `dev-api-key` | Yes (prod) | Secret key(s) for `X-API-Key` header. Generate with `openssl rand -hex 32`. Comma-separate for rotation. **Min 16 chars; no placeholders in production.** |
| `ENFORCE_AUTH` | `false` | Yes (prod) | `false` = open API (dev only). `true` = every batch route requires `X-API-Key`. |
| `TRUSTED_HOSTS` | *(empty)* | Prod recommended | Comma-separated hostnames the API accepts, e.g. `api.namanpuja.com,admin.namanpuja.com`. Prevents host-header attacks. |
| `TRUSTED_PROXY_IPS` | *(empty)* | If behind LB | Private IPs/CIDRs of your load balancer so rate limiting uses real client IP from `X-Forwarded-For`, e.g. `10.0.0.0/8,172.16.0.0/12`. |

---

### Rate limiting

| Variable | Default | Required | Where to get / what to set |
|----------|---------|----------|----------------------------|
| `RATE_LIMIT_ENABLED` | `true` | No | `true` = limit requests per minute per API key / IP. |
| `RATE_LIMIT_PER_MINUTE` | `120` | No | Max requests per minute per client. Increase for busy admin teams. |
| `RATE_LIMIT_FAIL_CLOSED` | `true` | No | `true` = reject requests if Redis is down (production default). `false` = allow through if Redis fails (dev only). |

---

### Pipeline tuning

| Variable | Default | Required | Where to get / what to set |
|----------|---------|----------|----------------------------|
| `BATCH_STUCK_MINUTES` | `30` | No | Alert threshold for `monitor.py` — batches stuck in `GENERATING` longer than this are logged as errors. |
| `PIPELINE_MAX_WORKERS` | `4` | No | Parallel LLM calls per pipeline stage. Increase for faster large batches; watch OpenAI rate limits and cost. |

---

## Frontend environment variables

Create `frontend/.env` from `frontend/.env.example`:

| Variable | Default | Required | Where to get / what to set |
|----------|---------|----------|----------------------------|
| `VITE_API_BASE_URL` | `/api/v1` | Yes | **Docker dev (Vite):** `http://localhost:8000/api/v1`. **Prod nginx build:** `/api/v1` (nginx proxies `/api` → API). |
| `VITE_API_KEY` | *(empty)* | If `ENFORCE_AUTH=true` | Same value as one of `API_KEYS` in `backend/.env`. Baked into the JS bundle at **build time** — rebuild frontend after changing. |

> **Note:** `VITE_*` variables are embedded in the static build. Anyone with access to the admin URL can extract the key. Put the admin UI behind VPN or SSO in production.

---

## Example configurations

### Minimal local dev (no OpenAI, no upload)

`backend/.env`:

```env
USE_MOCK_LLM=true
ENFORCE_AUTH=false
CMS_UPLOAD_ENABLED=false
USE_S3_STORAGE=false
```

`frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

---

### Local dev with real AI (Groq + Gemini)

`backend/.env`:

```env
LLM_PROVIDER=groq
USE_MOCK_LLM=false
GROQ_API_KEY=gsk_xxxxxxxx
GEMINI_API_KEY=xxxxxxxx
ENFORCE_AUTH=false
CMS_UPLOAD_ENABLED=false
```

---

### Production checklist

`backend/.env`:

```env
APP_ENV=production
USE_MOCK_LLM=false
OPENAI_API_KEY=sk-proj-xxxxxxxx
ENFORCE_AUTH=true
API_KEYS=<openssl rand -hex 32>
ALLOWED_ORIGINS=https://admin.namanpuja.com
TRUSTED_HOSTS=api.namanpuja.com,admin.namanpuja.com
CMS_UPLOAD_ENABLED=true
CMS_BASE_URL=https://your-cms-api.example.com
CMS_API_KEY=<from CMS team>
USE_S3_STORAGE=true
S3_BUCKET=namanpuja-assets
S3_PUBLIC_BASE_URL=https://cdn.namanpuja.com
MONGODB_URI=mongodb+srv://...
REDIS_URL=redis://...
```

`frontend/.env` (at build time):

```env
VITE_API_BASE_URL=/api/v1
VITE_API_KEY=<same as API_KEYS>
```

---

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/batch/create` | Create batch and enqueue generation |
| `GET` | `/api/v1/batch/{id}` | Batch detail with pages |
| `GET` | `/api/v1/batches` | List batches |
| `POST` | `/api/v1/batch/{id}/approve` | Approve and enqueue upload |
| `POST` | `/api/v1/batch/{id}/reject` | Reject with feedback |
| `POST` | `/api/v1/batch/{id}/upload` | Retry upload (requires `APPROVED` or `UPLOAD_PARTIAL`) |
| `POST` | `/api/v1/batch/{id}/regenerate` | Regenerate rejected/failed batch |

Authenticated requests (when `ENFORCE_AUTH=true`):

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/batches
```

---

## Makefile commands

| Command | Description |
|---------|-------------|
| `make dev` | Start full stack (Docker, development) |
| `make prod` | Start production compose (detached) |
| `make test` | Run backend tests |
| `make monitor` | Check for stuck batches (exit 1 if found) |
| `make backend-install` | Create venv + install Python deps |
| `make frontend-install` | `npm ci` in frontend |

---

## Tests

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
USE_MOCK_LLM=true ENFORCE_AUTH=false pytest -q
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Cannot connect to the Docker daemon` | Start **Docker Desktop** and wait until it is fully running |
| `port is already allocated` (6379 / 27017) | Stop conflicting containers: `docker stop namanpuja-mongo namanpuja-redis` then `docker rm ...`, or run only `make dev` — not both |
| `uvicorn: command not found` | Activate venv and install deps: `cd backend && source .venv/bin/activate && pip install -r requirements-dev.txt` |
| Batch stays `PENDING` / `GENERATING` | Ensure `python worker.py` is running (or Docker `worker` service) |
| `401 Unauthorized` on API | Set `X-API-Key` header; match `API_KEYS` in backend `.env` |
| `503` on `/health/ready` | MongoDB or Redis not reachable — check `MONGODB_URI` / `REDIS_URL` |
| Production API won't start | Placeholder secrets — use real `API_KEYS` (32+ chars) and valid LLM keys |
| Frontend can't reach API | Check `VITE_API_BASE_URL` and `ALLOWED_ORIGINS` includes frontend URL |
| Upload does nothing | `CMS_UPLOAD_ENABLED=false` skips upload by design; enable and set CMS vars |

---

## Further reading

- [infra/PRODUCTION.md](infra/PRODUCTION.md) — deployment checklist, workers, monitoring, TLS
