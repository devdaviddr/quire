# Client Brief

Camberwood Children's Hospital, Ruth's redaction workflow, what the app must do, and the two
rules that shape the whole architecture.

Every project starts the same way. Before models, before Azure, before a single dependency, you
understand the client and the recurring problem. The documents, the legal frame, and the
reviewer's workflow determine the schema, the model choice, the rulebook, and the UI. Starting
from a framework would hide all of those decisions.

## The organisation

Camberwood Children's Hospital is a fictional 320-bed paediatric health service in inner-north
Melbourne. As a Victorian public hospital it is an agency under the *Freedom of Information Act
1982* (Vic), overseen by the Office of the Victorian Information Commissioner (OVIC). Anyone can
request access to documents Camberwood holds, and the hospital has a statutory clock to respond.

Most requests are for a patient's clinical record. They come from four kinds of applicant:

- A former patient, now an adult, requesting their own childhood record
- A parent or guardian requesting their child's record
- A solicitor acting in a medico-legal or family law matter
- An insurer, coroner's office, or police unit with a defined scope

Ruth Callaghan is a Senior FOI Officer in Health Information Services. When a request is
accepted, the bundle lands on her desk. It might be 40 pages or 4,000. It is never uniform:
born-digital EMR exports, scanned paper from before digitisation, faxed correspondence,
photographed consent forms, and handwritten progress notes from the 1990s.

Before anything is released, Ruth must read every page and decide what has to be withheld. Not
the patient's own information, which the applicant is entitled to. Everything else. Another
patient's name in a ward round note. A social worker's record of what one parent alleged about
the other. A confidential notifier. A clinician's mobile number. A sibling's diagnosis mentioned
in a family history.

Today that is manual work, page by page, with a highlighter and a statutory deadline. On a large
bundle it takes days. If Ruth misses one span, the hospital has disclosed a third party's health
information to someone who should never have seen it, and there is no way to take it back.

## The user story

> As an FOI officer at a public health service, I want to upload a record bundle for a specific
> request and receive a prepared redaction review, with every candidate span located, classified,
> and mapped to a proposed exemption ground, so I can confirm or remove each proposal quickly and
> produce a defensible release package and a draft decision letter.

Read that carefully. Ruth does not want a system that redacts and releases. She wants a
**prepared review**. The app does the reading, locating, and proposing. She keeps every decision,
and the system records why she made it. That distinction drives everything that follows.

## What "the request" means

Unlike an invoice, a page of a clinical record has no fixed answer. The same name is exempt or
not depending on who is asking.

So the request itself is a first-class input to the pipeline, not metadata. Every run is
conditioned on:

- Applicant identity and their relationship to the patient (self, parent or guardian, legal
  representative, agency)
- Scope of the request, including any date range or document class
- Patient identity, including known aliases and previous names

A generic PII scrubber redacts every name it finds and produces an unusable document. The whole
point of this build is that the rulebook takes context.

## What the app must do

The scope for this build:

- Accept a bundle of PDFs and images for a single request, up to 200 pages and 50 MB
- Capture the request context above before processing begins
- Classify each document in the bundle by record type: progress note, discharge summary,
  correspondence, pathology, imaging report, consent form, allied health or social work note
- Locate candidate spans with page number and bounding box, using layered detectors: pattern and
  checksum rules for structured identifiers, named entity recognition for people and places, and
  a language model for context-dependent material the first two cannot see
- Classify each span's role relative to the applicant: patient's own information, third party,
  clinician acting in a professional capacity, confidential source, deliberative material
- Apply a deterministic exemption rulebook, conditioned on the request context, producing a
  proposed section citation and a plain-English ground for every proposal
- Enforce cross-bundle consistency, so the same entity is treated identically on page 3 and page 287
- Flag spans that require third-party consultation rather than redaction, as a distinct outcome
- Route pages that are substantially handwritten to a manual-only queue instead of partially
  redacting them
- Let Ruth accept, reject, adjust the bounds of, or hand-add any redaction, page by page, with the
  proposed ground visible
