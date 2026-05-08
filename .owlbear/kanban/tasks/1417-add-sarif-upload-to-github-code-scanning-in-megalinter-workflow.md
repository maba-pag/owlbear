---
id: 1417
title: Add SARIF upload to GitHub Code Scanning in MegaLinter workflow
status: research
priority: nice-to-have
created: 2026-05-07T23:28:57.957311+00:00
updated: 2026-05-07T23:29:18.927381+00:00
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

Add SARIF upload step (`github/codeql-action/upload-sarif`) after MegaLinter produces SARIF reports. This publishes findings to the GitHub Security tab for baseline tracking. See `.owlbear/research/1413-ci-sast-baseline.md` gap G2.

## Acceptance Criteria
P1: SARIF upload step added to MegaLinter workflow using `github/codeql-action/upload-sarif`
P2: Upload runs on `if: always()` so findings are recorded even on failure
P2: SARIF file path points to MegaLinter's generated SARIF output