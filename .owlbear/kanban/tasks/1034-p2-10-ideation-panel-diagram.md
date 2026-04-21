---
id: 1034
title: 'P2-10: Ideation panel diagram'
status: in-progress
priority: important
created: 2026-04-19T23:53:28.594403+00:00
updated: 2026-04-20T22:46:11.685237+00:00
tags:
- phase-2
- docs-currency
- docs-diagram
- type:docs
parent: 1016
depends_on:
- 1024
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #1016

## Acceptance Criteria

- [ ] `share/diagrams/ideation.excalidraw` created (valid Excalidraw JSON, target path overrides `h-excalidraw-diagram` default scratch delivery)
- [ ] Diagram shows the ideation flow with these structural elements:
  - Step 0 (Setup & Entry) as a precondition, then 6 moments M1–M6 as the primary timeline
  - Mediator (ideator agent) as the orchestrator, with two behavioral modes: Investigator (M1–M3) and Facilitative (M4–M6)
  - 6 panelist roles: Critic, Architect, Modeler, End User, Skeptic, Pragmatist — invoked as parallel batch between M3 and M4
  - Critic-loop protocol: each domain panelist invokes the Critic ≤5 cycles; Critic also runs standalone at M1, M2, M4, M5 boundaries
  - Pragmatist synthesis after domain panelists complete
  - Brief output (M5) and handoff to pipeline (M6: kanban parent task → planner decomposition)
- [ ] `.excalidraw` JSON contains top-level `"describes"` field with glob list: `["share/skills/w-ideation/**", "share/skills/h-ideation-panel/**", "share/agents/ideator.agent.md", "share/agents/ideation-*.agent.md"]` (doc-index tool extracts this automatically)
- [ ] Footer text element: `Last verified: YYYY-MM-DD (commit-hash)` — maintained by doc-writer during future passes
- [ ] Diagram is descriptive, not authoritative (documents current behavior; authority is the skill files)
- [ ] Follows `h-excalidraw-diagram` skill conventions (grid alignment, color-as-meaning, text sizing, bound arrows, quality checklist)

## Files

- Creates: `share/diagrams/ideation.excalidraw`
- Modifies: `.owlbear/doc-index.md` (auto-regen via `uv run doc-index`)

## Builder Guidance

- Authority sources for diagram content: `share/skills/w-ideation/SKILL.md` (moment definitions), `share/skills/h-ideation-panel/SKILL.md` (panelist roster, Critic-loop, selection logic)
- The Critic is the most structurally connected panelist — it appears both inside domain panelist loops AND at standalone boundary checks. Give it visual prominence.
- Layout recommendation: flowchart pattern for M1–M6 timeline; fan-out from M3→M4 gap for the parallel panelist deliberation phase; cycle pattern for Critic-loop
[[2026-04-20]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Creates one diagram file; doc-index regen is existing tool side-effect |
| Interface clarity | PASS (after REFINE) | Original AC had factual errors; corrected moment numbering, panelist roster, describes field location, delivery path |
| Dependency correctness | PASS | #1024 (doc-writer v2) archived/done; doc-index .excalidraw + describes support confirmed in code |
| Module layering | PASS | N/A — diagram file only, no code changes |
| TDD compliance | PASS | Tagged `type:docs` for test-writer pass-through (no testable Python code) |
| KISS/YAGNI | PASS | Minimal scope — one diagram |
| Premise challenge | PASS | Ideation system is complex (6 moments, 6 panelists, Critic loops); diagram justified for comprehension |
| Pattern consistency | PASS | Follows h-excalidraw-diagram conventions; first diagram but tooling infrastructure exists |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Documentation domain only |

### AC Refinements Applied

1. **Moment numbering M0-M5 → M1-M6**: Authority doc w-ideation/SKILL.md defines Steps 1-6 as M1-M6; Step 0 is setup with no M prefix
2. **Added Critic to panelist list**: h-ideation-panel/SKILL.md defines 6 panelists; AC had only 5 (omitted Critic — the most structurally significant role)
3. **Added Mediator role**: The ideator agent orchestrates the entire flow with two behavioral modes; was absent from original AC
4. **Clarified `describes` field**: Now specifies it's a JSON field in the .excalidraw file (not a doc-index metadata field); doc-index extracts it automatically
5. **Clarified delivery path**: AC1 now notes target path overrides h-excalidraw-diagram default scratch delivery
6. **Added `type:docs` tag**: Pass-through tag for test-writer (no testable Python code)
7. **Added Builder Guidance section**: Layout recommendation, authority source pointers, Critic visual prominence note

### Challenge Results

- Challenger: **block** (confidence 0.30) — identified critical AC errors: wrong moment numbering, missing Critic panelist, missing Mediator
- Architect response: **accepted** — all critical findings verified against authority docs and corrected in AC

### Verdict: REFINE → APPROVE
### Action Taken: Corrected AC factual errors, added type:docs tag, added builder guidance, advanced to todo
[[2026-04-20]]
## Test-Writer Notes
- Non-implementation task (tagged `type:docs`) — no tests applicable.
- AC is entirely about creating `share/diagrams/ideation.excalidraw` (Excalidraw JSON diagram) and regenerating `doc-index.md`.
- No Python interfaces, functions, or modules to test.
- Passing through to builder.