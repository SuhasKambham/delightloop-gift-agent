# DelightLoop Gift Recommendation Agent

AI-powered corporate gifting workflow for the DelightLoop founding engineering assignment.

The app turns enriched LinkedIn-style contact data into grounded, reviewable gift recommendations. It uses a FastAPI backend, a LangGraph workflow, Groq-hosted LLM calls, SerpAPI Google Shopping search, persistent reviewer feedback memory, and a Streamlit review UI.

## Submission Contents

- GitHub repository: this project folder
- README with setup and usage instructions: this file
- Sample input and output: `sample_input/`, `sample_output/`
- Short architecture note: `docs/ARCHITECTURE.md`
- Evaluation, tradeoffs, and future improvements: `docs/EVALUATION.md`
- Demo video or screenshots: to be added manually after final testing



## What The Prototype Does

1. Accepts a professional contact profile with relationship and gift context.
2. Extracts safe gift-relevant signals from posts, comments, topics, and experience.
3. Builds product search plans from those signals.
4. Searches real Google Shopping results through SerpAPI.
5. Validates products for budget, professional appropriateness, and URL availability.
6. Ranks the top gifts and writes personalized messages.
7. Pauses for human review: approve, reject, edit notes, or regenerate.
8. Saves reviewer feedback so future runs for the same contact can improve.



## Tech Stack


| Layer          | Technology                                     |
| -------------- | ---------------------------------------------- |
| Backend API    | FastAPI, Uvicorn                               |
| Workflow       | LangGraph                                      |
| LLM            | Groq via LangChain (`llama-3.3-70b-versatile`) |
| Product search | SerpAPI Google Shopping                        |
| UI             | Streamlit                                      |
| Persistence    | In-memory run store plus JSON feedback memory  |
| Observability  | Optional LangSmith tracing                     |
| Tests          | pytest                                         |




## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```bash
GROQ_API_KEY=your_groq_api_key_here
SERPAPI_KEY=your_serpapi_key_here

# Optional LangSmith tracing
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=delightloop-gift-agent
```

Do not commit `.env`. It is already listed in `.gitignore`.

## Local Setup

```bash
git clone https://github.com/YOUR_USERNAME/delightloop-gift-agent.git
cd delightloop-gift-agent

python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

Create `.env`:

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Run the backend:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful URLs(local):

- Health check: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Useful URLs(live):

