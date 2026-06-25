from app.workflow.state import GraphState
from app.services.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import json


SIGNAL_EXTRACTION_PROMPT = """
You are an expert at analysing professional profiles to extract gifting signals.

Given the following LinkedIn profile data, extract signals that can help recommend
a thoughtful, professional gift.

PROFILE:
Name: {name}
Role: {role}
Company: {company}
Location: {location}
Headline: {headline}
About: {about}
Recent Posts: {recent_posts}
Recent Comments: {recent_comments}
Engaged Topics: {engaged_topics}
Experience: {experience}

Occasion: {occasion}
Budget: {currency} {budget_min} - {budget_max}
Country: {country}
Relationship: {relationship_type}
Business Goal: {business_goal}
{reviewer_feedback_section}

Extract gifting signals and return ONLY a valid JSON object in this exact format:
{{
    "strong_signals": ["signal 1", "signal 2"],
    "weak_signals": ["signal 1", "signal 2"],
    "signals_to_avoid": ["always include: Do not infer religion, politics, health, family status, or ethnicity"]
}}

RULES:
- Strong signals: clearly visible interests from posts, comments, topics
- Weak signals: possible interests that are less certain
- Always add sensitive attribute warnings to signals_to_avoid
- Never infer religion, politics, health, family status, ethnicity, or gender
- Keep signals professional and gift-relevant
- Return ONLY the JSON, no extra text
"""


def _format_reviewer_feedback(reviewer_feedback: str | None) -> str:
    if not reviewer_feedback or not reviewer_feedback.strip():
        return ""
    return f"\nReviewer feedback to incorporate: {reviewer_feedback.strip()}"


def extract_signals(state: GraphState) -> GraphState:
    print(">> Step 2: Extracting profile signals...")

    try:
        contact = state["contact"]
        profile = contact["linkedin_profile"]
        gift_ctx = contact["gift_context"]
        rel_ctx = contact["relationship_context"]

        # Format experience as readable string
        experience_str = ", ".join([
            f"{e['title']} at {e['company']}"
            for e in profile.get("experience", [])
        ])

        llm = get_llm()

        prompt = ChatPromptTemplate.from_template(SIGNAL_EXTRACTION_PROMPT)

        chain = prompt | llm

        response = chain.invoke({
            "name": contact["name"],
            "role": contact["role"],
            "company": contact["company"],
            "location": contact["location"],
            "headline": profile.get("headline", ""),
            "about": profile.get("about", ""),
            "recent_posts": ", ".join(profile.get("recent_posts", [])),
            "recent_comments": ", ".join(profile.get("recent_comments", [])),
            "engaged_topics": ", ".join(profile.get("engaged_topics", [])),
            "experience": experience_str,
            "occasion": gift_ctx["occasion"],
            "currency": gift_ctx["currency"],
            "budget_min": gift_ctx["budget_min"],
            "budget_max": gift_ctx["budget_max"],
            "country": gift_ctx["country"],
            "relationship_type": rel_ctx["relationship_type"],
            "business_goal": rel_ctx.get("business_goal", ""),
            "reviewer_feedback_section": _format_reviewer_feedback(
                state.get("reviewer_feedback")
            ),
        })

        # Parse the JSON response
        raw = response.content.strip()

        # Clean markdown code blocks if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        signals = json.loads(raw)

        state["profile_signals"] = signals
        state["current_step"] = "extract_signals"

        print(f"   Strong signals: {signals['strong_signals']}")
        print(f"   Weak signals: {signals['weak_signals']}")

    except Exception as e:
        print(f"   ERROR in signal extraction: {e}")
        state["errors"].append(f"signal_extraction_error: {str(e)}")
        # Fallback signals
        state["profile_signals"] = {
            "strong_signals": ["Professional in their field"],
            "weak_signals": ["May appreciate general business gifts"],
            "signals_to_avoid": [
                "Do not infer religion, politics, health, family status, or ethnicity"
            ]
        }

    return state