from serpapi import GoogleSearch
from dotenv import load_dotenv
import os
import urllib.parse
import json
import re

load_dotenv()


SEARCH_PLANNER_PROMPT = """
You are a gift search strategist for a corporate gifting AI agent.

Your job is to convert extracted profile signals into specific purchasable gift
categories and Google Shopping search queries.

INPUT CONTEXT:
Strong signals: {strong_signals}
Weak signals: {weak_signals}
Signals to avoid: {signals_to_avoid}

Occasion: {occasion}
Budget: {currency} {budget_min} to {budget_max}
Country: {country}
Relationship type: {relationship_type}
Business goal: {business_goal}
Reviewer feedback: {reviewer_feedback}

RULES:
- Create search plans from the recipient's actual interests, not generic corporate gifting.
- Strong signals should dominate the search plan.
- Every query MUST target the provided budget range: {budget_min} to {budget_max} rupees.
- Do NOT generate lower price ranges than {budget_min}.
- For higher budgets, search for premium products, bundles, subscriptions, kits, or higher-end accessories.
- Relationship context may affect price level and tone, but must NOT override product category.
- Do NOT default to hampers, executive gift boxes, or generic corporate gifts unless there are no usable personal/professional signals.
- For each strong signal, generate concrete purchasable gift categories.
- Queries must be specific enough to find real products in India.
- Include known product/category words when useful, but do not invent fake products.
- Stay within or near the stated budget range.
- Never infer religion, politics, health, family status, ethnicity, or other sensitive attributes.
- Return ONLY valid JSON.

Return this exact JSON shape:
{{
  "search_plan": [
    {{
      "matched_signal": "Mechanical Keyboards",
      "gift_category": "premium mechanical keyboard accessories",
      "queries": [
        "premium mechanical keyboard accessories India {budget_min} to {budget_max} rupees Amazon Flipkart",
        "Keychron wrist rest desk mat artisan keycaps India {budget_min} to {budget_max} rupees"
      ]
    }}
  ]
}}
"""

'''
def build_fallback_url(title: str, store: str) -> str:
    encoded = urllib.parse.quote_plus(title)
    store_lower = store.lower()

    if "amazon" in store_lower:
        return f"https://www.amazon.in/s?k={encoded}"
    elif "flipkart" in store_lower:
        return f"https://www.flipkart.com/search?q={encoded}"
    else:
        return f"https://www.google.com/search?tbm=shop&q={encoded}"
'''
def build_fallback_url(title: str, store: str) -> str:
    encoded = urllib.parse.quote_plus(title)
    return f"https://www.google.com/search?tbm=shop&q={encoded}"

