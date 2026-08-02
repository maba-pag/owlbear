---
id: 803
title: Tests — refresh_config + config staleness fix
status: archived
priority: medium
created: '2026-04-10T21:20:57.293478+00:00'
updated: '2026-04-15T13:48:18.176519+00:00'
tags:
- phase-1
- type:test
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `refresh_config()` reloads YAML from disk
- Tests verify `refresh_config()` updates `_config`, tasks_dir, archive_dir, and rank maps
- Tests verify `create_task` uses fresh config (staleness scenario: modify config on disk → create → new config reflected)
- Tests verify `refresh_config()` after external config change → `move_task` validates against new statuses
- Tests fail RED before implementation

## Context

Phase 1, independent pair. No dependencies within Phase 1.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-11]]
## Research
- Research doc: .owlbear/research/refresh-config-tests-803.md
- Sources: 6 studied, 4 high-relevance (engine.py impl, existing #828 tests, models, config_loader)
- Recommendation: Write 6 focused refresh_config() tests in test_refresh_config_803.py; skip create_task staleness tests (already covered by test_config_staleness_fix_828.py). Tests will be GREEN immediately since implementation exists. (confidence: 0.90)
- Follow-up tasks created: #840 (todo — write test file)
- Decision requests: none
- Tier: T1 — Autonomous (test file addition, no arch/security implications)
[[2026-04-11]]
## Architecture Review

### AC Assessment

| AC line | Assessment | Action |
|---------|-----------|--------|
| AC1: `refresh_config()` reloads YAML from disk | PASS — verifiable, covered by child #840 test 1 | None |
| AC2: `refresh_config()` updates `_config`, tasks_dir, archive_dir, and rank maps | **CORRECTION** — `archive_dir` is derived from constant `_ARCHIVE_DIR_NAME = "archive"` (engine.py L39), NOT from config. Not meaningfully testable as a config-derived update. | Downstream: drop `archive_dir` from test scope; test `_config`, `tasks_dir`, and rank maps only |
| AC3: `create_task` uses fresh config (staleness scenario) | **SKIP** — already fully covered by `test_config_staleness_fix_828.py` (AC1+AC2 in that file). Duplicating these tests violates DRY. | No new tests needed for this AC line |
| AC4: `refresh_config()` + `move_task` validates new statuses | PASS — verifiable, covered by child #840 tests 5-6 | None |
| AC5: Tests fail RED before implementation | **MOOT** — `refresh_config()` implementation exists at engine.py L106-113. Tests will be GREEN immediately. | Treat as documentation note, not test gate |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure test task, one module under test (`refresh_config()`) |
| Interface clarity | PASS (with corrections above) | Public API: `refresh_config()`, `board_config()`, `valid_transitions()`, `move_task()` |
| Dependency correctness | PASS | No `depends_on` listed, none needed — implementation exists |
| Module layering | PASS | Tests import from `owlbear_kanban` public API only |
| TDD compliance | N/A | This IS the test task; implementation preceded it |
| KISS/YAGNI | PASS | 6 focused tests, no over-engineering |
| Premise challenge | PASS | `refresh_config()` has zero existing test coverage; tests are warranted |
| Pattern consistency | PASS | Follows `test_config_staleness_fix_828.py` fixture patterns (`tmp_path`, `_BASE_CONFIG_YAML`) |
| Security surface | PASS | No new system boundaries; tests use tmp_path |
| Single domain | PASS | scope:mcp-kanban only |

### Failure Mode Map
N/A — test-only task introduces no failure modes.

### Challenge Results
- Challenger: reconsider (confidence 0.40 for straight approval)
- Key concerns: AC2 archive_dir misleading, AC3/AC5 should be removed, child #840 status
- Architect response: **Override with justification.** AC corrections documented above. Child #840 verified at `todo` (confirmed via `show_task`). AC inaccuracies are mitigated by: (a) this arch review appended to body, (b) child #840 having correct refined AC with 6 specific test cases, (c) research doc documenting skip rationale. Parent #798 missing is structural debt, not a blocker.

### Delegation Note
**Test implementation is fully delegated to child #840** ("Write refresh_config() tests — test_refresh_config_803.py", status: todo). #840 has correct, refined AC with 6 specific test cases. The test-writer for #803 should pass through — no additional test file creation needed beyond what #840 produces.

### Verdict: APPROVE
### Action Taken: Advanced to todo with AC corrections and delegation note in architecture review.
[[2026-04-11]]
## Test-Writer Notes
- Non-implementation task (tagged `type:test`) — no new tests written.
- Arch review Delegation Note: test implementation fully delegated to child #840 ("Write refresh_config() tests — test_refresh_config_803.py").
- Child #840 status: **review** — builder has written all 6 AC tests (GREEN against pre-existing implementation in `engine.py` L106-113).
- No RED phase applicable per arch review: `refresh_config()` implementation preceded this task; tests will be GREEN immediately.
- Passing through to builder.
[[2026-04-12]]
## Builder Notes

**Files changed:** None new — `tests/test_refresh_config_803.py` was delivered by child #840 builder (status: review). #803 builder role is verification and pass-through only (type:test, non-implementation task).

**Test results:** 6 passed, 0 failed
- `test_refresh_config_reloads_yaml_from_disk` ✅ — next_id: 100 → 999 on disk → refresh → board_config().next_id == 999
- `test_refresh_config_updates_tasks_dir` ✅ — tasks_dir changed on disk → refresh → create_task writes to newtasks/
- `test_refresh_config_updates_statuses` ✅ — staging added on disk → refresh → valid_transitions("research") includes "staging"
- `test_refresh_config_updates_priorities` ✅ — priorities replaced on disk → refresh → board_config().priorities == ["low", "high"]
- `test_refresh_config_then_move_task_accepts_new_status` ✅ — new status on disk → refresh → move_task succeeds
- `test_refresh_config_then_move_task_rejects_removed_status` ✅ — backlog removed on disk → refresh → move_task raises ValueError

**Lint status:** ruff clean

**Coverage:** 6 tests cover refresh_config() at engine.py L106-113; engine.py overall 33% (expected — these tests target only the refresh_config() method). Full AC coverage achieved for the targeted function.

**AC corrections (from arch review):** archive_dir not tested (derived from constant, not config); create_task staleness covered by existing #828 tests (no duplication).
[[2026-04-12]]
## Review Evidence

**Reviewer:** reviewer-mode (Claude Sonnet 4.6)
**Task:** #803 — Tests — refresh_config + config staleness fix
**Test file:** `tests/test_refresh_config_803.py` (6 tests, delivered by child #840 builder)

---

### Test Execution
- Quality-Runner dispatched; pytest crashed at initialization: `KeyboardInterrupt` during `logfire/opentelemetry → google.protobuf.internal.containers` import chain.
- Identical failure on second retry. Confirmed persistent environment issue (see session memory: task-800-pytest-issues).
- **Passed: UNKNOWN. Failed: UNKNOWN.** — tests were never collected.

### Lint
- `get_errors` on `tests/test_refresh_config_803.py`: **clean (no errors)**
- Builder self-reported ruff clean; unverifiable via quality-runner (ruff not run due to pytest crash).

### Coverage
- Unverifiable from quality-runner output.

### Code Inspection — Implementation
`refresh_config()` at `engine.py` L106-109:
```python
self._config = load_config(self._kanban_dir)
self._tasks_dir = self._kanban_dir / self._config.tasks_dir
self._archive_dir = self._kanban_dir / _ARCHIVE_DIR_NAME
```
- Rank maps (`_priority_rank`, `_status_rank`) are on-demand computed from `self._config` — no eager cache to invalidate.
- `move_task()` L410-412 reads `{s["name"] for s in self._config.statuses}` live.
- `valid_transitions()` reads `self._config.statuses` live.
- All refresh-dependent paths are correctly wired.

### AC Compliance (manual code inspection)

| AC line | Coverage | Assessment |
|---------|----------|------------|
| AC1: `refresh_config()` reloads YAML from disk | test 1: `next_id 100→999`, asserts `board_config().next_id == 999` | STRONG |
| AC2: updates `_config`, tasks_dir, rank maps (`archive_dir` excluded per arch review) | tests 1,2,3,4 | STRONG |
| AC3: `create_task` staleness | SKIP — covered by `test_config_staleness_fix_828.py` (arch approved) | ACCEPTABLE |
| AC4: `move_task` validates new statuses after refresh | tests 5,6 | STRONG |
| AC5: Tests fail RED | MOOT — impl pre-existed (arch approved) | ACCEPTABLE |

### Assertion Quality
All 6 assertions are discriminating:
- Tests 1,4: exact equality checks on scalar/list values
- Test 2: filesystem glob confirming file written to new dir
- Test 3: membership in computed set
- Test 5: status field equality after successful move
- Test 6: `pytest.raises(ValueError, match="backlog")` — type + message match

No `TestFromAC_*` modifications by builder (file authored entirely by #840 builder; #803 builder is pass-through only).

### Deductions
| Issue | Deduction |
|-------|-----------|
| Tests not run independently (WMI/logfire env crash) | −∞ (blocking) |
| Lint unverified via tool (only get_errors static check done) | −.02 |

### Verdict
**BLOCK** — Confidence: N/A (tests not run)

Cannot give PASS or FAIL without independent test execution. Code quality through inspection is high; infrastructure is the sole blocker.

### Action
Resolve WMI/logfire/protobuf hang in pytest environment before re-review. Once tests can run, expected outcome is PASS based on code inspection.
[[2026-04-13]]
## Environment Restored
pytest environment recovered (WMI hang resolved). Quality-Runner confirmed operational. Test results: all tests passed in batch run (`test_refresh_config_803.py`). Unblocked for review continuation.
[[2026-04-14]]
## Review Evidence

**Reviewer:** reviewer-mode (Claude Sonnet 4.6)
**Task:** #803 — Tests — refresh_config + config staleness fix
**Test file:** `tests/test_refresh_config_803.py` (6 tests, delivered by child #840 builder; #803 builder pass-through)
**Review cycle:** 2nd (cycle 1 blocked by env; environment confirmed restored)

---

### Test Execution (Quality-Runner, independent — 2026-04-14)
First attempt: FATAL (pywin32/WMI env hang — recurring Windows issue). Retry succeeded.
**6 passed, 0 failed** (exit code 0). Builder self-report of 6/6 confirmed.

### Lint
ruff: **clean** — 0 violations (`tests/test_refresh_config_803.py`). Exit code 0.
`get_errors` static check: clean on both test file and `serve/kanban/src/owlbear_kanban/engine.py`.

### Coverage
| Module | % | Notes |
|--------|---|-------|
| `owlbear_kanban.engine` | 33 | Expected — 6 tests cover refresh_config() only; rest covered by dedicated task suites |
| `owlbear_kanban.config_loader` | 91 | Config loading path well covered |

---

### AC Compliance Table

| AC | Mapped Test | Assertion | Would Fail If Violated? | Status |
|----|------------|-----------|------------------------|--------|
| AC1: reload YAML from disk | `test_refresh_config_reloads_yaml_from_disk` | `board_config().next_id == 999` | YES — exact equality | STRONG |
| AC2: update `_config`, `tasks_dir`, rank maps (`archive_dir` excluded per arch review) | Tests 1–4 | Exact value/list/glob assertions | YES | STRONG |
| AC3: `create_task` staleness | SKIP — arch-approved; covered by #828 tests | — | ACCEPTABLE |
| AC4: `move_task` validates against new statuses | Tests 5–6 | `record.status == "staging"` + `pytest.raises(ValueError, match="backlog")` | YES — type + message match | STRONG |
| AC5: Tests fail RED | MOOT — impl pre-existed (arch-approved) | — | ACCEPTABLE |

### Implementation Analysis
`refresh_config()` at engine.py L161-168:
```python
self._config = load_config(self._kanban_dir)
self._tasks_dir = self._kanban_dir / self._config.tasks_dir
self._archive_dir = self._kanban_dir / _ARCHIVE_DIR_NAME
```
- `_priority_rank()` and `_status_rank()` are on-demand computed from `self._config` — no eager cache. Correct.
- `move_task()` reads `{s["name"] for s in self._config.statuses}` live. Correct.
- All test assertions trace through correct code paths.

### TestFromAC Integrity
`TestFromAC_RefreshConfig` is a NEW class in a NEW file. #803 builder is verified pass-through — no prior TestFromAC_ classes to protect. PRESERVED.

### Security
All tests use `tmp_path`; no I/O beyond temp directory. No injection surface, no secrets, no shell. PASS.

### Deductions
| Finding | Deduction |
|---------|-----------|
| Quality-runner first attempt fatal (env issue — pywin32/WMI); retry succeeded | −0.01 |

### Verdict
Confidence: **0.99 → PASS**

[[2026-04-15]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `type:test` task — only `tests/test_refresh_config_803.py` added; no production code modified; copilot-instructions.md unchanged |
| 2 | Module docstrings | Yes | Verified | Module-level docstring with AC coverage map; class `TestFromAC_RefreshConfig` docstring; all 6 test method docstrings present and accurate |
| 3 | External attribution | No | N/A | Research doc sources all internal (engine.py, models.py, test_config_staleness_fix_828.py); no external repos or articles used |
| 4 | CLI changes | No | N/A | Test-only task; no CLI additions or modifications |
| 5 | Research doc | Yes | Verified | `.owlbear/research/refresh-config-tests-803.md` exists; linked in task body; follow-up #840 delivered 6 tests (GREEN, 0 failures) |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/803-*` files found)

[[2026-04-15]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: refresh_config() reloads YAML from disk | test_refresh_config_reloads_yaml_from_disk — next_id 100→999, asserts board_config().next_id == 999 | PASS |
| AC2: updates _config, tasks_dir, rank maps (archive_dir excluded per arch review) | Tests 1-4: exact equality, glob, set membership assertions | PASS |
| AC3: create_task staleness | SKIP — arch-approved; covered by test_config_staleness_fix_828.py | PASS (skip) |
| AC4: move_task validates new statuses after refresh | Tests 5-6: status equality + pytest.raises(ValueError, match="backlog") | PASS |
| AC5: Tests fail RED before implementation | MOOT — impl pre-existed (arch-approved) | PASS (moot) |

### Test Results
- pytest (task-scoped): 6 passed, 0 failed — exit 0
- pytest (full suite): 4385 passed, 193 failed, 8 skipped — all 193 failures in unrelated modules (pre-existing debt); zero failures in test_refresh_config_803.py
- ruff: clean — 0 violations

### Architect Quality: 4/5
AC was adequate. Arch review caught and corrected AC2 (archive_dir from constant, not config), properly skipped redundant AC3 (already covered by #828), and acknowledged AC5 as moot. Challenger cycle exercised. Minor gaps resolved during review, not improvised by builder.

### Deduction Breakdown
- AC lines: all evidenced or arch-approved exceptions — no deduction
- Lint: clean — no deduction
- AC quality 4/5 (> 3) — no deduction
- Reviewer evidence: present, detailed, PASS verdict — no deduction
- Full-suite failures in task scope: 0 — no deduction

### Confidence: 0.98
### Action: archive