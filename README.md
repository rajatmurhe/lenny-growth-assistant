# Lenny Growth Assistant

> A grounded product and growth intelligence workspace for PMs and growth operators.
> Ask questions about podcast transcripts → get evidence-backed answers with citations → write Ship 30 essays → export artifacts.

---

## Architecture Overview

```
┌─────────────┐     SSE stream      ┌───────────────────────────────────┐
│   Browser   │◄────────────────────│  FastAPI Backend (port 8000)       │
│  React+Vite │────── POST ─────────│  ├── Router (rules→LLM fallback)   │
│  (port 3000)│                     │  ├── Query Rewriter                │
└─────────────┘                     │  ├── Hybrid Retrieval (pgvector+FTS)│
                                    │  ├── Grounded Answer Agent          │
┌─────────────┐                     │  ├── Ship 30 Pipeline              │
│  PostgreSQL  │◄───────────────────│  └── Artifact Agent                │
│  +pgvector   │                    └───────────────────────────────────┘
│  (port 5432) │                              │
└─────────────┘                    ┌──────────▼──────────┐
                                   │   Ollama (host)      │
                                   │   llama3.2:3b (chat) │
                                   │   nomic-embed-text   │
                                   └─────────────────────┘
```

**Request flow:** Message → Query rewrite (condensed standalone query) → Route (rules-first) → Hybrid retrieve (pgvector + FTS via RRF) → Relevance gate → Generate with `<UNTRUSTED_CONTEXT>` grounding → Validate citations → Persist → Stream SSE to UI.

**Grounding contract:** The system answers *only* from retrieved transcript chunks. Below threshold → "Insufficient Evidence" response. Every `[n]` citation is validated against the retrieved set post-generation.

**Artifact security:** Sandboxed iframe (`sandbox=""` — no `allow-scripts`, no `allow-same-origin`) + CSP meta `default-src 'none'; style-src 'unsafe-inline'; img-src data:` + server-side nh3 sanitization before storage. The artifact viewer is a rendering surface, not an execution environment.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Docker Desktop | 4.x+ | With Compose v2 |
| Ollama | 0.3+ | Running locally before `make up` |
| Git | any | For transcript cloning |

**Ollama models to pull before starting:**
```bash
ollama pull llama3.2:3b        # Chat model (~2GB)
ollama pull nomic-embed-text   # Embedding model (~274MB)
```

---

## Quick Start (one command)

```bash
git clone <this-repo> lenny-growth-assistant
cd lenny-growth-assistant

# 1. Start all services
make up

# 2. Ingest transcripts (first run: ~10 min, embeds 50 episodes)
make ingest

# 3. Open the app
open http://localhost:3000
```

`make up` automatically copies `.env.example` → `.env` on first run.

---

## Environment Variables

Copy `.env.example` to `.env` and edit as needed.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_USER` | ✅ | `lenny` | PostgreSQL username |
| `POSTGRES_PASSWORD` | ✅ | `lenny_secret` | **Change in production** |
| `POSTGRES_DB` | ✅ | `lenny_db` | Database name |
| `OLLAMA_BASE_URL` | ✅ | `http://host.docker.internal:11434` | Ollama URL (Docker uses host-gateway) |
| `OLLAMA_CHAT_MODEL` | ✅ | `llama3.2:3b` | Chat model name in Ollama |
| `OLLAMA_EMBED_MODEL` | ✅ | `nomic-embed-text` | Embedding model name |
| `ANTHROPIC_API_KEY` | ⬜ | — | If set, enables Anthropic provider in UI |
| `ANTHROPIC_CHAT_MODEL` | ⬜ | `claude-3-5-haiku-20241022` | Anthropic model to use |
| `ACTIVE_PROVIDER` | ⬜ | `ollama` | Default provider at startup |
| `RETRIEVAL_TOP_K` | ⬜ | `10` | Chunks to retrieve per query |
| `RETRIEVAL_THRESHOLD` | ⬜ | `0.35` | RRF score threshold for "insufficient evidence" |
| `LOG_LEVEL` | ⬜ | `INFO` | `DEBUG` / `INFO` / `WARNING` |
| `VITE_API_URL` | ⬜ | `http://localhost:8000` | Backend URL as seen from browser |

