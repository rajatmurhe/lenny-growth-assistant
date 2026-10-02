.PHONY: up down build ingest test eval logs clean help

# Default target
help:
	@echo "Lenny Growth Assistant — Available Commands"
	@echo "─────────────────────────────────────────────"
	@echo "  make up       Start all services (Docker Compose)"
	@echo "  make down     Stop all services"
	@echo "  make build    Rebuild Docker images"
	@echo "  make ingest   Run transcript ingestion pipeline"
	@echo "  make test     Run automated test suite"
	@echo "  make eval     Run evaluation against ground truth questions"
	@echo "  make logs     Tail logs from all services"
	@echo "  make clean    Remove containers, volumes, and build artifacts"
	@echo "─────────────────────────────────────────────"
	@echo "Prerequisites: Docker Desktop running, Ollama running with models pulled."
	@echo "See README.md for full setup instructions."

## ─── SERVICE MANAGEMENT ────────────────────────────────────────────────────

up:
	@echo "→ Copying .env.example to .env if not present..."
	@test -f .env || cp .env.example .env
	@echo "→ Starting all services..."
	docker compose up -d
	@echo "→ Waiting for backend to become ready..."
	@for i in $$(seq 1 30); do \
		if curl -sf http://localhost:8000/health > /dev/null 2>&1; then \
			echo "✅ Backend ready at http://localhost:8000"; \
			break; \
		fi; \
		echo "   waiting... ($$i/30)"; \
		sleep 3; \
	done
	@echo "✅ Frontend at http://localhost:3000"
	@echo "→ Running readiness check..."
	@curl -s http://localhost:8000/health/ready | python3 -m json.tool || true

down:
	docker compose down

build:
	docker compose build --no-cache

logs:
	docker compose logs -f

## ─── DATA ──────────────────────────────────────────────────────────────────

ingest:
	@echo "→ Running transcript ingestion pipeline..."
	@echo "   This clones the transcript repo and processes all episodes."
	@echo "   First run takes several minutes (embedding 50 episodes)."
	docker compose exec backend python -m backend.ingestion.cli ingest
	@echo "✅ Ingestion complete."

## ─── TESTING ────────────────────────────────────────────────────────────────

test:
	@echo "→ Running unit and integration tests..."
	docker compose exec backend python -m pytest tests/ -v --tb=short
	@echo "✅ Tests complete."

test-unit:
	docker compose exec backend python -m pytest tests/unit/ -v --tb=short

test-integration:
	docker compose exec backend python -m pytest tests/integration/ -v --tb=short

test-security:
	docker compose exec backend python -m pytest tests/security/ -v --tb=short

## ─── EVALUATION ─────────────────────────────────────────────────────────────

eval:
	@echo "→ Running evaluation against ground truth questions..."
	@echo "   Testing citation validity, refusal correctness, and retrieval hit rate."
	docker compose exec backend python -m backend.eval.runner
	@echo "→ Report saved to /data/eval_report.json"
	@docker compose exec backend cat /data/eval_report.json | python3 -m json.tool || true

## ─── MAINTENANCE ─────────────────────────────────────────────────────────────

clean:
	@echo "→ Stopping containers and removing volumes..."
	docker compose down -v
	@echo "→ Removing build artifacts..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf frontend/dist 2>/dev/null || true
	@echo "✅ Clean complete."

## ─── DEVELOPMENT HELPERS ─────────────────────────────────────────────────────

dev-backend:
	@echo "→ Starting backend in dev mode (hot reload)..."
	cd backend && uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@echo "→ Starting frontend in dev mode..."
	cd frontend && npm run dev

migrate:
	docker compose exec backend alembic upgrade head

shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec db psql -U $${POSTGRES_USER:-lenny} -d $${POSTGRES_DB:-lenny_db}
