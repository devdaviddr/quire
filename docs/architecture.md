# Architecture

## The request is an input, not metadata

Unlike an invoice, a page of a clinical record has no fixed answer. The same name is exempt or not depending on who is asking. Every run is therefore conditioned on:

- **Applicant identity** and their relationship to the patient — self, parent, guardian or substitute decision-maker, legal representative, agency
- **Scope** of the request, including any date range or document class
- **Patient identity**, including known aliases and previous names

A generic PII scrubber redacts every name it finds and produces an unusable document. The whole point of this build is that the rulebook takes context, so the context flows through every stage rather than being attached to the job record.

## The two rules

### Rule one: the split

> Models locate and characterise evidence. Deterministic code cites the exemption. The human owns the decision.

A model can tell you that a span is a person's name and that the person is not the patient. Whether that makes it exempt is a question about the Act and about this particular request, and a rulebook belongs in ordinary Python that you can read, test, and reproduce offline.

Concretely, this means model output never selects a section citation. Stages 3 and 4 emit spans and roles; stage 6 is a pure function from `(span, role, request context)` to a proposed ground, with no network call in it. The exemption catalog is a fixed, closed set — which is what makes the proposals evaluable at all.

### Rule two: the asymmetry

The two failure modes are not symmetric. An unnecessary redaction is an over-claim of exemption: a compliance failure, appealable, and correctable. A missed redaction is an unlawful disclosure of someone's health information, and a released bundle cannot be recalled.

Three consequences, each of which shows up in the code:

1. **The system over-flags on purpose.** Detection is a *union* of the three passes, not an intersection or a confidence-weighted vote. Tune for recall on must-redact spans and accept the precision cost.
2. **The reviewer's default action is subtractive.** The UI presents proposals to remove, not a blank page to annotate.
3. **The system never emits a clearance.** There is no "this page is clean" state and no bulk-approve fast path. The absence of a flag must never come to function as a signal, because the moment the reviewer starts trusting it, the safeguard is gone.

The value proposition is compressed review time and a defensible audit trail. It is not fewer pages read.

## Pipeline

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

### Stage notes

**1 — Ingest.** Bundles are never uniform: born-digital EMR exports, scanned paper, faxed correspondence, photographed consent forms, handwritten progress notes. Everything normalises to the same shape — a page with text runs and word-level bounding boxes — so no downstream stage needs to know how the page arrived. Substantially handwritten pages are routed to a manual-only queue rather than partially redacted, because a partial redaction on a page the OCR could not read is worse than no automation at all.

**3 — Detect.** The three passes are independent and their outputs are unioned. Pattern and checksum rules handle identifiers with a verifiable shape. NER handles people, places, and organisations. The language model handles what the first two structurally cannot see — a third party identified only by their role, a person re-identifiable from context after their name is removed, material provided in confidence. Overlapping spans from different passes are merged, not deduplicated away.

**5 — Resolve.** Cross-bundle consistency is a first-class outcome, not a side effect. Entity resolution runs over the whole bundle before the rulebook, so a decision about a person applies to every occurrence of that person — including name variants and misspellings.

**6 — Rulebook.** Some spans do not resolve to a redaction at all. Where the correct action is to consult a third party before deciding, that is a distinct outcome the officer sees and acts on, not a redaction proposal with low confidence.

**8 — Produce.** "Redacted" means the content is removed from the PDF content stream and the document metadata is stripped — not a black rectangle drawn over live, selectable text. The output is verified by reopening it and asserting the redacted strings are not extractable. A release that fails that assertion is not produced.

## Audit trail

Every decision is appended: span, ground, officer, timestamp. Nothing is updated in place, so the record shows what was proposed, what the officer did with it, and when. Deletion is explicit and total, so a demo can be reset without leaving partial state behind.

## See also

- [Client brief](client-brief.md) — the organisation, the user, and the problem
- [Tech stack](tech-stack.md) — what each stage is built on, and why
- [Evaluation](evaluation.md) — how "working" is measured
