---
id: 1510
title: 'Cockpit: Sync PDS local assets in public/ with npm package version'
status: archived
priority: medium
created: 2026-05-12T09:09:32.883043+00:00
updated: 2026-05-12T19:24:24.791553+00:00
tags:
  - cockpit
  - frontend
  - bug
  - research
parent: 1495
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## Problem\n\nThe PDS npm package is at v4.1.0 but `public/porsche-design-system/components/` contains v4.0.0 core chunk. Additionally `public/porsche-design-system/icons/` has only 1 icon file when more are needed (e.g. `close.eec3c5d.svg` is missing). This causes:\n\n1. **404s** for the core chunk (version mismatch between loader and local assets)\n2. **CDN CSP violations** for icon assets that fall back to CDN fetch when not found locally\n\n## Acceptance Criteria\n\n- [ ] Research how PDS assets are structured in `node_modules/@porsche-design-system/` and what files must be copied to `public/`\n- [ ] Identify the complete set of required icon SVGs beyond what is currently present\n- [ ] Determine whether a build script (npm `postinstall` or Vite plugin) or manual copy is the right approach\n- [ ] Produce follow-up kanban tasks for implementation (asset sync script/plugin + verification)
2026-05-12T15:50:49+00:00
## Planning

Research complete. Created 2 follow-up tasks at research:

| ID | Title | Priority | Tags | Parent | Depends on |
|----|-------|----------|------|--------|------------|
| #1511 | Cockpit: Implement PDS asset sync script | important | cockpit, frontend, bug | #1495 | — |
| #1512 | Cockpit: Add PDS asset version check to build | nice-to-have | cockpit, frontend, cleanup | #1495 | #1511 |

Dependency graph: #1512 → #1511 (version check requires sync script to exist first).

Both tasks reference `.owlbear/research/1510-pds-asset-sync.md` for full analysis.
2026-05-12T15:51:09+00:00
## Research
- Research doc: .owlbear/research/1510-pds-asset-sync.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: Node.js sync script + committed assets (confidence: 0.82)
- Follow-up tasks: #1511 (implement sync script), #1512 (build-time version check)
- Challenge: FALLBACK — subagent unavailable
2026-05-12T16:15:05+00:00
## Architecture Review

**Verdict:** APPROVE — research task, all deliverables produced.

**Proof bundle:** skip
**Test-writer:** SKIP (research tag → pass-through)

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| Research PDS asset structure | Done — research doc §3 Finding 1-3 covers npm package contents, CDN structure, chunk mapping | None |
| Identify required icon SVGs | Done — 290 icons identified from icon chunk mapping (§3 Finding 2) | None |
| Determine approach | Done — trade-off matrix of 4 options, Option A selected (sync script + committed assets, confidence 0.82) | None |
| Produce follow-up tasks | Done — #1511 (sync script, important) and #1512 (version check, nice-to-have) created with dependency graph | None |

### Architecture Notes

- Research validated against codebase: `package.json` has PDS v4.1.0, `public/` has ~52 component chunks (v4.0.0 hashes) and only 1 icon SVG — confirms the problem statement.
- Recommended approach (Node.js sync script + committed assets) aligns with OwlBear's offline-first architecture and KISS principle. ~1 MB git footprint acceptable given existing 783 KB baseline.
- Follow-up decomposition is clean: #1511 is the core fix (sync script), #1512 is an optional guard (version check). Dependency #1512 → #1511 is correct.
- No `postinstall` or Vite plugin for asset sync exists — greenfield for follow-up tasks.

### Dependency Analysis

- No dependencies on this task. Parent #1495 is the cockpit umbrella.
- Follow-up tasks #1511 and #1512 are at `research` status and will flow through the pipeline independently.

### Challenge

Skipped per proof-bundle=skip rule (Step 2.1).

### Non-implementation tagging

Added `research` tag for test-writer pass-through.
2026-05-12T16:55:25+00:00
## Test-Writer Notes
- Non-implementation task (tagged research) — no tests applicable.
- Proof bundle: skip confirmed in Architecture Review.
- Passing through to builder.
2026-05-12T17:08:26+00:00
## Builder Notes
- Routing: Non-implementation pass-through confirmed from upstream notes (`Proof bundle: skip`, `Test-writer: SKIP`, task tagged `research`).
- Implementation: No code changes required for this task.
- Verification: No `TestFromAC_*` gate required under `Proof bundle: skip`; no additional proof command mandated in task body.
- Files changed: none.
- Lint/tests/coverage: not applicable for this research pass-through.
- Evidence summary: AC deliverables already completed in research artifact `.owlbear/research/1510-pds-asset-sync.md` and follow-up tasks #1511/#1512 are created as implementation handoff.
2026-05-12T17:48:13+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1510 -> docs | AC mapped to research deliverables and evidence sufficient.
- AC evidence map:

