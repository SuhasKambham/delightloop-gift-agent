from app.workflow.state import GraphState
from app.services.llm import get_llm
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

BUDGET: {currency} {budget_min} to {budget_max} (strict — gifts must fall in this range)

PROFILE SIGNALS:
Strong: {strong_signals}
Weak: {weak_signals}
Avoid: {signals_to_avoid}

VALIDATED PRODUCTS (each line shows whether price is in budget):
{products}

{reviewer_feedback_section}

RANKING RULES:
- Pick the top 3 DISTINCT gifts from the products list (never rank the same product twice)
- Heavily penalise any product priced outside {currency} {budget_min}–{budget_max}.
  Out-of-budget products must score confidence <= 0.3 regardless of relevance.
- Prefer in-budget products; if fewer than 3 exist, rank what you have and lower overall confidence.
- Confidence must reflect data quality: sparse signals or weak product matches → lower scores.

REASONING RULES (why_this_gift and personalisation_reasoning):
- Reference specific profile signals by name (e.g. cricket posts, GTM leadership, last discovery call).
- Explain why THIS product fits THIS person — not generic meta-commentary like "shows we understand their hobbies".
- Never infer religion, politics, health, family status, or ethnicity.

MESSAGE RULES (personalised_message):
- Write 2–3 sentences maximum, warm and professional.
- Open with something specific to THIS contact — their cricket passion, VP Sales role, or the discovery call.
- NEVER open with "Dear {name}, I wanted to thank you" or similar generic corporate openers.
- Mention one concrete signal from their profile naturally (a post topic, engaged topic, or business goal).
- Tie the gift to that signal so the note feels written by someone who actually knows them.
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
    # Extract outermost JSON object if model added prose
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        text = match.group(0)
    return json.loads(text)


def _fallback_rank(validated_products: list, contact: dict, signals: dict) -> list:
    """Deterministic ranking when LLM output fails."""
    name = contact["name"].split()[0]
    strong = signals.get("strong_signals", [])
    signal_hint = strong[0] if strong else "your professional interests"

    gifts = []
    for i, p in enumerate(validated_products[:3]):
        gifts.append({
            "rank": i + 1,
            "gift_name": p["title"],
            "product_url": p["url"],
            "store": p.get("store", ""),
            "estimated_price": p.get("price_raw", ""),
            "why_this_gift": f"Matches {signal_hint} and fits the stated budget.",
            "personalisation_reasoning": f"Selected from validated products based on: {', '.join(strong[:2]) or 'professional context'}.",
            "personalised_message": (
                f"Hi {name}, our conversation stuck with me — especially your take on "
                f"{signal_hint.lower()}. Hope this gift resonates. Looking forward to our next chat."
            ),
            "confidence_score": 0.55,
            "risk_level": "medium",
            "assumptions": ["Fallback ranking used because LLM parse failed"],
        })
    return gifts


def _format_reviewer_feedback(reviewer_feedback: str | None) -> str:
    if not reviewer_feedback or not reviewer_feedback.strip():
        return ""
    return f"""
REVIEWER FEEDBACK (address this in your next recommendations):
{reviewer_feedback.strip()}
"""


def rank_gifts(state: GraphState) -> GraphState:
    print(">> Step 5: Ranking gifts...")

    try:
        validated_products = state["validated_products"]

        if not validated_products:
            print("   No validated products to rank — skipping")
            state["errors"].append("ranking_error: no validated products available")
            state["recommended_gifts"] = []
            return state

        contact = state["contact"]
        signals = state["profile_signals"]
        gift_ctx = contact["gift_context"]
        rel_ctx = contact["relationship_context"]

        products_str = ""
        for i, p in enumerate(validated_products):
            budget_flag = "IN BUDGET" if p.get("is_price_in_budget") else "OUT OF BUDGET"
            products_str += f"""
Product {i + 1} [{budget_flag}]:
  Title: {p['title']}
  Store: {p['store']}
  Price: {p['price_raw']} (numeric: {p.get('price_numeric', 'unknown')})
  URL: {p['url']}
  Snippet: {p.get('snippet', '')}
"""

        llm = get_llm()
        prompt = ChatPromptTemplate.from_template(RANKING_PROMPT)
        chain = prompt | llm

        invoke_args = {
            "name": contact["name"],
            "role": contact["role"],
            "company": contact["company"],
            "occasion": gift_ctx["occasion"],
            "relationship_type": rel_ctx["relationship_type"],
            "last_interaction": rel_ctx.get("last_interaction", "Not specified"),
            "business_goal": rel_ctx.get("business_goal", ""),
            "currency": gift_ctx["currency"],
            "budget_min": gift_ctx["budget_min"],
            "budget_max": gift_ctx["budget_max"],
            "strong_signals": ", ".join(signals.get("strong_signals", [])),
            "weak_signals": ", ".join(signals.get("weak_signals", [])),
            "signals_to_avoid": ", ".join(signals.get("signals_to_avoid", [])),
            "products": products_str,
            "reviewer_feedback_section": _format_reviewer_feedback(
                state.get("reviewer_feedback")
            ),
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
        for g in gifts:
            print(f"   Rank {g['rank']}: {g['gift_name']} — confidence: {g['confidence_score']}")

    except Exception as e:
        print(f"   ERROR in ranking: {e}")
        state["errors"].append(f"ranking_error: {str(e)}")
        state["recommended_gifts"] = []

    return state
