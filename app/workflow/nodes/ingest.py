from app.workflow.state import GraphState


def ingest_contact(state: GraphState) -> GraphState:
    print(">> Step 1: Ingesting contact...")
    state["current_step"] = "ingest_contact"
    return state