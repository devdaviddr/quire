# Quire

**A prepared redaction review for FOI requests against paediatric clinical records.**

A children's hospital receives a Freedom of Information request for a patient's clinical record. Before anything is released, an FOI officer must read every page and decide what has to be withheld — another patient's name in a ward round note, a confidential notifier, a clinician's mobile number, a sibling's diagnosis in a family history. On a 4,000-page bundle that takes days, and a single missed span is an unlawful disclosure that cannot be recalled.

Quire does the reading, locating, and proposing. The officer keeps every decision.

Upload a bundle for a specific request, and Quire returns a page-by-page review: every candidate span located with a bounding box, classified by its role relative to the applicant, and mapped to a proposed exemption ground. The officer accepts, rejects, or adjusts each proposal, and Quire produces a release package with the redacted content genuinely removed, a schedule of documents, a draft decision letter, and an audit trail of who decided what and why.

No real patient information is used at any stage. See the [client brief](docs/client-brief.md) for the full problem statement.

## Two rules that shape the architecture

**1. The split.** Models locate and characterise evidence. Deterministic code cites the exemption. The human owns the decision.

A model can tell you a span is a person's name and that the person is not the patient. Whether that makes it exempt is a question about the Act and about this particular request, so the rulebook is ordinary Python — readable, testable, and reproducible offline. Model output never selects a section citation.

**2. The asymmetry.** An unnecessary redaction is a correctable compliance failure. A missed redaction is an unlawful disclosure, and a released bundle cannot be recalled.

So the system over-flags on purpose and tunes for recall, the reviewer's default action is subtractive, and there is no "this page is clean" state and no bulk-approve path. The absence of a flag must never come to function as a signal.

## Architecture

The request context — who is asking, their relationship to the patient, the scope, and the patient's known aliases — is a first-class input to every stage, not metadata. The same name is exempt for one applicant and not another.

```
Bundle (PDF/image, ≤200pp, ≤50MB) + Request context
  │
  ├─ 1. Ingest        normalise to per-page text + word boxes (PyMuPDF);
  │                   OCR scanned pages (Tesseract); route substantially
  │                   handwritten pages to a manual-only queue
  │
  ├─ 2. Classify      record type per document — progress note, discharge
  │                   summary, correspondence, pathology, imaging, consent,
  │                   allied health / social work
  │
  ├─ 3. Detect        layered, union of three passes:
  │                     a. pattern + checksum rules (structured identifiers)
  │                     b. named entity recognition (people, places, orgs)
  │                     c. language model (context-dependent material the
  │                        first two cannot see)
  │
  ├─ 4. Role          each span classified relative to the applicant: patient's
  │                   own / third party / clinician in professional capacity /
  │                   confidential source / deliberative
  │
  ├─ 5. Resolve       entity resolution across the bundle, so the same person
  │                   is treated identically on page 3 and page 287
  │
  ├─ 6. Rulebook      deterministic, request-conditioned. Emits a proposed
  │                   section citation + plain-English ground, or flags the
  │                   span for third-party consultation instead
  │
  ├─ 7. Review        page-by-page UI. Accept / reject / adjust bounds /
  │                   hand-add. Subtractive by default. No clearance state.
  │
  └─ 8. Produce       output PDF with redacted content removed (not covered)
                      and metadata stripped, verified by reopening the output
                      and asserting the strings are not extractable; plus a
                      schedule of documents and a draft decision letter
```

Every decision — span, ground, officer, timestamp — is appended to an audit log with explicit deletion so a demo can be reset.

## Tech stack

