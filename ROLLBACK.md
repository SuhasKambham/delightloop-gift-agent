# Rollback Guide

Git was initialized in this repo. To enable commits, configure your identity once:

```bash
git config user.email "you@example.com"
git config user.name "Your Name"
```

## Changes by fix (revert individually if needed)

### Fix 1 — Ranking prompt (`app/workflow/nodes/rank.py`)
- Budget-aware ranking with out-of-budget penalty (confidence ≤ 0.3)
- Specific message rules (no generic "Dear X, I wanted to thank you")
- Signal-grounded reasoning (no meta-commentary)
- JSON parse retry + deterministic fallback ranking

### Fix 2 — Conditional search retry (`app/workflow/graph.py`, `nodes/search.py`, `nodes/validate.py`, `services/search.py`)
- LangGraph conditional edge: if < 3 validated products, retry search (up to 2 retries)
- Alternate query strategies per retry attempt
- Product deduplication across retries

### Fix 3 — Reviewer feedback loop (`app/main.py`, `nodes/rank.py`, `nodes/signals.py`, `ui/review_app.py`)
- Regenerate passes reviewer notes into signal extraction and ranking prompts
- UI notes field wired to regenerate

### Fix 4 — LangSmith + validation (`app/services/llm.py`, `app/utils/validators.py`)
- LangSmith auto-enabled when `LANGCHAIN_API_KEY` is set
- Budget validation tightened from 80% to 95% of `budget_min`

## Quick test

```bash
# Terminal 1
uvicorn app.main:app --reload

# Terminal 2
python test_schema.py
pytest tests/test_feedback_memory.py -q

# curl (use single contact, not array)
curl -X POST http://127.0.0.1:8000/recommend -H "Content-Type: application/json" -d @sample_input/contact_single.json
```

## Fix 5 — Persistent learning memory (`app/services/feedback_memory.py`)

- Saves approve/reject/regenerate/edit notes to `data/feedback_memory.json`
- Future `/recommend` runs for the same contact inject past feedback into prompts
- LangSmith scores traces on approve (+1) / reject (0) via `app/services/tracing.py`
