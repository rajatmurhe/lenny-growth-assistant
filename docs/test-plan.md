# Manual UI Test Plan

## Purpose
Human-executed test checklist to verify end-to-end flows before client handoff or demo. Run after `make up && make ingest`.

---

## Prerequisites
- [ ] `docker compose ps` shows all 3 services healthy
- [ ] `curl http://localhost:8000/health/ready | python3 -m json.tool` shows `status: ready`
- [ ] Index populated: `chunk_count > 0` in health/ready response

---

## TC-01: Basic Question and Answer

**Steps:**
1. Open http://localhost:3000
2. Click "New Chat"
3. Type: `What did Molly Graham say about giving away your Legos?`
4. Press Enter

**Expected:**
- [ ] Streaming tokens appear in the chat pane (not all at once)
- [ ] Response contains inline citations like [1] or [2]
- [ ] Source cards appear below the response showing episode title "Molly Graham"
- [ ] Source cards show relevance score
- [ ] Response is grounded (mentions Legos/ownership framework)
- [ ] No hallucinated external sources

---

## TC-02: Out-of-Corpus Refusal

**Steps:**
1. In a new chat, type: `What did Jeff Bezos say about Amazon's flywheel?`

**Expected:**
- [ ] Response does NOT attempt to answer the question from memory
- [ ] "Insufficient Evidence" state shown (yellow banner or special UI)
- [ ] List of closest related episodes shown
- [ ] No citations with made-up episode names

---

## TC-03: Multi-Turn Follow-Up

**Steps:**
1. Ask: `What did Peter Sellis say about product decisions at Discord?`
2. Wait for response
3. Type: `What else did he say about user data?`

**Expected:**
- [ ] Second question correctly identifies Peter Sellis as the subject (query rewriter working)
- [ ] Response retrieves Discord/Sellis-related chunks
- [ ] Citations reference the same episode

---

## TC-04: Ship 30 Essay Generation

**Steps:**
1. New chat, type: `Write a Ship 30 essay about giving away your Legos in management`

**Expected:**
- [ ] Response routed to Ship 30 pipeline (not plain Q&A)
- [ ] Essay appears with ## headings (at least 2)
- [ ] Essay has bullet list
- [ ] Citations [1], [2], [3]+ appear inline
- [ ] Validation badge shows "✓ Valid essay · ~1200 words"
- [ ] Word count is between 1100–1400

---

## TC-05: Session Isolation

**Steps:**
1. Start Session A, ask about Molly Graham
2. Start Session B (New Chat), ask about Peter Sellis
3. Switch back to Session A

**Expected:**
- [ ] Session A shows only Molly Graham messages
- [ ] Session B shows only Peter Sellis messages
- [ ] No cross-contamination of context

---

## TC-06: Artifact Creation

**Steps:**
1. After a Q&A session, type: `Create a one-pager summarizing what we've discussed`

**Expected:**
- [ ] Artifact viewer pane shows the generated document
- [ ] Preview tab renders the content (no script execution)
- [ ] Source tab shows raw markdown
- [ ] Copy button works
- [ ] Download button downloads a file

---

## TC-07: Artifact Security

**Steps:**
1. (Dev mode only) Directly call POST /artifacts with HTML containing a script tag
2. View the artifact in the UI

**Expected:**
- [ ] Script tag not present in rendered iframe
- [ ] No JavaScript executes (no alerts)
- [ ] Security info panel shows blocked items

---

## TC-08: Provider Toggle

**Steps:**
1. Click the provider badge in the header
2. If Anthropic key is set: select Anthropic, confirm
3. Ask a question

**Expected:**
- [ ] Provider badge updates to show Anthropic
- [ ] If no API key: Anthropic shows as "Unavailable" with reason
- [ ] Disabled providers cannot be selected

---

## TC-09: Health Degraded State

**Steps:**
1. Stop Ollama: (on host) stop Ollama process
2. Refresh http://localhost:3000
3. Check header

**Expected:**
- [ ] Health dot turns orange/red
- [ ] Header shows degraded reason: "Ollama is unreachable"
- [ ] `/health/ready` returns `status: degraded`
- [ ] Restart Ollama → health recovers within 30s

---

## TC-10: Mobile Layout

**Steps:**
1. Open http://localhost:3000 in Chrome DevTools, set viewport to 375px width
2. Verify layout

**Expected:**
- [ ] Sidebar hidden, mobile tabs visible (Chat | Artifacts)
- [ ] Chat tab active by default
- [ ] Artifacts tab shows artifact viewer when created
- [ ] All text readable, no overflow

---

## TC-11: Keyboard Navigation

**Steps:**
1. Tab through the UI without using mouse

**Expected:**
- [ ] Focus visible on all interactive elements (2px blue outline)
- [ ] Can reach: New Chat button, session list items, message input, Send button, provider badge
- [ ] Enter on Send button submits message
- [ ] Shift+Enter in input adds newline without submitting

---

## TC-12: Screen Reader Compatibility

**Steps:**
1. Enable VoiceOver (macOS: Cmd+F5)
2. Navigate the app

**Expected:**
- [ ] ARIA live region announces streaming tokens
- [ ] Sidebar announced as "Chat sessions"
- [ ] Source cards have accessible labels
- [ ] Degraded banner announced as alert
