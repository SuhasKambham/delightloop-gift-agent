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

    # If reviewer gave specific product feedback, search for that first
    feedback_queries = _feedback_queries(reviewer_feedback, budget_min, budget_max)

    if retry_attempt == 0:
        base = _primary_queries(strong, weak, budget_min, budget_max)
    elif retry_attempt == 1:
        base = _broader_queries(strong, weak, budget_min, budget_max)
    else:
        base = _aggressive_queries(strong, budget_min, budget_max)

    # Feedback queries go first, then fill remaining slots with base queries
    combined = feedback_queries + [q for q in base if q not in feedback_queries]
    return combined[:4]


def _feedback_queries(reviewer_feedback: str, budget_min: float, budget_max: float) -> list:
    """
    Use LLM to extract specific search queries from reviewer feedback.
    Dynamic — works for any product type the reviewer mentions.
    """
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
