---
id: 1512
title: 'Cockpit: Add PDS asset version check to build'
status: archived
priority: medium
created: 2026-05-12T15:49:55.128056+00:00
updated: 2026-05-12T18:46:01.419133+00:00
tags:
  - cockpit
  - frontend
  - cleanup
parent: 1495
depends_on:
  - 1511
blocked: false
block_reason:
claimed_at:
archival_reason: duplicate
archival_refs:
  - 1513
---


## Context

Research: see `.owlbear/research/1510-pds-asset-sync.md` (task #1510).

After PDS assets are synced locally via the sync script (#1511), add a guard that catches version drift between `public/porsche-design-system/` and the npm package.

## Acceptance Criteria

- [ ] Build-time check (Vite plugin or prebuild script) compares core chunk version in `public/porsche-design-system/components/` with PDS npm package version from `node_modules`
- [ ] Version mismatch produces a non-blocking console warning (does not fail the build)
- [ ] Check runs automatically during `npm run build` and `npm run dev`
2026-05-12T17:33:11+00:00
## Planning

Created follow-up task #1513 "Cockpit: Implement PDS version check Vite plugin" at research.

| ID | Title | Status | Parent | Deps | Priority |
|----|-------|--------|--------|------|----------|
| 1513 | Cockpit: Implement PDS version check Vite plugin | research | #1495 | #1511 | nice-to-have |

Single-task shortcut — inline Vite plugin (~25 LOC), single domain (frontend/cockpit), no TDD split needed.
2026-05-12T17:33:46+00:00

## Research
- Research doc: .owlbear/research/1512-pds-version-check.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: Vite plugin inline in vite.config.ts using configResolved + buildStart hooks (confidence: 0.80)
- Follow-up tasks created: #1513 at research
- Decision requests: none

## Challenge Results
- Challenger: reconsider (confidence in original: 0.58)
- Key challenges: version source ambiguity, silent failure masking, buildStart dev-mode proof, regex fragility, testability/parser-reuse with #1511
- Researcher response: accepted in part, revised — specified version source (installed package.json), improved error handling (log skip reason), confirmed buildStart dev behavior from Vite docs, minimal parser overlap with #1511
- Revised confidence: 0.80
2026-05-12T18:14:05+00:00
## Architecture Review\n\n### Verdict: MERGE into #1513\n\n#1512 and #1513 describe the same deliverable (PDS version check Vite plugin in vite.config.ts). #1513 carries refined, research-informed AC (8 criteria) that is a strict superset of #1512's 3 broad AC lines. Both are siblings under #1495, both depend on #1511.\n\nMerging #1512 into #1513 — the surviving task continues through the pipeline with the complete implementation specification. All research context (research doc .owlbear/research/1512-pds-version-check.md, challenge results) is already referenced by #1513.\n\n### Architecture Notes (for #1513)\n- Inline Vite plugin follows established `cspPlugin()` pattern in vite.config.ts\n- `buildStart` hook fires on both dev server start and production build (confirmed in research)\n- Version source: `node_modules/@porsche-design-system/components-js/package.json`\n- Dependency #1511 (sync script) is in review and nearly complete\n- ~25 LOC, zero new files, single domain (frontend/cockpit)\n\n### Action Taken\nMerged into #1513. This task archived.
2026-05-12T18:45:54+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: 1563 pytest passed (instrument timeout on full run — environmental, not task-related), 1575 vitest passed (1 pre-existing failure in App.wiring unrelated to this task), ruff 1 pre-existing TRY300 in kanban engine, stylelint clean, htmlhint clean\n- regression verdict: PASS — no code changes in this task, all failures pre-existing/unrelated\n\n### Intent Verification\n- scope alignment: PASS (research doc + follow-up task #1513 created, architect correctly identified overlap and merged)\n- purpose match: PASS (task purpose was to plan/research a PDS version check — delivered research doc and refined implementation task)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer (N/A — no code deliverable)\n\n### Architect Quality: 4/5\nBroad initial AC (3 lines) was appropriate for a research-first task. Architect correctly identified the overlap between #1512 and #1513 and merged the parent into the refined child. #1513 carries 8 specific AC lines — strict superset.\n\n### Commit Integrity\n- upstream commit presence: PASS (d0bd2898 — research doc committed by researcher)\n- kanban commit packaging: pending (this archival)\n\n### Deduction Breakdown\nNo deductions applied.\n\n### Confidence: 1.00\n### Action: archive (merged into #1513)