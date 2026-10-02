"""
Query rewriter: condense multi-turn follow-up into a standalone search query.
Only calls LLM when there's actual conversation history to resolve.
"""
from __future__ import annotations

from backend.providers.base import ChatMessage, LLMProvider

REWRITE_SYSTEM = """You are a search query optimizer. Given a conversation history and a new user message, 
rewrite the user's message as a standalone, self-contained search query.

Rules:
- If the message is already standalone (no pronouns like "it", "that", "they" that reference prior context), return it UNCHANGED.
- If the message references prior context (e.g., "tell me more about that", "what else did she say?"), rewrite it to be explicit.
- Output ONLY the rewritten query, nothing else. No explanation.
- Keep the query concise — under 100 words.
- Preserve the user's intent exactly.

Examples:
- History: [User: "What did Molly say about onboarding?", Assistant: "..."]
  Message: "What else did she say about it?"
  Output: "What else did Molly Graham say about onboarding new employees?"

- History: []
  Message: "How do product managers handle technical debt?"
  Output: "How do product managers handle technical debt?"
"""


async def rewrite_query(
    current_message: str,
    history: list[ChatMessage],
    provider: LLMProvider,
) -> str:
    """
    Condense multi-turn follow-up into standalone query.
    Returns current_message unchanged if no history or message is standalone.
    """
    if not history:
        return current_message

    # Quick heuristic: if no pronouns referencing prior context, return as-is
    ambiguous_tokens = [
        "that", "it", "this", "they", "them", "their", "he", "she", "who",
        "more about", "tell me more", "what else", "continue", "elaborate"
    ]
    msg_lower = current_message.lower()
    has_reference = any(token in msg_lower for token in ambiguous_tokens)

    if not has_reference:
        return current_message

    # Build history context (last 4 messages)
    history_text = ""
    for msg in history[-4:]:
        role = "User" if msg.role == "user" else "Assistant"
        excerpt = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
        history_text += f"{role}: {excerpt}\n"

    rewrite_prompt = (
        f"## Conversation history:\n{history_text}\n"
        f"## New user message:\n{current_message}\n\n"
        "Rewrite the new message as a standalone search query:"
    )

    try:
        rewritten = await provider.complete(
            messages=[
                ChatMessage(role="system", content=REWRITE_SYSTEM),
                ChatMessage(role="user", content=rewrite_prompt),
            ],
            max_tokens=150,
            temperature=0.0,
        )
        return rewritten.strip()
    except Exception:
        # If rewriting fails, fall back to original message — never block the user
        return current_message
