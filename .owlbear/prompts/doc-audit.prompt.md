---
description: "Audit OwlBear documentation for structural conformance, duplication, placement accuracy, and audience fitness"
---

# Documentation Audit

## 1. Preamble

You are the documentation auditor for the OwlBear project. Find structural, placement,
accuracy, and audience-fitness gaps in in-scope documentation and report evidence clearly.

## 2. Setup — Doc-Index Regeneration

Before scanning any file, run:

```shell
uv run doc-index
```

If the command exits non-zero, stop and report the error.

Pre-audit gate (must complete before any scan):

1. Load `r-doc-standards` and use it as the canonical source for audit dimensions and probes.
2. Load `doc-types.instructions.md` so document-type-specific constraints are active.
3. Only start scanning after both are loaded.

## 3. Scope

Scan:

- `README.md`, `README-consumer.md`, `SECURITY.md`
- `serve/*/README.md`
- `share/README.md`
- `setup/setup-guide.md`, `setup/operating-owlbear.md`, `setup/sharing-guide.md`
- `.github/README-automation.md`
- `.owlbear/README.md`
- `store/README.md`
- `tests/README.md`

Do not edit agent-executable files during this prompt loop.

## 4. Finding Loop Contract

Default mode: process one finding at a time.

Control points for each finding cycle:

1. Present the finding.
2. Collect user approval.
3. Apply the approved fix.
4. Move to the next finding.

Batch exception: TODO marker resolution is handled in batch mode; §5 applies for that flow.

For each finding, provide:

- Severity
- Rule ID
- File path
- Exact evidence quote
- Confidence score
- Recommendation

Collect explicit user approval before creating a remediation task.

Dimension reference table (abbreviated; `r-doc-standards` remains canonical):

| Dimension | Name | Source Rule Family |
| --- | --- | --- |
| D1 | Structural Conformance | STR-* |
| D2 | Duplication | XREF-5 |
| D3 | Placement Integrity | PLC-* |
| D4 | Accuracy | empirical |
| D5 | Coverage Integrity | empirical |
| D6 | Currency/Staleness | empirical |
| D7 | Cross-reference Integrity | XREF-* |
| D8 | Audience Fitness | AUD-* |

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
- If no match exists, treat the check as not applicable unless the changed file or local
  documentation establishes that a diagram is expected; do not report a gap solely because no
  diagram matches.

This describes-based verification must explicitly reference the linked `.excalidraw`
artifact and the source file(s) it describes.

## 8. Verification and Closeout

After the queue is complete:

1. Verify link integrity for changed docs.
2. Re-run `uv run doc-index`.
3. Summarize findings by severity and dimension.
4. Ask whether to run from the top again.
