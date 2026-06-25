"""
Persistent reviewer feedback memory.

Stores approve/reject/regenerate signals per contact so future runs
can learn from past human judgments — not just the current session.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

MAX_ENTRIES_PER_CONTACT = 10
MAX_ENTRIES_IN_PROMPT = 5

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
FEEDBACK_FILE = DATA_DIR / "feedback_memory.json"


def _contact_key(contact: dict) -> str:
    name = contact.get("name", "unknown").strip().lower()
    company = contact.get("company", "unknown").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", f"{name}_{company}").strip("_")
    return slug or "unknown_contact"


def _load_store() -> dict:
    if not FEEDBACK_FILE.exists():
        return {}
    try:
        with open(FEEDBACK_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_store(store: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)


def save_feedback(
    contact: dict,
    run_id: str,
    action: str,
    notes: Optional[str] = None,
    recommended_gifts: Optional[list] = None,
) -> None:
    """Append a human review event for this contact."""
    key = _contact_key(contact)
    store = _load_store()

    record = store.get(key, {
        "contact_name": contact.get("name"),
        "company": contact.get("company"),
        "entries": [],
    })

    gift_names = [
        g.get("gift_name", "")
        for g in (recommended_gifts or [])
        if g.get("gift_name")
    ]

    record["entries"].append({
        "run_id": run_id,
        "action": action,
        "notes": (notes or "").strip(),
        "gift_names": gift_names[:3],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    record["entries"] = record["entries"][-MAX_ENTRIES_PER_CONTACT:]
    store[key] = record
    _save_store(store)


def get_feedback_entries(contact: dict) -> list[dict]:
    key = _contact_key(contact)
    store = _load_store()
    return store.get(key, {}).get("entries", [])


def build_feedback_context(
    contact: dict,
    session_notes: str = "",
) -> tuple[str, int]:
    """
    Build prompt-ready feedback text from history + optional session notes.
    Returns (context_string, number_of_historical_entries_used).
    """
    entries = get_feedback_entries(contact)
    recent = entries[-MAX_ENTRIES_IN_PROMPT:]
    lines: list[str] = []

    for entry in recent:
        action = entry.get("action", "")
        notes = entry.get("notes", "")
        gifts = entry.get("gift_names", [])
        gift_hint = f" (gifts: {', '.join(gifts)})" if gifts else ""

        if action in ("approved", "approve"):
            line = "Previous recommendations were APPROVED"
            if notes:
                line += f" — reviewer noted: {notes}"
            lines.append(line)
        elif action in ("rejected", "reject"):
            line = "Previous recommendations were REJECTED"
            if notes:
                line += f" — reason: {notes}"
            else:
                line += " — avoid similar suggestions"
            lines.append(line + gift_hint)
        elif action in ("regenerate", "regenerate_requested", "edited"):
            if notes:
                lines.append(f"Reviewer asked to improve: {notes}{gift_hint}")
        elif notes:
            lines.append(f"Reviewer feedback ({action}): {notes}{gift_hint}")

    if session_notes and session_notes.strip():
        if not lines or session_notes.strip() not in "\n".join(lines):
            lines.append(f"Current session feedback: {session_notes.strip()}")

    if not lines:
        return "", 0

    context = (
        "LEARNING FROM PAST HUMAN REVIEWS (apply these lessons):\n"
        + "\n".join(f"- {line}" for line in lines)
    )
    return context, len(recent)


def get_learning_summary(contact: dict) -> dict:
    """API-friendly summary of stored feedback for a contact."""
    entries = get_feedback_entries(contact)
    if not entries:
        return {"historical_feedback_applied": False, "feedback_entries_count": 0}

    last = entries[-1]
    return {
        "historical_feedback_applied": True,
        "feedback_entries_count": len(entries),
        "last_action": last.get("action"),
        "last_notes": last.get("notes") or None,
    }
