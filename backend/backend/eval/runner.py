"""
Evaluation runner: tests the live system against ground-truth questions.
Reports citation validity, refusal correctness, retrieval hit rate, and latency.

Run with: python -m backend.eval.runner
Or via: make eval
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Optional

import yaml


QUESTIONS_PATH = os.path.join(os.path.dirname(__file__), "questions.yaml")
REPORT_PATH = "/data/eval_report.json"

API_BASE = os.environ.get("EVAL_API_URL", "http://localhost:8000")


@dataclass
class QuestionResult:
    question_id: str
    category: str
    question: str
    status: str  # "passed" | "failed" | "error"
    latency_ms: int
    citations_valid: Optional[bool]
    refusal_correct: Optional[bool]
    retrieval_hit: Optional[bool]
    error: Optional[str] = None


async def _stream_response(session_id: str, question: str) -> dict:
    """Send question and collect full SSE response."""
    import httpx

    full_content = ""
    citations = []
    insufficient = False
    closest_episodes = []
    error_msg = None
    t0 = time.monotonic()

    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            f"{API_BASE}/sessions/{session_id}/messages",
            json={"content": question},
        ) as resp:
            if resp.status_code != 200:
                return {
                    "content": "",
                    "citations": [],
                    "insufficient": True,
                    "error": f"HTTP {resp.status_code}",
                    "latency_ms": int((time.monotonic() - t0) * 1000),
                }

            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    event = json.loads(line[6:])
                    if event["type"] == "token":
                        full_content += event.get("content", "")
                    elif event["type"] == "citations":
                        citations = event.get("citations", [])
                    elif event["type"] == "insufficient_evidence":
                        insufficient = True
                        closest_episodes = event.get("closest_episodes", [])
                    elif event["type"] == "error":
                        error_msg = event.get("message", "Unknown error")
                    elif event["type"] == "done":
                        break
                except (json.JSONDecodeError, KeyError):
                    pass

    return {
        "content": full_content,
        "citations": citations,
        "insufficient": insufficient,
        "closest_episodes": closest_episodes,
        "error": error_msg,
        "latency_ms": int((time.monotonic() - t0) * 1000),
    }


async def _create_session() -> str:
    import httpx
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{API_BASE}/sessions", json={"provider": "ollama"})
        return resp.json()["id"]


def _check_citations_valid(response: dict) -> Optional[bool]:
    """Check all [n] citations map to returned chunks."""
    import re
    content = response["content"]
    citations = response.get("citations", [])
    if not citations:
        return None  # Can't validate if no citations returned

    cited_numbers = set(int(m) for m in re.findall(r'\[(\d+)\]', content))
    if not cited_numbers:
        return None

    max_valid = len(citations)
    return all(n <= max_valid and n > 0 for n in cited_numbers)


def _check_refusal(response: dict) -> bool:
    """Check whether the response correctly refused an OOC question."""
    if response.get("insufficient"):
        return True
    content = response["content"].upper()
    return "INSUFFICIENT EVIDENCE" in content or "DON'T HAVE" in content or "NO INFORMATION" in content


def _check_retrieval_hit(response: dict, expected_episodes: list[str]) -> bool:
    """Check if any expected episode appears in the citations."""
    if not expected_episodes:
        return True  # No expectation = pass
    citations = response.get("citations", [])
    found_slugs = {c.get("episode_slug", "") for c in citations}
    return any(ep in slug for ep in expected_episodes for slug in found_slugs)


async def run_eval() -> dict:
    with open(QUESTIONS_PATH) as f:
        data = yaml.safe_load(f)

    questions = data["questions"]
    print(f"\n→ Running eval on {len(questions)} questions against {API_BASE}\n")

    results: list[QuestionResult] = []
    latencies: list[int] = []

    for q in questions:
        qid = q["id"]
        category = q["category"]
        question = q["question"]
        expected_episodes = q.get("expected_episodes", [])
        expected_refusal = q.get("expected_refusal", False)

        print(f"  [{qid}] {category}: {question[:60]}...")

        try:
            # Create a fresh session for each question (session isolation)
            session_id = await _create_session()
            response = await _stream_response(session_id, question)

            latencies.append(response["latency_ms"])

            citations_valid = _check_citations_valid(response) if not expected_refusal else None
            refusal_correct = _check_refusal(response) if expected_refusal else None
            retrieval_hit = _check_retrieval_hit(response, expected_episodes) if not expected_refusal else None

            # Determine pass/fail
            checks = [v for v in [citations_valid, refusal_correct, retrieval_hit] if v is not None]
            passed = all(checks) if checks else True

            status = "passed" if passed else "failed"
            print(f"    → {status} | {response['latency_ms']}ms | citations_valid={citations_valid} | refusal_correct={refusal_correct} | retrieval_hit={retrieval_hit}")

            results.append(QuestionResult(
                question_id=qid,
                category=category,
                question=question,
                status=status,
                latency_ms=response["latency_ms"],
                citations_valid=citations_valid,
                refusal_correct=refusal_correct,
                retrieval_hit=retrieval_hit,
                error=response.get("error"),
            ))

        except Exception as e:
            print(f"    → ERROR: {e}")
            results.append(QuestionResult(
                question_id=qid,
                category=category,
                question=question,
                status="error",
                latency_ms=0,
                citations_valid=None,
                refusal_correct=None,
                retrieval_hit=None,
                error=str(e),
            ))

    # ── Aggregate metrics ──────────────────────────────────────────────────────
    total = len(results)
    passed = sum(1 for r in results if r.status == "passed")
    failed = sum(1 for r in results if r.status == "failed")
    errors = sum(1 for r in results if r.status == "error")

    citation_checks = [r.citations_valid for r in results if r.citations_valid is not None]
    citation_valid_rate = sum(citation_checks) / len(citation_checks) if citation_checks else 0

    refusal_checks = [r.refusal_correct for r in results if r.refusal_correct is not None]
    refusal_correct_rate = sum(refusal_checks) / len(refusal_checks) if refusal_checks else 0

    retrieval_checks = [r.retrieval_hit for r in results if r.retrieval_hit is not None]
    retrieval_hit_rate = sum(retrieval_checks) / len(retrieval_checks) if retrieval_checks else 0

    latencies_sorted = sorted(latencies)
    p50 = latencies_sorted[len(latencies_sorted) // 2] if latencies_sorted else 0
    p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)] if latencies_sorted else 0

    report = {
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": round(passed / total, 3) if total > 0 else 0,
        },
        "metrics": {
            "citation_validity_rate": round(citation_valid_rate, 3),
            "refusal_correctness_rate": round(refusal_correct_rate, 3),
            "retrieval_hit_rate": round(retrieval_hit_rate, 3),
            "latency_p50_ms": p50,
            "latency_p95_ms": p95,
        },
        "results": [asdict(r) for r in results],
    }

    # Print summary
    print("\n" + "─" * 60)
    print("EVAL SUMMARY")
    print("─" * 60)
    print(f"  Total questions:         {total}")
    print(f"  Passed:                  {passed} ({round(passed/total*100, 1) if total else 0}%)")
    print(f"  Failed:                  {failed}")
    print(f"  Errors:                  {errors}")
    print(f"  Citation validity rate:  {round(citation_valid_rate*100, 1)}%")
    print(f"  Refusal correctness:     {round(refusal_correct_rate*100, 1)}%")
    print(f"  Retrieval hit rate:      {round(retrieval_hit_rate*100, 1)}%")
    print(f"  Latency P50:             {p50}ms")
    print(f"  Latency P95:             {p95}ms")
    print("─" * 60)

    # Save report
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n→ Full report saved to {REPORT_PATH}")

    return report


def main():
    asyncio.run(run_eval())


if __name__ == "__main__":
    main()
