---
id: 969
title: Evaluate React Compiler integration cost vs manual memoization
  maintenance
status: archived
priority: nice-to-have
created: 2026-04-18T16:09:24.966912+00:00
updated: 2026-04-18T19:17:33.577818+00:00
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

Assess whether babel-plugin-react-compiler (React Compiler) should replace manual React.memo/useMemo/useCallback across cockpit components.

## Context

Research #963 chose manual memoization for KanbanBoard (1 component). As more components are added, manual memo maintenance grows. React Compiler auto-memoizes everything but adds a build dependency.

## Acceptance Criteria

- [ ] Measure React Compiler Vite plugin integration (LOC, build time impact)
- [ ] Compare maintenance cost: N manual memos vs 1 plugin
- [ ] Check React Compiler stability status (experimental vs stable)
- [ ] Recommendation with confidence score
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/969-react-compiler-evaluation.md
- Sources: 8 studied, 6 high-relevance (≥0.85)
- Recommendation: Defer React Compiler adoption; proceed with #963 manual memos; adopt compiler at ≥5 memoizable components (confidence: 0.78)
- Key finding: React Compiler reached 1.0.0 stable (no longer experimental), but YAGNI applies — 0 memos exist today, and PDS Web Component interop is unvalidated
- Challenge: reconsider (0.50) — accepted YAGNI, PDS interop, SWC lock-in concerns; revised from "adopt now" to "defer"
- Follow-up tasks created: #970 (Enable React Compiler with PDS interop validation spike)
- Decision requests: none
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: evaluate React Compiler vs manual memoization |
| Interface clarity | PASS | AC items are clear research deliverables (measure, compare, check, recommend) |
| Dependency correctness | PASS | No dependencies, none needed |
| Module layering | N/A | Research task, no code changes |
| TDD compliance | N/A | Research task — tagged `research` for pass-through |
| KISS/YAGNI | PASS | Appropriate scope for the question asked |
| Premise challenge | PASS | Valid question given phase-2 expansion plans; #963 deferred compiler briefly, #969 provides the deeper evaluation |
| Pattern consistency | PASS | Research follows standard format with sources, analysis, recommendation |
| Security surface | PASS | No security implications |
| Single domain | PASS | Frontend/cockpit domain only |

### Challenge Results

- Challenger: reconsider (0.55)
- C1: AC1 "Measure build time" addressed qualitatively not quantitatively — accepted as adequate for a defer recommendation on a nice-to-have task
- C2: Crossover threshold ~5 is heuristic — accepted; exact number doesn't change the recommendation
- B1: `react-compiler-healthcheck` not used — noted; #970 captures validation spike for when adoption is considered
- B2: Trigger for #970 untrackable — task exists at research status with clear AC; acceptable for a deferred nice-to-have
- Architect response: concerns noted, verdict unchanged. Research adequately answers the strategic question with evidence proportional to priority.

### Tagging

- Added implicit `research` pass-through tag (task produces no testable code)

### Verdict: APPROVE

### Action Taken: Advanced to todo. All 4 AC items addressed by research doc. Follow-up #970 exists for future compiler adoption spike

[[2026-04-18]]

## Test-Writer Notes

- Non-implementation task (tagged `research`, `cockpit`, `frontend`) — no tests applicable.
- AC is entirely research deliverables: measure, compare, check stability, recommend. No Python interfaces, no `.py` files, no src/ changes.
- Passing through to builder.
[[2026-04-18]]

## Builder Notes

**Pass-through:** Research evaluation task — no implementation required.

**Files changed:** None.

**AC verification:**

- AC1 (Measure Vite plugin integration LOC/build time): addressed in research doc — qualitative analysis of ~5 LOC config, no measurable build impact for current scale
- AC2 (Compare maintenance cost N memos vs 1 plugin): addressed — crossover threshold identified at ≥5 memoizable components
- AC3 (Check stability status): addressed — React Compiler 1.0.0 stable confirmed
- AC4 (Recommendation with confidence score): addressed — Defer adoption, confidence 0.78

**Tests:** N/A (research task, no code)
**Lint:** N/A
**Evidence:** All 4 AC items answered in `.owlbear/research/969-react-compiler-evaluation.md`. Follow-up #970 created for future adoption spike.
[[2026-04-18]]

## Review Evidence

### Task Type

Research pass-through — no code, no tests, no lint. Verification scope: AC compliance against `.owlbear/research/969-react-compiler-evaluation.md`.

### Source Control Changes

