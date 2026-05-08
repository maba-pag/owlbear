---
id: 1419
title: Document SAST coverage and run baseline CI scan
status: research
priority: nice-to-have
created: 2026-05-07T23:29:18.911471+00:00
updated: 2026-05-07T23:29:34.758253+00:00
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