from serpapi import GoogleSearch
from dotenv import load_dotenv
import os
import urllib.parse

load_dotenv()


def build_fallback_url(title: str, store: str) -> str:
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


def _primary_queries(strong: list, weak: list, budget_min: float, budget_max: float) -> list:
    queries = []

    if any("cricket" in s.lower() for s in strong):
        queries.append(f"premium cricket gift hamper India {budget_min} to {budget_max} INR")
        queries.append(f"cricket memorabilia luxury gift box India {budget_max} rupees")

    if any(
        "leadership" in s.lower() or "book" in s.lower() or
        "saas" in s.lower() or "gtm" in s.lower() or "sales" in s.lower()
        for s in strong
    ):
        queries.append(f"executive leadership gift hamper India {budget_min} to {budget_max} rupees")

    if any("coffee" in s.lower() for s in strong + weak):
        queries.append(f"premium coffee gift set India {budget_min} to {budget_max} rupees")

    if any("trek" in s.lower() or "hik" in s.lower() for s in strong + weak):
        queries.append(f"premium trekking gift set India {budget_max} rupees")

    if any("design" in s.lower() for s in strong + weak):
        queries.append(f"design thinking premium book gift set India {budget_max} rupees")

    queries.append(
        f"luxury corporate gift hamper India {budget_min} to {budget_max} rupees Amazon Flipkart"
    )

    return queries[:4]


def _broader_queries(strong: list, weak: list, budget_min: float, budget_max: float) -> list:
    mid = (budget_min + budget_max) / 2
    return [
        f"luxury gift hamper under {budget_max} rupees Amazon India",
        f"premium executive gift set {int(mid)} rupees India buy online",
        f"corporate thank you gift box {int(budget_min)} INR India",
        f"gift set {int(budget_min)} rupees India buy online premium",
    ]


def _aggressive_queries(strong: list, budget_min: float, budget_max: float) -> list:
    signal = strong[0].lower() if strong else "corporate"
    return [
        f"luxury hamper {int(budget_max)} INR Flipkart corporate gift",
        f"executive gift box India price {int(budget_min)} to {int(budget_max)}",
        f"premium {signal} gift India {int(budget_max)} rupees",
    ]


def _feedback_queries(reviewer_feedback: str, budget_min: float, budget_max: float) -> list:
    if not reviewer_feedback or not reviewer_feedback.strip():
        return []

    try:
        from app.services.llm import get_llm
        from langchain_core.prompts import ChatPromptTemplate
        import json

        prompt = ChatPromptTemplate.from_template("""
You are a search query generator for a gift recommendation system.
A human reviewer left this feedback about gift recommendations:
"{feedback}"
Budget range: {budget_min} to {budget_max} INR
Country: India
Generate 1-2 specific Google Shopping search queries to find the exact type of
products the reviewer is asking for. Queries should target Amazon.in or Flipkart.
Return ONLY a JSON array of query strings. No explanation. Example:
["electric kettle gift India under 3000 rupees", "coffee maker gift India 2000 to 4000 rupees"]
""")

        llm = get_llm()
        chain = prompt | llm
        response = chain.invoke({
            "feedback": reviewer_feedback.strip(),
            "budget_min": budget_min,
            "budget_max": budget_max
        })

        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        queries = json.loads(raw)
        if isinstance(queries, list):
            print(f"   Feedback-driven queries: {queries}")
            return queries[:2]

    except Exception as e:
        print(f"   Feedback query generation failed: {e}")

    return []


def generate_search_queries(
    signals: dict,
    gift_context: dict,
    retry_attempt: int = 0,
    reviewer_feedback: str = ""
) -> list:
    budget_min = gift_context["budget_min"]
    budget_max = gift_context["budget_max"]
    strong = signals.get("strong_signals", [])
    weak = signals.get("weak_signals", [])

    feedback_queries = _feedback_queries(reviewer_feedback, budget_min, budget_max)

    if retry_attempt == 0:
        base = _primary_queries(strong, weak, budget_min, budget_max)
    elif retry_attempt == 1:
        base = _broader_queries(strong, weak, budget_min, budget_max)
    else:
        base = _aggressive_queries(strong, budget_min, budget_max)

    combined = feedback_queries + [q for q in base if q not in feedback_queries]
    return combined[:4]
