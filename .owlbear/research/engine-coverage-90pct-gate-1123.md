# Engine Coverage 90% Gate — Already Met

> **Owning task:** #1123 — TEST-CURATION: raise owlbear_kanban.engine coverage to 90%
> **Date:** 2026-04-25 **Status:** Complete

## 1. Context and Question

Task requests raising `owlbear_kanban.engine` module coverage to 90%. Prior tasks #1110, #1111, and #1113 drove systematic coverage uplift from 75% → 84% → 96% over the past two days. Question: is the 90% gate already closed, and what remains uncovered?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/kanban/src/owlbear_kanban/engine.py` (1206 stmts) | Codebase | 1.0 — target module |
| S2 | pytest-cov `--cov=owlbear_kanban.engine` — kanban tests only | Measurement | 1.0 — 95% (56 missing) |
| S3 | pytest-cov — kanban + workspace tests | Measurement | 1.0 — 96% (51 missing) |
| S4 | `.owlbear/research/1111-engine-coverage-gate.md` | Prior research | 0.9 — classified 111 gaps at 84% |
| S5 | `.owlbear/research/engine-coverage-edit-show-property-1113.md` | Prior research | 0.8 — targeted edit/show/property gaps |

## 3. Analysis

### 3.1 Current Baseline

| Scope | engine.py Stmts | Miss | Cover |
|-------|----------------|------|-------|
| Kanban tests only | 1206 | 56 | 95% |
| Kanban + workspace tests | 1206 | 51 | 96% |

**The 90% target is exceeded by 5–6 percentage points.**

### 3.2 Classification of 56 Remaining Uncovered Lines

| Category | Lines | Count | Testable? |
|----------|-------|-------|-----------|
| Subprocess/platform guards | 367-370 (`_move_file` git-mv path) | 4 | Hard — needs git repo fixture |
| AgentView duplicate logic | 1602, 1641, 1679, 1698, 1702-1708 | 8 | Yes but low value — mirrors KanbanEngine |
| Error handlers / rollback | 1090-1093, 2556, 2582-2589 | 13 | Yes — defensive paths worth covering |
| Scan/cache edge cases | 469-473, 573, 659, 694-702, 711, 836-837, 1363 | 18 | Mixed — some require timing/corruption |
| AgentView feature paths | 1786, 1915, 1948, 2042-2069, 2408-2471 | 19 | Yes — real feature paths, highest value |

Covering error handlers (13) + AgentView features (19) would reach 98%.

### 3.3 Package-Level Context

The broader `owlbear_kanban` package is at 78% due to `migrate.py` (0%, 335 stmts), `corruption.py` (56%), and `dispatch.py` (26%). These are separate modules with distinct coverage concerns, outside the scope of this engine-focused task.

## 4. Recommendation (confidence: 0.95)

**Close #1123 as already satisfied.** The 90% target was achieved by prior tasks #1110–#1113. No additional test-writing is needed.

If further coverage uplift is desired, a new task targeting the 19-line AgentView feature path gap (pick_tasks helpers, edit_task kwargs/no-op, predicate validation, section extraction) would be the highest-value follow-up.

Challenge: FALLBACK — trivial finding, no competing options to challenge.

## 5. Follow-up Tasks

None required. The target is met. Optional follow-up for AgentView feature-path coverage noted in §4 if desired.
