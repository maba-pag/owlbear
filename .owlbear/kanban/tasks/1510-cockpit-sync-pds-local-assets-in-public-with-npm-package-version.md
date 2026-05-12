---
id: 1510
title: 'Cockpit: Sync PDS local assets in public/ with npm package version'
status: in-progress
priority: important
created: 2026-05-12T09:09:32.883043+00:00
updated: 2026-05-12T16:55:25.911314+00:00
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
archival_reason:
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