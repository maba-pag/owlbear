---
id: 1172
title: Fix MCP server.py L481 status_names dict-form assumption
status: archived
priority: needed
created: 2026-04-28T22:52:50.258936+00:00
updated: 2026-04-29T03:49:12.643119+00:00
tags:
- scope:mcp-kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

Pre-existing bug: serve/mcp-kanban/src/owlbear_mcp_kanban/server.py L481 uses `s['name'] for s in board_config().statuses` but statuses is list[str] post-Brief-C. Raises TypeError, silently caught by contextlib.suppress(Exception). Guidance collection is broken on new-schema boards. Found during #1155 research. See .owlbear/research/1155-config-schema-grouping-validation.md §3.
[[2026-04-28]]

## Planning

Created follow-up task #1173 "Fix server.py L481 status_names dict-form and stale test mock" at backlog with tags scope:mcp-kanban, bugfix and priority needed. Task includes full AC and affected-file list from the research findings.
[[2026-04-28]]

## Research

- Research doc: .owlbear/research/1172-mcp-status-names-dict-form-bug.md
- Sources: 6 studied, 4 high-relevance (all internal)
- Recommendation: T1 trivial fix — replace dict subscript with direct list usage (confidence: .95)
- Follow-up tasks created: #1173 at backlog (fix server.py L481 + stale test mock)
- Decision requests: none

## Challenge Results

- Challenger: FALLBACK — trivial fix with .95 confidence; challenger adds no value
- Confidence in original: .95

## Key Findings

- server.py L481 `[s["name"] for s in statuses]` fails because statuses is list[str] post-Brief-C
- contextlib.suppress(Exception) silently swallows TypeError → move guidance broken
- Fix: `list(app_ctx.engine.board_config().statuses)` (1 line) + test mock correction (1 line)
- Cockpit routes/read.py already uses the correct pattern via config.status_names
[[2026-04-28]]

## Test-Writer Notes

- Test file: tests/test_server_1172.py
- Classes: TestFromAC_StatusNamesDictFormBug
- Tests per category: happy 3, edge 0, error 1, boundary 1
- Total: 5 tests, all FAIL
- ruff: clean

**Key finding:** The bug at L481 is in the *fallback* path. Normal operation uses `AgentView.move_task` which provides guidance correctly. The L481 code executes only when `agent_view = None`. Tests monkeypatch `engine.agent_view = None` to force the fallback, then verify that guidance is returned for forward-skips (currently fails because `s["name"]` on `list[str]` raises TypeError silently).

**AC coverage:**

| AC | Test(s) |
|----|---------|
| L481 fix: list[str] statuses → guidance populated for forward-skip | test_forward_skip_more_than_one_slot_returns_guidance, test_four_slot_forward_skip_returns_guidance |
| Guidance message references source/target status | test_forward_skip_guidance_contains_source_status, test_forward_skip_guidance_contains_target_status |
| collect_guidance called with list[str] status_names | test_collect_guidance_called_with_list_str_status_names |
[[2026-04-28]]

## Builder Notes

- Implementation: updated fallback guidance status-name extraction in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` from dict-form (`s["name"]`) to direct list-form (`list(board_config().statuses)`).
- Files changed: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`.
- Fix applied: ensures `collect_guidance` receives `list[str]` in the legacy/fallback `move_task` path when `agent_view` is unavailable.
- Test results (task-scoped): 5/5 `TestFromAC_StatusNamesDictFormBug` tests passed via quality-runner (`tests/test_server_1172.py`), 0 failed.
- Lint: ruff clean on changed source file and task test file.
- Coverage evidence: task-scoped coverage report for `owlbear_mcp_kanban.server` = 36% (single-task suite only). Expanded scoped regression run across `serve/mcp-kanban/tests/` + task test reached 73% on `owlbear_mcp_kanban.server` and surfaced 5 pre-existing failures in historical guidance suites outside this task contract.
- Regression scope: verified task AC behavior in fallback path (forward-skip guidance populated and `collect_guidance` called with `list[str]`).
- Commit: `8c65d68a` — `fix: handle list-status guidance fallback (#1172, builder)`.

### Reflection

- Problem faced: coverage target on a large legacy server module is not reachable with strictly task-scoped tests.
- Workaround applied: ran an expanded scoped regression set to increase confidence without broadening code changes.
- Pattern discovered: fallback-path bugs can remain hidden due to `contextlib.suppress(Exception)` and require explicit forced-path tests.
- Quality gap: adjacent historical guidance tests are currently unstable and reduce confidence in broader scoped runs for unrelated tasks.
[[2026-04-29]]

