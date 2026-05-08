# Todo Reset for AC Re-Gate Under New Quality Rules

> **Owning task:** #1420 — Reset todo tasks to backlog for AC re-gate under new quality rules
> **Date:** 2026-05-08 **Status:** Complete

## 1. Context and Question

Task #1405 (A2: Planner skill update) deployed new AC quality rules (`h-ac-quality`) via builder commit `9a9e5e10` at 2026-05-08 03:20:44+02. Tasks placed in `todo` before this deployment bypassed the new architect gate. This research identifies which tasks must be moved to `backlog` for re-gating.

**Question:** Which tasks were in `todo` at the time A2 deployed, and which of those still need to be moved?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| Git tree at `9a9e5e10` (builder commit) | Primary — board snapshot | 1.0 |
| Git tree at `88d8ac1c^` (pre-archive commit) | Confirmation | 0.9 |
| Current board state via `list_tasks` | Live validation | 1.0 |
| Task bodies (#1413, #1417, #1427, #1428–#1433) | AC and arch review evidence | 0.9 |

## 3. Analysis

### Board snapshot at A2 deployment (9a9e5e10, 2026-05-08 03:20)

7 tasks were in `todo`:

| ID | Title | Current Status | Has Arch Review? |
|----|-------|---------------|-----------------|
| #1413 | D2: CI/SAST baseline | **todo** | Yes (pass 2, APPROVE after REFINE) |
| #1428 | Ideation UX: jargon elimination | **todo** | No — planner skipped backlog |
| #1429 | P1-01: Communication Patterns | **review** | No |
| #1430 | P1-02: Directive rewrites mediation | **todo** | No |
| #1431 | P1-03: Directive rewrite discovery | **todo** | No |
| #1432 | P1-04: Agent enforcement lines | **todo** | No |
| #1433 | P1-05: Panel output phrasing | **review** | No |

### Current-state filtering per AC P2

AC P2 says: "tasks that were in `in-progress`, `review`, or `done` are untouched."

- **#1429** → now in `review` → **untouched**
- **#1433** → now in `review` → **untouched**

### Tasks to move (5)

| ID | Title | Arch-reviewed? | Note |
|----|-------|---------------|------|
| **#1413** | D2: CI/SAST baseline | Yes (APPROVE) | Architect reviewed, but under old rules pre-deployment |
| **#1428** | Ideation UX parent | No | Planner explicitly "skipped backlog intentionally" |
| **#1430** | P1-02: Directive rewrites | No | Child of #1428, no gate |
| **#1431** | P1-03: Directive rewrite | No | Child of #1428, no gate |
| **#1432** | P1-04: Agent enforcement | No | Child of #1428, no gate |

### Tasks NOT to move (currently in `todo` but entered after deployment)

| ID | Title | Status at deploy | Reason |
|----|-------|-----------------|--------|
| #1417 | SARIF upload | `research` | Entered `todo` after A2 deployed; has architect APPROVE |
| #1427 | Planner skill updates | `backlog` | Entered `todo` after A2 deployed; has architect APPROVE |

## 4. Recommendation

**Move 5 tasks** from `todo` to `backlog` via `move_task`. Confidence: **0.92**.

Risk: #1413 already has a thorough architecture review (pass 2 with refine). Re-gating it may be redundant — the architect may simply re-approve. Low cost regardless.

Challenge: skipped — straightforward board operation with no competing options.

## 5. Follow-up Tasks

The execution (actual `move_task` calls) is the task #1420 itself — it should proceed through the pipeline to builder, who will execute the 5 moves.

**Task IDs to move:** #1413, #1428, #1430, #1431, #1432.
