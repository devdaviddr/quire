# Evaluation

The corpus defines the target before any model runs. Without it, "the redaction looks good" is the only available verdict, and that is not a verdict.

## The corpus

`corpus/` ships a synthetic bundle of fictional patient records with a ground-truth redaction map: for every document, every span that must be redacted, the ground it falls under, and why.

**No real patient information is used at any stage of this build.** Every name, date, identifier, and clinical detail in the corpus is fabricated.

The corpus is deliberately salted with hard cases:

| Case | What it tests |
| --- | --- |
| Name variants and misspellings | Entity resolution across the bundle (stage 5) |
| A third party identified only by role | The contextual detector — pattern rules and NER structurally cannot see this |
| A person re-identifiable from context after their name is removed | Whether redaction actually de-identifies, or only removes the obvious token |
| The same document at two OCR qualities | Consistency when the text layer degrades |
| A page of handwriting | The manual-only routing path, not partial redaction |

Each of these exists because it is a way the system can look like it is working while failing. A harness that only measures clean cases measures nothing.

### Why the corpus is paediatric

Nothing in the pipeline, the rulebook, or the exemption catalog is specific to children's health — Quire applies to hospital records generally, and the [client brief](client-brief.md) describes one hospital rather than the only one.

The corpus is paediatric because that is where the hardest applicant-context cases live. A paediatric bundle produces a triangle a general adult record does not: a former patient now an adult requesting their own childhood record, a parent or guardian requesting a child's record, and a second parent whose statements appear in that same record as a third party. The same name is exempt in one of those requests and releasable in another, which is the sharpest available test of the rule that the request is an input to the pipeline rather than metadata attached to it. Add child protection material and confidential notifiers, and a single bundle exercises four of the six exemption grounds.

A system that scores well on this corpus handles an adult general-medicine bundle as a simpler case. The reverse is not true, which is why the harder corpus is the one worth building.

## The four numbers

| Metric | Definition | Target |
| --- | --- | --- |
| **Recall on must-redact spans**, reported per ground | Proportion of ground-truth spans the system proposed | Near 1.0 — the requirement, not the aspiration |
| **Over-redaction rate** | Proportion of proposals not in the ground truth | The accepted cost of that recall — tracked, not minimised |
| **Leak rate** | Proportion of documents containing at least one missed must-redact span | The operational metric |
| **Consistency** | Proportion of entities redacted on every occurrence rather than some | Near 1.0 |

**Recall is reported per ground, not aggregated.** A system with 0.98 overall recall that misses most confidential-source spans is not a 0.98 system; it is a system with a hole in one ground, and averaging hides it.

**Leak rate is the operational metric.** One miss ruins a release regardless of how the other spans scored, so a document-level measure matters more than a span-level one. A run can post excellent recall and still have an unacceptable leak rate if the misses cluster.

**Over-redaction is a cost line, not a failure.** Because the two failure modes are asymmetric (see [architecture.md](architecture.md)), the harness reports over-redaction to make the trade visible, not to drive it toward zero. A change that improves precision at the cost of recall is a regression.

## Running it

Not yet implemented. The harness will run as a CLI over `corpus/`, offline, with no model in the loop for the rulebook stages — so exemption proposals are reproducible run to run.
