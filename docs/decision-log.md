# Decision Log — Lenny Growth Assistant

This document records all architectural decisions made during Phase 0 spikes and beyond. It is the source of truth for "why did we do X instead of Y?"

---

## Spike 1 — Transcript Corpus

**Date:** 2026-10-04  
**Question:** What is the exact URL and structure of the Lenny transcript repository?

**Result:**
- Repository: `https://github.com/LennysNewsletter/lennys-newsletterpodcastdata.git`
- Cloned to: `data/transcripts/`
- Format: `index.json` (schema_version 2.0) + individual `.md` files in `podcasts/` and `newsletters/`
- `index.json` structure: `{ "podcasts": [{ "slug", "filename", "title", "guest", "date", "word_count", "post_url" }] }`
- File format: YAML frontmatter + speaker-turn body (`**Speaker Name** (HH:MM:SS):\nText`)
- Count: 50 podcast episodes, 10 newsletter posts
- Average episode length: ~16,000 words
- License: Personal/non-commercial use permitted. Raw redistribution NOT allowed.

**Decision:** Ingest podcasts/ directory only by default. Newsletters could be added as a second content type.

---

## Spike 2 — Agent Layer

**Date:** 2026-10-04  
**Question:** Can the Claude Agent SDK run against Ollama with reliable tool calling? Should we use it?

**Test model:** `llama3.2:3b` via Ollama 0.34.2

**Results:**
| Test | Result | Latency |
|------|--------|---------|
| Citation formatting | ✅ Model correctly used `[1]`, `[2]` inline | 11.51s (cold) |
| Out-of-corpus refusal | ✅ Returned exact `"INSUFFICIENT EVIDENCE"` string | 2.44s |
| Router classification | ✅ Returned `"write_ship30_essay"` correctly | 1.81s |

**Decision:** Use **thin provider-agnostic router** (NOT Claude Agent SDK).

**Rationale:**
1. `llama3.2:3b` instruction-following is adequate for routing/citations with clear prompts
2. The Claude Agent SDK adds SDK dependency complexity and requires a compatible endpoint format
3. A thin router is simpler, fully testable (mock provider), and works identically across Ollama and Anthropic
4. The Anthropic path uses the `anthropic` Python SDK directly

---

## Spike 3 — Embedding Model

**Date:** 2026-10-04  
**Model:** `nomic-embed-text:latest` (274MB, 768 dimensions)

**Measurements:**
- Cold start (model load): 1.75s
- Warm P50: ~79ms
- Vector dimension: 768
- Tested with 3 representative podcast chunks

**Decision:** Use `nomic-embed-text` for embeddings, `llama3.2:3b` for chat (default, configurable via env).

---

## Architecture Decisions

### ADR-001: Hybrid Retrieval with RRF

**Decision:** pgvector cosine similarity + Postgres FTS (`plainto_tsquery`) merged with Reciprocal Rank Fusion (k=60).

**Rationale:**
- Vector search alone misses exact keyword matches (guest names, product names)
- FTS alone misses semantic paraphrases
- RRF is proven, parameter-free, and requires no separate retrieval model
- Stored entirely in PostgreSQL — no additional infrastructure

**Threshold:** 0.35 normalized RRF score. Below this → "Insufficient Evidence" response. Configurable via `RETRIEVAL_THRESHOLD`.

---

### ADR-002: Prompt Injection Defense

**Decision:** Wrap retrieved chunks in `<UNTRUSTED_CONTEXT>` delimiters. Instruct model to treat content inside as raw data only.

**Rationale:**
- Transcripts are user-submitted content and could contain adversarial instructions
- Delimiter + explicit instruction is the standard defense for this class of attack
- Sandboxed iframe adds a second layer for rendered artifacts

---

### ADR-003: No Authentication

**Decision:** Single implicit user, no auth layer.

**Rationale:** Demo system. Adding auth would add complexity without helping the evaluator. The spec does not require auth.

---

### ADR-004: PostgreSQL as the Only Datastore

**Decision:** PostgreSQL handles relational data, pgvector embeddings, and full-text search. No Redis, no separate vector DB.

**Rationale:**
- Reduces operational complexity (one service to run, one backup target)
- pgvector ivfflat index handles 50 episodes × ~30 chunks × 400-600 tokens = ~1,500 chunks trivially
- FTS via tsvector is built-in — no Elasticsearch needed
- Matches the "keep it lean" requirement

---

### ADR-005: SSE via Fetch (Not EventSource)

**Decision:** Use `fetch()` + `ReadableStream` for SSE, not the browser's `EventSource` API.

**Rationale:** `EventSource` only supports GET requests. Our SSE endpoint is POST (with message body). `fetch` with streaming body parsing gives identical behavior and supports the request body.

---

### ADR-006: Ship 30 Essay Word Count

**Decision:** Target 1,200 words, valid range 1,100–1,400 words.

**Rationale:** The assignment spec explicitly states "length target of about 1,250 words" and range [1,100–1,400]. This is NOT the Ship 30 atomic essay format (250 words) — it is a longer-form essay as specified in the engagement brief.

---

### ADR-007: Artifact Viewer Security Model

**Decision:** Three-layer defense:
1. Server-side nh3 allowlist sanitization before DB storage
2. iframe with `sandbox=""` (no tokens — maximum restriction)
3. `srcdoc` with CSP meta `default-src 'none'; style-src 'unsafe-inline'; img-src data:`

**Why `sandbox=""`?** The most restrictive possible setting. No JavaScript, no same-origin access, no forms, no popups, no navigation.

**Why CSP meta in srcdoc?** Defense-in-depth. Even if the sandbox is misconfigured, the CSP blocks resource loading.

**Rationale:** Generated HTML content is hostile by default. The artifact viewer must be a rendering surface, not an execution environment.
