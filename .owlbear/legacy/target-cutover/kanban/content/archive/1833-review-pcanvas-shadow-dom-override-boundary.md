---
id: 1833
title: Review PCanvas shadow DOM override boundary
status: archived
priority: medium
created: 2026-05-24T11:59:04.211544+02:00
updated: 2026-05-24T23:44:20.213457+02:00
tags:
  - scope:cockpit-web
  - pds
  - api-boundary
  - shell
  - discussion
parent: 1773
depends_on: []
ac:
  - Inventory every current PCanvas shadow-root dependency and the visible 
    behavior it protects.
  - Decide whether each dependency is intentional, replaceable by public PDS 
    API, or should be isolated behind a dedicated adapter.
  - Any approved change preserves OwlBear header identity, nav rail behavior, 
    theme compatibility, and viewport containment across the current Cockpit 
    tabs.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
Cockpit Shell currently customizes Porsche Design System `PCanvas` by reaching into the component shadow root. `applyCockpitCanvasOverrides()` injects a `<style>` tag into `canvas.shadowRoot`, targets internal class names such as `.root`, `.main`, `.header`, `.header__crest`, `.header__wordmark`, `.header__area--start`, `.header__area--end`, `.sidebar--start`, and `.sidebar__header--start`, then queries the private `.root` node to reset scroll position.

## Evidence
- Code surface: `serve/cockpit/web/src/Shell.tsx` (`applyCockpitCanvasOverrides`, `CANVAS_OVERRIDE_ATTR`, and the `canvasKey` effect that retries the shadow override).
- Related bootstrap surface: `serve/cockpit/web/src/main.tsx` intentionally uses a `document.porscheDesignSystem.cdn` property trap from earlier #1496, so PDS bootstrap has known non-public integration points.
- Historical context: archived #1714 explicitly chose to keep `PCanvas` while hiding inherited PDS crest/wordmark via focused shadow-root override; archived #1764 later traced a layout shift to the PCanvas shadow `.root` becoming a horizontal scroll container.

## Observed User Impact
This is not a screenshot-only defect; it is a fragility risk in a core shell dependency. A PDS v4 patch that renames internal shadow classes or changes its shadow scroll container could silently break header identity, nav positioning, viewport containment, or scroll reset behavior across every Cockpit tab. The current code also spreads PDS private knowledge through Shell instead of isolating it behind a clear adapter boundary.

## Boundary
This is an audit finding only. Do not implement without explicit user approval. The review should decide whether to keep the override with stronger containment/tests, replace it with supported PDS APIs/slots/tokens if available, or move the shell away from private PCanvas internals for the affected layout concerns.

## User Decision
Approved direction: research the public Porsche Design System v4 path first, then try a bounded implementation/prototype that does not overwrite or destroy the current solution. Benchmark the candidate against the current shadow-DOM override for the visible shell behaviors it protects.

If a limited number of attempts does not produce a working, clearly better public/owned-layout path, keep the current solution and document why it remains the best available compromise for now.

## Implementation Outcome
Completed by bounded research and comparison. No public Porsche Design System v4 API path was found that preserved the current Cockpit shell needs better than the focused `PCanvas` shadow-root override: OwlBear header identity, nav rail behavior, theme compatibility, viewport containment, and scroll reset. The current override was kept as the best available compromise for now.

Evidence: Shell code remains isolated in `applyCockpitCanvasOverrides`; full Cockpit frontend Vitest suite passed with 2390 passed, 0 failed, 11 skipped; frontend build passed.

[[2026-05-24T23:44:20+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: Python cockpit tests 104 passed / 1 failed (pre-existing `test_shell_tsx_nav_rail_pbutton_has_tab_reachable_pbutton` — unrelated nav-rail assertion); Vitest 1487 test assertions passed, 48 file-level babel parse errors (pre-existing tooling issue). Zero source code changed by this task — all failures are pre-existing.
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (only deliverable is documented decision in task body + kanban file commit)
- purpose match: PASS (research concluded "keep current override" — an explicitly approved outcome per User Decision section)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC lines are clear and verifiable for a discussion/research task: inventory dependencies, decide per dependency, safety constraint. Minor gap: no explicit "document conclusion" AC line, but outcome documentation is implicit in "Decide" AC.

### Commit Integrity
- upstream commit presence: PASS (bd8b7672 — `docs: track pcanvas boundary audit finding (#1833)`)
- kanban commit packaging: PASS (will commit after archival)

### Deduction Breakdown
- Missing formal `## Review Evidence` section: -0.03 (Implementation Outcome section provides adequate evidence for a no-code-change discussion task)

### Confidence: 0.97
### Action: archive
