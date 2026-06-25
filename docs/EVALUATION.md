# Evaluation Note

Companion to [README.md](../README.md). Submission artifact for DelightLoop assignment.

## Quality dimensions

### 1. Gift relevance (manual, 1–5)

**Question:** Does each gift clearly connect to visible profile signals?

**Example pass (Aarav Mehta):** Personalised cricket bat → cites cricket posts and India vs Australia match.

**Example fail:** Generic book hamper with no tie to VP Sales / cricket / GTM signals.

### 2. Budget fit (automated)

Validator enforces `(budget_min × 0.95) ≤ price ≤ budget_max`.

**Metric:** `% of validated products in budget` and `% of final ranked gifts in budget`.

**Target:** 100% of ranked gifts should be in budget; if not, confidence must be ≤ 0.3.

### 3. Product link validity

- SerpAPI returns real shopping results (not LLM-generated URLs)
- Fallback: Amazon/Flipkart search URLs when direct links unavailable
- **Metric:** `% URLs returning HTTP < 400` on HEAD request

### 4. Message quality (manual rubric)

| Criterion | Pass | Fail |
|-----------|------|------|
| Opener | References specific signal or interaction | "Dear X, I wanted to thank you..." |
| Length | 2–3 sentences | Generic paragraph |
| Tone | Matches relationship + occasion | Overly personal / creepy |
| Grounding | Cites profile data | Invents facts |

### 5. Guardrails (adversarial)

Test profiles with religious/political/health hints → system must not recommend based on those attributes and must list them in `signals_to_avoid`.

### 6. Failure handling

| Scenario | Expected behaviour |
|----------|-------------------|
| SerpAPI returns only cheap products | Search retry with broader queries |
| Still < 3 products | Rank available with lower confidence |
| LLM returns invalid JSON | Parse retry → fallback ranking |
| Reviewer rejects as "too generic" | Next run injects feedback; message should change |

## Metrics to track in production

- **Approval rate** — % of runs approved without regenerate
- **Regeneration rate** — % requiring second pass
- **Edit rate** — reviewer notes frequency
- **Latency** — p50/p95 end-to-end (target: < 90s)
- **Cost** — Groq + SerpAPI calls per contact
- **LangSmith scores** — mean human_review feedback score over time

## Golden test cases

1. **Aarav Mehta** — cricket + SaaS VP, INR 3000–5000 → cricket or executive gifts
2. **Sparse profile** — minimal LinkedIn data → lower confidence, explicit assumptions
3. **Budget edge** — only products at 2900 and 5100 → 2900 passes, 5100 filtered

Run: `python test_schema.py` and `pytest tests/ -q`

## Is the AI getting better?

**Tracing alone:** No — LangSmith records runs.

**Feedback memory:** Yes — reject/approve notes persist and inject into future prompts for the same contact.

**Next step for measurable improvement:** LangSmith dataset with scored examples + CI check that golden contacts maintain minimum relevance score.
