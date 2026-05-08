---
id: 1419
title: Document SAST coverage and run baseline CI scan
status: backlog
priority: nice-to-have
created: 2026-05-07T23:29:18.911471+00:00
updated: 2026-05-08T07:00:26.153986+00:00
tags:
- scope:infra
parent: 1413
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Create documentation for the CI/SAST tooling: tool coverage matrix, suppression rationale, scan scope. Then run the MegaLinter workflow on dev branch and save the report as the baseline.
See `.owlbear/research/1413-ci-sast-baseline.md` gap G5 and follow-up item 6.

## Acceptance Criteria
P2: Documentation lists all security scanning tools (Ruff S-rules, Gitleaks, DevSkim, Trivy) with what each covers
P2: Production `noqa` S-rule suppressions are documented with rationale
P3: MegaLinter workflow has been run at least once on dev branch (baseline established)
[[2026-05-08]]
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