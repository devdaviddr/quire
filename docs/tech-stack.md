# Tech stack

Local-first: `docker compose up` gives you the whole system on one machine, with no cloud account, no managed database, and no object store. Every choice below is downstream of a constraint in the [client brief](client-brief.md) or one of the two rules in [architecture.md](architecture.md).

| Layer | Choice | Why |
| --- | --- | --- |
| Orchestration | Docker Compose — `db`, `api`, `web` | Three services, one command, no host installs beyond Docker |
| Frontend | React 19, Vite, TypeScript | Vite dev server proxies `/api`, so the browser is same-origin and there is no CORS config to maintain |
| Backend | Python 3.12, FastAPI, Pydantic v2 | The rulebook must be plain readable Python; the API lives beside it |
| Database | PostgreSQL 16, SQLAlchemy, Alembic | Spans, entities, decisions, append-only audit trail |
| Storage | Local Docker volume | Bundles and outputs stay on disk |
| PDF | PyMuPDF | Word-level boxes on read, true content removal on write (`apply_redactions`) |
| OCR | Tesseract, bundled in the API image | Word-level boxes for scanned pages; its confidence output routes handwriting to the manual queue |
| Structured detectors | Regex + checksum rules | Identifiers with a verifiable shape — deterministic, offline |
| NER | spaCy | People, places, organisations across the bundle |
| Contextual detector | NVIDIA Nemotron 3 Super via NIM | The one hosted call; see below |
| Rulebook | Plain Python + pytest | A closed set of grounds, unit-tested, no model in the loop |
| Evaluation | pytest + a CLI over `corpus/` | Recall per ground, over-redaction, leak rate, consistency |

## FastAPI, not "Pydantic"

Pydantic isn't an alternative to FastAPI — it's the validation library FastAPI is built on, so choosing FastAPI gets you Pydantic v2 models for free. That pairing is what we want here: the request context, spans, and decisions are all typed models, and the OpenAPI schema falls out of them rather than being maintained separately.

(PydanticAI, the agent framework, is a different thing and we don't need it. The contextual detector is one structured call per page, not an agent loop — a plain HTTP client with a JSON schema is less machinery and one less dependency to track.)

## Where "local-first" stops, and why that's the boundary

Everything runs on your machine except one thing: pipeline stage 3c, the contextual detector, which calls NVIDIA NIM. That is the only network dependency, and it's a deliberate line rather than an accident.

The consequence is that **ingest, the pattern and checksum rules, entity resolution, the rulebook, and the entire output path run offline**. Exemption proposals are reproducible without an API key — you can re-run the rulebook against stored spans and get the same citations, which is what makes the [evaluation harness](evaluation.md) meaningful.

**The detector is swappable because NIM is OpenAI-compatible.** The same client drives a local llama.cpp or Ollama server; only the base URL and model name change:

```bash
QUIRE_LLM_BASE_URL=http://host.docker.internal:11434/v1
QUIRE_LLM_MODEL=gpt-oss
```

That keeps a fully-offline path open, at some cost in detection quality on the context-dependent cases that motivate stage 3c in the first place.

## Why Nemotron

Free-tier NIM keys are rate-limited rather than token-billed, so a 200-page bundle costs throughput rather than money — which suits a teaching build that people will run repeatedly against the same corpus. `nemotron-3-super-120b-a12b` runs ~7–10s per page and, counter-intuitively, is faster than the smaller nano model.

The client compensates for several undocumented behaviours — `nvext.guided_json` silently failing, intermittently malformed JSON, silent truncation, and role misclassification from bare enum labels. All of it is written down in [model-notes.md](model-notes.md), with the measurements behind each decision.

## Deliberate omissions

- **No queue, no workers.** Processing is synchronous. The 200-page ceiling makes that viable and keeps the pipeline readable as a straight line. Page-level concurrency inside a run is bounded by `QUIRE_LLM_CONCURRENCY`.
- **No object store.** Local volume. A demo should not need cloud credentials.
- **No auth.** Named as out of scope in the brief; adding it would obscure the boundaries this build exists to show.
- **No production frontend build.** The `web` service runs the Vite dev server with hot reload. A static build behind nginx is a deployment concern, and this does not deploy.
