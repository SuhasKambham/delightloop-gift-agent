# Architecture Note

Companion to [README.md](../README.md). Submission artifact for DelightLoop assignment.

## System context

The Gift Agent sits between **enriched contact data** (LinkedIn-style profiles) and **human reviewers** who approve gifts before sending. It is a **stateful, multi-step workflow** with deterministic guardrails — not a single LLM prompt.

## Component diagram

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

| Store | Scope | Persistence |
|-------|-------|-------------|
| `GraphState` | Single workflow run | In-memory during invoke |
| `results_store` | API run results by `run_id` | In-memory (lost on restart) |
| `feedback_memory.json` | Reviewer notes per contact | Disk (`data/`, gitignored) |

## Failure handling

| Failure | Response |
|---------|----------|
| SerpAPI error | Empty products; retry with alternate queries |
| < 3 validated products | Conditional loop back to search (max 2 retries) |
| LLM JSON parse error | Retry once; deterministic fallback ranking |
| No products at all | Empty recommendations + error in `errors[]` |
| Weak profile signals | Lower confidence; explicit assumptions listed |

## Extension points

- Swap `get_llm()` for OpenAI / Anthropic
- Replace SerpAPI with Amazon Product Advertising API
- Add LangGraph Postgres checkpointer for durable workflow state
- Webhook on approve → CRM integration
