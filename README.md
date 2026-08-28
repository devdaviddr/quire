# Quire

A prepared redaction review for FOI requests against paediatric clinical records.

An FOI officer at a children's hospital uploads a record bundle for a specific request. Quire locates every candidate span, classifies its role relative to the applicant, and proposes an exemption ground for each one. The officer confirms or removes each proposal, and Quire produces a release package with the redacted content genuinely removed, a schedule of documents, a draft decision letter, and an audit trail.

Quire does the reading, locating, and proposing. The officer keeps every decision.

Two rules shape the whole design:

1. **The split** — models locate and characterise evidence, deterministic code cites the exemption, the human owns the decision.
2. **The asymmetry** — a missed redaction cannot be recalled, so the system over-flags on purpose, the reviewer's default action is subtractive, and it never emits a clearance.

No real patient information is used at any stage.

## Quick start

Requires Docker and Docker Compose. Nothing else is installed on the host.

```bash
cp .env.example .env      # then set ANTHROPIC_API_KEY
docker compose up --build
curl -s localhost:8000/health
```

| Service | Address |
| --- | --- |
| `api` | http://localhost:8000 — OpenAPI docs at `/docs` |
| `db` | internal only (PostgreSQL 16) |

```bash
docker compose logs -f api        # follow API logs
docker compose exec api pytest    # run the test suite
docker compose down -v            # stop and delete the database volume
```

Source under `api/` is bind-mounted and Uvicorn reloads on change. The API image bundles Tesseract, so OCR needs no host setup.

## Configuration

All configuration is environment variables. See `.env.example` for the full list.

| Variable | Default | Purpose |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | — | Required for the contextual detector. The rest of the pipeline runs without it. |
| `QUIRE_MODEL` | `claude-opus-5` | Model used for contextual detection |
| `QUIRE_PORT` | `8000` | Host port for the API. Set it if 8000 is taken. |
| `DATABASE_URL` | set by Compose | PostgreSQL connection string |
| `QUIRE_DATA_DIR` | `/data` | Where bundles and outputs are written |

## Documentation

| Document | Contents |
| --- | --- |
| [Client brief](docs/client-brief.md) | The organisation, the officer's workflow, full scope and non-scope |
| [Architecture](docs/architecture.md) | The two rules in detail, the eight pipeline stages, the audit trail |
| [Tech stack](docs/tech-stack.md) | What each stage is built on, and why |
| [Evaluation](docs/evaluation.md) | The corpus, its hard cases, and the four metrics |

## Out of scope

No automatic release of any kind, no EMR integration, no request intake or applicant identity verification, no sending of correspondence, no pixel redaction of burnt-in DICOM annotations, no authentication, no queues, no case management. This is a teaching skeleton that keeps the engineering boundaries visible, not a production FOI system. See the [client brief](docs/client-brief.md) for the reasoning.

## Status

Design phase. The Compose stack, API skeleton, and configuration are in place. The pipeline stages, rulebook, review UI, and evaluation harness are not yet implemented.
