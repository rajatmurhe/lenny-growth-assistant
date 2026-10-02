# Lenny Growth Assistant — Demo Script
# This script guides a live demonstration of the system in ~10 minutes.

---

## Pre-demo Checklist

- [ ] `docker compose ps` — all 3 containers healthy
- [ ] `curl http://localhost:8000/health/ready | python3 -m json.tool` — status: ready
- [ ] Open http://localhost:3000 in Chrome (not a private window)
- [ ] Ollama running on host
- [ ] Health dot in header is green

---

## Part 1: Architecture Overview (2 min)

> "This is the Lenny Growth Assistant — a grounded product intelligence workspace. Every answer comes with citations from real podcast transcripts. Let me show you the three things this system does."

1. Point to the three-pane layout: **Sessions sidebar | Chat | Artifact Viewer**
2. Show the provider badge in the header: "llama3.2:3b running locally — no cloud dependency for the demo"
3. Point to health dot: "Green = DB, Ollama, and index all healthy"

---

## Part 2: Grounded Q&A (3 min)

> "The system's primary job is to answer questions from transcript evidence."

**Query 1** (answerable):
```
What did Molly Graham say about giving away your Legos?
```

- Watch tokens stream in real-time
- Point to the inline `[1]`, `[2]` citations
- Point to the source cards: "Episode title, guest, relevance score, text snippet"
- "Every claim traces back to a real transcript chunk. This is the grounding contract."

**Query 2** (out-of-corpus — most important demo moment):
```
What did Jeff Bezos say about Amazon's flywheel?
```

- System shows "Insufficient Evidence" (yellow banner)
- "The system doesn't hallucinate. It says 'I don't have evidence for this' and shows the closest episodes it does have."

---

## Part 3: Multi-Turn (1 min)

> "It handles follow-up questions by rewriting context into standalone queries."

Type:
```
What specific advice did she give about preventing burnout?
```

- "The query rewriter resolved 'she' to Molly Graham from context."

---

## Part 4: Ship 30 Essay (3 min)

> "The second skill is long-form writing — Ship 30 for 30 essays grounded in evidence."

**Query:**
```
Write a Ship 30 essay about giving away your Legos in a world full of AI
```

- Watch the outline → draft → validate pipeline
- Point to the validation badge: "✓ Valid essay · 1,247 words"
- "It validates: word count, hook, headings, bullets, citations, takeaway — and repairs automatically if anything fails."

---

## Part 5: Artifact Viewer Security (1 min)

> "When content is generated as an artifact, it renders in a sandboxed viewer."

Point to the artifact pane:
1. Click "Preview" tab — content renders
2. Click the 🔒 security panel: "JavaScript execution blocked. External resources blocked. The viewer is a rendering surface, not an execution environment."
3. Click "Source" tab — show the raw markdown
4. Click Copy / Download

---

## Part 6: Provider Toggle (30 sec)

Click the provider badge → Show provider modal:
- "Ollama: available, running locally"
- "Anthropic: unavailable (no API key set). To enable: add ANTHROPIC_API_KEY to .env"
- "Zero code changes needed to switch between providers"

---

## Wrap-up

> "The full stack: FastAPI backend, pgvector hybrid retrieval, streaming SSE, React frontend — one `docker compose up`, one `make ingest`. The README has everything needed to extend it."

---

## If Something Goes Wrong

| Issue | Fix |
|-------|-----|
| Health dot is red | `docker compose logs backend` — probably Ollama port issue |
| No citations appear | Check index: `curl http://localhost:8000/health/ready` → chunk_count |
| Streaming stops midway | Model timeout — retry with shorter question |
| Frontend 502 | Backend still starting — wait 30s |