| Layer | Choice | Why |
| --- | --- | --- |
| API | Python 3.12, FastAPI, Uvicorn | The rulebook must be plain readable Python; the API lives beside it |
| PDF | PyMuPDF | Word-level bounding boxes on read, and true content removal on write (`apply_redactions`) rather than a black rectangle over live text |
| OCR | Tesseract | Word-level boxes for scanned and faxed pages; also the signal for routing handwriting to the manual queue |
| Structured detectors | Regex + checksum rules | Identifiers with a verifiable shape — deterministic, no model needed |
| NER | spaCy | People, places, and organisations across the bundle |
| Contextual detector | Claude Opus 5 (`claude-opus-5`) | Spans only readable in context — a person identifiable by role, a confidential source, deliberative material |
| Rulebook | Plain Python + pytest | A closed set of exemption grounds, unit-tested, runs offline with no model in the loop |
| Database | PostgreSQL 16, SQLAlchemy, Alembic | Spans, entities, decisions, audit trail |
| Storage | Local volume | Bundles and outputs stay on disk; no object store, no cloud dependency |
| Review UI | React + Vite + TypeScript, pdf.js | Page render with a bounding-box overlay *(not yet implemented)* |
| Evaluation | pytest + a CLI over `corpus/` | Recall per ground, over-redaction rate, leak rate, consistency |

Processing is synchronous — no queue, no workers. That is a deliberate scope decision, not a gap to fill.

## Running it

Requires Docker and Docker Compose. Nothing else is installed on the host.

```bash
git clone git@github.com:devdaviddr/quire.git
cd quire
cp .env.example .env      # then set ANTHROPIC_API_KEY
docker compose up --build
```

This starts:

| Service | Address | Notes |
| --- | --- | --- |
| `api` | http://localhost:8000 | OpenAPI docs at http://localhost:8000/docs |
| `db` | internal only | PostgreSQL 16, data in the `quire-db` volume |

Check it came up:

```bash
curl -s localhost:8000/health
# {"status":"ok","database":"ok","version":"0.1.0"}
```

Common commands:

```bash
docker compose logs -f api        # follow API logs
docker compose exec api pytest    # run the test suite
docker compose down               # stop
docker compose down -v            # stop and delete the database volume
```

The API image bundles Tesseract, so OCR needs no host setup. Source under `api/` is bind-mounted and Uvicorn reloads on change — edit and the container picks it up.

### Configuration

All configuration is environment variables; see `.env.example` for the full list.

| Variable | Default | Purpose |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | — | Required for the contextual detector. The rest of the pipeline runs without it. |
| `QUIRE_MODEL` | `claude-opus-5` | Model used for contextual detection |
| `DATABASE_URL` | set by Compose | PostgreSQL connection string |
| `QUIRE_DATA_DIR` | `/data` | Where bundles and outputs are written |
| `QUIRE_PORT` | `8000` | Host port the API binds to. Set it if 8000 is taken: `QUIRE_PORT=8200 docker compose up`. |

## What "working" means

The corpus defines the target before any model runs. `corpus/` ships a synthetic bundle of fictional records with a ground-truth redaction map: for every document, every span that must be redacted, the ground it falls under, and why. It is deliberately salted with hard cases — name variants and misspellings, a third party identified only by role, a person re-identifiable from context after their name is removed, the same document duplicated at different OCR quality, and a page of handwriting.

The harness reports four numbers:

| Metric | Target |
| --- | --- |
| **Recall on must-redact spans**, per ground | Near 1.0 — the requirement, not the aspiration |
| **Over-redaction rate** | The accepted cost of that recall |
| **Leak rate** — documents with ≥1 missed must-redact span | The operational metric; one miss ruins a release |
| **Consistency** — entities redacted on every occurrence | Near 1.0 |

## Out of scope

Deliberately excluded, and named rather than quietly ignored: automatic release of any kind; EMR integration; request intake, fee handling, or applicant identity verification; sending consultation or decision correspondence; pixel redaction of burnt-in annotations on DICOM imaging; authentication; queues; case management.

This is a teaching skeleton that keeps the engineering boundaries visible, not a production FOI system.

## Documentation

- [Client brief](docs/client-brief.md) — the organisation, the user, the request, full scope and non-scope, and the two rules in detail.

## Status

Design phase. The Compose stack, API skeleton, and configuration are in place; the pipeline stages, rulebook, review UI, and evaluation harness are not yet implemented.
