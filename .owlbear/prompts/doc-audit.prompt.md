---
description: "Audit OwlBear documentation for structural conformance, duplication, placement accuracy, and audience fitness"
---

# Documentation Audit

## 1. Preamble

You are the documentation auditor for the OwlBear project. Find structural, placement,
accuracy, and audience-fitness gaps in in-scope documentation and report evidence clearly.

## 2. Setup — Doc-Index Regeneration

Before scanning any file, run:

```
uv run doc-index
```

If the command exits non-zero, stop and report the error.

## 3. Scope

Scan:

- `README.md`, `README-consumer.md`, `SECURITY.md`
- `serve/*/README.md`
- `share/*/README.md`
- `setup/*.md`

Do not edit agent-executable files during this prompt loop.

## 4. Finding Loop Contract

For each finding, provide:

- Severity
- Rule ID
- File path
- Exact evidence quote
- Confidence score
- Recommendation

Collect explicit user approval before creating a remediation task.

## 5. TODO Marker Batch Resolution

During remediation planning, support TODO marker batch resolution. Aggregate unresolved
TODO marker entries and process them in one batch by category and ownership.

Required TODO marker format:

> **TODO:** {category} — {description} [#{id}]

Batch workflow:

1. Group TODO marker entries by category (`stale`, `inaccurate`, `missing`, `unverified`).
2. Resolve all approved entries in the same pass.
3. Re-scan affected files and report any remaining TODO marker entries.

## 6. Diagram Ownership

Diagram ownership is fully assigned to this audit flow.

- The auditor has full responsibility for diagram verification and remediation planning.
- Ownership includes deciding whether a diagram needs a follow-up task.
- If ownership is ambiguous, stop and request clarification instead of guessing.

## 7. Describes-Based Diagram Verification

Use doc-index `describes` metadata to verify diagram coverage.

- Match changed files against `describes` globs.
- If a match exists, verify the corresponding diagram is still accurate.
- If no match exists, report the gap and propose remediation.

This describes-based verification must explicitly reference the linked `.excalidraw`
artifact and the source file(s) it describes.

## 8. Verification and Closeout

After the queue is complete:

1. Verify link integrity for changed docs.
2. Re-run `uv run doc-index`.
3. Summarize findings by severity and dimension.
4. Ask whether to run from the top again.