- Health check: [https://delightloop-gift-agent.onrender.com](https://delightloop-gift-agent.onrender.com)
- API docs: [https://delightloop-gift-agent.onrender.com/docs](https://delightloop-gift-agent.onrender.com/docs)
  
Run the Streamlit UI:

```bash
streamlit run ui/review_app.py
```

The current UI points to the deployed Render API:

```python
API_URL = "[https://delightloop-gift-agent.onrender.com](https://delightloop-gift-agent-1.onrender.com)"
```

For local UI testing, change it in `ui/review_app.py` to:

```python
API_URL = "http://127.0.0.1:8000"
```



## API Usage

Single contact:

```bash
curl -X POST http://127.0.0.1:8000/recommend ^
  -H "Content-Type: application/json" ^
  -d @sample_input/contact_single.json
```

Bulk contacts:

```bash
curl -X POST http://127.0.0.1:8000/recommend/bulk ^
  -H "Content-Type: application/json" ^
  -d @sample_input/contacts.json
```

Review or regenerate:

```bash
curl -X POST "http://127.0.0.1:8000/review/RUN_ID?action=regenerate&notes=suggest%20gifts%20related%20to%20coffee"
```

Supported review actions:

- `approve`
- `reject`
- `edit`
- `regenerate`

Inspect feedback memory:

```bash
curl "http://127.0.0.1:8000/feedback?name=Aarav%20Mehta&company=Acme%20Corp"
```



## Main Response Shape

```json
{
  "run_id": "uuid",
  "contact_name": "Aarav Mehta",
  "profile_signals": {
    "strong_signals": [],
    "weak_signals": [],
    "signals_to_avoid": []
  },
  "search_trace": {
    "queries_used": [],
    "products_considered_count": 0,
    "search_retries": 0
  },
  "recommended_gifts": [
    {
      "rank": 1,
      "gift_name": "Product name",
      "product_url": "https://...",
      "store": "Store name",
      "estimated_price": "INR price",
      "why_this_gift": "Why it fits",
      "personalisation_reasoning": "Signals used",
      "personalised_message": "Short professional message",
      "confidence_score": 0.85,
      "risk_level": "low",
      "assumptions": []
    }
  ],
  "human_review": {
    "status": "pending_review",
    "available_actions": ["approve", "reject", "edit", "regenerate"],
    "reviewer_notes": null
  },
  "learning_context": {
    "historical_feedback_applied": false,
    "feedback_entries_count": 0
  },
  "errors": []
}
```



## Architecture Summary

The backend runs this LangGraph workflow:

```
ingest_contact
  -> extract_signals
  -> search_products
  -> validate_products
  -> rank_gifts
  -> human_review
```

If fewer than three products pass validation, the graph loops from `validate_products` back to `search_products` for up to three total search attempts. The search node uses the LLM to create a search plan, then SerpAPI to fetch real Google Shopping results. The ranking node receives validated products and produces the final recommendation JSON.

See `docs/ARCHITECTURE.md` for the full architecture note.

## Human Review And Learning

Each recommendation run ends in `pending_review`. A reviewer can approve, reject, save notes, or regenerate.

Reviewer notes are persisted in:

```
data/feedback_memory.json
```

That file is ignored by Git because it is runtime data. For future runs with the same name + company, recent feedback is injected into signal extraction and ranking prompts.

## Testing

Unit tests that do not require external API keys:

```bash
pytest tests/ -q
```

End-to-end workflow smoke test that requires `GROQ_API_KEY` and `SERPAPI_KEY`:

```bash
python test_schema.py
```

Manual testing checklist:

1. Start the backend.
2. Send `sample_input/contact_single.json` to `/recommend`.
3. Confirm `profile_signals`, `search_trace`, `recommended_gifts`, and `human_review` are present.
4. Use `/review/{run_id}?action=regenerate&notes=...`.
5. Confirm `learning_context.historical_feedback_applied` becomes `true` after feedback exists for the contact.



## Tradeoffs


| Decision                  | Benefit                                   | Limitation                                      |
| ------------------------- | ----------------------------------------- | ----------------------------------------------- |
| Groq LLM                  | Fast and simple for assignment use        | External dependency and rate limits             |
| SerpAPI Google Shopping   | Real product grounding                    | Search results can be noisy or change over time |
| LLM search planning       | More adaptive than static query templates | Adds latency and LLM variability                |
| JSON file feedback memory | Easy to inspect and demo                  | Not safe for concurrent production writes       |
| In-memory result store    | Simple run lookup by run_id               | Results disappear after server restart          |
| Streamlit UI              | Quick review interface                    | Not a production-grade frontend                 |
| Permissive CORS           | Easy demo/deployment setup                | Should be restricted in production              |




## Future Improvements

- Replace in-memory run storage with Postgres or another durable store.
- Add authenticated reviewer accounts and stricter CORS.
- Use LangGraph checkpointing for resumable runs.
- Add structured Pydantic request models to FastAPI routes.
- Add product-source adapters for Amazon Product Advertising API or other commerce APIs.
- Improve price normalization for ranges, discounts, and non-INR currencies.
- Add CI tests for validators, graph routing, API contracts, and fallback ranking.
- Add LangSmith evaluation datasets for regression testing.
- Make the Streamlit API URL configurable through environment variables.
- Add inline editing of gift recommendations in the review UI.



## Submission Notes

- The app is already deployed on Render. Add the live backend/UI links before sending the final submission.
- Add demo screenshots or a short walkthrough video after manual testing.
- Keep `.env`, `venv/`, `__pycache__/`, and `data/feedback_memory.json` out of Git.
- Use `sample_input/contact_single.json` and `sample_output/aarav_mehta.json` as reference artifacts.

