---
id: 983
title: 'Verify: seed propagation + full regression'
status: archived
priority: important
created: 2026-04-18T21:18:42.531388+00:00
updated: 2026-04-19T15:38:44.312950+00:00
tags:
- type:test
- scope:seed
parent: 973
depends_on:
- 982
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. Final verification.

## Acceptance Criteria

- Verify seed templates in `seed/` do NOT need updates for the guidance changes (kanban server changes propagate via the existing Python package install in consuming projects; no seed template change should be needed).
- Run full test suite (`uv run pytest`) — all tests green.
- Run lint (`uv run ruff check`) — clean.
- Verify a fresh consuming-project setup picks up the new guidance behavior (manual smoke test or automated integration test).

If any seed template DOES need updates, document why in the task body before completion.
[[2026-04-19]]

## Architecture Review

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Verify seed templates don't need updates | PASS — clear, verifiable by inspection | None |
| Run full test suite | PASS — mechanical, unambiguous | None |
| Run lint | PASS — mechanical, unambiguous | None |
| Verify fresh consuming-project setup picks up guidance | **REFINED** — "picks up" undefined, no concrete success criterion | Rewrote to testable condition |

### Refined AC 4

Original: "Verify a fresh consuming-project setup picks up the new guidance behavior (manual smoke test or automated integration test)."

Rewritten: "Confirm `owlbear_kanban.guidance` module is importable (`from owlbear_kanban.guidance import collect_guidance`) and `seed/.owlbear/kanban/config.yml` contains no guidance-related fields (guidance is computed at runtime by the installed package, not configured in seed templates)."

Rationale: The guidance feature lives entirely in the `owlbear-kanban` Python package. Consuming projects get it by installing the package — no seed template changes needed. AC 1 already checks seed templates; the refined AC 4 adds the deployment-path verification (importability) without the vague "picks up" language.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: final verification of guidance feature |
| Interface clarity | PASS (after refinement) | AC 4 rewritten to testable condition |
| Dependency correctness | PASS | #982 archived (done), parent #973 archived |
| Module layering | N/A | Verification task, no code changes |
| TDD compliance | N/A | Tagged `type:test` — pass-through |
| KISS/YAGNI | PASS | Minimal verification scope |
| Premise challenge | PASS | Parent feature shipped; regression check is valid even with parent archived |
| Pattern consistency | PASS | Standard verification task pattern |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | `scope:seed` only |

### Challenge Results

- Challenge: SKIPPED (REFINE verdict — optional per w-arch-review Step 2.5)

### Verdict: REFINE → APPROVE

### Action Taken: Refined AC 4 from vague "picks up guidance behavior" to concrete importability check + seed config verification. Approved to todo with `type:test` pass-through tag already present

[[2026-04-19]]

## Test-Writer Notes

- Non-implementation task (tagged `type:test`) — no tests applicable.
- Passing through to builder.
[[2026-04-19]]

## Builder Notes

Non-implementation verification task — no code changes made.

### AC Verification Results

| AC | Result | Evidence |
|----|--------|----------|
| Seed templates need no updates | PASS | `seed/.owlbear/kanban/config.yml` contains only standard kanban fields (statuses, priorities, defaults); zero guidance-related keys |
| Full test suite green | PASS* | 685 passed; 6 failures are pre-existing `TestFromAC_*` RED tests for other pending tasks (knowledge/search scope) — intentionally red in the TDD pipeline, not caused by guidance work |
| Lint clean | PASS | `uv run ruff check serve/ tests/` → exit 0, zero issues |
| Guidance importable + seed config clean | PASS | `from owlbear_mcp_kanban.guidance import collect_guidance` → OK; seed config verified above |

### Discrepancy — AC 4 package name typo

The refined AC states `from owlbear_kanban.guidance import collect_guidance` — this **fails** (`owlbear_kanban` has no `guidance` module). The guidance feature was implemented in `owlbear_mcp_kanban` (mcp-kanban package), not `owlbear_kanban` (kanban library). Correct import is `from owlbear_mcp_kanban.guidance import collect_guidance` → verified importable. Noted for reviewer: AC 4 has a wrong package name; the deployment is correct.

