from app.workflow.state import GraphState
from app.services.search import search_products, generate_search_queries


def _dedupe_products(products: list) -> list:
    seen = set()
    unique = []
    for p in products:
        key = (p.get("title", "").lower().strip(), p.get("url", ""))
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def search_products_node(state: GraphState) -> GraphState:
    retry_count = state.get("search_retry_count", 0)
    is_retry = retry_count > 0
    print(f">> Step 3: Searching for products{' (retry ' + str(retry_count) + ')' if is_retry else ''}...")

    try:
        signals = state["profile_signals"]
        gift_context = state["contact"]["gift_context"]
        reviewer_feedback = state.get("reviewer_feedback", "")

        queries = generate_search_queries(
            contact=state["contact"],
            signals=signals,
            retry_attempt=retry_count,
            reviewer_feedback=reviewer_feedback
        )

        print(f"   Queries generated: {queries}")

        new_products = []
        for query in queries:
            print(f"   Searching: {query}")
            results = search_products(query=query, country="in")
            new_products.extend(results)

        if is_retry:
            existing = state.get("raw_products", [])
            all_products = _dedupe_products(existing + new_products)
        else:
            all_products = _dedupe_products(new_products)

        prior_queries = state.get("search_trace", {}).get("queries_used", [])
        state["search_trace"] = {
            "queries_used": prior_queries + queries if is_retry else queries,
            "products_considered_count": len(all_products),
            "search_retries": retry_count,
        }

        state["raw_products"] = all_products
        state["current_step"] = "search_products"
        print(f"   Found {len(all_products)} unique products total")

    except Exception as e:
        print(f"   ERROR in product search: {e}")
        state["errors"].append(f"search_error: {str(e)}")
        if not is_retry:
            state["raw_products"] = []

    return state
