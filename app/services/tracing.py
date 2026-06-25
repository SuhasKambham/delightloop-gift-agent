"""LangSmith trace metadata and human feedback scoring."""

from __future__ import annotations

import os
from typing import Optional


def build_run_config(run_id: str, contact: dict) -> dict:
    """Attach run metadata so LangSmith traces map to API run IDs."""
    return {
        "run_id": run_id,
        "run_name": f"gift-agent:{contact.get('name', 'unknown')}",
        "tags": ["gift-agent", contact.get("company", "unknown")],
        "metadata": {
            "contact_name": contact.get("name"),
            "company": contact.get("company"),
            "occasion": contact.get("gift_context", {}).get("occasion"),
        },
    }


def record_human_feedback(
    run_id: str,
    action: str,
    notes: Optional[str] = None,
) -> None:
    """
    Score the LangSmith trace when a reviewer approves or rejects.
    No-op if LangSmith is not configured.
    """
    if not os.getenv("LANGCHAIN_API_KEY"):
        return

    if action not in ("approve", "reject"):
        return

    try:
        from langsmith import Client

        client = Client()
        score = 1.0 if action == "approve" else 0.0
        client.create_feedback(
            run_id,
            key="human_review",
            score=score,
            comment=notes or f"Reviewer {action}d recommendations",
        )
    except Exception as e:
        print(f"   LangSmith feedback skipped: {e}")
