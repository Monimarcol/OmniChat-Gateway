"""Model recommendation agent: given a hardware profile and the user's free-text
description of what they'll use the assistant for, returns a ranked, explained
shortlist of models to actually run.

Two-stage design, deliberately not "let the LLM decide everything":
1. Deterministic hardware fit filter (RAM_SAFETY_MARGIN) -- a plain Python comparison,
   never delegated to the model. This is a correctness guarantee: the agent below can
   only affect ranking and rationale among models that are already known to fit, never
   recommend something that will actually fail to run on this device.
2. An LLM call (via the already-guaranteed-present default model) reasons about which
   of the *feasible* models best match the user's stated intent, and returns why.

If the LLM call fails or returns something we can't parse, this falls back to a
keyword/tag-overlap heuristic rather than raising -- a degraded recommendation beats a
broken setup screen.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from litellm import completion

from .hardware import HardwareProfile
from .model_catalog import CATALOG, ModelSpec

RAM_SAFETY_MARGIN = 0.7

# The model used to *run* the recommendation reasoning itself. Decoupled from whatever
# model the user ultimately picks for their chats -- llama3 is what setup.ps1
# guarantees is already pulled, so recommending happens before any other model needs
# to exist locally.
AGENT_MODEL = "ollama/llama3"
AGENT_API_BASE = "http://127.0.0.1:11434"

_KEYWORDS: dict[str, list[str]] = {
    "chat": ["chat", "talk", "conversation", "assistant", "everyday", "questions"],
    "content_creation": ["write", "writing", "blog", "content", "draft", "copy", "article", "story"],
    "research": ["research", "paper", "citation", "study", "analy", "literature", "summarize", "summarise"],
    "brainstorming": ["brainstorm", "idea", "ideas", "plan", "planning", "project"],
    "coding": ["code", "coding", "program", "programming", "script", "debug", "developer", "software"],
}


@dataclass
class Recommendation:
    model: ModelSpec
    rationale: str


def _usable_ram_gb(hardware: HardwareProfile) -> float:
    return hardware.ram_available_gb * RAM_SAFETY_MARGIN


def _feasible_models(hardware: HardwareProfile) -> list[ModelSpec]:
    usable_ram = _usable_ram_gb(hardware)
    return [m for m in CATALOG if m.min_ram_gb <= usable_ram]


def _fallback_recommend(feasible: list[ModelSpec], description: str, max_results: int) -> list[Recommendation]:
    """Keyword/tag-overlap heuristic, used only if the LLM agent call fails."""
    text = description.lower()
    tag_scores: dict[str, int] = {}
    for tag, keywords in _KEYWORDS.items():
        hits = sum(text.count(kw) for kw in keywords)
        if hits:
            tag_scores[tag] = hits
    usecases = [t for t, _ in sorted(tag_scores.items(), key=lambda kv: kv[1], reverse=True)[:2]] or ["chat"]

    scored = []
    for m in feasible:
        matched = [t for t in usecases if t in m.tags]
        scored.append((m, matched))
    scored.sort(key=lambda pair: (-len(pair[1]), pair[0].min_ram_gb))

    results = []
    for m, matched in scored[:max_results]:
        rationale = (
            f"Matches your stated use case ({', '.join(matched)})."
            if matched
            else "Fits this device, though it doesn't specifically match your stated use case."
        )
        results.append(Recommendation(model=m, rationale=rationale))
    return results


def _build_prompt(hardware: HardwareProfile, description: str, feasible: list[ModelSpec]) -> list[dict]:
    catalog_json = json.dumps(
        [
            {
                "id": m.id,
                "tags": m.tags,
                "strengths": m.strengths,
                "limitations": m.limitations,
            }
            for m in feasible
        ]
    )
    system = (
        "You are a model recommendation agent for a local-first AI assistant. "
        "You are given a list of AI models that are ALREADY CONFIRMED to run on the "
        "user's device -- you must never reject a model for hardware reasons, only "
        "rank and explain fit for the user's stated intent. "
        "Respond with ONLY a JSON array, no prose, no markdown fences. "
        'Each element: {"id": "<model id from the list>", "rationale": "<one sentence, plain language>"}. '
        "Order the array best match first. Include at most 3 entries. "
        "Only use ids that appear in the provided list."
    )
    user = (
        f"Available models: {catalog_json}\n\n"
        f"User's description of what they'll use this for: {description!r}\n\n"
        "Return the ranked JSON array now."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _parse_agent_response(raw: str, feasible: list[ModelSpec]) -> list[Recommendation] | None:
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None

    by_id = {m.id: m for m in feasible}
    results = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        model = by_id.get(item.get("id"))
        if model is None:
            continue
        rationale = str(item.get("rationale") or "Recommended for your stated use case.")
        results.append(Recommendation(model=model, rationale=rationale))
    return results or None


def recommend_models(hardware: HardwareProfile, description: str, max_results: int = 3) -> list[Recommendation]:
    feasible = _feasible_models(hardware)
    if not feasible:
        return []

    try:
        response = completion(
            model=AGENT_MODEL,
            messages=_build_prompt(hardware, description, feasible),
            api_base=AGENT_API_BASE,
        )
        raw = response.choices[0].message.content
        parsed = _parse_agent_response(raw, feasible)
        if parsed:
            return parsed[:max_results]
    except Exception:
        pass

    return _fallback_recommend(feasible, description, max_results)
