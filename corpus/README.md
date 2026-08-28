# Corpus

The synthetic evaluation bundle and its ground-truth redaction map. The corpus defines the target before any model runs — see [docs/evaluation.md](../docs/evaluation.md) for the four metrics it feeds.

**No real patient information is used at any stage.** Every name, date, identifier, address, provider number and clinical detail here is fabricated, and every rendered page carries a footer saying so.

## Layout

```
requests/         Two request contexts over the same bundle
documents/        Markdown sources — the source of truth
rendered/         PDFs the pipeline ingests — build artefacts
ground-truth.json The redaction map
render.py         documents/ -> rendered/
```

Markdown is the source of truth because it is reviewable and diffable; a ground-truth map is only trustworthy if a human can read the document beside it. The PDFs are regenerated from it:

```bash
docker compose run --rm --no-deps -v "$PWD/corpus:/corpusrw" api python /corpusrw/render.py
```

Rendering is seeded and deterministic — the same sources produce the same bytes, so the harness measures detector behaviour rather than render noise.

## The bundle

Eleven documents covering all seven record types in the brief, plus one document rendered twice at different quality. One fictional patient, 1997–2004.

| # | Document | Type | Carries |
| --- | --- | --- | --- |
| 01 | Consent form | consent_form | Guardian signature, third-party contact details, provider number |
| 02 | Progress note | progress_note | **Handwriting** — manual-only routing |
| 03 | Ward round note | progress_note | Another patient by name, sibling diagnosis, unnamed grandmother |
| 04 | Coeliac serology | pathology | A sibling's result inside the patient's report |
| 05 | Social work note | social_work_note | Confidential notifier, role-only identification, child protection material |
| 06 | Discharge summary | discharge_summary | Rendered **clean and degraded** — the consistency case |
| 07 | GP letter | correspondence | **Name variants and misspellings** |
| 08 | Bone age report | imaging_report | Burnt-in DICOM annotation — the named gap |
| 09 | Legal advice | correspondence | Legal professional privilege, document-level outcome |
| 10 | Internal email | correspondence | Deliberative material, health-of-the-applicant |
| 11 | Adolescent clinic note | progress_note | **Alias** after a change of name |

## Two requests, one bundle

`requests/` holds two request contexts over the same documents:

- **request-a-self** — Thomas Byrne, now an adult, requesting his own childhood record.
- **request-b-guardian** — Sandra Byrne, his mother and guardian, requesting the record while he was a minor.

**Thirteen spans change their required action between the two**, with no change to the documents. Sandra Byrne is a third party under A and the applicant under B. One span in document 10 is exempt under *health of the applicant* in A and *internal working documents* in B — same words, different ground, purely because the applicant changed.

This is the corpus's central claim: a system that treats the request as metadata rather than an input gets thirteen spans wrong on a bundle this small.

## Ground truth

`ground-truth.json` records, for every span: the text, the entity it belongs to, its role, and a per-request action with the ground and the reasoning. Actions are `redact`, `release`, `consult_third_party`, and `manual_only` — `release` matters as much as `redact`, because redacting a treating clinician's name or a provider number is the over-redaction failure the harness is meant to measure.

61 spans. All six exemption grounds exercised. Entity surface forms are listed so consistency can be scored across name variants.

## Known limitation

The handwritten page is a *simulation of the OCR failure*, not real handwriting: per-character jitter, rotation and baseline drift over a degraded background. It reliably produces the low-confidence output that should trigger manual-only routing, which is the behaviour under test — but it does not exercise a real handwriting recogniser, and a system tuned to pass it has not been shown to handle genuine 1990s ward-round scrawl.
