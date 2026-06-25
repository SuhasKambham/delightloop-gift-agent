# Architecture Note

Companion to [README.md](../README.md). Submission artifact for DelightLoop assignment.

## System context

The Gift Agent sits between **enriched contact data** (LinkedIn-style profiles) and **human reviewers** who approve gifts before sending. It is not a chatbot — it is a **stateful, multi-step workflow** with deterministic guardrails.

## Component responsibilities

```
┌─────────────────────────────────────────────────────────┐
│                     FastAPI Layer                        │
│  HTTP · run_id · review actions · feedback persistence   │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                   LangGraph Workflow                     │
│  ingest → signals → search → validate ⇄ retry → rank    │
└─────┬───────────────────┬───────────────────┬───────────┘
      │ LLM               │ Tool              │ LLM
      ▼                   ▼                   ▼
   Groq              SerpAPI              Groq
```

## State management

- **Workflow state:** `GraphState` TypedDict passed between LangGraph nodes
- **Session state:** in-memory `results_store` keyed by `run_id` (API layer)
- **Persistent learning:** `data/feedback_memory.json` keyed by contact name + company

## Failure handling

| Failure | Response |
|---------|----------|
| SerpAPI error | Empty products; retry with alternate queries |
| < 3 validated products | Conditional loop to search (max 2 retries) |
| LLM JSON parse error | Retry once; fallback deterministic ranking |
| No products at all | Empty recommendations + error in `errors[]` |
| Weak profile signals | Lower confidence scores; assumptions listed |

## Extension points

- Swap `get_llm()` for OpenAI/Anthropic
- Replace SerpAPI with Amazon Product API
- Add Postgres checkpointing via LangGraph checkpointer
- Add approval webhook to CRM
