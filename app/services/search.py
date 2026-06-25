from serpapi import GoogleSearch
from dotenv import load_dotenv
import os
import urllib.parse

load_dotenv()


def build_fallback_url(title: str, store: str) -> str:
    """
    Build a direct search URL on Amazon or Flipkart
    when SerpAPI doesn't return a direct link.
    """
    encoded = urllib.parse.quote_plus(title)

    store_lower = store.lower()

    if "amazon" in store_lower:
        return f"https://www.amazon.in/s?k={encoded}"
    elif "flipkart" in store_lower:
        return f"https://www.flipkart.com/search?q={encoded}"
    else:
        return f"https://www.google.com/search?tbm=shop&q={encoded}"


def search_products(query: str, country: str = "in") -> list:
    try:
        params = {
            "engine": "google",
            "q": query + " buy online",
            "gl": country,
            "hl": "en",
            "tbm": "shop",
            "num": 10,
            "api_key": os.getenv("SERPAPI_KEY")
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        shopping_results = results.get("shopping_results", [])

        products = []
        for item in shopping_results[:5]:
            title = item.get("title", "")
            store = item.get("source", "")

            url = (
                item.get("link") or
                item.get("product_link") or
                item.get("source_url") or
                ""
            )

            if not url or "google.com/search" in url:
                url = build_fallback_url(title, store)

            products.append({
                "title": title,
                "url": url,
                "store": store,
                "price_raw": item.get("price", ""),
                "snippet": item.get("snippet", ""),
            })

        return products

    except Exception as e:
        print(f"   Search error: {e}")
        return []


def generate_search_queries(signals: dict, gift_context: dict, retry_attempt: int = 0) -> list:
    budget_min = gift_context["budget_min"]
    budget_max = gift_context["budget_max"]
    currency = gift_context["currency"]
    strong = signals.get("strong_signals", [])
    weak = signals.get("weak_signals", [])

    if retry_attempt == 0:
        return _primary_queries(strong, weak, budget_min, budget_max)
    if retry_attempt == 1:
        return _broader_queries(strong, weak, budget_min, budget_max)
    return _aggressive_queries(strong, budget_min, budget_max)


def _primary_queries(strong: list, weak: list, budget_min: float, budget_max: float) -> list:
    queries = []

    if any("cricket" in s.lower() for s in strong):
        queries.append(f"premium cricket gift hamper India {budget_min} to {budget_max} INR")
        queries.append(f"cricket memorabilia luxury gift box India {budget_max} rupees")

    if any("leadership" in s.lower() or "book" in s.lower() or "saas" in s.lower() or "gtm" in s.lower() or "sales" in s.lower() for s in strong):
        queries.append(f"executive leadership gift hamper India {budget_min} to {budget_max} rupees")

    if any("coffee" in s.lower() for s in strong + weak):
        queries.append(f"premium coffee gift set India {budget_min} to {budget_max} rupees")

    if any("trek" in s.lower() or "hik" in s.lower() for s in strong + weak):
        queries.append(f"premium trekking gift set India {budget_max} rupees")

    if any("design" in s.lower() for s in strong + weak):
        queries.append(f"design thinking premium book gift set India {budget_max} rupees")

    queries.append(f"luxury corporate gift hamper India {budget_min} to {budget_max} rupees Amazon Flipkart")

    return queries[:4]


def _broader_queries(strong: list, weak: list, budget_min: float, budget_max: float) -> list:
    """Retry 1: broader premium queries with explicit store and price anchors."""
    mid = int((budget_min + budget_max) / 2)
    queries = [
        f"luxury gift hamper under {budget_max} rupees Amazon India",
        f"premium executive gift set {mid} rupees India buy online",
        f"corporate thank you gift box {budget_min} INR India",
    ]

    if any("cricket" in s.lower() for s in strong):
        queries.append(f"premium cricket bat signed memorabilia gift {budget_max} rupees India")

    return queries[:4]


def _aggressive_queries(strong: list, budget_min: float, budget_max: float) -> list:
    """Retry 2: price-tier targeted queries when budget fit is still poor."""
    queries = [
        f"gift set {budget_min} rupees India buy online premium",
        f"luxury hamper {budget_max} INR Flipkart corporate gift",
        f"executive gift box India price {budget_min} to {budget_max}",
    ]

    for signal in strong[:2]:
        topic = signal.split()[0] if signal else "professional"
        queries.append(f"premium {topic} gift India {budget_max} rupees")

    return queries[:4]
