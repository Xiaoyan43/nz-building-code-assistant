"""Answer a Building Code question using ONLY the retrieved clauses, with citations.

The whole point: it must not invent code. If the retrieved clauses don't cover the
question, it says so (grounded=false) rather than guessing.
"""

from __future__ import annotations

from anthropic import Anthropic

from .config import settings

SYSTEM_PROMPT = """You are an assistant that helps an architecture studio look things up in the
New Zealand Building Code. You are given a question and a set of Building Code clause summaries.

Hard rules:
- Answer ONLY using the provided clauses. Do not use outside knowledge or invent clause numbers,
  measurements, R-values, or heights.
- Cite the clause id(s) you used (e.g. "E2", "F4") in cited_clauses.
- If the provided clauses do not actually answer the question, set grounded=false and say you
  can't find it in the loaded clauses — do not guess.
- These summaries are paraphrased for a demo and are NOT legal advice; tell the user to confirm
  against the official MBIE Acceptable Solution and that specific figures must be checked there.
- Be concise and practical.

Answer ONLY by calling the building_code_answer tool."""

ANSWER_TOOL = {
    "name": "building_code_answer",
    "description": "Return a grounded, cited answer to a NZ Building Code question.",
    "input_schema": {
        "type": "object",
        "properties": {
            "answer": {"type": "string", "description": "Concise answer grounded in the provided clauses."},
            "cited_clauses": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Clause ids actually used, e.g. ['E2'].",
            },
            "grounded": {
                "type": "boolean",
                "description": "True only if the provided clauses genuinely answer the question.",
            },
        },
        "required": ["answer", "cited_clauses", "grounded"],
    },
}

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def _format_clauses(clauses: list[dict]) -> str:
    return "\n\n".join(f"[{c['id']}] {c['title']}\n{c['text']}" for c in clauses)


def answer_question(question: str, clauses: list[dict]) -> dict:
    client = _get_client()
    context = _format_clauses(clauses)
    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=700,
        temperature=0,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        tools=[ANSWER_TOOL],
        tool_choice={"type": "tool", "name": "building_code_answer"},
        messages=[
            {
                "role": "user",
                "content": f"Question: {question}\n\nBuilding Code clauses:\n{context}",
            }
        ],
    )
    tool_input = next(
        (b.input for b in message.content if b.type == "tool_use" and b.name == "building_code_answer"),
        None,
    )
    if tool_input is None:
        raise ValueError("Model did not return a building_code_answer tool call")
    return {
        "answer": tool_input.get("answer", ""),
        "cited_clauses": tool_input.get("cited_clauses", []),
        "grounded": bool(tool_input.get("grounded", False)),
    }
