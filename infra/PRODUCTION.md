# NamanPuja Content Pipeline — Production Guide

The API **refuses to start** in `APP_ENV=production` with weak API keys or missing LLM configuration.

## Checklist

### MongoDB
- Use MongoDB Atlas replica set or self-hosted replica set
- Enable automated backups
- Create indexes on startup (handled by API lifespan)
- Restrict network access to API/worker subnets only

### Redis
- Use managed Redis with persistence (AOF)
- Required for background generation/upload jobs and rate limiting

### Secrets
- `API_KEYS` — strong random keys (comma-separated for rotation)
- `OPENAI_API_KEY` — production key with spend limits
- `CMS_API_KEY` — CMS bearer token
- Store in AWS Secrets Manager / Doppler; never commit `.env`

### Workers
Run at least one worker process listening to:
- `batch_generation`
- `batch_upload`

### CMS
- Set `CMS_BASE_URL` to NamanPuja CMS API
- Set `CMS_UPLOAD_ENABLED=true` only when endpoint is verified
- Upload agent posts page payload to `POST {CMS_BASE_URL}/pages`

### Images
- Set `USE_S3_STORAGE=true`
- Configure `S3_BUCKET` and `S3_PUBLIC_BASE_URL` (CloudFront)
- Page documents store public CDN URLs

### Auth
- `ENFORCE_AUTH=true`
- Admin UI sends `X-API-Key` header (`VITE_API_KEY` at build time)
- Prefer placing admin UI behind VPN or SSO gateway

### Observability
- Ship structured JSON logs to centralized logging
- Alert when batches remain in `GENERATING` longer than `BATCH_STUCK_MINUTES`
- Monitor Redis queue depth and worker restarts

### Hardening (enabled in production)
- OpenAPI docs disabled
- Security headers (HSTS, nosniff, frame deny)
- Optional `TRUSTED_HOSTS` allowlist
- Rate limiting via Redis

### Health probes
- **Liveness:** `GET /api/v1/health`
- **Readiness:** `GET /api/v1/health/ready` (MongoDB + Redis required)

### Deploy
```bash
cp backend/.env.production.example backend/.env
# edit secrets
docker compose -f docker-compose.prod.yml up --build -d
```

Build and deploy the admin frontend separately:
```bash
cd frontend
VITE_API_BASE_URL=https://api.namanpuja.com/api/v1 VITE_API_KEY=... npm run build
# deploy dist/ to static hosting
```
