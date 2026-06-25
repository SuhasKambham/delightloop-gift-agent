import json
from app.workflow.graph import gift_agent

with open("sample_input/contacts.json", "r") as f:
    contacts = json.load(f)

contact = contacts[0]

test_state = {
    "contact": contact,
    "profile_signals": {},
    "search_trace": {"queries_used": [], "products_considered_count": 0},
    "raw_products": [],
    "validated_products": [],
    "recommended_gifts": [],
    "human_review": {},
    "errors": [],
    "current_step": "not_started",
    "search_retry_count": 0,
    "reviewer_feedback": "",
}

result = gift_agent.invoke(test_state)

print("\n========= SIGNAL EXTRACTION =========")
print(json.dumps(result["profile_signals"], indent=2))

print("\n========= SEARCH TRACE =========")
print(json.dumps(result["search_trace"], indent=2))

print("\n========= FINAL GIFT RECOMMENDATIONS =========")
for gift in result["recommended_gifts"]:
    print(f"""
Rank #{gift['rank']}: {gift['gift_name']}
  Store     : {gift['store']}
  Price     : {gift['estimated_price']}
  URL       : {gift['product_url']}
  Why       : {gift['why_this_gift']}
  Reasoning : {gift['personalisation_reasoning']}
  Message   : {gift['personalised_message']}
  Confidence: {gift['confidence_score']}
  Risk      : {gift['risk_level']}
  Assumptions: {gift['assumptions']}
""")

print("\n========= HUMAN REVIEW STATUS =========")
print(json.dumps(result["human_review"], indent=2))

print(f"\nErrors: {result['errors']}")