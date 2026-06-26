from app.workflow.state import GraphState
from app.services.llm import get_llm
from app.services.search import score_product_signal_match
from langchain_core.prompts import ChatPromptTemplate
import json
import re


RANKING_PROMPT = """
You are an expert corporate gifting consultant.

Given validated products and contact profile signals, rank the TOP 3 most appropriate gifts
and write a genuinely personalised message for each.

CONTACT:
Name: {name}
Role: {role}
Company: {company}
Occasion: {occasion}
Relationship: {relationship_type}
Last Interaction: {last_interaction}
Business Goal: {business_goal}

{reviewer_feedback_section}

BUDGET: {currency} {budget_min} to {budget_max} (strict — gifts must fall in this range)

PROFILE SIGNALS:
Strong: {strong_signals}
Weak: {weak_signals}
Avoid: {signals_to_avoid}

VALIDATED PRODUCTS:
{products}

RANKING RULES:
- Pick the top 3 DISTINCT gifts from the products list.
- Prefer products with the highest Signal Match Score.
- The product must directly match at least one strong or weak profile signal.
- Do not invent a connection between a product and a signal.
- Generic hampers, vague gift boxes, and executive gift sets should be ranked only if there are no specific signal-matched products.
- Relationship context should affect tone, budget, and formality, not override the recipient's actual interests.
- Heavily penalise any product priced outside {currency} {budget_min}–{budget_max}.
- Out-of-budget products must score confidence <= 0.3 regardless of relevance.
- Prefer in-budget products; if fewer than 3 exist, rank what you have and lower confidence.
- Confidence must reflect product match quality, price fit, and data quality.

REASONING RULES:
- Reference the exact matched signal and gift category shown for the product.
- Explain why THIS product fits THIS person.
- Never claim a product matches a signal unless the product title, category, or snippet supports that connection.
- Never infer religion, politics, health, family status, ethnicity, or gender.

MESSAGE RULES:
- Write 2–3 sentences maximum, warm and professional.
- Open with something specific to THIS contact.
- Mention one concrete signal naturally.
- Tie the gift to that signal.
- Match tone to the relationship ({relationship_type}) and occasion ({occasion}).

Return ONLY valid JSON in this exact format:
{{
    "recommended_gifts": [
        {{
            "rank": 1,
            "gift_name": "product title here",
            "product_url": "url here",
            "store": "store name here",
            "estimated_price": "price here",
            "why_this_gift": "specific reason this product fits this contact",
            "personalisation_reasoning": "which exact profile signals drove this pick",
            "personalised_message": "specific warm note — not generic",
            "confidence_score": 0.85,
            "risk_level": "low",
            "assumptions": ["assumption 1"]
        }},
        {{ "rank": 2, ... }},
        {{ "rank": 3, ... }}
    ]
}}
"""


def _parse_llm_json(raw: str) -> dict:
    text = raw.strip()

    if text.startswith("```"):
        text = text.split("```")[1]

        if text.startswith("json"):
            text = text[4:]

        text = text.strip()

    match = re.search(r"\{[\s\S]*\}", text)

    if match:
        text = match.group(0)

    return json.loads(text)


def _fallback_rank(validated_products: list, contact: dict, signals: dict) -> list:
    name = contact["name"].split()[0]
    strong = signals.get("strong_signals", [])
    signal_hint = strong[0] if strong else "your professional interests"

    gifts = []

    for index, product in enumerate(validated_products[:3]):
        matched_signal = product.get("matched_signal") or signal_hint
        gift_category = product.get("gift_category") or "gift"

        gifts.append({
            "rank": index + 1,
            "gift_name": product["title"],
            "product_url": product["url"],
            "store": product.get("store", ""),
            "estimated_price": product.get("price_raw", ""),
            "why_this_gift": (
                f"This product was retrieved for {matched_signal} and fits the "
                f"{gift_category} category within the stated budget."
            ),
            "personalisation_reasoning": (
                f"Selected because it directly connects to {matched_signal}, one of "
                "the extracted profile signals."
            ),
            "personalised_message": (
                f"Hi {name}, your interest in {matched_signal.lower()} stood out, "
                f"so I thought this would be a thoughtful way to mark the occasion. "
                "Appreciate the partnership and look forward to what we build next."
            ),
            "confidence_score": 0.6,
            "risk_level": "medium",
            "assumptions": ["Fallback ranking used because LLM parsing failed"],
        })

    return gifts


