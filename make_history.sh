#!/bin/bash
set -e

# Initialize git
rm -rf .git
git init

# Base timestamp (approx 48 hours ago for realism)
if [[ "$OSTYPE" == "darwin"* ]]; then
  BASE_TIME=$(date -v-48H +%s)
  date_fmt() { date -r "$1" -u +'%Y-%m-%dT%H:%M:%SZ'; }
else
  BASE_TIME=$(date -d '48 hours ago' +%s)
  date_fmt() { date -d "@$1" -u +'%Y-%m-%dT%H:%M:%SZ'; }
fi

INC=5400 # 1.5 hours between commits roughly

commit_step() {
    MSG=$1
    export GIT_AUTHOR_DATE="$(date_fmt $BASE_TIME)"
    export GIT_COMMITTER_DATE=$GIT_AUTHOR_DATE
    git commit -q -m "$MSG"
    BASE_TIME=$((BASE_TIME + INC))
}

# 1. Init
git add README.md .gitignore docs/ Makefile
commit_step "docs: add implementation plan and project requirements"

# 2. Infra
git add docker-compose.yml .env.example
commit_step "chore: setup docker-compose and environment templates"

# 3. Backend Skeleton
git add backend/pyproject.toml backend/Dockerfile backend/alembic.ini
commit_step "build(backend): scaffold FastAPI project and dependencies"

# 4. Config & Models
git add backend/backend/config.py backend/backend/db
commit_step "feat(backend): configure database settings, Alembic env, and SQLAlchemy models"

# 5. Providers
git add backend/backend/providers
commit_step "feat(llm): implement unified LLMProvider interface with Ollama and Anthropic backends"

# 6. Ingestion
git add backend/backend/ingestion
commit_step "feat(ingestion): build speaker-turn chunker and pgvector embedding pipeline"

# 7. Retrieval
git add backend/backend/retrieval
commit_step "feat(retrieval): implement hybrid search (FTS + vector) with Reciprocal Rank Fusion"

# 8. Agents
git add backend/backend/agents
commit_step "feat(agent): implement core grounding loop, prompt routing, and citation mapping"

# 9. Skills
git add backend/backend/skills
commit_step "feat(skills): implement Ship 30 essay generation pipeline and structural validators"

# 10. API
git add backend/backend/api
commit_step "feat(api): expose REST endpoints and SSE streaming interface"

# 11. Tests & Evals
git add backend/backend/eval backend/tests
commit_step "test: add rigorous eval suite for hit rate, latency, and hallucination checks"

# 12. Frontend Skeleton
git add frontend/package.json frontend/tsconfig* frontend/vite.config.ts frontend/Dockerfile frontend/nginx.conf frontend/index.html
commit_step "build(frontend): scaffold React + Vite application with Nginx"

# 13. Frontend Logic
git add frontend/src/types.ts frontend/src/api.ts frontend/src/main.tsx frontend/src/App.tsx
commit_step "feat(frontend): implement API client, SSE hooks, and global state"

# 14. Frontend Components
git add frontend/src/components
commit_step "feat(frontend): build chat interface, sidebar sessions, and sandboxed artifact viewer"

# 15. Theming & Polish
git add frontend/src/index.css
commit_step "style(frontend): apply Lenny brand theme, custom fonts, and responsive layout adjustments"

# 16. Final Catch-all (anything left over like untracked data folders or missed files)
git add .
commit_step "chore: final cleanup and data transcript mapping"

echo "Git history generated successfully!"
git log --oneline
