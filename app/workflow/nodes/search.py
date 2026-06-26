from app.workflow.state import GraphState
from app.services.search import search_products, generate_search_plan_with_llm


def _dedupe_products(products: list) -> list:
    seen = set()
    unique = []

    for product in products:
        key = (
            product.get("title", "").lower().strip(),
            product.get("url", "").lower().strip(),
        )

        if key not in seen:
            seen.add(key)
            unique.append(product)

    return unique


def _flatten_queries(search_plan: list[dict]) -> list[str]:
    queries = []

    for item in search_plan:
        queries.extend(item.get("queries", []))

    return queries


def search_products_node(state: GraphState) -> GraphState:
    retry_count = state.get("search_retry_count", 0)
    is_retry = retry_count > 0

    print(
        f">> Step 3: Searching for products"
        f"{' (retry ' + str(retry_count) + ')' if is_retry else ''}..."
    )

    try:
        signals = state["profile_signals"]
        contact = state["contact"]
        gift_context = contact["gift_context"]
        relationship_context = contact["relationship_context"]
        reviewer_feedback = state.get("reviewer_feedback", "")

        search_plan = generate_search_plan_with_llm(
            signals=signals,
            gift_context=gift_context,
            relationship_context=relationship_context,
            retry_attempt=retry_count,
            reviewer_feedback=reviewer_feedback,
        )

        queries = _flatten_queries(search_plan)

        print(f"   Search plan generated: {len(search_plan)} categories")
        print(f"   Queries generated: {queries}")

        new_products = []

        for item in search_plan:
            matched_signal = item.get("matched_signal", "")
            gift_category = item.get("gift_category", "")
            item_queries = item.get("queries", [])

            for query in item_queries:
                print(f"   Searching: {query}")
                results = search_products(
                    query=query,
                    country="in",
                    matched_signal=matched_signal,
                    gift_category=gift_category,
                )
                new_products.extend(results)

        if is_retry:
            existing_products = state.get("raw_products", [])
            all_products = _dedupe_products(existing_products + new_products)
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
