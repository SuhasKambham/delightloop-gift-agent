# Evaluation Note

Companion to [README.md](../README.md). Submission artifact for DelightLoop assignment.

## Quality dimensions

### 1. Gift relevance (manual, 1–5)

**Question:** Does each gift clearly connect to visible profile signals?

- **Pass:** Personalised cricket bat for Aarav — cites cricket posts and match comment
- **Fail:** Generic book hamper with no tie to VP Sales / cricket / GTM signals

### 2. Budget fit (automated)

Validator: `(budget_min × 0.95) ≤ price ≤ budget_max`

**Metrics:** % validated in budget; % ranked gifts in budget  
**Target:** 100% of ranked gifts in range (or confidence ≤ 0.3 if not)

### 3. Product link validity

- Products sourced from SerpAPI (not LLM-generated)
- Fallback Amazon/Flipkart search URLs when direct links unavailable
- **Metric:** % URLs returning HTTP < 400 on HEAD request

### 4. Message quality (manual rubric)

| Criterion | Pass | Fail |
|-----------|------|------|
| Opener | References specific signal or interaction | "Dear X, I wanted to thank you..." |
| Length | 2–3 sentences | Generic paragraph |
| Tone | Matches relationship + occasion | Overly personal / creepy |
| Grounding | Cites profile data | Invents facts |

### 5. Guardrails (adversarial)

Profiles with religious/political/health hints → must not recommend based on those; must list in `signals_to_avoid`.

### 6. Failure handling

| Scenario | Expected |
|----------|----------|
| Search returns only cheap products | Retry with broader queries |
| Still < 3 valid products | Rank available; lower confidence |
| Reviewer rejects as "too generic" | Next run injects feedback; message changes |

## Production metrics

- Approval rate (% approved without regenerate)
- Regeneration rate
- Mean confidence score per run
- p95 end-to-end latency (target < 90s)
- Groq + SerpAPI cost per contact
- LangSmith mean human_review score over time

## Golden test cases

1. **Aarav Mehta** — cricket + SaaS VP, INR 3000–5000
2. **Sparse profile** — minimal LinkedIn → lower confidence, explicit assumptions
3. **Budget edge** — products at 2900 and 5100 → only 2900 passes validation

```bash
pytest tests/ -q
python test_schema.py
```

## Is the AI getting better?

| Mechanism | Improves output? |
|-----------|-----------------|
| LangSmith traces | No — observability only |
| Feedback memory | Yes — reject/approve notes persist per contact |
| Regenerate with notes | Yes — same-session improvement |
| Next step | LangSmith eval dataset + CI regression on golden contacts |
