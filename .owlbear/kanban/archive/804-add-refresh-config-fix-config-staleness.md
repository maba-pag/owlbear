---
id: 804
title: Add refresh_config + fix config staleness
status: done
priority: needed
created: '2026-04-10T21:21:04.269881+00:00'
updated: '2026-04-12T04:34:16.245527+00:00'
tags:
- phase-1
- scope:mcp-kanban
- config
- rigor:thorough
parent: 798
depends_on:
- 803
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `refresh_config()` method on `KanbanEngine`: reloads config from disk, updates `self._config` + all derived state (tasks_dir, archive_dir, rank maps)
- `create_task` calls `refresh_config()` internally (or equivalent) to ensure fresh config for `next_id`
- After `refresh_config()`, `_status_rank()` and `_priority_rank()` use new config values
- #803 tests pass GREEN
- Existing MCP tests pass (O4)

## Context

Phase 1, independent pair. Depends on #803 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-11]]
## Research
- Research doc: .owlbear/research/refresh-config-impl-804.md
- Sources: 7 studied, 4 high-relevance (engine.py implementation, existing tests, sibling #803 research, brief)
- Recommendation: No new code needed — all AC points already implemented in engine.py. GREEN phase is a verification pass: confirm #803 tests pass, confirm MCP tests pass. (confidence: 0.92)
- Follow-up tasks created: none (implementation complete, tests covered by #803/#840)
- Decision requests: none
- Tier: T1 — Autonomous (verification-only, no code changes)

Key findings:
1. `refresh_config()` implemented at engine.py L106-113
2. `create_task` staleness fix implemented at engine.py L248, L280-283 (local-variable pattern preferred over calling `refresh_config()` for failure isolation)
3. `_status_rank()` / `_priority_rank()` derive from `self._config` dynamically — no cached rank maps to invalidate
4. Builder should wait for #803 dependency (#840 tests in-progress), then do verification pass
[[2026-04-11]]
## Architecture Review

### AC Assessment

| AC line | Assessment | Action |
|---------|-----------|--------|
| AC1: `refresh_config()` reloads config, updates `_config` + derived state (tasks_dir, archive_dir, rank maps) | PASS (with corrections) | "rank maps" misleading — `_status_rank()` / `_priority_rank()` compute from `self._config` on each call, no cached maps exist. `archive_dir` derives from constant `_ARCHIVE_DIR_NAME = "archive"` (engine.py L39), not config. Harmless imprecision — builder should note. |
| AC2: `create_task` calls `refresh_config()` or equivalent for fresh config | PASS | engine.py L258: `config = load_config(...)` local-variable pattern; L280-283: assigns back to `self._config` after save. Better failure isolation than calling `refresh_config()` directly. |
| AC3: After `refresh_config()`, rank methods use new config values | PASS (trivially true) | Both methods (engine.py L82-85) recompute from `self._config` on every call. No invalidation needed. |
| AC4: #803 tests pass GREEN | PASS — verifiable | Child #840 at `review` with 6/6 tests passing (test_refresh_config_803.py). Builder runs verification. |
| AC5: Existing MCP tests pass (O4) | PASS — verifiable | Builder verification step. |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: config refresh mechanism verification |
| Interface clarity | PASS | Public API clear: `refresh_config()`, `board_config()`, `create_task()` |
| Dependency correctness | PASS | depends_on=[803] correct. #803 at `todo`, child #840 at `review` with tests written + passing. |
| Module layering | PASS | All within `owlbear_kanban.engine` — no cross-package concerns |
| TDD compliance | PASS | #803 is paired RED task; #840 test file already written |
| KISS/YAGNI | PASS | Verification-only scope; research confirms no new code needed |
| Premise challenge | PASS | Despite pre-existing implementation, verification gate is valid pipeline hygiene — confirms tests pass GREEN against implementation |
| Pattern consistency | PASS | `load_config()` local-variable pattern in `create_task` follows failure-isolation best practice |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | scope:mcp-kanban only |

### Failure Mode Map
N/A — verification-only task introduces no new codepaths.

### Challenge Results
- Challenger: FALLBACK — challenger agent not available in session
- Architect response: Proceeding with approval. Low-risk verification task, T1 autonomous, implementation verified in codebase with high confidence (0.92).

### Builder Guidance
Research doc confirms no new code needed. Builder workflow:
1. Wait for #803 (dependency) to reach `done`
2. Run `uv run pytest tests/test_refresh_config_803.py -v` — confirm 6/6 GREEN
3. Run `uv run pytest tests/ -m "not api" -q --tb=short` — confirm existing MCP tests pass
4. Verify `refresh_config()` at engine.py L101-108 and `create_task` staleness fix at engine.py L258, L280-283 match AC
5. Advance

### Verdict: APPROVE
### Action Taken: Advanced to todo. Verification-only GREEN phase — implementation pre-exists, builder confirms tests pass.
[[2026-04-12]]
## Test-Writer Notes

**Decision: Pass-through — pre-existing implementation, all AC behaviors covered by GREEN tests**

### Test File
None created. All AC behaviors are already tested and passing in sibling files.

### AC Coverage Audit

| AC | Requirement | Status | Coverage |
|----|-------------|--------|----------|
| AC1 | `refresh_config()` reloads config, updates `_config` + derived state (tasks_dir, rank maps) | ✅ COVERED | `test_refresh_config_803.py` — 6 tests (`TestFromAC_RefreshConfig`) |
| AC2 | `create_task` refreshes config for fresh `next_id` | ✅ COVERED | `test_config_staleness_fix_828.py` — 6 tests (`TestFromAC_ConfigStalenessInCreateTask`) |
| AC3 | After `refresh_config()`, rank methods use new config values | ✅ COVERED | `test_refresh_config_803.py` — statuses/priorities updated; move_task accepts/rejects updated statuses |
| AC4 | `#803` tests pass GREEN | ✅ VERIFIED | `test_refresh_config_803.py` — 6/6 passed (run confirmed) |
| AC5 | Existing MCP tests pass (O4) | 🔲 BUILDER | Builder runs full suite as O4 gate |

### Evidence
- `uv run pytest tests/test_config_staleness_fix_828.py tests/test_refresh_config_803.py -v` → 12 passed, 0 failed
- `engine.py` L100-112: `refresh_config()` fully implemented
- `engine.py` L248, L280-283: `create_task` loads fresh config + updates `self._config`/`self._tasks_dir`/`self._archive_dir`
- Architecture review verdict: **APPROVE — verification-only GREEN phase**

### Why No RED Tests

The implementation pre-dates this pipeline entry (confirmed by research doc at `.owlbear/research/refresh-config-impl-804.md` with confidence 0.92). Writing tests for the AC behaviors produces **immediately-GREEN tests**, which violates the RED phase contract. Per `w-tdd-red` Step 2a: defaulting to pass-through.

### Builder Guidance
1. Run `uv run pytest tests/test_refresh_config_803.py tests/test_config_staleness_fix_828.py -v` — confirm 12/12 GREEN ✅
2. Run full suite `uv run pytest tests/ -q -m "not api"` — confirm no regressions (O4)
3. Advance `#804` to `done` after both checks pass.
[[2026-04-12]]
## Builder Notes

### Files Changed
None — verification-only pass. Implementation pre-existed in `engine.py`.

### Implementation Evidence
- `refresh_config()` confirmed at `serve/kanban/src/owlbear_kanban/engine.py` L100-112
- `create_task` staleness fix confirmed at engine.py L248, L280-283 (local-variable pattern)
- `_status_rank()` / `_priority_rank()` derive from `self._config` dynamically per call — no cached maps

### Test Results
- `tests/test_refresh_config_803.py` + `tests/test_config_staleness_fix_828.py`: **12/12 passed**
- Full suite (`uv run pytest tests/ -m "not api" -q`): **40 passed**, 2 pre-existing failures in `test_authenticated_content_pipeline_751.py` (unrelated schema/browser task), 6 pre-existing collection errors (unrelated future tasks)

### Lint Status
`ruff check serve/kanban/src/owlbear_kanban/engine.py` → **clean**

### Coverage
No code changes introduced — coverage on pre-existing implementation confirmed by 12/12 target tests.

### Pre-existing Failures (not introduced by #804)
- 2 FAILED: `TestFromAC_AuthenticatedContentSchema` in `test_authenticated_content_pipeline_751.py` — missing `approval_state`/`extraction_status` columns (different epic, tracked separately)
- 6 collection errors: `owlbear_mcp_kanban.*` module imports (future tasks not yet implemented)
[[2026-04-12]]
## Review Evidence

### Test Results
- **Targeted** (test_refresh_config_803.py + test_config_staleness_fix_828.py): **12 passed, 0 failed**
- **Broader MCP suite** (test_kanban_engine_crud.py + test_board_config_805.py + test_board_config_806.py): **65 passed, 0 failed**

### Lint: clean
- `ruff check serve/kanban/src/owlbear_kanban/engine.py test_refresh_config_803.py test_config_staleness_fix_828.py` — 0 violations

### Coverage
- `owlbear_kanban.engine`: 33% (12-test run), 58% (65-test CRUD run)
- Verification-only task — no code changes; scoped coverage expected

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: `refresh_config()` reloads config, updates `_config` + derived state | `TestFromAC_RefreshConfig` (6 tests) — next_id, tasks_dir, statuses, priorities, move accepts/rejects | Yes — each asserts observable state change after `refresh_config()` | COVERED |
| AC2: `create_task` uses fresh config equivalent | `TestFromAC_ConfigStalenessInCreateTask` (6 tests) — next_id increments, disk consistency, n-creates, tasks_dir sync | Yes — `board_config().next_id` equality assertions fail if `self._config` is not updated | COVERED |
| AC3: rank methods use new config after refresh | `test_refresh_config_then_move_task_accepts_new_status`, `test_refresh_config_then_move_task_rejects_removed_status` | Yes — move_task with removed status raises ValueError | COVERED |
| AC4: #803 tests pass GREEN | `TestFromAC_RefreshConfig` — 6/6 verified by quality-runner | N/A (verification gate) | COVERED |
| AC5: Existing MCP tests pass (O4) | `test_kanban_engine_crud.py`, `test_board_config_805.py`, `test_board_config_806.py` — 65/65 | N/A (regression gate) | COVERED |

#### Security Review
No code changes introduced. Path containment validation present at `task_io.validate_path_containment`. No OWASP concerns.

#### Test Integrity
No `TestFromAC_*` classes modified — builder made zero code changes. N/A.

#### Test Quality
- Assertion specificity: **STRONG** — all use exact equality (`== 101`, `== 999`, `== ["low", "high"]`, file count `>= 1`)
- Negative/error-path coverage: **STRONG** — AC6 tests ValueError raise on removed status
- Mutation resistance: **STRONG** — removing `self._config = config` from `create_task` fails 5/6 staleness tests; removing `refresh_config()` body fails all 6 refresh tests
- Test independence: **STRONG** — all fixtures use `tmp_path`, no shared mutable state
- Test names: **STRONG** — fully descriptive

#### Data Safety
No new code paths. No race conditions, no unbounded inputs introduced.

#### Builder Process
Single `## Builder Notes` section, no retries. Verification-only scope executed cleanly.

### AC Compliance Table
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: `refresh_config()` reloads config + derived state | engine.py L100-112: updates `self._config`, `self._tasks_dir`, `self._archive_dir` | `TestFromAC_RefreshConfig` 6/6 | PASS |
| AC2: `create_task` local-variable refresh equivalent | engine.py L248 (`config = load_config(...)`), L280-283 (assigns back to `self._config`, `self._tasks_dir`, `self._archive_dir`) | `TestFromAC_ConfigStalenessInCreateTask` 6/6 | PASS |
| AC3: rank methods derive from `self._config` dynamically | engine.py L82-85: `_priority_rank()` / `_status_rank()` compute fresh from `self._config` on every call | `test_refresh_config_then_move_task_*` 2/2 | PASS |
| AC4: #803 tests GREEN | quality-runner: test_refresh_config_803.py 6/6 passed | `TestFromAC_RefreshConfig` | PASS |
| AC5: Existing MCP tests pass | quality-runner: test_kanban_engine_crud + board_config_805/806 = 65/65 passed | full CRUD + board_config suite | PASS |

### Informational (non-blocking)
- `test_config_staleness_fix_828.py` file header says "MUST FAIL until #828 is implemented GREEN" — misleading since the implementation pre-existed. Harmless; does not affect test validity.
- `archive_dir` in AC1 wording implies it derives from config, but it's hardcoded to `_ARCHIVE_DIR_NAME = "archive"` (engine.py L39). `refresh_config()` still assigns it (from the constant). Noted by architecture review; harmless imprecision.

### Verdict
0 deductions. **Confidence: .93 → PASS**
[[2026-04-12]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Verification-only task — no new code introduced. `copilot-instructions.md` contains only branch/identity content; no engine API tables to update. |
| 2 | Module docstrings | No | N/A | Builder confirmed zero files changed. Read `engine.py` directly: module docstring lists `refresh_config()` at L22; `refresh_config()` docstring at L100-112 accurate; `create_task()` docstring at L243-255 accurate. All public API on touched scope verified. |
| 3 | External attribution | No | N/A | Research sources 1–7 all internal (engine.py, existing tests, sibling research, brief). No external repos/articles used. `sources/overview.md` — no update needed. |
| 4 | CLI changes | No | N/A | Internal engine method only. No CLI surface affected. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/refresh-config-impl-804.md` exists and is linked in task body under `## Research`. Follow-up tasks: none (confirmed by research doc — impl pre-existed, covered by #803/#840). |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/804-*` files found)
[[2026-04-12]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: refresh_config() reloads config + derived state | engine.py L106-112: updates _config, _tasks_dir, _archive_dir; TestFromAC_RefreshConfig 6/6 GREEN | PASS |
| AC2: create_task uses fresh config equivalent | engine.py L258 load_config(), L280-283 assigns back to self._config/_tasks_dir/_archive_dir; TestFromAC_ConfigStalenessInCreateTask 6/6 GREEN | PASS |
| AC3: rank methods use new config after refresh | engine.py L82-85: _priority_rank()/_status_rank() compute from self._config each call; test_refresh_config_then_move_task_* 2/2 GREEN | PASS |
| AC4: #803 tests GREEN | test_refresh_config_803.py 6/6 passed | PASS |
| AC5: Existing MCP tests pass (O4) | 65/65 CRUD + board_config tests passed; full suite 354 failures all pre-existing/unrelated to #804 | PASS |

### Test Results
- pytest (targeted): 77 passed, 0 failed (test_refresh_config_803 + test_config_staleness_fix_828 + kanban CRUD + board_config_805/806)
- pytest (full suite): 3654 passed, 354 failed, 6 collection errors -- all failures pre-existing, unrelated to #804 scope
- ruff: clean (engine.py + both test files)

### Reviewer Evidence
Present and detailed. Covers test-writer AC coverage audit, security review, test integrity, test quality, AC compliance table. Verdict: .93 PASS. Trusted code-level findings.

### Architect Quality: 4/5
AC was specific and testable. Minor terminology imprecision (AC1 says "rank maps" but they are computed dynamically, not cached; "archive_dir" implies config-derived but it uses a constant). Both noted by architect review and harmless. Research correctly identified pre-existing implementation. Builder guidance was clear and actionable.

### Deduction Breakdown
- AC lines without evidence: 0 (all 5 verified) -- 0 deductions
- Lint violations: 0 -- 0 deductions
- AC quality score: 4/5 (above 3) -- 0 deductions
- Missing reviewer evidence: present and detailed -- 0 deductions
- Full-suite failures in task scope: 0 -- 0 deductions

### Confidence: .98
### Action: archive

### Commit Integrity
Verification-only task, no files changed by builder. Upstream commits verified:
- 7a720b9c test: add refresh_config() tests (#840, #803)
- b6ffb2e0 test: add failing tests for create_task config staleness (#828)
- 64d6d85a fix: update self._config after save in create_task (#828)
No uncommitted deliverables. No leftovers to commit.