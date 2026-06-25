from langgraph.graph import StateGraph, END
from app.workflow.state import GraphState
from app.workflow.nodes.ingest import ingest_contact
from app.workflow.nodes.signals import extract_signals
from app.workflow.nodes.search import search_products_node
from app.workflow.nodes.validate import validate_products
from app.workflow.nodes.rank import rank_gifts
from app.workflow.nodes.review import human_review

MAX_SEARCH_RETRIES = 3  # initial search + up to 2 retries
MIN_VALIDATED_PRODUCTS = 3


def route_after_validate(state: GraphState) -> str:
    validated_count = len(state.get("validated_products", []))
    retry_count = state.get("search_retry_count", 0)

    if validated_count < MIN_VALIDATED_PRODUCTS and retry_count < MAX_SEARCH_RETRIES:
        print(f"   Only {validated_count} validated products — retrying search (attempt {retry_count + 1}/{MAX_SEARCH_RETRIES})")
        return "search_products"
    return "rank_gifts"


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("ingest_contact", ingest_contact)
    graph.add_node("extract_signals", extract_signals)
    graph.add_node("search_products", search_products_node)
    graph.add_node("validate_products", validate_products)
    graph.add_node("rank_gifts", rank_gifts)
    graph.add_node("human_review", human_review)

    graph.set_entry_point("ingest_contact")
    graph.add_edge("ingest_contact", "extract_signals")
    graph.add_edge("extract_signals", "search_products")
    graph.add_edge("search_products", "validate_products")
    graph.add_conditional_edges(
        "validate_products",
        route_after_validate,
        {
            "search_products": "search_products",
            "rank_gifts": "rank_gifts",
        },
    )
    graph.add_edge("rank_gifts", "human_review")
    graph.add_edge("human_review", END)

    return graph.compile()


gift_agent = build_graph()