### Swapping the chat model

```bash
# Pull a better model (needs ~8GB RAM)
ollama pull qwen2.5:7b-instruct

# Update .env
OLLAMA_CHAT_MODEL=qwen2.5:7b-instruct

# Restart backend
docker compose restart backend
```

---

## Local Development (without Docker)

```bash
# Backend
cd backend
pip install -e ".[dev]"
# Set env vars manually or export from .env
uvicorn backend.api.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev  # http://localhost:5173
```

---

## Makefile Reference

| Command | Description |
|---------|-------------|
| `make up` | Start all services, wait for readiness, run health check |
| `make down` | Stop all services |
| `make build` | Rebuild Docker images from scratch |
| `make ingest` | Clone transcripts and run ingestion pipeline |
| `make test` | Run full test suite (unit + integration + security) |
| `make test-unit` | Unit tests only |
| `make test-security` | XSS sanitizer tests |
| `make eval` | Run evaluation against 30 ground-truth questions |
| `make logs` | Tail logs from all services |
| `make clean` | Remove containers, volumes, and build artifacts |
| `make shell-backend` | Open bash in running backend container |
| `make shell-db` | Open psql in running database container |

---

## API Reference

### Health
- `GET /health` → `{"status": "ok"}`
- `GET /health/ready` → detailed readiness check (DB, Ollama, index, Anthropic)

### Sessions
- `POST /sessions` → create session
- `GET /sessions` → list sessions (last 50)
- `GET /sessions/{id}` → session with messages
- `POST /sessions/{id}/messages` → **SSE stream** (body: `{"content": "..."}`)
- `POST /sessions/{id}/provider` → switch provider for this session

### Config
- `GET /config/providers` → available providers and their status

### Admin
- `POST /admin/ingest` → trigger ingestion run (background)
- `GET /admin/ingest/{run_id}` → ingestion run status

### Artifacts
- `GET /artifacts/{id}` → artifact content
- `GET /artifacts/{id}/versions` → version history

### SSE Event Types
```json
{"type": "token", "content": "..."}
{"type": "citations", "citations": [...]}
{"type": "insufficient_evidence", "message": "...", "closest_episodes": [...]}
{"type": "validation", "passed": true, "word_count": 1247, "failures": []}
{"type": "artifact", "artifact_id": "...", "title": "..."}
{"type": "error", "message": "...", "code": "..."}
{"type": "done", "latency_ms": 4200}
```

---

## Cloud Mode (Anthropic)

1. Set `ANTHROPIC_API_KEY=sk-ant-...` in `.env`
2. Restart: `docker compose restart backend`
3. In the UI, click the provider badge (top-right) → select Anthropic
4. Embeddings always use Ollama (`nomic-embed-text`) regardless of chat provider

---

## Resilience Behavior

| Failure | System Response |
|---------|----------------|
| Ollama unreachable | `/health/ready` → `degraded`; UI banner; Anthropic used if key set |
| Model timeout | Bounded to `REQUEST_TIMEOUT_S`; 1 retry; structured error returned |
| Empty retrieval | "Insufficient Evidence" response + 3 closest episode suggestions |
| Index empty | `/health/ready` → `degraded`; prompt to run `make ingest` |
| DB connection failure | `/health/ready` → `not_ready`; UI degraded banner |
| Missing API key | Anthropic disabled in provider selector with visible reason |

---

## Running Tests

```bash
# All tests
make test

# Unit tests (no DB needed)
make test-unit

# Security (XSS sanitizer corpus)
make test-security

# Evaluation (needs running stack + ingested data)
make eval
```

---

## License & Transcript Usage

The transcript corpus (`data/transcripts/`) is licensed under Lenny's starter pack terms:
- ✅ Personal and non-commercial use permitted
- ❌ Raw redistribution of transcripts not allowed
- See `data/transcripts/LICENSE.md` for full terms

This codebase (excluding transcripts) is available under MIT license.