| AC Line | Evidence | Status |
|---|---|---|
| Research PDS asset structure and required files | `.owlbear/research/1510-pds-asset-sync.md:27-56` documents the npm-package/CDN split, the v4.1.0 asset inventory, and deterministic extraction from the core/icon chunks. Workspace cross-checks matched `serve/cockpit/web/package.json:19-20`, `serve/cockpit/web/public/porsche-design-system/components/` (59 `.js` files including `porsche-design-system.v4.0.0.9faf55bc815263bee13d.js`), and `serve/cockpit/web/public/porsche-design-system/icons/list.411dd00.svg`. | PASS |
| Identify the complete set of required icon SVGs | `.owlbear/research/1510-pds-asset-sync.md:40,49,79` records 290 SVGs sourced from the icon chunk's full name→filename map, and the implementation handoff preserves that requirement in `.owlbear/kanban/tasks/1511-cockpit-implement-pds-asset-sync-script.md:33,89,92`. | PASS |
| Determine the right approach (build script/postinstall/Vite/manual) | `.owlbear/research/1510-pds-asset-sync.md:58-84` compares the four options and recommends a Node.js sync script plus committed assets. Current Cockpit config shows no existing sync hook in `serve/cockpit/web/package.json` and only the existing CSP Vite plugin in `serve/cockpit/web/vite.config.ts:5,23`, so the recommendation matches the live workspace. | PASS |
| Produce follow-up kanban tasks for implementation and verification | `.owlbear/kanban/tasks/1511-cockpit-implement-pds-asset-sync-script.md:30-37,86-92` defines the sync-script implementation task, and `.owlbear/kanban/tasks/1512-cockpit-add-pds-asset-version-check-to-build.md:31-33` defines the build/dev version-check verification task. Both exist and are concrete enough for downstream implementation flow. | PASS |

- Blocking findings: none.
- Safety/security check: no executable code or dependency changes were made on #1510; the task is research-only, and the recommendation keeps assets local rather than widening CDN reliance at runtime.

## Observations
- Non-blocking: the Architecture Review note on #1510 says `~52 component chunks`, while the research doc and task #1511 consistently use the validated 58 component-chunk / 59 total JS-file figures. The follow-up tasks encode the correct counts, so this does not block approval.
2026-05-12T18:32:22+00:00
## Docs Gate

**Verdict:** PASS — no docs impact, all checklist items verified.

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | N/A | No code files changed (research pass-through). Convention mapping yields no README targets. |
| 2. External Attribution | PASS | `.owlbear/sources/overview.md` lines 52–58: 3 sources added under "PDS Asset Sync Research (Task #1510)" — CDN core chunk, icon chunk, and vue-offline sample repo. |
| 3. Research Doc | PASS | `.owlbear/research/1510-pds-asset-sync.md` line 3 contains owning task link; task body (Research section) cross-references the doc by path. |
| 4. Deletion Detection | N/A | No files deleted. No orphaned references. |

### Files Updated
None — research-only task, no docs drift detected.

### Scratch Cleanup
No `.owlbear/scratch/1510-*` files found.
2026-05-12T19:24:24+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: 4393 passed, 20 failed (all pre-existing in unrelated modules: cockpit_view, ideation_diagram, server, engine_accessor_migration, list_sessions), lint clean\n- 20 failures are in domains unrelated to #1510 (research task, zero code changes). No regressions attributable to this task.\n- regression verdict: PASS\n\n### Research Task Verification\n- Research doc: `.owlbear/research/1510-pds-asset-sync.md` exists with owning task link ✓\n- Follow-up tasks: #1511 (todo, important) and #1512 (archived as duplicate → #1513) ✓\n- Follow-ups reference research doc ✓\n- Verdict: PASS\n\n### Intent Verification\n- scope alignment: PASS (research deliverables only — doc + follow-up tasks, no code changes)\n- purpose match: PASS (researched PDS asset structure, identified 349 required assets, recommended sync approach, created follow-up tasks)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 4/5\nAC was specific with 4 clear research deliverables. Minor gap: follow-up task priority/tags not specified in AC, but naturally resolved downstream.\n\n### Commit Integrity\n- upstream commit presence: PASS (eb48e411 — research doc; d0bd2898 — sources)\n- kanban commit packaging: pending (this audit cycle)\n\n### Deduction Breakdown\nNo deductions applied.\n\n### Confidence: 1.00\n### Action: archive