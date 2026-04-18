---
id: 971
title: Run React Compiler validation spike when memoization trigger is met
status: research
priority: nice-to-have
created: 2026-04-18T17:00:32.289510+00:00
updated: 2026-04-18T17:41:12.955817+00:00
tags:
- cockpit
- frontend
- phase-2
parent:
depends_on: []
blocked: true
block_reason: 'Trigger unmet: only 2 memo-wrapped components (Card, Column in KanbanBoard.tsx)
  + hook-level memoization in KanbanBoard parent. Need ≥5 memoized components. #963
  in review. Re-check after more cockpit components are built.'
claimed_by:
claimed_at:
---
## Objective

Execute the React Compiler enablement spike when the cockpit reaches ≥5 components with active memoization (manual React.memo/useMemo/useCallback).

## Trigger

Activate when EITHER:
- Task #963 (KanbanBoard memos) lands AND component count grows, OR
- Performance profiling shows re-render overhead warranting compiler adoption

## Context

Research #970 validated PDS interop risk as LOW (confidence: 0.85). Shell.tsx patterns follow Rules of React — callback refs, useEffect with custom events, and PDS custom elements are all safe for compiler optimization. See `.owlbear/research/970-react-compiler-pds-interop.md`.

## Acceptance Criteria

- [ ] `npm install -D babel-plugin-react-compiler` in serve/cockpit/web/
- [ ] Update vite.config.ts: `react({ babel: { plugins: ['babel-plugin-react-compiler'] } })`
- [ ] Vitest suite passes (all tests green)
- [ ] Playwright E2E suite passes (smoke.spec.ts)
- [ ] Shell.tsx tab switching verified (imperative ref + tabChange event)
- [ ] Check React DevTools for "Memo ✨" badge
- [ ] Remove redundant manual React.memo/useMemo/useCallback
- [ ] Document any `"use no memo"` opt-outs needed
- [ ] Assess Vitest coverage impact — adjust thresholds if compiler-generated branches cause drop
[[2026-04-18]]
## Research

### Trigger Assessment (2026-04-18)

**Current memoization inventory:**

| Component | memo() | useMemo | useCallback |
|-----------|--------|---------|-------------|
| Card | ✓ | — | — |
| Column | ✓ | ✓ (sorted) | — |
| KanbanBoard | — | ✓ (tasksByStatus) | ✓ (handleContextMenu) |

**Distinct memoized components: 2–3** (depending on whether hook-only counts)
**Threshold: ≥5**
**Verdict: DEFERRED** — trigger condition not met.

#963 memos have landed in source but task still in review pipeline. No other cockpit components use memoization yet. Re-activate when cockpit grows to ≥5 components with active memo patterns (e.g., after TaskDetail, FilterBar, or other feature components are added).