from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uuid
from dotenv import load_dotenv
from app.workflow.graph import gift_agent
from app.services.feedback_memory import (
    build_feedback_context,
    get_feedback_entries,
    get_learning_summary,
    save_feedback,
)
from app.services.tracing import build_run_config, record_human_feedback

load_dotenv()

app = FastAPI(
    title="DelightLoop Gift Agent",
    description="AI-powered personalised gift recommendation agent",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

results_store = {}


def _initial_state(contact: dict, session_notes: str = "") -> dict:
    feedback_context, _ = build_feedback_context(contact, session_notes=session_notes)
    return {
        "contact": contact,
        "profile_signals": {},
        "search_trace": {"queries_used": [], "products_considered_count": 0},
        "raw_products": [],
        "validated_products": [],
        "recommended_gifts": [],
        "human_review": {},
        "errors": [],
        "current_step": "not_started",
        "search_retry_count": 0,
        "reviewer_feedback": feedback_context,
    }


def _invoke_workflow(contact: dict, run_id: str, session_notes: str = "") -> dict:
    state = _initial_state(contact, session_notes=session_notes)
    config = build_run_config(run_id, contact)
    return gift_agent.invoke(state, config=config)


def _response_payload(run_id: str, contact: dict, result: dict) -> dict:
    return {
        "run_id": run_id,
        "contact_name": contact.get("name"),
        "profile_signals": result["profile_signals"],
        "search_trace": result["search_trace"],
        "recommended_gifts": result["recommended_gifts"],
        "human_review": result["human_review"],
        "learning_context": get_learning_summary(contact),
        "errors": result["errors"],
    }


@app.get("/")
def root():
    return {"status": "DelightLoop Gift Agent is running"}


@app.post("/recommend")
def recommend_gifts(contact: dict):
    """
    Run the gift recommendation workflow for a single contact.
    Loads persisted reviewer feedback for this contact when available.
    """
    try:
        run_id = str(uuid.uuid4())
        result = _invoke_workflow(contact, run_id)
        results_store[run_id] = result
        return _response_payload(run_id, contact, result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recommend/bulk")
def recommend_bulk(contacts: list):
    """
    Run gift recommendations for multiple contacts.
    """
    results = []
    for contact in contacts:
        try:
            run_id = str(uuid.uuid4())
            result = _invoke_workflow(contact, run_id)
            results_store[run_id] = result

            results.append({
                "run_id": run_id,
                "contact_name": contact.get("name"),
                "recommended_gifts": result["recommended_gifts"],
                "human_review": result["human_review"],
                "learning_context": get_learning_summary(contact),
                "errors": result["errors"],
            })

        except Exception as e:
            results.append({
                "contact_name": contact.get("name"),
                "error": str(e),
            })

    return results


@app.post("/review/{run_id}")
def update_review(run_id: str, action: str, notes: Optional[str] = None):
    """
    Human review action — approve, reject, edit, or regenerate.
    Persists feedback for future runs on the same contact.
    """
    if run_id not in results_store:
        raise HTTPException(status_code=404, detail="Run ID not found")

    valid_actions = ["approve", "reject", "edit", "regenerate"]
    if action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Must be one of: {valid_actions}"
        )

    stored = results_store[run_id]
    contact = stored["contact"]
    prior_notes = stored.get("human_review", {}).get("reviewer_notes") or ""
    feedback_notes = notes if notes else prior_notes
    gifts = stored.get("recommended_gifts", [])

    if action == "edit":
        stored["human_review"] = {
            "status": "edited",
            "available_actions": valid_actions,
            "reviewer_notes": feedback_notes,
        }
        if feedback_notes:
            save_feedback(contact, run_id, "edited", feedback_notes, gifts)

    elif action == "regenerate":
        save_feedback(contact, run_id, "regenerate", feedback_notes, gifts)
        result = _invoke_workflow(contact, run_id, session_notes=feedback_notes)
        results_store[run_id] = result
        results_store[run_id]["human_review"] = {
            "status": "pending_review",
            "available_actions": valid_actions,
            "reviewer_notes": feedback_notes,
        }

    else:
        stored["human_review"] = {
            "status": action + "d",
            "available_actions": valid_actions,
            "reviewer_notes": feedback_notes,
        }
        save_feedback(contact, run_id, action, feedback_notes, gifts)
        record_human_feedback(run_id, action, feedback_notes)

    return {
        "run_id": run_id,
        "action": action,
        "human_review": results_store[run_id]["human_review"],
        "recommended_gifts": results_store[run_id].get("recommended_gifts", []),
        "profile_signals": results_store[run_id].get("profile_signals", {}),
        "search_trace": results_store[run_id].get("search_trace", {}),
        "learning_context": get_learning_summary(contact),
        "errors": results_store[run_id].get("errors", []),
    }


@app.get("/feedback")
def get_contact_feedback(name: str, company: str):
    """Inspect persisted feedback history for a contact."""
    contact = {"name": name, "company": company}
    return {
        "contact_name": name,
        "company": company,
        "entries": get_feedback_entries(contact),
        "learning_context": get_learning_summary(contact),
    }


@app.get("/results/{run_id}")
def get_result(run_id: str):
    """
    Get stored result by run ID.
    """
    if run_id not in results_store:
        raise HTTPException(status_code=404, detail="Run ID not found")
    return results_store[run_id]


@app.get("/results")
def list_results():
    """
    List all run IDs and contact names.
    """
    return [
        {
            "run_id": rid,
            "contact_name": r.get("contact", {}).get("name", "Unknown"),
            "status": r.get("human_review", {}).get("status", "unknown"),
        }
        for rid, r in results_store.items()
    ]