def _format_reviewer_feedback(reviewer_feedback: str | None) -> str:
    if not reviewer_feedback or not reviewer_feedback.strip():
        return ""

    return f"""CRITICAL REVIEWER FEEDBACK:
{reviewer_feedback.strip()}

You MUST change your recommendations based on the above feedback.
If reviewer said suggestions were too generic, choose more specific signal-matched products.
Do NOT repeat the same gifts or messages from previous runs.
"""


def _prepare_ranked_products(validated_products: list, signals: dict) -> list:
    strong_signals = signals.get("strong_signals", [])
    weak_signals = signals.get("weak_signals", [])

    for product in validated_products:
        product["signal_match_score"] = score_product_signal_match(
            product,
            strong_signals,
            weak_signals,
        )

    return sorted(
        validated_products,
        key=lambda product: (
            product.get("signal_match_score", 0),
            1 if product.get("is_price_in_budget") else 0,
            product.get("price_numeric", 0),
        ),
        reverse=True,
    )


def rank_gifts(state: GraphState) -> GraphState:
    print(">> Step 5: Ranking gifts...")

    reviewer_feedback = state.get("reviewer_feedback", "")

    if reviewer_feedback:
        print(f"   Reviewer feedback injected: {reviewer_feedback[:100]}...")
    else:
        print("   No reviewer feedback for this run")

    try:
        validated_products = state["validated_products"]

        if not validated_products:
            print("   No validated products to rank — skipping")
            state["errors"].append("ranking_error: no validated products available")
            state["recommended_gifts"] = []
            return state

        contact = state["contact"]
        signals = state["profile_signals"]
        gift_context = contact["gift_context"]
        relationship_context = contact["relationship_context"]

        validated_products = _prepare_ranked_products(validated_products, signals)

        products_str = ""

        for index, product in enumerate(validated_products):
            budget_flag = "IN BUDGET" if product.get("is_price_in_budget") else "OUT OF BUDGET"

            products_str += f"""
Product {index + 1} [{budget_flag}]:
  Title: {product['title']}
  Store: {product['store']}
  Price: {product['price_raw']} (numeric: {product.get('price_numeric', 'unknown')})
  URL: {product['url']}
  Matched Signal: {product.get('matched_signal', '')}
  Gift Category: {product.get('gift_category', '')}
  Signal Match Score: {product.get('signal_match_score', 0)}
  Snippet: {product.get('snippet', '')}
"""

        llm = get_llm()
        prompt = ChatPromptTemplate.from_template(RANKING_PROMPT)
        chain = prompt | llm

        invoke_args = {
            "name": contact["name"],
            "role": contact["role"],
            "company": contact["company"],
            "occasion": gift_context["occasion"],
            "relationship_type": relationship_context["relationship_type"],
            "last_interaction": relationship_context.get("last_interaction", "Not specified"),
            "business_goal": relationship_context.get("business_goal", ""),
            "currency": gift_context["currency"],
            "budget_min": gift_context["budget_min"],
            "budget_max": gift_context["budget_max"],
            "strong_signals": ", ".join(signals.get("strong_signals", [])),
            "weak_signals": ", ".join(signals.get("weak_signals", [])),
            "signals_to_avoid": ", ".join(signals.get("signals_to_avoid", [])),
            "products": products_str,
            "reviewer_feedback_section": _format_reviewer_feedback(reviewer_feedback),
        }

        gifts = []
        last_error = None

        for attempt in range(2):
            response = chain.invoke(invoke_args)
            raw = response.content if hasattr(response, "content") else str(response)

            try:
                result = _parse_llm_json(raw)
                gifts = result.get("recommended_gifts", [])

                if gifts:
                    break

            except (json.JSONDecodeError, AttributeError) as e:
                last_error = e
                print(f"   Ranking parse attempt {attempt + 1} failed: {e}")

                if raw:
                    print(f"   Raw response preview: {raw[:200]}...")

        if not gifts:
            print("   Using fallback deterministic ranking")
            gifts = _fallback_rank(validated_products, contact, signals)

            if last_error:
                state["errors"].append(f"ranking_fallback: LLM parse failed ({last_error})")

        state["recommended_gifts"] = gifts
        state["current_step"] = "rank_gifts"

        print(f"   Ranked {len(gifts)} gifts successfully")

        for gift in gifts:
            print(
                f"   Rank {gift['rank']}: {gift['gift_name']} "
                f"— confidence: {gift['confidence_score']}"
            )

    except Exception as e:
        print(f"   ERROR in ranking: {e}")
        state["errors"].append(f"ranking_error: {str(e)}")
        state["recommended_gifts"] = []

    return state
