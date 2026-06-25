"""
Backend client for the Streamlit UI.

Supports two modes:
- HTTP mode: calls FastAPI at API_URL (local dev, Docker API Space)
- Direct mode: invokes LangGraph in-process (Hugging Face Streamlit Space)
"""

from __future__ import annotations

import os
import uuid
from typing import Optional


def _direct_mode() -> bool:
    flag = os.getenv("GIFT_AGENT_DIRECT", "").lower()
    if flag in ("1", "true", "yes"):
        return True
    if flag in ("0", "false", "no"):
        return False
    # Default: direct when no API_URL is configured (typical on Hugging Face)
    return not os.getenv("API_URL")


def api_base_url() -> str:
    return os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")


def recommend(contact: dict) -> dict:
    if _direct_mode():
        from app.main import _invoke_workflow, _response_payload, results_store

        run_id = str(uuid.uuid4())
        result = _invoke_workflow(contact, run_id)
        results_store[run_id] = result
        return _response_payload(run_id, contact, result)

    import requests

    response = requests.post(f"{api_base_url()}/recommend", json=contact, timeout=180)
    response.raise_for_status()
    return response.json()


def review(run_id: str, action: str, notes: Optional[str] = None) -> dict:
    if _direct_mode():
        from app.main import update_review

        return update_review(run_id, action, notes)

    import requests

    params = {"action": action}
    if notes:
        params["notes"] = notes
    response = requests.post(
        f"{api_base_url()}/review/{run_id}",
        params=params,
        timeout=180,
    )
    response.raise_for_status()
    return response.json()
