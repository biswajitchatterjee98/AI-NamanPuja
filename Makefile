.PHONY: dev prod test backend-install frontend-install

backend-install:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

frontend-install:
	cd frontend && npm install

dev:
	cp -n backend/.env.example backend/.env || true
	docker compose up --build

prod:
	docker compose -f docker-compose.prod.yml up --build -d

test:
	cd backend && . .venv/bin/activate && pytest -q
