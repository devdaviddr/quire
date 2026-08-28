# Corpus

The synthetic evaluation bundle and its ground-truth redaction map: for every
document, every span that must be redacted, the ground it falls under, and why.

The corpus defines the target before any model runs. It is deliberately salted
with hard cases — name variants and misspellings, a third party identified only
by role, a person re-identifiable from context after their name is removed, the
same document duplicated at different OCR quality, and a page of handwriting.

**No real patient information is used at any stage.** Every name, date,
identifier, and clinical detail here is fabricated.

Mounted read-only into the API container at `/corpus`. See
[docs/evaluation.md](../docs/evaluation.md) for the hard cases and the four
metrics the harness reports.

Not yet populated.