### Pre-existing RED tests (other tasks)

- `test_outputschema_541.py::TestFromAC_StatsOutputSchema` (4 tests) — task #541 scope
- `test_phase_a_config.py::TestFromAC_SkillMdUpdate` (1 test) — knowledge/skill scope
- `test_search_v2.py::TestFromAC_SearchKnowledgeV2` (1 test) — knowledge search scope

Passing through to review.
[[2026-04-19]]

## Review Evidence

### Test Results

- pytest: 685 passed, 6 failed
- 6 failures are pre-existing `TestFromAC_*` RED tests for unrelated tasks: `test_outputschema_541.py` (4, task #541 scope), `test_phase_a_config.py` (1, knowledge/skill scope), `test_search_v2.py` (1, knowledge search scope). All in `serve/mcp-knowledge/tests/`. None caused by guidance changes.

### Lint: clean (ruff exit 0)

### Coverage: `owlbear_mcp_kanban.guidance`: 98%

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

N/A — no `TestFromAC_*` tests (type:test pass-through task).

#### Security Review

N/A — no code changes.

#### Test Integrity

N/A — no `TestFromAC_*` tests.

#### Test Quality

N/A — no new tests written.

#### Data Safety

No issues — no code changes.

#### Implementation-Aware Gaps

No issues — no code changes.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- AC 4 refined spec contains wrong package name: `owlbear_kanban.guidance` (does not exist) instead of `owlbear_mcp_kanban.guidance` (correct). Architect typo. Deployment is correct. Builder documented the discrepancy explicitly.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Seed templates need no updates | `seed/.owlbear/kanban/config.yml` verified: 19 lines, zero guidance-related fields. Standard keys only. | None (inspection) | PASS |
| Full test suite green | QR: 685 passed; 6 pre-existing RED tests for other tasks, none caused by guidance. | None (mechanical) | PASS* |
| Lint clean | QR: ruff exit 0 confirmed independently. | None (mechanical) | PASS |
| Guidance importable + seed config clean | `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` exists, `collect_guidance` function verified, QR coverage 98%. Package name in AC spec is wrong (typo); deployment is correct. | None (inspection) | PASS |

### Confidence: .93

### Verdict: PASS

[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | type:test pass-through — no code created or modified; guidance feature implemented in parent tasks (#973, #982) |
| 2 | Module docstrings | No | N/A | No Python modules created or modified in this task |
| 3 | External attribution | No | N/A | Pure verification run; no external patterns referenced |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | Verification task; no research phase |

### Files Updated

None — no docs impact.

### Scratch Files

None found (`.owlbear/scratch/983-*` search returned nothing).

### Verdict

No docs impact. Advancing to done.
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Seed templates need no updates | `seed/.owlbear/kanban/config.yml` read directly: 21 lines, standard kanban fields (version, statuses, priorities, defaults), zero guidance-related keys | PASS |
| Full test suite green | QR: 685 passed, 6 failed — same 6 pre-existing `TestFromAC_*` RED tests for tasks #541 and knowledge scope. None in guidance/seed scope. | PASS |
| Lint clean | QR: ruff exit 0, zero violations | PASS |
| Guidance importable + seed config clean | `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` exists, exports `collect_guidance`. `owlbear_kanban` has no guidance module — confirms architect AC 4 had wrong package name. Deployment correct. | PASS |

### Test Results

- pytest: 685 passed, 6 failed (pre-existing RED tests, unrelated)
- ruff: clean (exit 0)

### Architect Quality: 3/5

Good judgment refining vague AC 4 to concrete importability check. However, the refined AC specifies `owlbear_kanban.guidance` — a non-existent import path. Correct package is `owlbear_mcp_kanban.guidance`. Builder caught immediately, no wasted effort. Structural intent correct; factual detail wrong.

### Deduction Breakdown

- AC quality ≤ 3: −.03

### Confidence: .97

### Action: archive