## Review Evidence

### Test Results

- pytest: 5 passed, 0 failed via quality-runner on [tests/test_server_1172.py](tests/test_server_1172.py)

### Lint

- ruff: clean on [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py) and [tests/test_server_1172.py](tests/test_server_1172.py)

### Coverage

- Module owlbear_mcp_kanban.server: 36% via quality-runner
- Coverage remains below the 90% review target

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| [task AC 1](.owlbear/kanban/tasks/1172-fix-mcp-server-py-l481-status-names-dict-form-assumption.md#L55) | [tests/test_server_1172.py](tests/test_server_1172.py#L136), [tests/test_server_1172.py](tests/test_server_1172.py#L216) | Yes. The suite forces the fallback path at [tests/test_server_1172.py](tests/test_server_1172.py#L114) and asserts non-empty guidance at [tests/test_server_1172.py](tests/test_server_1172.py#L146) and [tests/test_server_1172.py](tests/test_server_1172.py#L227). | COVERED |
| [task AC 2](.owlbear/kanban/tasks/1172-fix-mcp-server-py-l481-status-names-dict-form-assumption.md#L56) | [tests/test_server_1172.py](tests/test_server_1172.py#L151), [tests/test_server_1172.py](tests/test_server_1172.py#L168) | Yes. Source and target text are asserted at [tests/test_server_1172.py](tests/test_server_1172.py#L163) and [tests/test_server_1172.py](tests/test_server_1172.py#L180). | COVERED |
| [task AC 3](.owlbear/kanban/tasks/1172-fix-mcp-server-py-l481-status-names-dict-form-assumption.md#L57) | [tests/test_server_1172.py](tests/test_server_1172.py#L187) | No. [tests/test_server_1172.py](tests/test_server_1172.py#L205) defaults missing status_names to [], so [tests/test_server_1172.py](tests/test_server_1172.py#L206) and [tests/test_server_1172.py](tests/test_server_1172.py#L209) still pass if [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L483) stops forwarding the kwarg. | LAX |

#### Security Review

- No issues found in the changed fallback guidance block at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L481) and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L483)

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| [tests/test_server_1172.py](tests/test_server_1172.py#L123) | No weakening is visible in the current TestFromAC snapshot. | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | [tests/test_server_1172.py](tests/test_server_1172.py#L205) substitutes [] for missing status_names, so the AC3 test cannot distinguish correct forwarding from omission at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L483). |
| Negative/error-path coverage | ADEQUATE | The fallback path is forced at [tests/test_server_1172.py](tests/test_server_1172.py#L114), and collect_guidance reachability is checked at [tests/test_server_1172.py](tests/test_server_1172.py#L201). |
| Manual mutation reasoning | WEAK | Removing status_names=status_names at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L483) would still keep the current AC3 test green. |
| Test independence | STRONG | Fresh temp-board fixture per test at [tests/test_server_1172.py](tests/test_server_1172.py#L103). |
| Descriptive names | STRONG | The task-owned tests at [tests/test_server_1172.py](tests/test_server_1172.py#L136), [tests/test_server_1172.py](tests/test_server_1172.py#L151), [tests/test_server_1172.py](tests/test_server_1172.py#L168), [tests/test_server_1172.py](tests/test_server_1172.py#L187), and [tests/test_server_1172.py](tests/test_server_1172.py#L216) are clear and branch-specific. |

#### Data Safety

- No issues found. The changed block computes in-memory guidance after the move and does not broaden persistent-state risk at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L468), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L481), and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L482).

#### Implementation-Aware Gaps

- No task-owned assertion requires status_names to be present in mock_cg.call_args without a default or equal the configured ordered board status list declared in [tests/test_server_1172.py](tests/test_server_1172.py#L44).
- No task-owned assertion binds the result.guidance assignment at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L482); the patched collect_guidance return value is never asserted against result.guidance.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1, starting at [task 1172 body](.owlbear/kanban/tasks/1172-fix-mcp-server-py-l481-status-names-dict-form-assumption.md#L59) |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- The implementation itself matches the reported fix: the fallback materializes board statuses with list(...) at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L481) and forwards them into collect_guidance at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L483).
- The task-owned suite precisely forces the fallback path by disabling AgentView at [tests/test_server_1172.py](tests/test_server_1172.py#L114).

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| [task AC 1](.owlbear/kanban/tasks/1172-fix-mcp-server-py-l481-status-names-dict-form-assumption.md#L55) | Fallback forced at [tests/test_server_1172.py](tests/test_server_1172.py#L114); non-empty guidance assertions at [tests/test_server_1172.py](tests/test_server_1172.py#L146) and [tests/test_server_1172.py](tests/test_server_1172.py#L227); independent run: 5 passed, 0 failed | [tests/test_server_1172.py](tests/test_server_1172.py#L136), [tests/test_server_1172.py](tests/test_server_1172.py#L216) | PASS |
| [task AC 2](.owlbear/kanban/tasks/1172-fix-mcp-server-py-l481-status-names-dict-form-assumption.md#L56) | Source and target substrings asserted at [tests/test_server_1172.py](tests/test_server_1172.py#L163) and [tests/test_server_1172.py](tests/test_server_1172.py#L180); independent run green | [tests/test_server_1172.py](tests/test_server_1172.py#L151), [tests/test_server_1172.py](tests/test_server_1172.py#L168) | PASS |
| [task AC 3](.owlbear/kanban/tasks/1172-fix-mcp-server-py-l481-status-names-dict-form-assumption.md#L57) | collect_guidance reachability is asserted at [tests/test_server_1172.py](tests/test_server_1172.py#L201), but the proof of forwarded status_names is lax because [tests/test_server_1172.py](tests/test_server_1172.py#L205) defaults to []; the changed forwarding line is [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L483) | [tests/test_server_1172.py](tests/test_server_1172.py#L187) | FAIL |

### Deductions

- -0.12: Test quality is WEAK for AC 3 because omission of the changed kwarg still passes.
- -0.05: No test binds the patched collect_guidance return to result.guidance.
- -0.05: Module coverage is 36%, below the 90% review target.

### Verdict

- FAIL with confidence 0.78

### Action

- Reject to backlog. The implementation fix appears correct, but the existing TestFromAC proof for AC 3 is too weak to sustain a PASS. Strengthen AC 3 so it fails when status_names is omitted or reordered, and add a direct proof that the patched collect_guidance return is written into result.guidance.
[[2026-04-29]]

## Architecture Review (cycle 2 — post-reviewer rejection)

### Context

Reviewer rejected at confidence 0.78. Two specific gaps cited:

1. AC 3 test defaults missing `status_names` to `[]` — test passes even when kwarg is omitted
2. No test binds `collect_guidance` return value to `result.guidance`

Implementation fix (commit `8c65d68a`) is correct and already merged. Only test strengthening is needed.

### Refined AC

1. *(unchanged)* `move_task` forward-skip (>1 slot) returns non-empty guidance when `board_config().statuses` is `list[str]` and the AgentView fallback path is active.
2. *(unchanged)* Guidance message references both the source and target status names.
3. *(refined)* `collect_guidance` is called with `status_names` equal to the board's configured ordered status list — assert the exact value matches `list(board_config().statuses)`, not just type. Test must fail if `status_names` kwarg is omitted or contents differ. Do NOT use `kwargs.get("status_names", [])` with a default — use `kwargs["status_names"]` or assert the key is present before reading.
4. *(new)* The return value of `collect_guidance` is assigned to `result.guidance` — mock `collect_guidance` to return a sentinel list (e.g. `["sentinel"]`) and assert `result.guidance` equals it.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One bug fix, one fallback path |
| Interface clarity | PASS (after refinement) | AC 3 now requires exact value assertion; AC 4 covers return wiring |
| Dependency correctness | PASS | No dependencies |
| Module layering | PASS | No new imports, existing module boundary respected |
| TDD compliance | PASS | Test file exists at `tests/test_server_1172.py` |
| KISS/YAGNI | PASS | One-line fix, no new abstractions |
| Premise challenge | PASS | Real bug confirmed — `s["name"]` on `list[str]` raises TypeError, silently swallowed |
| Pattern consistency | PASS | Matches cockpit routes/read.py pattern (`config.status_names`) |
| Security surface | PASS | No new system boundaries; in-memory guidance computation only |
| Single domain | PASS | `scope:mcp-kanban` only |

### Challenge Results

- Challenger: SKIPPED — REFINE verdict (optional per w-arch-review Step 2.5)

### Verdict: REFINE → APPROVE

### Action Taken

Refined AC 3 to require exact-value assertion (not type-check with default). Added AC 4 for `collect_guidance` return-value wiring proof. Implementation is already committed — only test strengthening needed in this cycle.
[[2026-04-29]]
REFINE→APPROVE: Refined AC 3 (exact-value assertion, no default masking) and added AC 4 (collect_guidance return wiring proof). Implementation fix already committed — only test strengthening needed this cycle.
[[2026-04-29]]

## Test-Writer Notes

- Test file: tests/test_server_1172.py
- Classes: TestFromAC_StatusNamesDictFormBug
- Tests per category: happy 3, edge 0, error 1 (existing), boundary 1 (existing), strict-AC3 1 (new), AC4 1 (new)
- Total: 7 tests, all PASS (implementation already merged at commit 8c65d68a)
- ruff: clean

**Retry context:** Implementation fix is already committed. This cycle strengthens two gaps cited by reviewer.

**Changes (retry — new tests only, existing 5 preserved):**

1. `test_collect_guidance_receives_exact_board_status_list` — uses `kwargs["status_names"]` (no default) and asserts exact value equals `list(engine.board_config().statuses)`. Fails if kwarg omitted (KeyError) or contents differ.
2. `test_collect_guidance_return_value_assigned_to_result_guidance` — mocks `collect_guidance` to return `["sentinel-guidance-item"]`, asserts `result.guidance == sentinel`. Fails if assignment line removed.

**AC coverage:**

| AC | Test(s) |
|----|---------|
| AC1: forward-skip returns non-empty guidance (fallback) | test_forward_skip_more_than_one_slot_returns_guidance, test_four_slot_forward_skip_returns_guidance |
| AC2: guidance references source and target status names | test_forward_skip_guidance_contains_source_status, test_forward_skip_guidance_contains_target_status |
| AC3 (strict): collect_guidance called with exact board status list | test_collect_guidance_called_with_list_str_status_names (existing type check), test_collect_guidance_receives_exact_board_status_list (new exact-value) |
| AC4: collect_guidance return value assigned to result.guidance | test_collect_guidance_return_value_assigned_to_result_guidance |
[[2026-04-29]]

## Planning

Created follow-up task #1170 at backlog:

| ID | Title | Status | Priority | Tags |
|----|-------|--------|----------|------|
| 1170 | Stabilize MCP server guidance suites and raise server module coverage gate | backlog | needed | scope:mcp-kanban, quality, testing |

AC covers: (1) fix pre-existing failures in guidance/lifecycle server suites, (2) establish stable scoped test set for server, (3) ≥90% module coverage gate, (4) document canonical quality-runner test_paths list.
[[2026-04-29]]

## Review Evidence

### Test Results

- pytest: 7 passed, 0 failed via quality-runner on [tests/test_server_1172.py](tests/test_server_1172.py)

### Lint

- ruff: clean on [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py) and [tests/test_server_1172.py](tests/test_server_1172.py)

### Coverage

- Module `owlbear_mcp_kanban.server`: 36% via quality-runner
- Residual risk only: the changed fallback guidance block is directly and specifically proved by task-owned tests, and broader module-coverage debt is already split into follow-up task #1170.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| [task AC 1](.owlbear/kanban/tasks/1172-fix-mcp-server-py-l481-status-names-dict-form-assumption.md#L157) | [tests/test_server_1172.py](tests/test_server_1172.py#L136), [tests/test_server_1172.py](tests/test_server_1172.py#L216) | Yes. The suite forces the fallback path via [tests/test_server_1172.py](tests/test_server_1172.py#L114) and requires non-empty guidance at [tests/test_server_1172.py](tests/test_server_1172.py#L146) and [tests/test_server_1172.py](tests/test_server_1172.py#L227). Reintroducing dict-form extraction at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L481) would break these assertions. | COVERED |
| [task AC 2](.owlbear/kanban/tasks/1172-fix-mcp-server-py-l481-status-names-dict-form-assumption.md#L158) | [tests/test_server_1172.py](tests/test_server_1172.py#L151), [tests/test_server_1172.py](tests/test_server_1172.py#L168) | Yes. Source and target status names are required at [tests/test_server_1172.py](tests/test_server_1172.py#L163) and [tests/test_server_1172.py](tests/test_server_1172.py#L180). | COVERED |
| [task AC 3](.owlbear/kanban/tasks/1172-fix-mcp-server-py-l481-status-names-dict-form-assumption.md#L159) | [tests/test_server_1172.py](tests/test_server_1172.py#L187), [tests/test_server_1172.py](tests/test_server_1172.py#L234) | Yes. The strict proof requires the kwarg to exist at [tests/test_server_1172.py](tests/test_server_1172.py#L255) and exact ordered equality at [tests/test_server_1172.py](tests/test_server_1172.py#L256), so omission or reordering of `status_names` from [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L482) fails. | COVERED |
| [task AC 4](.owlbear/kanban/tasks/1172-fix-mcp-server-py-l481-status-names-dict-form-assumption.md#L160) | [tests/test_server_1172.py](tests/test_server_1172.py#L263) | Yes. The sentinel return from `collect_guidance` is asserted against `result.guidance` at [tests/test_server_1172.py](tests/test_server_1172.py#L279), so removing the assignment at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L482) fails. | COVERED |

#### Security Review

- No issues found in the changed fallback guidance block at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L481) and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L482).

#### Test Integrity

| AC-scoped proof | Evidence | Assessment |
|-----------------|----------|------------|
| Exact ordered `status_names` forwarding | [tests/test_server_1172.py](tests/test_server_1172.py#L234), [tests/test_server_1172.py](tests/test_server_1172.py#L255), [tests/test_server_1172.py](tests/test_server_1172.py#L256) | STRENGTHENED |
| Direct `result.guidance` passthrough | [tests/test_server_1172.py](tests/test_server_1172.py#L263), [tests/test_server_1172.py](tests/test_server_1172.py#L279) | STRENGTHENED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact equality on ordered `status_names` at [tests/test_server_1172.py](tests/test_server_1172.py#L256) and on `result.guidance` passthrough at [tests/test_server_1172.py](tests/test_server_1172.py#L279). |
| Negative/error-path coverage | ADEQUATE | The suite explicitly disables `agent_view` at [tests/test_server_1172.py](tests/test_server_1172.py#L114) to force the formerly broken fallback path. |
| Manual mutation reasoning | STRONG | Omitting `status_names` breaks [tests/test_server_1172.py](tests/test_server_1172.py#L255) and [tests/test_server_1172.py](tests/test_server_1172.py#L256); removing assignment at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L482) breaks [tests/test_server_1172.py](tests/test_server_1172.py#L279). |
| Test independence | STRONG | Fresh temp-board fixture per test at [tests/test_server_1172.py](tests/test_server_1172.py#L103). |
| Descriptive names | STRONG | Branch-specific test names at [tests/test_server_1172.py](tests/test_server_1172.py#L136), [tests/test_server_1172.py](tests/test_server_1172.py#L234), and [tests/test_server_1172.py](tests/test_server_1172.py#L263). |

#### Data Safety

- No issues found. The touched code computes in-memory guidance after the move and does not broaden persisted-state or concurrency risk at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L467), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L481), and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L482).

#### Implementation-Aware Gaps

- No task-local gaps remain in the changed behavior. The fallback path, ordered `status_names` forwarding, and `result.guidance` assignment are each directly bound by task-owned tests.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- The module-level AC summary in [tests/test_server_1172.py](tests/test_server_1172.py#L20) still lists only the original three AC items, while direct AC4 proof now exists later in the file.
- The class docstring in [tests/test_server_1172.py](tests/test_server_1172.py#L123) still describes the pre-fix failing state; non-blocking, but stale.
- The earlier helper test at [tests/test_server_1172.py](tests/test_server_1172.py#L187) still uses a defaulted `kwargs.get("status_names", [])`; non-blocking because the stricter proof at [tests/test_server_1172.py](tests/test_server_1172.py#L234) closes the gap.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| [task AC 1](.owlbear/kanban/tasks/1172-fix-mcp-server-py-l481-status-names-dict-form-assumption.md#L157) | Fallback forced at [tests/test_server_1172.py](tests/test_server_1172.py#L114); non-empty guidance asserted at [tests/test_server_1172.py](tests/test_server_1172.py#L146) and [tests/test_server_1172.py](tests/test_server_1172.py#L227); quality-runner: 7 passed, 0 failed | [tests/test_server_1172.py](tests/test_server_1172.py#L136), [tests/test_server_1172.py](tests/test_server_1172.py#L216) | PASS |
| [task AC 2](.owlbear/kanban/tasks/1172-fix-mcp-server-py-l481-status-names-dict-form-assumption.md#L158) | Source and target substrings asserted at [tests/test_server_1172.py](tests/test_server_1172.py#L163) and [tests/test_server_1172.py](tests/test_server_1172.py#L180); quality-runner green | [tests/test_server_1172.py](tests/test_server_1172.py#L151), [tests/test_server_1172.py](tests/test_server_1172.py#L168) | PASS |
| [task AC 3](.owlbear/kanban/tasks/1172-fix-mcp-server-py-l481-status-names-dict-form-assumption.md#L159) | Exact ordered list asserted via [tests/test_server_1172.py](tests/test_server_1172.py#L255) and [tests/test_server_1172.py](tests/test_server_1172.py#L256) against the forwarding site at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L482) | [tests/test_server_1172.py](tests/test_server_1172.py#L234) | PASS |
| [task AC 4](.owlbear/kanban/tasks/1172-fix-mcp-server-py-l481-status-names-dict-form-assumption.md#L160) | Sentinel passthrough asserted at [tests/test_server_1172.py](tests/test_server_1172.py#L279) against the assignment line at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L482) | [tests/test_server_1172.py](tests/test_server_1172.py#L263) | PASS |

### Deductions

- -0.05: Module coverage for `owlbear_mcp_kanban.server` remains 36% in the task-scoped run, below the nominal 90% target. This is retained as residual risk, not a gate failure, because the changed fallback block is directly covered and broader server-coverage debt is already tracked in #1170.

### Verdict

- PASS with confidence 0.93

### Action

- Advance to docs. No blocking implementation or test-quality defects remain for the refined AC.
[[2026-04-29]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | `serve/mcp-kanban/README.md` `### guidance Field` section is still accurate — fix is an internal fallback-path repair; no API shape, CLI, or config changes. |
| 2 | Module docstrings | Yes | N/A | `move_task` docstring ("Move a task to the specified status column…") and module docstring remain accurate. No changed public interface. |
| 3 | External attribution | No | N/A | Research doc confirms all 4 sources internal. |
| 4 | Research doc | Yes | N/A | `.owlbear/research/1172-mcp-status-names-dict-form-bug.md` exists and is linked in task body. |
| 5 | Diagram maintenance | Yes | Updated | `share/diagrams/kanban.excalidraw` (`describes: serve/mcp-kanban/src/**`) and `share/diagrams/mcp-topology.excalidraw` (`describes: serve/mcp-*/src/**`) footers updated to `Last verified: 2026-04-29 (aff6a392)`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs detected. |

### Files Updated

- `share/diagrams/kanban.excalidraw` — footer updated
- `share/diagrams/mcp-topology.excalidraw` — footer updated
- Commit: `de164ee7`

### Child Tasks Created

None.

### Scratch Files Cleaned

None found (no `.owlbear/scratch/1172-*` files).
[[2026-04-29]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: forward-skip returns non-empty guidance (fallback) | Fallback forced at test_server_1172.py:L114; non-empty guidance asserted at L146, L227; full suite: 0 task-scope failures | PASS |
| AC2: guidance references source/target status names | Source/target substrings asserted at L163, L180 | PASS |
| AC3: collect_guidance called with exact ordered status list | kwargs["status_names"] (no default) at L255; exact equality at L256 vs list(board_config().statuses) | PASS |
| AC4: collect_guidance return value assigned to result.guidance | Sentinel passthrough asserted at L279 | PASS |

### Test Results

- pytest: 2848 passed, 26 failed (all pre-existing, 0 in task scope), 4 skipped
- ruff: 4 violations (all outside task scope: knowledge, mcp-knowledge, mcp-memory, orchestrator)

### Architect Quality: 3/5

Initial AC3 did not mandate exact-value assertion or prohibit default masking, allowing a lax test (kwargs.get with default []) that required a full reject/refine cycle. Cycle 2 refinement was responsive and correct.

### Deduction Breakdown

- AC quality score 3 (leq 3): -0.03
- No other deductions (all AC lines evidenced, reviewer section present and detailed, no task-scope lint or test failures)

### Confidence: 0.97

### Action: archive

### Commits Verified

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 4e49649f | test | tests/test_server_1172.py | #1172 |
| 8c65d68a | fix | serve/mcp-kanban/src/owlbear_mcp_kanban/server.py | #1172 |
| 056b3999 | test | tests/test_server_1172.py | #1172 |
| de164ee7 | docs | share/diagrams/kanban.excalidraw, share/diagrams/mcp-topology.excalidraw | #1172 |
