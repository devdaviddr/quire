# Quire

A prepared redaction review for FOI requests against hospital clinical records.

An FOI officer at a public hospital uploads a record bundle for a specific request. Quire locates every candidate span, classifies its role relative to the applicant, and proposes an exemption ground for each one. The officer confirms or removes each proposal, and Quire produces a release package with the redacted content genuinely removed, a schedule of documents, a draft decision letter, and an audit trail.

Quire does the reading, locating, and proposing. The officer keeps every decision.

Two rules shape the whole design:

1. **The split** — models locate and characterise evidence, deterministic code cites the exemption, the human owns the decision.
2. **The asymmetry** — a missed redaction cannot be recalled, so the system over-flags on purpose, the reviewer's default action is subtractive, and it never emits a clearance.

Local-first: three containers, one command, no cloud account. The only network call is the contextual detector, and it is swappable for a local model. No real patient information is used at any stage.

## Quick start

Requires Docker and Docker Compose. Nothing else is installed on the host.

```bash
cp .env.example .env      # then set NVIDIA_API_KEY (free: build.nvidia.com)
docker compose up --build
```

| Service | Address | Stack |
| --- | --- | --- |
| `web` | http://localhost:5173 | React 19, Vite, TypeScript |
| `api` | http://localhost:8000 | Python 3.12, FastAPI — OpenAPI docs at `/docs` |
| `db` | internal only | PostgreSQL 16 |

```bash
curl -s localhost:8000/health   # checks database and detector reachability
docker compose exec api pytest  # backend tests (offline, no API key needed)
docker compose exec web npx tsc -b
docker compose down -v          # stop and delete the database volume
```

Both `api/` and `web/` are bind-mounted with hot reload. The API image bundles Tesseract, so OCR needs no host setup.

## Configuration

All configuration is environment variables. See `.env.example` for the full list.

| Variable | Default | Purpose |
| --- | --- | --- |
| `NVIDIA_API_KEY` | — | Free NIM key for the contextual detector. Every other stage runs offline. |
| `QUIRE_LLM_MODEL` | `nvidia/nemotron-3-super-120b-a12b` | Detection model (~7–10s/page) |
| `QUIRE_LLM_BASE_URL` | NVIDIA NIM | Any OpenAI-compatible endpoint — point it at Ollama or llama.cpp to run fully offline |
| `QUIRE_LLM_CONCURRENCY` | `4` | Pages detected in parallel. Free endpoints are rate-limited, not token-billed. |
| `QUIRE_API_PORT` / `QUIRE_WEB_PORT` | `8000` / `5173` | Host ports, if those are taken |

## Documentation

| Document | Contents |
| --- | --- |
| [Client brief](docs/client-brief.md) | The organisation, the officer's workflow, full scope and non-scope |
| [Architecture](docs/architecture.md) | The two rules in detail, the eight pipeline stages, the audit trail |
| [Tech stack](docs/tech-stack.md) | Every choice and why, and where local-first stops |
| [Model notes](docs/model-notes.md) | Measured Nemotron behaviour the model cards don't document |
| [Evaluation](docs/evaluation.md) | The corpus, its hard cases, and the four metrics |

## Out of scope

No automatic release of any kind, no EMR integration, no request intake or applicant identity verification, no sending of correspondence, no pixel redaction of burnt-in DICOM annotations, no authentication, no queues, no case management. This is a teaching skeleton that keeps the engineering boundaries visible, not a production FOI system. See the [client brief](docs/client-brief.md) for the reasoning.

## Status

Design phase. The Compose stack, API skeleton, detector client, and configuration are in place and tested. The pipeline stages, rulebook, review UI, and evaluation harness are not yet implemented.