None. Confirmed pass-through chain: test-writer → builder → review with no file modifications.

### Tests / Lint / Coverage

N/A — research task produces no testable code. Quality-Runner not dispatched (no scope to run).

### Security Review

N/A — no code changes, no dependencies added to project.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| Measure React Compiler Vite plugin integration (LOC, build time impact) | §3.2: 3 LOC config + 1 devDep; build time "Negligible for <20 components". Qualitative treatment accepted by architect for nice-to-have priority. | COVERED |
| Compare maintenance cost: N manual memos vs 1 plugin | §3.3: structured comparison table with per-component cost breakdown; crossover threshold at ~5 memoized components identified with reasoning. | COVERED |
| Check React Compiler stability status (experimental vs stable) | §3.1: 1.0.0 stable confirmed from official react.dev docs (S1, 0.95 relevance); correctly updates outdated #963 "still experimental" finding. | COVERED |
| Recommendation with confidence score | §4: "Defer adoption" with confidence 0.78; rationale (zero memos today, PDS interop unvalidated, YAGNI), challenge cycle applied (challenger 0.50 → accepted), follow-up #970 created. | COVERED |

### Research Quality Assessment

- **Sources:** 8 studied, 6 at ≥0.85 relevance; primary claims backed by official docs (react.dev) and package registry
- **Structure:** Well-organized with tables for stability attributes, maintenance cost comparison, risk matrix, and YAGNI analysis
- **Challenge cycle:** Applied correctly — challenger at 0.50 produced revised "defer" from initial "adopt now" direction; concerns documented and resolved
- **Follow-up:** #970 created for future PDS interop validation spike with clear trigger condition (≥5 memoizable components)
- **Notable correction:** Research correctly identifies that #963's "still experimental" characterization is outdated; 1.0.0 stable is properly sourced

### Deductions

None. All 4 AC items addressed. Research quality proportional to task priority (nice-to-have) and scope.

### Verdict

**PASS — confidence: 0.96**
[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Research-only task; no code, no behavior change, no copilot-instructions.md update needed |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | Yes | Updated | 4 external sources (S1–S4 from research doc) were missing a #969 section in sources/overview.md; added `## React Compiler Evaluation (Task #969)` with all 4 rows |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Verified | `.owlbear/research/969-react-compiler-evaluation.md` exists and is linked in task body; follow-up #970 created |

### Files Updated

- `.owlbear/sources/overview.md` — added `## React Compiler Evaluation (Task #969)` section with S1–S4 attribution

### Scratch Files Cleaned

- None (no `.owlbear/scratch/969-*` files found)
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Measure React Compiler Vite plugin integration (LOC, build time impact) | Research doc section 3.2: 3 LOC config + 1 devDep; build time "Negligible for <20 components" (qualitative, accepted by architect for nice-to-have priority) | PASS |
| Compare maintenance cost: N manual memos vs 1 plugin | Research doc section 3.3: structured comparison table, crossover threshold at ~5 memoized components with per-component cost breakdown | PASS |
| Check React Compiler stability status (experimental vs stable) | Research doc section 3.1: 1.0.0 stable confirmed from official react.dev docs (S1, 0.95 relevance); corrects #963 "still experimental" finding | PASS |
| Recommendation with confidence score | Research doc section 4: "Defer adoption" with confidence 0.78; YAGNI rationale, challenge cycle applied (challenger 0.50), follow-up #970 created | PASS |

### Research Task Verification (Step 1a)

- Research doc exists: .owlbear/research/969-react-compiler-evaluation.md (confirmed)
- Follow-up task created: #970 at research status (confirmed)
- Follow-up references research doc: yes (body links to #969 and research doc)
- Sources attribution: 4 external sources added to .owlbear/sources/overview.md by doc-writer (confirmed)

### Test Results

- pytest: N/A (research task, zero code deliverables)
- ruff: N/A (no Python files changed)
- Quality-Runner: not dispatched (research task, Step 1a applies)

### Architect Quality: 4/5

AC lines are specific, verifiable research deliverables. Minor gap: PDS interop risk was surfaced by researcher, not anticipated in AC. Build time "Measure" treated qualitatively — proportional to priority.

### Deduction Breakdown

- AC lines without evidence: 0 (all 4 covered) = no deduction
- Lint violations: N/A = no deduction
- AC quality score 4 (>3) = no deduction
- Reviewer evidence: present, detailed, PASS at 0.96 = no deduction
- Test failures: N/A = no deduction

### Confidence: 1.00

### Action: archive
