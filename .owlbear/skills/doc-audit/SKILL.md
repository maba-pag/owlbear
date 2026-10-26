---
name: doc-audit
description: "Workflow: Audit OwlBear documentation for structural conformance, duplication, placement accuracy, and audience fitness"
argument-hint: "Optional: one document or a subset of the scope below"
user-invocable: true
disable-model-invocation: true
---

# Documentation Audit

## 1. Preamble

You are the documentation auditor for the OwlBear project. Find structural, placement,
accuracy, and audience-fitness gaps in in-scope documentation and report evidence clearly. The owner
invokes this skill by name; text supplied with the invocation narrows the scope.

## 2. Setup

Find documents, headings and links with plain search (`rg`, file search); OwlBear keeps no generated
document index. Read each document before reporting on it.

Pre-audit gate (must complete before any scan):

1. Load `r-doc-standards` and use it as the canonical source for audit dimensions and probes.
2. Load `doc-types.instructions.md` so document-type-specific constraints are active.
3. Only start scanning after both are loaded.

## 3. Scope

Scan:

- `README.md`, `CONTRIBUTING.md`, `SECURITY.md`
- `serve/*/README.md`
- `share/README.md`
- `setup/setup-guide.md`, `setup/operating-owlbear.md`, `setup/sharing-guide.md`
- `.github/README-automation.md`
- `.owlbear/README.md`
- `store/README.md`
- `tests/README.md`

Do not edit agent-executable files (agents, skills, instructions, scripts, workflows, source)
during this audit. Edit only in-scope documentation, and only for a finding the owner approved.

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

## 6. Verification and Closeout

After the queue is complete:

1. Verify link integrity for changed docs.
2. Summarize findings by severity and dimension.
3. Ask whether to run from the top again.
