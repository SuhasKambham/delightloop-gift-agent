# Evaluation, Tradeoffs, And Future Improvements

This note describes how to judge the prototype and what should be improved before a production launch.

## Quality Rubric


| Dimension                    | What to check                                                        | Target                                                                                  |
| ---------------------------- | -------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Relevance                    | Gifts clearly map to visible profile signals                         | At least 2 of 3 recommendations should cite strong or weak signals                      |
| Product grounding            | Product URLs come from SerpAPI results or safe search fallbacks      | No LLM-invented product URLs                                                            |
| Budget fit                   | Ranked gifts should be within or near the requested budget           | Out-of-budget items should be avoided or assigned low confidence                        |
| Professional appropriateness | No alcohol, adult, political, religious, medical, or sensitive gifts | 100% pass for professional contexts                                                     |
| Message quality              | Message is specific, warm, and tied to the occasion                  | No generic template opening                                                             |
| Guardrails                   | Sensitive traits are not inferred                                    | Religion, politics, health, family status, ethnicity, and gender should not drive gifts |
| Reviewability                | Reviewer can understand why each gift was suggested                  | Signals, search trace, assumptions, and confidence are visible                          |
| Learning loop                | Reviewer notes change future recommendations                         | Regeneration should reflect notes such as "focus on coffee"                             |




## Suggested Manual Test Cases

1. **Strong interests:** A profile with clear hobbies such as coffee, running, or mechanical keyboards.
2. **Sparse profile:** Minimal posts and topics. Expected result: lower confidence and explicit assumptions.
3. **Budget edge:** Products around the minimum and maximum budget. Expected result: invalid prices are filtered or scored down.
4. **Sensitive data:** A profile that mentions religion, politics, health, or family. Expected result: those signals are avoided.
5. **Reviewer regeneration:** Reject or regenerate with notes like "suggest gifts related to coffee." Expected result: recommendations and messages shift toward that note.



## Automated Tests

Fast tests without API keys:

```bash
pytest tests/ -q
```

Full workflow smoke test with Groq and SerpAPI keys:

```bash
python test_schema.py
```



## Current Tradeoffs


| Tradeoff                       | Why it was chosen                                                | Limitation                                                           |
| ------------------------------ | ---------------------------------------------------------------- | -------------------------------------------------------------------- |
| LLM-based search planning      | Adapts queries to the contact rather than using static templates | More latency and variable outputs                                    |
| SerpAPI Google Shopping        | Fastest way to ground gifts in real products                     | Product availability, price, and relevance can vary by search result |
| JSON feedback memory           | Easy to demo and inspect                                         | Not suitable for high concurrency                                    |
| In-memory run store            | Simple review flow for assignment prototype                      | Run history disappears on restart                                    |
| Streamlit UI                   | Quick human-review surface                                       | Limited styling and production UX                                    |
| Permissive CORS                | Keeps deployed UI/API integration simple                         | Should be locked down for production                                 |
| Keyword appropriateness filter | Simple and transparent                                           | Misses nuanced unsafe products and can over-block benign titles      |




## Future Improvements

- Add Pydantic request and response models directly to FastAPI route signatures.
- Store runs, contacts, products, and feedback in Postgres.
- Use LangGraph checkpointing for resumable workflows.
- Make the Streamlit API URL configurable from environment variables.
- Add authentication and reviewer identity.
- Add inline editing for gift title, URL, reasoning, and message.
- Improve product validation with richer price parsing, currency conversion, and merchant allowlists.
- Add a stronger safety classifier for sensitive or inappropriate gift categories.
- Add CI with unit tests for validators, graph retry routing, fallback ranking, and API contracts.
- Build a LangSmith evaluation dataset from golden contacts and reviewer outcomes.
- Add analytics for approval rate, regeneration rate, latency, and cost per recommendation.

