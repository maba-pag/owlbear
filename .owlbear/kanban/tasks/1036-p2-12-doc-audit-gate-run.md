---
id: 1036
title: 'P2-12: doc-audit gate run'
status: backlog
priority: important
created: 2026-04-19T23:53:48.225574+00:00
updated: 2026-04-19T23:53:48.225574+00:00
tags:
- phase-2
- docs-currency
parent: 1016
depends_on:
- 1025
- 1026
- 1027
- 1028
- 1029
- 1030
- 1031
- 1032
- 1033
- 1034
- 1035
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #1016

## Acceptance Criteria

- [ ] `doc-audit.prompt.md` invoked against the full repo
- [ ] Doc-index regenerated successfully at audit start (hard requirement — audit fails on regen failure)
- [ ] Pre-scan summary reviewed: finding counts per area, estimated time
- [ ] Zero critical or high-severity findings remaining across all IN-scope files
- [ ] Any medium/low findings logged as follow-up kanban tasks
- [ ] All ~25 IN-scope files pass structural checks per `r-doc-standards`
- [ ] All 7 diagrams have current `Last verified` footers matching recent commits
- [ ] Cross-reference integrity: all outbound links from IN-scope files resolve
- [ ] Sweep working-doc (`.owlbear/scratch/docs-sweep-checklist.md`) deleted after gate passes

## Files

- Reference: all IN-scope files per Brief section 3
- Deletes: `.owlbear/scratch/docs-sweep-checklist.md` (ephemeral sweep artifact)

## Notes

This is the final acceptance gate for the entire documentation-currency project. All sweep and diagram tasks must be complete before this runs. Pure verification — no TDD pairing.