# Model notes — NVIDIA Nemotron

Measured against `https://integrate.api.nvidia.com/v1`. None of this is on the model cards, and each item cost a live call to establish. The client in `api/app/llm.py` is shaped by all of it.

## Model choice

`nvidia/nemotron-3-super-120b-a12b` is the default. Measured on the same span-extraction prompt:

| Model | Latency/page | Note |
| --- | --- | --- |
| `nemotron-3-super-120b-a12b` | **~7–10s** | The default |
| `nemotron-3-nano-30b-a3b` | ~18s | Slower *despite* being smaller — far more verbose (2297 vs 298 output tokens on the same task) |
| `nemotron-3-ultra-550b-a55b` | ~59s | Unusable per-page — a 200-page bundle would take ~3 hours even at concurrency 4 |

The intuition that the smaller model is the faster one is wrong here. Verbosity dominates parameter count at this scale.

## Structured output: `response_format`, never `nvext`

**`nvext.guided_json` does not work on the nemotron-3 family.** Nano and ultra silently ignore the schema and return JSON in their own invented shape; super rejects the field with an HTTP error. Silent schema-ignoring is the dangerous case — the call succeeds and the spans come back malformed.

Use the OpenAI-style `response_format: {type: "json_schema", json_schema: {...}}`, which works across the family. Numeric JSON-Schema bounds (`minimum`/`maximum`) are respected, unlike some providers that strip them.

## The response is not reliably `json.loads`-able

Even under `response_format`, the content **intermittently** carries a stray duplicated opening brace:

```
{
{
  "spans": [ ... ]
```

So `extract_json_object()` scans for the first *balanced* object rather than parsing the string directly. It is string-aware, so braces inside span text don't break the balance count. It raises rather than falling back to a guess — a detector that silently returns zero spans is the worst possible failure for this system.

Reasoning is returned in a separate `reasoning_content` field and does **not** pollute `content`.

## Budget tokens generously

Reasoning is billed inside `completion_tokens`. At `max_tokens: 1200` a dense page truncated mid-array with `finish_reason: "length"` — the JSON was cut off and the tail of the span list was simply lost. Default is now 6000, and `detect_page()` raises on `finish_reason == "length"` rather than returning a short list.

Truncation is silent under-reporting, on exactly the densest pages. It must be an error.

## Role definitions have to be spelled out

Given a bare enum of role labels, the model classified the patient's **mother and father as `patient_own`** — a third party marked as the applicant's own information, which is an under-redaction and the failure mode that cannot be recalled.

With each role defined in one line, plus `A family member is NEVER patient_own` and `When unsure, choose third_party`, the same page classified all six spans correctly, including the confidential notifier ("a teacher who asked not to be named") and a sibling's diagnosis.

The fail-safe direction matters: uncertainty must resolve toward `third_party`, because over-flagging is correctable and under-flagging is not.

## Do not ask for self-reported confidence

Asked to self-report a 1–10 confidence, these models emit the boundary value every time (`1` consistently, `0` when the bound is removed). There is no signal in it. Span ranking is by detector provenance — which pass found it — not by a number the model made up.

## Operational

- **`GET /v1/models` is unauthenticated.** The health check uses it to verify the configured model id is actually served, without spending a rate-limited inference call. A typo'd model name otherwise surfaces only when the first bundle runs.
- **Free endpoints are rate-limited, not token-billed.** Throughput is the constraint, not cost — hence bounded concurrency (`QUIRE_LLM_CONCURRENCY`) and backoff rather than a cost ceiling.

## Adjacent models, not used

- `nvidia/nemotron-parse` — a document-parsing model. Plausible for ingest, but stage 1 is deliberately local (Tesseract), and sending every page of a clinical bundle to a hosted parser would invert the local-first split for the largest data volume in the system.
- `nvidia/nemotron-3-embed-1b` — 2048-dim (unpublished; probed) and **asymmetric**: the same text as `passage` vs `query` scores cosine 0.7164 against itself. A candidate for entity resolution (stage 5), where both sides are corpus text and so both should be sent as `passage`. Sending the wrong `input_type` doesn't error, it just quietly degrades matching.
