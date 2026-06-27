import json
import time

import requests
import streamlit as st

API_URL = "https://delightloop-gift-agent.onrender.com"


def wake_backend():
    """Ping backend and wait for it to wake up if Render spun it down."""
    max_attempts = 6

    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{API_URL}/", timeout=15)
            if response.status_code == 200:
                return True
        except Exception:
            pass

        if attempt < max_attempts - 1:
            time.sleep(8)

    return False


st.set_page_config(
    page_title="DelightLoop Gift Agent",
    page_icon="🎁",
    layout="wide",
)

st.title("🎁 DelightLoop - Gift Recommendation Agent")
st.markdown("AI-powered personalised gift recommendations with human review")

st.sidebar.header("Contact Input")

input_method = st.sidebar.radio(
    "Input method",
    ["Use sample contact", "Paste JSON"],
)

sample_contact = {
    "name": "Aarav Mehta",
    "role": "VP Sales",
    "company": "Acme Corp",
    "location": "Bengaluru, India",
    "linkedin_profile": {
        "headline": "VP Sales at Acme Corp | Enterprise SaaS | GTM Leadership",
        "about": "I enjoy building high-performing revenue teams and scaling SaaS businesses.",
        "experience": [
            {
                "title": "VP Sales",
                "company": "Acme Corp",
                "description": "Leading enterprise sales and GTM expansion.",
            }
        ],
        "recent_posts": [
            "Great sales teams are built on trust, coaching, and consistency.",
            "Still recovering from yesterday's India vs Australia match. What a game!",
        ],
        "recent_comments": [
            "Cricket teaches leadership better than most management books."
        ],
        "engaged_topics": ["Cricket", "Revenue leadership", "SaaS GTM"],
    },
    "relationship_context": {
        "relationship_type": "Prospective customer",
        "last_interaction": "Positive discovery call last week",
        "business_goal": "Nurture relationship before follow-up meeting",
    },
    "gift_context": {
        "occasion": "Post-meeting thank you",
        "budget_min": 3000,
        "budget_max": 5000,
        "currency": "INR",
        "country": "India",
    },
}

if input_method == "Use sample contact":
    contact_data = sample_contact
    st.sidebar.success("Sample contact loaded")
else:
    raw = st.sidebar.text_area(
        "Paste contact JSON here",
        height=300,
    )
    try:
        contact_data = json.loads(raw) if raw else None
    except Exception:
        st.sidebar.error("Invalid JSON")
        contact_data = None

if contact_data:
    st.markdown(
        f"### Contact: **{contact_data['name']}** - "
        f"{contact_data['role']} at {contact_data['company']}"
    )

    if st.button("Generate Gift Recommendations", type="primary"):
        with st.spinner(
            "Waking up backend... this may take 30-60 seconds on Render free tier"
        ):
            backend_ready = wake_backend()

        if not backend_ready:
            st.warning("Backend is still waking up. Please try again in a few seconds.")
        else:
            with st.spinner("Running AI workflow... this takes around 30-90 seconds"):
                try:
                    response = requests.post(
                        f"{API_URL}/recommend",
                        json=contact_data,
                        timeout=180,
                    )

                    if response.status_code != 200:
                        st.error(
                            f"Backend error {response.status_code}: "
                            f"{response.text[:500]}"
                        )
                    else:
                        result = response.json()
                        st.session_state["result"] = result
                        st.session_state["run_id"] = result["run_id"]

                except Exception as e:
                    st.error(f"Error: {e}")

