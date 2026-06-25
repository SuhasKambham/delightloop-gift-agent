from app.workflow.state import GraphState


def human_review(state: GraphState) -> GraphState:
    print(">> Step 6: Awaiting human review...")
    state["current_step"] = "human_review"
    state["human_review"] = {
        "status": "pending_review",
        "available_actions": ["approve", "reject", "edit", "regenerate"],
        "reviewer_notes": None
    }
    return state