def search_products(
    query: str,
    country: str = "in",
    matched_signal: str = "",
    gift_category: str = "",
) -> list:
    try:
        params = {
            "engine": "google",
            "q": query + " buy online",
            "gl": country,
            "hl": "en",
            "tbm": "shop",
            "num": 10,
            "api_key": os.getenv("SERPAPI_KEY"),
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        shopping_results = results.get("shopping_results", [])

        products = []

        for item in shopping_results[:5]:
            title = item.get("title", "")
            store = item.get("source", "")

            url = (
                item.get("link")
                or item.get("product_link")
                or item.get("source_url")
                or ""
            )

            if not url or "google.com/search" in url:
                url = build_fallback_url(title, store)

            products.append({
                "title": title,
                "url": url,
                "store": store,
                "price_raw": item.get("price", ""),
                "snippet": item.get("snippet", ""),
                "matched_signal": matched_signal,
                "gift_category": gift_category or query,
            })

        return products

    except Exception as e:
        print(f"   Search error: {e}")
        return []


def _clean_llm_json(raw: str) -> str:
    text = raw.strip()

    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        text = match.group(0)

    return text


def _enforce_budget_in_query(query: str, budget_min: int, budget_max: int) -> str:
    """
    Force LLM-generated search queries to respect the requested budget range.
    The LLM can choose categories, but Python enforces the actual price band.
    """
    budget_text = f"{budget_min} to {budget_max} rupees"

    # Replace explicit ranges like "1000 to 3000 rupees" or "1000-3000 INR".
    query = re.sub(
        r"\b\d{3,6}\s*(to|-)\s*\d{3,6}\s*(rupees|inr)?\b",
        budget_text,
        query,
        flags=re.IGNORECASE,
    )

    # Replace under/upto language, e.g. "under 5000 rupees".
    query = re.sub(
        r"\b(under|below|upto|up to|less than)\s*\d{3,6}\s*(rupees|inr)?\b",
        budget_text,
        query,
        flags=re.IGNORECASE,
    )

    # If the query has no price language at all, append the required range.
    if "rupees" not in query.lower() and "inr" not in query.lower():
        query = f"{query} {budget_text}"

    return query.strip()


def _fallback_search_plan(signals: dict, gift_context: dict) -> list[dict]:
    budget_min = int(gift_context["budget_min"])
    budget_max = int(gift_context["budget_max"])

    strong = signals.get("strong_signals", [])
    weak = signals.get("weak_signals", [])
    usable_signals = strong or weak or ["professional interests"]

    plan = []

    for signal in usable_signals[:4]:
        query = f"{signal} premium gift India {budget_min} to {budget_max} rupees Amazon Flipkart"
        plan.append({
            "matched_signal": signal,
            "gift_category": f"premium gift related to {signal}",
            "queries": [query],
        })

    return plan


def generate_search_plan_with_llm(
    signals: dict,
    gift_context: dict,
    relationship_context: dict,
    retry_attempt: int = 0,
    reviewer_feedback: str = "",
) -> list[dict]:
    try:
        from app.services.llm import get_llm
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_template(SEARCH_PLANNER_PROMPT)
        llm = get_llm()
        chain = prompt | llm

        retry_instruction = ""
        if retry_attempt > 0:
            retry_instruction = (
                f"Previous search attempt #{retry_attempt} did not produce enough "
                "good products. Generate different, more premium product queries "
                "inside the requested budget range."
            )

        budget_min = int(gift_context.get("budget_min", 0))
        budget_max = int(gift_context.get("budget_max", 0))

        response = chain.invoke({
            "strong_signals": ", ".join(signals.get("strong_signals", [])),
            "weak_signals": ", ".join(signals.get("weak_signals", [])),
            "signals_to_avoid": ", ".join(signals.get("signals_to_avoid", [])),
            "occasion": gift_context.get("occasion", ""),
            "currency": gift_context.get("currency", "INR"),
            "budget_min": budget_min,
            "budget_max": budget_max,
            "country": gift_context.get("country", "India"),
            "relationship_type": relationship_context.get("relationship_type", ""),
            "business_goal": relationship_context.get("business_goal", ""),
            "reviewer_feedback": reviewer_feedback or retry_instruction,
        })

        raw = response.content if hasattr(response, "content") else str(response)
        result = json.loads(_clean_llm_json(raw))
        search_plan = result.get("search_plan", [])

        cleaned_plan = []
        seen_queries = set()

        for item in search_plan:
            matched_signal = item.get("matched_signal", "").strip()
            gift_category = item.get("gift_category", "").strip()
            queries = item.get("queries", [])

            if not matched_signal or not gift_category or not isinstance(queries, list):
                continue

            clean_queries = []
            for query in queries:
                if not isinstance(query, str):
                    continue

                query = query.strip()
                if not query:
                    continue

                query = _enforce_budget_in_query(query, budget_min, budget_max)

                if query.lower() in seen_queries:
                    continue

                seen_queries.add(query.lower())
                clean_queries.append(query)

            if clean_queries:
                cleaned_plan.append({
                    "matched_signal": matched_signal,
                    "gift_category": gift_category,
                    "queries": clean_queries[:2],
                })

        if cleaned_plan:
            return cleaned_plan[:6]

    except Exception as e:
        print(f"   LLM search planning failed: {e}")

    return _fallback_search_plan(signals, gift_context)


def generate_search_queries(
    signals: dict,
    gift_context: dict,
    retry_attempt: int = 0,
    reviewer_feedback: str = "",
) -> list:
    relationship_context = {
        "relationship_type": "",
        "business_goal": "",
    }

    search_plan = generate_search_plan_with_llm(
        signals=signals,
        gift_context=gift_context,
        relationship_context=relationship_context,
        retry_attempt=retry_attempt,
        reviewer_feedback=reviewer_feedback,
    )

    queries = []
    for item in search_plan:
        queries.extend(item.get("queries", []))

    return queries[:6]


def score_product_signal_match(
    product: dict,
    strong_signals: list,
    weak_signals: list,
) -> float:
    text = " ".join([
        product.get("title", ""),
        product.get("snippet", ""),
        product.get("gift_category", ""),
        product.get("matched_signal", ""),
    ]).lower()

    score = 0.0
    matched_signal = product.get("matched_signal", "").lower()

    for signal in strong_signals:
        signal_lower = signal.lower().strip()

        if matched_signal == signal_lower:
            score += 40

        if signal_lower and signal_lower in text:
            score += 25

    for signal in weak_signals:
        signal_lower = signal.lower().strip()

        if matched_signal == signal_lower:
            score += 15

        if signal_lower and signal_lower in text:
            score += 10

    specific_terms = [
        "keyboard",
        "keychron",
        "keycap",
        "desk mat",
        "coffee",
        "espresso",
        "aeropress",
        "grinder",
        "french press",
        "book",
        "architecture",
        "engineering",
        "running",
        "cycling",
        "camera",
        "photography",
        "tripod",
        "lens",
        "foam roller",
        "massage",
        "hydration",
    ]

    if any(term in text for term in specific_terms):
        score += 10

    generic_terms = [
        "hamper",
        "gift box",
        "gift set",
        "corporate gift",
        "executive gift",
        "birthday gift",
    ]

    if any(term in text for term in generic_terms):
        score -= 15

    return max(score, 0.0)
