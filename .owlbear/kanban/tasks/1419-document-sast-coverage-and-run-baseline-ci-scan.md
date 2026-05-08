---
id: 1419
title: Document SAST coverage and run baseline CI scan
status: in-progress
priority: nice-to-have
created: 2026-05-07T23:29:18.911471+00:00
updated: 2026-05-08T16:21:59.245131+00:00
tags:
- scope:infra
- type:docs
parent: 1413
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Create `.owlbear/sast-coverage.md` documenting CI/SAST tooling: tool coverage matrix, suppression rationale, baseline evidence. Content source: `.owlbear/research/1419-sast-coverage.md` sections 3–5.
See `.owlbear/research/1413-ci-sast-baseline.md` gap G5 and follow-up item 6.

## Acceptance Criteria
P2: `.owlbear/sast-coverage.md` contains a tool coverage matrix listing Ruff S-rules, Gitleaks, DevSkim, and Trivy with category, scan scope, and determinism for each (td:0)
P2: Same document contains a table of all production `noqa` S-rule suppressions with rule code, affected file(s), count, and justification (td:0)
P3: Same document records MegaLinter baseline evidence: CI trigger configuration and confirmation that baseline runs have executed (td:0)

## Research
- Research doc: .owlbear/research/1419-sast-coverage.md
- Sources: 6 studied (all local — configs, codebase, git history), 5 high-relevance
- Recommendation: T1 autonomous — documentation of existing state (confidence: 0.85)

### Key findings
- 4 security scanning tools active: Ruff S-rules, Gitleaks, DevSkim, Trivy
- 26 inline noqa S-rule suppressions in production code + 1 global (S101) — all justified
- S608 (SQL formatting) accounts for 15/26 — all use parameterized values with trusted table/column names
- MegaLinter baseline exists: 5+ runs triggered via push to origin/dev since trigger addition, 2 merged megalinter-fixes PRs confirm execution
- No follow-up tasks created — documentation is complete, baseline is established

## Architecture Review
**Verdict:** APPROVED
- Output: `.owlbear/sast-coverage.md` (dev-only ops doc, not synced to main)
- All td:0 — Test-writer: SKIP
- Builder: promote research doc sections 3–5 into the target file; adapt formatting as needed
- This doc is a prerequisite for the reviewer rewrite (Brief D2→B1 in `draft-pipeline-review-rethink`)

[[2026-05-08]]
## Architecture Review
**Verdict:** APPROVED → todo

**AC Assessment:**
| AC Line | Assessment | Action |
|---------|-----------|--------|
| P2: Tool coverage matrix | Verifiable but lacked output location | Refined: target `.owlbear/sast-coverage.md` |
| P2: Suppression rationale | Verifiable but lacked output location | Refined: same target file |
| P3: MegaLinter baseline | Already satisfied per research | Refined: document baseline evidence |

**Architecture Notes:**
- Documentation-only task — no code, no interfaces, no dependencies
- Output: `.owlbear/sast-coverage.md` (dev-only ops doc, not synced to main)
- Research doc sections 3–5 contain all content; builder promotes into persistent doc
- Added `type:docs` tag for test-writer pass-through
- All td:0 — Test-writer: SKIP
- Prerequisite for reviewer rewrite (Brief D2→B1 in `draft-pipeline-review-rethink`)
- Challenger: skipped (all td:0)
[[2026-05-08]]
## Test-Writer Notes
- Non-implementation task (tagged type:docs) — no tests applicable.
- All AC lines annotated td:0; architecture review explicitly flagged Test-writer: SKIP.
- Passing through to builder.