if "result" in st.session_state:
    result = st.session_state["result"]
    run_id = st.session_state["run_id"]

    st.divider()

    st.subheader("Profile Signals Extracted")
    signals = result.get("profile_signals", {})
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Strong Signals**")
        for signal in signals.get("strong_signals", []):
            st.markdown(f"- {signal}")

    with col2:
        st.markdown("**Weak Signals**")
        for signal in signals.get("weak_signals", []):
            st.markdown(f"- {signal}")

    with col3:
        st.markdown("**Signals to Avoid**")
        for signal in signals.get("signals_to_avoid", []):
            st.markdown(f"- {signal}")

    st.divider()

    learning = result.get("learning_context", {})
    if learning.get("historical_feedback_applied"):
        st.info(
            f"Learning memory active - {learning['feedback_entries_count']} "
            f"past review(s) for this contact are shaping this run"
            + (
                f" (last: {learning.get('last_action')})"
                if learning.get("last_action")
                else ""
            )
        )

    st.subheader("Search Trace")
    search_trace = result.get("search_trace", {})
    st.markdown(
        f"**Products considered:** "
        f"{search_trace.get('products_considered_count', 0)}"
    )
    st.markdown("**Queries used:**")
    for query in search_trace.get("queries_used", []):
        st.markdown(f"- `{query}`")

    st.divider()

    st.subheader("Top 3 Gift Recommendations")

    if not result.get("recommended_gifts"):
        st.warning("No gift recommendations generated. Check errors below.")
    else:
        for gift in result["recommended_gifts"]:
            rank = gift["rank"]
            medal = ["1", "2", "3"][rank - 1] if rank in [1, 2, 3] else str(rank)

            with st.expander(
                f"Rank #{medal}: {gift['gift_name']} - {gift['estimated_price']}",
                expanded=True,
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"**Store:** {gift['store']}")
                    st.markdown(f"**Price:** {gift['estimated_price']}")
                    st.markdown(
                        f"**Confidence:** {int(gift['confidence_score'] * 100)}%"
                    )
                    st.markdown(f"**Risk:** {gift['risk_level']}")
                    st.markdown(f"**URL:** [View Product]({gift['product_url']})")

                with col2:
                    st.markdown("**Why this gift:**")
                    st.info(gift["why_this_gift"])

                st.markdown("**Personalised Message:**")
                st.success(gift["personalised_message"])

                st.markdown("**Reasoning:**")
                st.caption(gift["personalisation_reasoning"])

                if gift.get("assumptions"):
                    st.markdown("**Assumptions:**")
                    for assumption in gift["assumptions"]:
                        st.caption(f"- {assumption}")

    st.divider()

    st.subheader("Human Review")

    current_status = result["human_review"]["status"]
    st.markdown(f"**Current Status:** `{current_status}`")

    if current_status == "pending_review":
        notes = st.text_input(
            "Reviewer notes (used on regenerate to improve suggestions)",
            key="reviewer_notes",
            value=result["human_review"].get("reviewer_notes") or "",
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("Approve", type="primary"):
                try:
                    response = requests.post(
                        f"{API_URL}/review/{run_id}?action=approve",
                        params={"notes": notes} if notes else {},
                        timeout=60,
                    )
                    if response.status_code != 200:
                        st.error(
                            f"Backend error {response.status_code}: "
                            f"{response.text[:500]}"
                        )
                    else:
                        st.session_state["result"]["human_review"][
                            "status"
                        ] = "approved"
                        st.success("Recommendations approved!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        with col2:
            if st.button("Reject"):
                try:
                    response = requests.post(
                        f"{API_URL}/review/{run_id}?action=reject",
                        params={"notes": notes} if notes else {},
                        timeout=60,
                    )
                    if response.status_code != 200:
                        st.error(
                            f"Backend error {response.status_code}: "
                            f"{response.text[:500]}"
                        )
                    else:
                        st.session_state["result"]["human_review"][
                            "status"
                        ] = "rejected"
                        st.error("Recommendations rejected")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        with col3:
            if st.button("Regenerate"):
                if not notes:
                    st.warning(
                        "Add notes above to guide regeneration, otherwise results "
                        "may be similar."
                    )
                else:
                    with st.spinner("Regenerating with your feedback..."):
                        try:
                            response = requests.post(
                                f"{API_URL}/review/{run_id}?action=regenerate",
                                params={"notes": notes},
                                timeout=180,
                            )
                            if response.status_code != 200:
                                st.error(
                                    f"Backend error {response.status_code}: "
                                    f"{response.text[:500]}"
                                )
                            else:
                                new_result = response.json()
                                st.session_state["result"] = new_result
                                st.session_state["run_id"] = new_result.get(
                                    "run_id", run_id
                                )
                                st.success("Regenerated with feedback!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

        with col4:
            if st.button("Save Notes") and notes:
                try:
                    response = requests.post(
                        f"{API_URL}/review/{run_id}?action=edit",
                        params={"notes": notes},
                        timeout=60,
                    )
                    if response.status_code != 200:
                        st.error(
                            f"Backend error {response.status_code}: "
                            f"{response.text[:500]}"
                        )
                    else:
                        st.session_state["result"]["human_review"][
                            "reviewer_notes"
                        ] = notes
                        st.success("Notes saved!")
                except Exception as e:
                    st.error(f"Error: {e}")

    elif current_status == "approved":
        st.success("These recommendations have been approved")

    elif current_status == "rejected":
        st.error("These recommendations were rejected")

    if result.get("errors"):
        with st.expander("Errors"):
            for error in result["errors"]:
                st.error(error)

    with st.expander("View Raw JSON Output"):
        st.json(result)
