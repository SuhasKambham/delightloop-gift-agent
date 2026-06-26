# Architecture Note

This prototype is a workflow-based gift recommendation system. It is split into small deterministic and AI-assisted steps so product grounding, validation, review, and feedback are visible.

## High-Level Flow

```text
Client / Streamlit UI
        |
        v
FastAPI API
        |
        v
LangGraph workflow
  ingest -> signals -> search -> validate -> rank -> review
        |         |        |          |
        |         |        |          v
        |         |        |   deterministic filters
        |         |        v
        |         |   SerpAPI Google Shopping
        |         v
        |   Groq LLM
        v
feedback memory and in-memory run store
```



## Main Components


| Component                  | File                                                        | Responsibility                                                                               |
| -------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| API layer                  | `app/main.py`                                               | Exposes `/recommend`, `/recommend/bulk`, `/review/{run_id}`, `/feedback`, and `/results`     |
| Workflow graph             | `app/workflow/graph.py`                                     | Defines node order and conditional retry routing                                             |
| Workflow state             | `app/workflow/state.py`                                     | Shared dictionary state passed through LangGraph                                             |
| Signal extraction          | `app/workflow/nodes/signals.py`                             | Uses Groq to extract strong, weak, and avoided signals                                       |
| Search planning and search | `app/services/search.py`, `app/workflow/nodes/search.py`    | Builds LLM search plans and fetches SerpAPI shopping results                                 |
| Validation                 | `app/utils/validators.py`, `app/workflow/nodes/validate.py` | Parses prices, checks budget, verifies URLs, blocks inappropriate gifts                      |
| Ranking                    | `app/workflow/nodes/rank.py`                                | Scores signal match, calls Groq for final ranking and messages, falls back deterministically |
| Human review               | `app/workflow/nodes/review.py`, `app/main.py`               | Marks runs as pending and handles approve/reject/edit/regenerate actions                     |
| Feedback memory            | `app/services/feedback_memory.py`                           | Persists reviewer notes per contact in `data/feedback_memory.json`                           |
| UI                         | `ui/review_app.py`                                          | Streamlit interface for generating, reviewing, and regenerating recommendations              |




## Workflow State

```json
{
    "contact": dict,
    "profile_signals": dict,
    "search_trace": dict,
    "raw_products": list,
    "validated_products": list,
    "recommended_gifts": list,
    "human_review": dict,
    "errors": list,
    "current_step": str,
    "search_retry_count": int,
    "reviewer_feedback": str
}
```



## Retry Logic

After validation, the graph checks whether at least three products passed the hard filters. If not, it routes back to `search_products` while `search_retry_count` is below `MAX_SEARCH_RETRIES`.

Current constants:

```python
MAX_SEARCH_RETRIES = 3
MIN_VALIDATED_PRODUCTS = 3
```

This allows up to three search attempts total: the initial search plus retries.

## AI vs Deterministic Logic


| AI-assisted                         | Deterministic                   |
| ----------------------------------- | ------------------------------- |
| Signal extraction from profile text | Workflow routing                |
| Search-plan generation              | Product deduplication           |
| Final ranking and message writing   | Price parsing and budget checks |
| Interpreting reviewer feedback      | Appropriateness keyword filter  |
|                                     | Feedback persistence            |
|                                     | In-memory result storage        |


The LLM is used where language understanding and personalized writing matter. Python code is used where predictable rules matter.

## Persistence


| Store            | Location                        | Scope                  | Notes                                        |
| ---------------- | ------------------------------- | ---------------------- | -------------------------------------------- |
| results_store    | Process memory in `app/main.py` | Current server process | Lost on restart                              |
| Feedback memory  | `data/feedback_memory.json`     | Local runtime file     | Gitignored                                   |
| LangSmith traces | LangSmith cloud                 | Optional observability | Enabled only when `LANGCHAIN_API_KEY` exists |




## Failure Handling


| Failure                  | Current behavior                                       |
| ------------------------ | ------------------------------------------------------ |
| Signal extraction fails  | Adds an error and uses fallback generic signals        |
| Search planning fails    | Falls back to simple signal-based queries              |
| SerpAPI request fails    | Returns no products for that query and continues       |
| Too few valid products   | Retries search until retry limit                       |
| No valid products        | Returns empty recommendations and records an error     |
| Ranking JSON parse fails | Retries once, then uses deterministic fallback ranking |
| LangSmith feedback fails | Logs and continues without blocking review             |




## Deployment Shape

The current Streamlit app points to:

```python
API_URL = "https://delightloop-gift-agent.onrender.com"
```

For local development, set it to:

```python
API_URL = "http://127.0.0.1:8000"
```

Productionizing this would require durable storage, authentication, stricter CORS, request validation, and a configurable API URL.