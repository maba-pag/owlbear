---
id: 970
title: Enable React Compiler with PDS interop validation spike
status: archived
priority: nice-to-have
created: 2026-04-18T16:42:45.224158+00:00
updated: 2026-04-18T19:35:23.373306+00:00
tags:
- cockpit
- frontend
- phase-2
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

When the cockpit reaches ≥5 memoizable components, enable babel-plugin-react-compiler and validate PDS Web Component interop.

## Context

Research #969 evaluated React Compiler (1.0.0 stable) vs manual memoization. Recommended deferring adoption until component count justifies it. Key unknown: compiler behavior with PDS custom elements (p-tabs, p-icon), imperative refs (`setAttribute`), and custom DOM events (`tabChange` in Shell.tsx).

## Acceptance Criteria

- [ ] Add `babel-plugin-react-compiler` to vite.config.ts (3 LOC)
- [ ] Run full Vitest suite — all tests pass
- [ ] Run Playwright E2E suite — all tests pass
- [ ] Verify Shell.tsx tab switching works (imperative ref + custom event pattern)
- [ ] Remove any manual React.memo/useMemo/useCallback that become redundant
- [ ] Document any `"use no memo"` opt-outs needed for PDS interop

## Trigger

Activate this task when phase-2 cockpit reaches ≥5 components with memoization needs. See .owlbear/research/969-react-compiler-evaluation.md.
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/970-react-compiler-pds-interop.md
- Sources: 10 studied, 6 high-relevance (≥0.85)
- Recommendation: Keep deferred — trigger not met (0 manual memos, 0 perf issues). PDS interop risk is LOW. (confidence: 0.85)
- Follow-up tasks created: #971 (validation spike when trigger met) at research
- Decision requests: none
- Challenge: FALLBACK — subagent unavailable
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Focused on one concern: enable React Compiler + validate PDS interop |
| Interface clarity | PASS | AC lines are specific (vite.config.ts change, test suites, Shell.tsx verification) |
| Dependency correctness | FAIL | No dependency on #963 (manual memos), yet trigger requires memos to exist first |
| Module layering | PASS | Build-tool-level change, no layering concerns |
| TDD compliance | N/A | Validation spike, not a traditional implementation task |
| KISS/YAGNI | FAIL | Solves a problem that does not yet exist — 0 manual memos, 0 perf issues |
| Premise challenge | FAIL | Task's own research recommends "Keep deferred — trigger not met." Follow-up #971 already captures this work with better-scoped AC (9 items vs 6) |
| Pattern consistency | PASS | Follows existing Vite plugin pattern |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Frontend/build domain only |

### Key Evidence

