# Tech stack

Every choice here is downstream of a constraint in the [client brief](client-brief.md) or one of the two rules in [architecture.md](architecture.md). Nothing is here because it is conventional.

| Layer | Choice | Why |
| --- | --- | --- |
| API | Python 3.12, FastAPI, Uvicorn | The rulebook must be plain readable Python; the API lives beside it rather than across a process boundary |
| PDF | PyMuPDF | Word-level bounding boxes on read, and true content removal on write (`apply_redactions`) rather than a black rectangle over live text |
| OCR | Tesseract | Word-level boxes for scanned and faxed pages; its confidence output is also the signal for routing handwriting to the manual queue |
| Structured detectors | Regex + checksum rules | Identifiers with a verifiable shape — deterministic, offline, no model needed |
| NER | spaCy | People, places, and organisations across the bundle |
| Contextual detector | Claude Opus 5 (`claude-opus-5`) | Spans only readable in context — a person identifiable by role, a confidential source, deliberative material |
| Rulebook | Plain Python + pytest | A closed set of exemption grounds, unit-tested, runs offline with no model in the loop |
| Database | PostgreSQL 16, SQLAlchemy, Alembic | Spans, entities, decisions, append-only audit trail |
| Storage | Local volume | Bundles and outputs stay on disk; no object store, no cloud dependency |
| Review UI | React + Vite + TypeScript, pdf.js | Page render with a bounding-box overlay *(not yet implemented)* |
| Evaluation | pytest + a CLI over `corpus/` | Recall per ground, over-redaction rate, leak rate, consistency |

## Why PyMuPDF specifically

Two requirements point at the same library. Detection needs word-level bounding boxes so a span can be located on the page, and production needs redactions that genuinely remove content from the PDF content stream. PyMuPDF does both, which keeps the coordinate space consistent from detection through to output — a span located during detection is the same rectangle that gets removed, with no translation step in between to get wrong.

## Why one model, behind one config value

The contextual detector is the only stage that talks to a model. That is a deliberate boundary: it means the rulebook, the pattern rules, the ingest pipeline, and the entire output path run offline and deterministically. The exemption proposals can be regenerated and unit-tested without an API key.

`QUIRE_MODEL` is a single string. Swapping it changes one stage and nothing else.

## Deliberate omissions

- **No queue, no workers.** Processing is synchronous. A 200-page ceiling makes that viable, and it keeps the pipeline readable as a straight line rather than a set of message handlers.
- **No object store.** Local volume. A demo should not need cloud credentials.
- **No auth.** Named as out of scope in the brief; adding it would obscure the boundaries this build exists to show.
- **No ORM-generated API layer.** The schema is small and the shapes are specific; hand-written models are shorter than the configuration to generate them.