- Produce an output PDF in which redacted content is genuinely removed rather than covered, with
  metadata stripped, and verify this by reopening the output and asserting the redacted strings
  are not extractable
- Generate a schedule of documents and a draft decision letter citing the grounds relied on, which
  is never sent automatically
- Keep an audit trail of every decision — span, ground, officer, timestamp — with explicit
  deletion so a demo can be reset

## What stays out

Just as important is what is deliberately excluded. No automatic release of any kind. No EMR
integration. No request intake, fee handling, or applicant identity verification. No sending of
consultation or decision correspondence. No pixel redaction of burnt-in annotations on DICOM
imaging, which is a known gap and is named as one rather than quietly ignored. No authentication,
no queues, no case management.

This is a teaching skeleton that keeps the engineering boundaries visible, not a production FOI
system.

## Rule one: the split

> **Models locate and characterise evidence. Deterministic code cites the exemption. The human
> owns the decision.**

A model can tell you that a span is a person's name and that the person is not the patient.
Whether that makes it exempt is a question about the Act and about this particular request, and a
rulebook belongs in ordinary Python that you can read, test, and reproduce offline. Keep this
split in mind every time a model output shows up in the build.

The exemption catalog is a fixed, closed set, which is what makes the proposals evaluable at all.
Starting point, to be confirmed against current OVIC guidelines before the rulebook is written:

| Ground | Typical trigger in a clinical record |
| --- | --- |
| Personal affairs of a third party | Another patient, a family member, a notifier |
| Information given in confidence | A statement provided on the understanding it would not be disclosed |
| Secrecy provisions in other Acts | Child protection material, other statutory restrictions |
| Legal professional privilege | Advice from hospital legal counsel in the file |
| Internal working documents | Deliberative material not forming part of the clinical record |
| Health of the applicant | Where disclosure direct to the applicant may be prejudicial |

## Rule two: the asymmetry

This is where the project departs from an ordinary document-review app, and it must be designed
for from the first commit.

The two failure modes are not symmetric. An unnecessary redaction is an over-claim of exemption.
It is a compliance failure, it is appealable to OVIC and then VCAT, and it is correctable. A
missed redaction is an unlawful disclosure of someone's health information, and a released bundle
cannot be recalled.

Three consequences:

1. **The system over-flags on purpose.** Tune for recall on must-redact spans and accept the
   precision cost.
2. **The reviewer's default action is subtractive.** Ruth's job in the UI is removing proposals
   she disagrees with, not hunting for ones the system missed.
3. **The system never emits a clearance.** There is no "this page is clean" state, and no
   bulk-approve fast path. The absence of a flag must never come to function as a signal, because
   the moment Ruth starts trusting it, the safeguard is gone.

The value proposition is compressed review time and a defensible audit trail. It is not fewer
pages read.

## What "working" means

Before any model runs, the corpus defines the target. The repository ships a synthetic bundle of
fictional patient records with a ground-truth redaction map: for every document, every span that
must be redacted, the ground it falls under, and why.

The harness reports four numbers:

- **Recall on must-redact spans, per ground.** Near 1.0 is the requirement, not the aspiration.
- **Over-redaction rate**, as the cost side of that recall.
- **Leak rate**, the proportion of documents containing at least one missed must-redact span. This
  is the operational metric, because one miss ruins a release regardless of how the other spans
  scored.
- **Consistency**, the proportion of entities redacted on every occurrence rather than some.

The corpus is deliberately salted with hard cases: name variants and misspellings, a third party
identified only by role, a person re-identifiable from context after their name is removed, the
same document duplicated at different OCR quality, and a page of handwriting.

**No real patient information is used at any stage of this build.**

## Checkpoint

You should be able to describe, without mentioning any implementation:

- Who the user is and what her recurring problem looks like
- Why the same name can be exempt in one request and not another
- What a prepared redaction review contains
- Which decisions the app makes and which decisions Ruth keeps
- Why the system is tuned to over-flag, and what that means for the UI
- What is deliberately out of scope
