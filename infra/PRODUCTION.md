# NamanPuja Content Pipeline — Production Guide

The API **refuses to start** in `APP_ENV=production` with placeholder secrets, weak API keys, or missing required configuration.

## Checklist

### Database
- Prefer **MongoDB Atlas** replica set with automated backups
- Self-hosted `mongo` in `docker-compose.prod.yml` is for single-host staging only
- Indexes are created automatically on API startup

### Redis
- Use managed Redis with persistence (AOF)
- Required for background jobs and rate limiting
- Rate limiter **fails closed** in production when Redis is unavailable

### Secrets
- `API_KEYS` — 32+ character random keys (comma-separated for rotation)
- `OPENAI_API_KEY` — production key with spend limits
- `CMS_API_KEY` — required when `CMS_UPLOAD_ENABLED=true`
- `S3_BUCKET` + `S3_PUBLIC_BASE_URL` — required when `USE_S3_STORAGE=true`
- Store in AWS Secrets Manager / Doppler; never commit `.env`

### Workers
Run **separate worker processes** per queue (configured in `docker-compose.prod.yml`):
- `worker-generation` → `batch_generation`
- `worker-upload` → `batch_upload`

### Stuck batch monitoring
Run `python monitor.py` on a schedule (cron/Kubernetes CronJob). Exits non-zero when batches remain in `GENERATING` longer than `BATCH_STUCK_MINUTES`.

```bash
make monitor
```

### CMS
- Set `CMS_BASE_URL` to NamanPuja CMS API
- Set `CMS_UPLOAD_ENABLED=true` only when endpoint is verified
- Partial upload failures set status to `UPLOAD_PARTIAL`; full failures keep `APPROVED` for retry

### Images
- Set `USE_S3_STORAGE=true` with CloudFront CDN URL
- Readiness probe includes S3 when storage is enabled

### Auth
- `ENFORCE_AUTH=true`
- Admin UI sends `X-API-Key` via `VITE_API_KEY` at **build time**
- Place admin UI behind VPN or SSO gateway — API keys in static bundles are extractable

### Reverse proxy
- Terminate TLS at nginx/ALB
- Set `TRUSTED_PROXY_IPS` to your load balancer subnet
- Uvicorn uses restricted `forwarded-allow-ips` in prod compose

### Hardening
- OpenAPI docs disabled in production
- Security headers including Content-Security-Policy
- Optional `TRUSTED_HOSTS` allowlist
- HTML sanitized server-side (bleach) and client-side (DOMPurify)
- `/health/dependencies` requires auth when `ENFORCE_AUTH=true`

### Health probes
- **Liveness:** `GET /api/v1/health`
- **Readiness:** `GET /api/v1/health/ready` (MongoDB + Redis; + S3 when enabled)

### Deploy
```bash
cp backend/.env.production.example backend/.env
# edit secrets
make prod
```

Frontend (nginx with SPA routing + API proxy):
```bash
cd frontend
docker build \
  --build-arg VITE_API_BASE_URL=/api/v1 \
  --build-arg VITE_API_KEY=your-production-key \
  -t namanpuja-admin .
```

Or use the `frontend` service in `docker-compose.prod.yml`.
