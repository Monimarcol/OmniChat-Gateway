"""Thin wrapper around Ollama's local REST API for the two operations the setup flow
needs: checking what's already pulled, and pulling a new model on demand.
"""
from __future__ import annotations

import requests

from .config import settings


def list_local_tags() -> set[str]:
    resp = requests.get(f"{settings.API_BASE}/api/tags", timeout=5)
    resp.raise_for_status()
    return {m["name"] for m in resp.json().get("models", [])}


def is_pulled(tag: str) -> bool:
    return tag in list_local_tags()


def pull_model(tag: str) -> None:
    """Blocking pull -- can take minutes for multi-GB models. The caller is
    responsible for surfacing progress to the user (this project's setup screen shows
    a spinner rather than streaming progress, consistent with the rest of the
    one-click setup flow)."""
    resp = requests.post(
        f"{settings.API_BASE}/api/pull",
        json={"name": tag, "stream": False},
        timeout=None,
    )
    resp.raise_for_status()
