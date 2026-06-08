# NamanPuja AI Content Pipeline

Agentic content pipeline for generating, reviewing, and uploading SEO-optimized puja service pages to NamanPuja.com.

## Features

- LangGraph multi-agent pipeline (Content → Image → Humanizer → QC)
- Batch-level human review (approve / reject)
- Redis + RQ background workers for generation and upload
- MongoDB for pages, batches, and rejection feedback
- React admin dashboard
- Production-ready Docker deployment, health checks, API key auth, rate limiting

## Quick start (Docker)

```bash
cd namanpuja
cp backend/.env.example backend/.env
make dev
```

- API: http://localhost:8000
- Admin UI: http://localhost:5173
- API docs (dev): http://localhost:8000/docs

## Local development (without Docker)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Start MongoDB and Redis locally
uvicorn app.main:app --reload
python worker.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/batch/create` | Create batch and enqueue generation |
| GET | `/api/v1/batch/{id}` | Batch detail with pages |
| GET | `/api/v1/batches` | List batches |
| POST | `/api/v1/batch/{id}/approve` | Approve and enqueue upload |
| POST | `/api/v1/batch/{id}/reject` | Reject with feedback |
| POST | `/api/v1/batch/{id}/upload` | Manual upload trigger |
| POST | `/api/v1/batch/{id}/regenerate` | Regenerate rejected batch |

## Production hardening

- Separate generation/upload workers
- API key auth with production secret validation
- Rate limiting (fail-closed in production)
- HTML sanitization (server + client)
- Job retries with RQ
- Stuck-batch monitor (`make monitor`)
- nginx SPA frontend with API proxy
- Partial upload handling (`UPLOAD_PARTIAL` status)

See [infra/PRODUCTION.md](infra/PRODUCTION.md).

```bash
cp backend/.env.production.example backend/.env
make prod
```

## Tests

```bash
cd backend
pytest -q
```

Set `USE_MOCK_LLM=true` for local/CI runs without OpenAI credentials.