- Research doc (.owlbear/research/970-react-compiler-pds-interop.md) explicitly recommends: "Keep task deferred. Trigger condition not yet met."
- Trigger section: "Activate when phase-2 cockpit reaches ≥5 components with memoization needs"
- Current state: 0 manual React.memo/useMemo/useCallback in source code (all 50 grep hits are in test file KanbanBoard_963.test.tsx for unimplemented #963)
- Task #963 (planned 4 manual memos) has not landed — tests exist but implementation does not
- Follow-up #971 ("Run React Compiler validation spike when memoization trigger is met") already exists at research status with more detailed AC (9 criteria including Vitest coverage impact assessment)

### Duplicate Analysis

# 970 and #971 overlap significantly. #970 served its purpose as the research vehicle — producing the interop analysis doc and spawning #971 with refined AC. #971 is the proper vehicle for this work when the trigger is met

### Verdict: REJECT

### Action Taken: Returned to research. Trigger condition (≥5 memoizable components) is unmet — 0 manual memos exist today. #971 already captures the deferred work with better-scoped AC. This task should remain dormant until #963 lands AND component count grows, at which point #971 is the task to activate

[[2026-04-18]]

## Research (validation pass)

- Research doc: .owlbear/research/970-react-compiler-pds-interop.md (§6 added)
- Sources: 10 studied (8 external logged in sources/overview.md), 6 high-relevance (≥0.85)
- Recommendation: Keep deferred — trigger approaching but not met. #970 superseded by #971. PDS interop risk LOW. (confidence: 0.80)
- Follow-up tasks created: none new — #971 already exists. Added trigger refinement recommendation to research doc §5.3.
- Decision requests: none (T1 — autonomous disposition)
- Attribution: 8 external sources added to .owlbear/sources/overview.md

## Challenge Results

- Challenger: **reconsider** (confidence in original: 0.60)
- Key challenges: C1 (trigger text ambiguous — "needs" vs "has"), C2 (#971 trigger unbounded), B3 (OR trigger arm unevaluated)
- Researcher response: accepted C1/C2/B3 — revised confidence 0.85→0.80, added trigger refinement follow-up, documented OR arm status

## Disposition

# 970 served its purpose as the research vehicle: produced PDS interop analysis doc + spawned #971 with better-scoped AC. State has changed (#963 landed, 5 manual memos exist) but trigger still not met under any reading (3-4/5 memoizable components). Recommend archival — #971 is the canonical tracker

[[2026-04-18]]

## Architecture Review (2nd pass)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Focused scope |
| Interface clarity | PASS | AC lines are specific |
| Dependency correctness | FAIL | No dependency on trigger condition being met |
| Module layering | PASS | Build-tool level |
| TDD compliance | N/A | Validation spike |
| KISS/YAGNI | FAIL | Trigger unmet (2–3/5 memoized components); solves a problem that doesn't exist yet |
| Premise challenge | FAIL | #971 supersedes this task with better-scoped AC (9 vs 6 criteria). Task's own disposition recommends archival |
| Pattern consistency | PASS | Follows Vite plugin pattern |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Frontend only |

### Key Evidence

- Disposition section (appended by researcher): "Recommend archival — #971 is the canonical tracker"
- #971 exists at research (blocked, trigger unmet) with expanded AC including Vitest coverage impact assessment
- Memoization inventory: Card (memo), Column (memo+useMemo), KanbanBoard (useMemo+useCallback) = 2–3 distinct memoized components vs ≥5 threshold
- No state change since previous rejection — trigger still unmet

### Challenge Results

- Challenge: SKIPPED — REJECT verdict, no challenge required per protocol

### Verdict: REJECT

### Action Taken: Returned to research. **Recommend archival.** #970 completed its lifecycle purpose: produced .owlbear/research/970-react-compiler-pds-interop.md and spawned #971 with superior AC. Re-processing this task further is wasted pipeline cycles — #971 is the canonical vehicle for React Compiler enablement when the trigger is met

[[2026-04-18]]

## Research (final validation — 2026-04-18)

- Research doc: .owlbear/research/970-react-compiler-pds-interop.md (validated, current)
- Sources: 10 studied, 6 high-relevance (≥0.85)
- Recommendation: **Archive #970 — lifecycle complete.** PDS interop risk LOW (confidence: 0.85). Trigger (≥5 memoized components) still unmet: 3 memoized (Card, Column, KanbanBoard), 2 new stubs (DetailTab, ActivityTab) not yet implemented. #971 is the canonical tracker.
- Follow-up tasks: #971 (blocked, trigger unmet) — no new tasks needed
- Decision requests: none
- Challenge: N/A (validation pass, no new recommendation)

**Codebase delta since last pass:** DetailTab.tsx and ActivityTab.tsx added as RED-phase stubs (task #935). Neither uses memoization. No change to trigger assessment.
[[2026-04-18]]

## Architecture Review (3rd pass — final)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Focused scope |
| Interface clarity | PASS | AC lines are specific |
| Dependency correctness | FAIL | Trigger (≥5 memoized components) still unmet |
| KISS/YAGNI | FAIL | No problem to solve — 3 memoized components vs ≥5 threshold |
| Premise challenge | FAIL | #971 supersedes with better-scoped AC (9 vs 6 criteria). Three research passes and two architect rejections all recommend archival |

### Key Evidence

- Zero state change since 2nd rejection: 3 memoized components (Card, Column, KanbanBoard), 2 stubs (DetailTab, ActivityTab) without memoization
- Task's own Disposition section: "Recommend archival — #971 is the canonical tracker"
- Three consecutive research passes confirm trigger unmet and lifecycle complete

### Challenge Results

- Challenge: SKIPPED — REJECT verdict (3rd consecutive), no challenge required

### Verdict: REJECT

### Action Taken: Returned to research for the third and final time. **This task MUST be archived.** It has completed its lifecycle: produced .owlbear/research/970-react-compiler-pds-interop.md and spawned #971 with superior AC. Three research passes and three architect rejections confirm: trigger unmet, #971 is canonical. Any further research→backlog cycling is a pipeline anti-pattern — the researcher should archive on next pickup rather than re-promoting to backlog

[[2026-04-18]]

## Research (archival — 2026-04-18)

Validated on 4th pickup: no state change. 3 memoized components (Card, Column, KanbanBoard) vs ≥5 threshold. Research doc exists, #971 is canonical tracker.

**Disposition: ARCHIVE.** Moving to done to break the research→backlog→reject loop (3 cycles). Task completed its lifecycle: produced .owlbear/research/970-react-compiler-pds-interop.md and spawned #971 with superior AC (9 criteria vs 6). No further pipeline processing warranted.
[[2026-04-18]]

## Audit

### AC Verification (Step 1a — Research Task)

| Criterion | Evidence | Status |
|-----------|----------|--------|
| Research doc exists | .owlbear/research/970-react-compiler-pds-interop.md (100+ lines, 10 sources, 6 high-relevance, risk analysis, validation pass with challenger results) | PASS |
| Follow-up tasks created | #971 at research status (blocked, trigger unmet) with 9 AC items expanding original 6 | PASS |
| Follow-up references research doc | #971 body: "See .owlbear/research/970-react-compiler-pds-interop.md" | PASS |

### Test Results

- pytest: 604 passed, 6 failed (all in serve/mcp-knowledge — outputschema_541, search_v2, phase_a_config — pre-existing, unrelated to cockpit/frontend scope)
- ruff: clean

### Architect Quality: 3/5

Original AC described implementation (enable babel plugin, run suites, remove manual memos) for a trigger that was unmet (">=5 memoizable components" with 0 manual memos at creation). This mismatch caused 3 research-backlog-reject cycles before the researcher broke the loop by moving to done. AC was specific enough but fundamentally misaligned with task state — should have included trigger gate as AC prerequisite or been scoped as research-only from the start.

### Deduction Breakdown

- AC quality 3/5: -.03
- No other deductions (research criteria all pass, lint clean, test failures outside scope)

### Confidence: 0.97

### Action: archive
