# Stale Task-Scoped Test Cleanup

> **Owning task:** #1415 — E2: Stale test cleanup — delete/archive 219 task-scoped tests from completed tasks
> **Date:** 2026-05-09 **Status:** Complete

## 1. Context and Question

Task-scoped test files (`test_*_{task_id}.py`, `*_{task_id}.test.tsx`) accumulate as tasks complete. The brief estimated ~219 stale files. This research validates the count, categorizes the cleanup approach, and identifies consolidation needs.

**Question:** How many stale task-scoped tests exist, what's the safest cleanup strategy, and how should the work be decomposed?

## 2. Sources Studied

| # | Source | Rel. | What taken |
|---|--------|:----:|------------|
| S1 | `tests/test_*_*.py` filesystem scan | 1.0 | 84 task-scoped Python root tests |
| S2 | `serve/*/tests/*_*.py` filesystem scan | 1.0 | 43 task-scoped package-local tests |
| S3 | `serve/cockpit/web/src/__tests__/*_*.test.tsx` scan | 1.0 | 45 task-scoped frontend tests |
| S4 | Kanban board (active + archived) | 1.0 | 42 active tasks, 1416 archived |
| S5 | `.owlbear/research/stale-test-pick-tasks-cleanup.md` | .90 | Prior art: coverage overlap methodology |
| S6 | `.owlbear/briefs/draft-pipeline-review-rethink/brief.md` | .85 | E2 scope, C2/B1 dependency chain |

## 3. Analysis

### 3.1 Actual Count vs Estimate

| Location | Task-scoped files | Stale files | Active (retain) |
|----------|:-:|:-:|:-:|
| `tests/` (Python root) | 84 | 82 | 2 (#1439, #1448) |
| `serve/*/tests/` (pkg-local) | 43 | 43 | 0 |
| `serve/cockpit/web/src/__tests__/` (TSX) | 45 | 44 | 1 (#1380) |
| **Total** | **172** | **169** | **3** |

Original estimate of 219 was high. Actual stale count: **169 files, ~75K lines**.

### 3.2 Root Python Tests — Cleanup Categories

| Category | Files | Strategy |
|----------|:-----:|----------|
| Durable equivalent exists | 20 | Delete — coverage already consolidated |
| Single-file, no durable | 21 | Rename: drop `_{id}` suffix |
| Multi-file, no durable (16 groups) | 40 | Merge into single durable file per group |
| Active tasks (retain) | 2 | No action |
| **Total** | **83** | |

Multi-file merge groups (largest first): `test_server` (6), `test_decisions` (4), `test_cockpit_view` (3), `test_mcp_memory` (3), then 12 groups of 2 each.

### 3.3 Package-Local Tests — by Package

| Package | Stale files | Notes |
|---------|:-----:|-------|
| `kanban` | 22 | Engine test suite — heavy coverage overlap likely |
| `mcp-kanban` | 13 | Guidance + MCP tool tests |
| `mcp-knowledge` | 4 | SSRF, annotations, null safety |
| `knowledge` | 2 | SSRF fix tests |
| `mcp-browser` | 1 | SSRF preflight |
| `tools` | 1 | doc-index |

### 3.4 Frontend Tests — 44 Stale TSX Files

All 44 stale TSX tests are in `serve/cockpit/web/src/__tests__/`. Same approach: delete duplicates, rename singles, merge multiples. Separate task recommended (different toolchain: Vitest/npm vs pytest/uv).

### 3.5 Risk: Coverage Regression

- **Mitigation 1:** Run full test suite before and after each cleanup batch; compare pass count and coverage percentage.
- **Mitigation 2:** "Delete with durable equivalent" is safest — start there.
- **Mitigation 3:** Rename/merge preserves all tests — just reorganizes files.
- **Risk:** Merge conflicts when combining imports/fixtures from multiple task files. Low severity — mechanical work.

### 3.6 Known Issue

`test_decisions_1218.py` is consistently `--ignore`'d in recent CI runs, suggesting it's broken. Should be inspected during merge.

## 4. Recommendation

**Decompose into 3 follow-up tasks** (confidence: .85):

1. **Python root cleanup** (82 files) — delete 20 with durable equivalents, rename 21, merge 40 across 16 groups. Largest single batch.
2. **Package-local cleanup** (43 files) — same approach, scoped to `serve/*/tests/`.
3. **Frontend cleanup** (44 files) — TSX tests, different toolchain.

Each task runs full suite before/after for regression verification. Mechanical work — no architecture decisions needed.

Challenge: SKIPPED — T1 autonomous cleanup, no architectural recommendation to challenge.

## 5. Follow-up Tasks

Created via planner — see task body.
