from app.workflow.state import GraphState
from app.utils.validators import (
    parse_price,
    is_price_in_budget,
    is_url_valid,
    is_appropriate_for_professional
)


def validate_products(state: GraphState) -> GraphState:
    print(">> Step 4: Validating products...")

    try:
        raw_products = state["raw_products"]
        gift_context = state["contact"]["gift_context"]
        budget_min = gift_context["budget_min"]
        budget_max = gift_context["budget_max"]

        validated = []

        for product in raw_products:
            title = product.get("title", "")
            url = product.get("url", "")
            price_raw = product.get("price_raw", "")

            price_numeric = parse_price(price_raw)
            price_ok = is_price_in_budget(price_numeric, budget_min, budget_max)
            url_ok = is_url_valid(url)
            appropriate = is_appropriate_for_professional(title)

            product["price_numeric"] = price_numeric
            product["is_price_in_budget"] = price_ok
            product["is_url_valid"] = url_ok
            product["is_appropriate"] = appropriate

            print(f"   {title[:50]}...")
            print(f"     Price: {price_raw} ({price_numeric}) | In budget: {price_ok} | URL: {url_ok} | OK: {appropriate}")

            # Price and appropriateness are hard filters
            # URL is soft — we built fallback URLs so keep them
            if price_ok and appropriate:
                validated.append(product)

        state["validated_products"] = validated
        state["current_step"] = "validate_products"

        print(f"\n   {len(validated)} products passed validation out of {len(raw_products)}")

        if len(validated) < 3:
            state["search_retry_count"] = state.get("search_retry_count", 0) + 1

    except Exception as e:
        print(f"   ERROR in validation: {e}")
        state["errors"].append(f"validation_error: {str(e)}")
        state["validated_products"] = []

    return state