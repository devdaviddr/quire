# FOI Redaction Review

A prepared redaction review for FOI requests against paediatric clinical records at Camberwood
Children's Hospital (fictional Victorian public hospital).

An FOI officer uploads a record bundle for a specific request. The system locates every candidate
span, classifies its role relative to the applicant, and proposes an exemption ground for each
one. The officer confirms or removes each proposal and the system produces a defensible release
package, a schedule of documents, and a draft decision letter.

**Two rules shape the architecture:**

1. Models locate and characterise evidence. Deterministic code cites the exemption. The human owns
   the decision.
2. The failure modes are asymmetric — a missed redaction cannot be recalled — so the system
   over-flags on purpose, the reviewer's default action is subtractive, and it never emits a
   clearance.

No real patient information is used at any stage of this build.

## Documentation

- [Client brief](docs/client-brief.md) — the organisation, the user, the scope, what stays out,
  and the two rules.

## Status

Design phase. No implementation yet.
