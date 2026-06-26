# Change And Rollback Notes

This repository is Git-backed. Before pushing, confirm no secrets or runtime data are staged:

```bash
git status
```

Do not commit:

- `.env`
- `venv/`
- `__pycache__/`
- `.pytest_cache/`
- `data/feedback_memory.json`

## Current Prototype Capabilities


| Area               | Files                                                       | Notes                                                                       |
| ------------------ | ----------------------------------------------------------- | --------------------------------------------------------------------------- |
| FastAPI routes     | `app/main.py`                                               | Single contact, bulk contact, review, feedback, and result lookup endpoints |
| LangGraph workflow | `app/workflow/graph.py`                                     | Six-node workflow with conditional search retry                             |
| Signal extraction  | `app/workflow/nodes/signals.py`                             | Groq LLM extracts strong, weak, and avoided signals                         |
| Search planning    | `app/services/search.py`                                    | Groq LLM creates search plans; fallback query planner exists                |
| Product search     | `app/workflow/nodes/search.py`                              | SerpAPI Google Shopping search with deduplication                           |
| Validation         | `app/workflow/nodes/validate.py`, `app/utils/validators.py` | Price, URL, and professional appropriateness checks                         |
| Ranking            | `app/workflow/nodes/rank.py`                                | Signal scoring plus LLM ranking; deterministic fallback on parse failure    |
| Review loop        | `app/workflow/nodes/review.py`, `app/main.py`               | Approve, reject, edit, and regenerate actions                               |
| Learning memory    | `app/services/feedback_memory.py`                           | Persists reviewer feedback per contact                                      |
| UI                 | `ui/review_app.py`                                          | Streamlit review app currently targeting the Render API                     |
| Tests              | `tests/test_feedback_memory.py`                             | Unit tests for persistent feedback behavior                                 |




## Rollback Strategy

Use Git to inspect and selectively revert changes if needed:

```bash
git diff
git restore path/to/file
```

Avoid broad resets unless you intentionally want to discard all local work.

## Quick Verification

Run the no-key tests:

```bash
pytest tests/ -q
```

Run the full workflow after adding `GROQ_API_KEY` and `SERPAPI_KEY`:

```bash
python test_schema.py
```

Run the API locally:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run the UI locally:

```bash
streamlit run ui/review_app.py
```

For local UI testing, set `API_URL` in `ui/review_app.py` to `http://127.0.0.1:8000`.