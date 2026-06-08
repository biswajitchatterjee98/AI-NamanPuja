.PHONY: dev prod test backend-install frontend-install monitor

backend-install:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt

frontend-install:
	cd frontend && npm ci

dev:
	test -f backend/.env || cp backend/.env.example backend/.env
	docker compose up --build

prod:
	test -f backend/.env || (echo "Create backend/.env from .env.production.example first" && exit 1)
	docker compose -f docker-compose.prod.yml up --build -d

test:
	cd backend && . .venv/bin/activate && pytest -q

monitor:
	cd backend && . .venv/bin/activate && python monitor.py
