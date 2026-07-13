---
id: 1349
title: Add MCP KANBAN_DIR board binding validation
status: archived
priority: medium
created: 2026-05-04T18:17:29.608220+00:00
updated: 2026-05-05T09:28:10.835840+00:00
tags:
- sync-blocker
- mcp-kanban
- config
- dev-experience
parent:
depends_on:
- 1337
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

The MCP kanban server binds to `Path(".owlbear/kanban")` relative to the process working directory. That likely works when VS Code starts the server from a single project root, but it is implicit, hard to diagnose when wrong, and unlike Cockpit's explicit `KANBAN_DIR` override. It also makes dev-code smoke tests and multi-root/project layouts more brittle than they need to be.

Audit decision: add explicit `KANBAN_DIR` support and startup validation to MCP.

## Acceptance Criteria

1. MCP `app_lifespan` reads `KANBAN_DIR` env var when set (non-empty); otherwise preserves the current default of `.owlbear/kanban` relative to process working directory. (td:2)
2. Relative `KANBAN_DIR` values are resolved to absolute paths relative to process working directory. `AppContext.kanban_dir` always stores the resolved absolute path. (td:2)
3. Startup validates before `engine.sweep()`: (a) the resolved kanban directory exists (`is_dir()`), (b) `KanbanEngine` construction succeeds (which validates `config.yml` via `load_config`), (c) `engine.tasks_dir` exists (`is_dir()`). No duplicate validation of `config.yml` — the engine owns that check. (td:2)
4. On startup failure, the raised exception names the resolved kanban directory path and includes `KANBAN_DIR` as the remediation env var. Exceptions propagate through `mcp.run()` — no stderr writes needed. (td:1)
5. `engine.sweep()` runs only after the intended board is selected and all AC3 validation passes. (td:1)
6. Tests prove: default cwd binding, `KANBAN_DIR` override binding, relative path resolution to absolute, and invalid/missing path failure with actionable message. (td:0)
7. Docs: `serve/mcp-kanban/README.md` and `share/skills/h-mcp-kanban/SKILL.md` mention the optional `KANBAN_DIR` override. Seed config (`seed/.vscode/mcp.json`) unchanged. (td:0)
8. Cross-task enablement: the override mechanism is sufficient for `#1347` to bind MCP to an isolated test board without relying on process cwd. (td:0)

## Key Files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — `app_lifespan`, `AppContext`
- `serve/mcp-kanban/src/owlbear_mcp_kanban/__main__.py` — bare `mcp.run()`, exceptions propagate
- `serve/mcp-kanban/README.md`
- `share/skills/h-mcp-kanban/SKILL.md`
- `seed/.vscode/mcp.json` — unchanged
- `serve/mcp-kanban/tests/`

## Architecture Notes

- **Cockpit pattern reference**: Cockpit's `main.py` reads `KANBAN_DIR` → fallback → `is_dir()` check → engine init. MCP should follow the same env-var semantics but error delivery differs: Cockpit writes stderr + sys.exit; MCP raises from lifespan and exceptions propagate through `mcp.run()`.
- **Validation layering**: Pre-engine: `is_dir()` on resolved path. Engine construction: owns `config.yml` validation (via `load_config` → `FileNotFoundError`). Post-engine: `engine.tasks_dir.is_dir()` (public property). No access to `_archive_dir` (private) — archive validation is engine-internal.
- **Existing engine behavior**: `KanbanEngine.__init__` calls `load_config()` which raises `FileNotFoundError` if `config.yml` absent. Engine does NOT validate tasks_dir/archive_dir existence — it tolerates absent directories (glob returns empty). AC3(c) adds explicit tasks_dir existence check at MCP startup layer.
- **`__main__.py`**: Bare `mcp.run()` — lifespan exceptions propagate as Python tracebacks to the MCP client's stderr log. AC4 ensures exception messages are actionable.

## Audit Evidence

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` defines `_DEFAULT_KANBAN_DIR = Path(".owlbear/kanban")` and does not read `KANBAN_DIR`.
- Cockpit already supports `KANBAN_DIR`, so MCP and Cockpit have inconsistent board-selection behavior.
- A wrong process cwd can silently bind MCP tools to the wrong board or fail without an actionable configuration path.

## Source

Deployment audit finding group 6, 2026-05-04.

[[2026-05-05]]
## Architecture Review

### Verdict: APPROVED → todo

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC1: KANBAN_DIR env read with default fallback | Precise, testable. Matches Cockpit semantics. | Annotated (td:2) |
| AC2: Relative resolution to absolute, stored in AppContext | Refined — original said "resolved predictably," now specifies absolute resolution and AppContext contract. | Annotated (td:2) |
| AC3: Three-layer startup validation | Refined — decomposed into (a) is_dir, (b) engine construction owns config.yml, (c) tasks_dir existence. Eliminated duplicate validation risk flagged by challenger. Dropped archive_dir (private API). | Annotated (td:2) |
| AC4: Actionable failure messages | Refined — clarified exception-based delivery through mcp.run(), not stderr writes. | Annotated (td:1) |
| AC5: sweep() ordering | Clear, testable. | Annotated (td:1) |
| AC6: Test matrix | Meta-criterion describing test scenarios from AC1-4. | Annotated (td:0) |
| AC7: Docs update | Scoped to README + skill doc. Seed config explicitly unchanged. | Annotated (td:0) |
| AC8: Cross-task enablement for #1347 | Enablement criterion, not implementation. | Annotated (td:0) |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: KANBAN_DIR env support + startup validation for MCP kanban |
| Interface clarity | PASS | Inputs (env var), behavior (resolution, validation layers), outputs (AppContext.kanban_dir, exceptions) all specified |
| Dependency correctness | PASS | #1337 (task ID validation) is archived/done |
| Module layering | PASS | Changes within mcp-kanban; reads from kanban engine public API (tasks_dir property). No upward imports |
| TDD compliance | PASS | Test-writer will process — AC1-5 have td:1+ annotations |
| KISS/YAGNI | PASS | Minimal scope: env read + path resolution + 3 existence checks + wrap exceptions |
| Premise challenge | PASS | Cockpit already has KANBAN_DIR; MCP inconsistency is a real operational gap per audit evidence |
| Pattern consistency | PASS | Follows Cockpit env-var pattern; error delivery adapted for MCP lifespan (exceptions vs stderr) |
| Security surface | PASS | KANBAN_DIR is env-var only, no user-facing input. Engine's validate_path_containment handles traversal |
| Single domain | PASS | MCP kanban server configuration |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| KANBAN_DIR → non-existent path | is_dir() fails | Custom with path + remediation | Yes (AC3a, AC4) | Actionable error message |
| KANBAN_DIR → dir without config.yml | Engine load_config fails | FileNotFoundError wrapped with context | Yes (AC3b, AC4) | Names resolved dir + KANBAN_DIR hint |
| KANBAN_DIR → valid config but no tasks/ | tasks_dir.is_dir() fails | Custom with path + remediation | Yes (AC3c, AC4) | Actionable error message |
| KANBAN_DIR unset, wrong cwd | Same as above but default path | Same handling | Yes (AC1) | Error names default path + KANBAN_DIR |

### Challenger Results

Challenger returned `reconsider` (0.69). Key concerns addressed:
1. **Duplicate validation risk** — refined AC3 to explicit three-layer model: MCP owns is_dir() + tasks_dir check, engine owns config.yml. No overlap.
2. **Error delivery** — refined AC4 to specify exception propagation through mcp.run(), not stderr.
3. **Private API access** — dropped archive_dir from AC3 (engine-private). Only public `engine.tasks_dir` used.
4. **Cockpit pattern overstatement** — Architecture Notes clarify where MCP diverges from Cockpit (error delivery mechanism).
[[2026-05-05]]
## Test-Writer Notes

- **Test file:** `serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py`
- **Classes:** `TestFromAC_KanbanDirBinding`, `TestFromAC_StartupValidation`, `TestFromAC_SweepOrdering`
- **Total tests:** 15, all FAIL against current code
- **Lint:** clean (ruff 0 violations)
- **Commit:** f46f7908

### Tests per category

| Class | Tests | Categories |
|-------|-------|-----------|
| `TestFromAC_KanbanDirBinding` | 6 | happy (env override, default fallback, empty fallback), edge (relative→absolute, always absolute, absolute stored correctly) |
| `TestFromAC_StartupValidation` | 6 | error (missing dir, no config, no tasks_dir), happy (valid board), boundary (message has path, message has KANBAN_DIR) |
| `TestFromAC_SweepOrdering` | 3 | error (no sweep if dir missing, no sweep if tasks_dir missing), happy (sweep after validation with correct path) |

### AC coverage

| AC | Tests |
|----|-------|
| AC1 (td:2) — KANBAN_DIR env read / fallback | 3 tests |
| AC2 (td:2) — Relative→absolute resolution, always absolute | 3 tests |
| AC3 (td:2) — 3-layer validation (is_dir / engine / tasks_dir) | 4 tests |
| AC4 (td:1) — Actionable message (path + KANBAN_DIR) | 2 tests |
| AC5 (td:1) — sweep() ordering | 3 tests |
| AC6–AC8 (td:0) | skipped |

### Failure modes (current code)

- AC1/AC2: `kanban_dir` stored as relative `Path(".owlbear/kanban")` — `is_absolute()` False, not matching KANBAN_DIR override → AssertionError
- AC3a/AC3b: Exception message references default path, not KANBAN_DIR path → regex match fails
- AC3c: No tasks_dir check in current lifespan → no exception raised → pytest.raises DID NOT RAISE
- AC4: Same as AC3a — message doesn't include KANBAN_DIR var name
- AC5 ordering: Current code ignores KANBAN_DIR; either no exception raised or engine called with wrong path → AssertionError
[[2026-05-05]]
## Builder Notes
- Files changed: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, `serve/mcp-kanban/README.md`, `share/skills/h-mcp-kanban/SKILL.md`
- Implementation summary:
  - Added `KANBAN_DIR` environment binding with empty-string fallback to default `.owlbear/kanban`.
  - Added absolute path resolution for selected board path and stored resolved absolute path in `AppContext.kanban_dir`.
  - Added startup validation before `engine.sweep()`:
    - `kanban_dir.is_dir()` must be true.
    - `KanbanEngine(kanban_dir)` must construct successfully (engine-owned `config.yml` validation).
    - `engine.tasks_dir.is_dir()` must be true.
  - Added actionable startup exception messages that include the resolved board path and `KANBAN_DIR` remediation guidance.
  - Updated docs to mention optional `KANBAN_DIR` override (`README` + `h-mcp-kanban`).
- Test evidence:
  - RED verified first (quality-runner): 15 failed / 0 passed in `serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py`.
  - GREEN verification (quality-runner scoped): 15 passed / 0 failed / 0 skipped.
- Lint evidence:
  - Ruff scoped on changed source + task test: clean (0 violations).
- Coverage evidence:
  - Scoped coverage report for `owlbear_mcp_kanban.server`: 32% (task-scoped test file).
  - Additional package-level probe raised module coverage to 74% but surfaced unrelated pre-existing failures in guidance suites; task gating kept to scoped run.
- Commit:
  - `1472b3d6` — `feat: add KANBAN_DIR startup binding validation (#1349, builder)`
- Post-task reflection:
  - AC was tightly aligned to tests; minimal server-layer change satisfied all behavior requirements.
  - Startup validation split (directory, engine-init, tasks_dir) avoided duplicate config validation and matched architecture notes.
  - A broad package run remains useful for regression visibility but currently includes unrelated failing tests; scoped evidence isolates task correctness.
[[2026-05-05]]
## Review Evidence
### Test Results
- Scoped quality-runner pass: 15 passed, 0 failed, 0 skipped in [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py)
- Ruff clean on [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py) and [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py)
- Module coverage reported as 32% for [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py). Non-blocking here because the changed startup slice at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L75), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L82), and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L146) is exercised directly by the task-local tests.

### Scope Checks
- Test-writer and builder commits are present in [.git/logs/HEAD](.git/logs/HEAD#L1924) and [.git/logs/HEAD](.git/logs/HEAD#L1926).
- No prior Review Evidence section exists in [.owlbear/kanban/tasks/1349-add-mcp-kanban-dir-board-binding-validation.md](.owlbear/kanban/tasks/1349-add-mcp-kanban-dir-board-binding-validation.md), so this is the first review failure.
- Commit diff and dirty-tree contamination checks were not available from this tool surface. I applied a small confidence deduction for TestFromAC immutability and contamination certainty; no weakening is visible in the current test file.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L75) and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L148) read KANBAN_DIR with default fallback; tests assert env override, no-env fallback, and empty-string fallback at [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L104), [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L123), and [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L144). | TestFromAC_KanbanDirBinding | PASS |
| AC2 | [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L78) resolves to an absolute path and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L163) stores it in AppContext; tests assert absolute resolution and storage at [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L165), [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L185), and [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L203). | TestFromAC_KanbanDirBinding | PASS |
| AC3 | The implementation validates in order at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L151), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L155), and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L159); tests cover the three branches at [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L232), [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L247), and [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L263). Proof is weaker than ideal for the pre-engine ordering claim, but current implementation complies. | TestFromAC_StartupValidation | PASS |
| AC4 | All startup failures route through [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L82), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L152), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L157), and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L160), but the tests only assert resolved-path text for the engine-init branch at [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L247) and only a bare exception for the missing-tasks-dir branch at [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L278). If KANBAN_DIR remediation text disappeared on either branch, the suite would still pass. Bare propagation through mcp.run is present at [serve/mcp-kanban/src/owlbear_mcp_kanban/__main__.py](serve/mcp-kanban/src/owlbear_mcp_kanban/__main__.py#L8). | TestFromAC_StartupValidation | FAIL |
| AC5 | sweep runs only after validation in [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L162); negative and positive ordering tests are at [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L337), [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L363), and [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L392). | TestFromAC_SweepOrdering | PASS |
| AC6 | The test matrix proves default cwd binding, env override, and relative-to-absolute resolution, but it does not fully prove actionable failure messaging across the startup-failure branches for AC4. | TestFromAC_KanbanDirBinding; TestFromAC_StartupValidation | FAIL |
| AC7 | The docs mention the optional override at [serve/mcp-kanban/README.md](serve/mcp-kanban/README.md#L111), [serve/mcp-kanban/README.md](serve/mcp-kanban/README.md#L113), and [share/skills/h-mcp-kanban/SKILL.md](share/skills/h-mcp-kanban/SKILL.md#L11). Current [seed/.vscode/mcp.json](seed/.vscode/mcp.json) contains no KANBAN_DIR override. | Direct file inspection | PASS |
| AC8 | The resolved board path selected at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L148) is passed into the engine at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L155) and stored in context at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L163), which is sufficient for isolated-board binding without depending on default cwd selection. | Direct code inspection | PASS |

### Findings
- Weak proof on the missing-tasks-dir branch: [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L278) uses a bare pytest.raises(Exception), so it would pass on any exception and does not prove the actionable-message requirement for the branch implemented at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L159).
- AC4 is only strongly asserted on the missing-board path. The engine-init branch test at [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L247) matches only the resolved path, not the KANBAN_DIR remediation text required by AC4.
- The pre-engine wording in [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L237) is not directly asserted; the test body at [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L242) proves the raise, but not that KanbanEngine was not called.

### Deductions
- 0.08: AC4 proof incomplete across engine-init and missing-tasks-dir startup-failure branches.
- 0.04: Weak assertion specificity on the missing-tasks-dir branch.
- 0.03: No direct commit diff or dirty-tree overlap check available from this tool surface.

### Verdict
- FAIL with confidence 0.85.
- Route to todo for test-writer strengthening. Current source implementation appears correct in the reviewed slice; the gate failure is proof quality in TestFromAC coverage, not a builder defect.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | test-writer | Strengthen AC4 coverage so the engine-init and missing-tasks-dir failure tests each assert both the resolved board path and the KANBAN_DIR remediation text, not just path-only or any-exception behavior. | serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py | [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L247), [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L278), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L157), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L160) |
| 2 | test-writer | Add a discriminating assertion that the nonexistent-board validation branch fails before KanbanEngine construction, so the pre-engine wording is executable rather than descriptive only. | serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py | [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L237), [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L242), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L151), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L155) |

### Informational
- [share/skills/h-mcp-kanban/SKILL.md](share/skills/h-mcp-kanban/SKILL.md#L3) and [share/skills/h-mcp-kanban/SKILL.md](share/skills/h-mcp-kanban/SKILL.md#L17) still describe 8 tools, while [serve/mcp-kanban/README.md](serve/mcp-kanban/README.md#L19) and [serve/mcp-kanban/README.md](serve/mcp-kanban/README.md#L31) describe 9 tools including create_dr. This is doc drift, but not the gating defect for task 1349.
[[2026-05-05]]
## Test-Writer Notes
- Retry: added 3 tests for reviewer AC4 proof gaps. All 18 pass against current impl.
- Builder skip: test-only retry, all tests green (Step 1b.1 direct-to-review).

### New tests added (serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py)

| Test | Gap addressed |
|------|---------------|
| `test_engine_init_failure_message_names_path_and_kanban_dir` | RF#1: engine-init branch now asserts both resolved path AND "KANBAN_DIR" in exception |
| `test_tasks_dir_failure_message_names_path_and_kanban_dir` | RF#1: tasks-dir branch now asserts both resolved path AND "KANBAN_DIR" in exception |
| `test_nonexistent_board_skips_engine_construction` | RF#2: proves KanbanEngine is NOT called when kanban_dir.is_dir() fails |

### Quality evidence
- Tests: 18 passed / 0 failed / 0 skipped
- Lint: ruff clean (0 violations)
- Commit: 5d14d112
[[2026-05-05]]
## Builder Notes
- Implementation: no code changes in this cycle (verification-only builder pass after test-writer retry).
- Files changed: none.
- Tests: quality-runner scoped run on `serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py` -> 18 passed, 0 failed, 0 skipped.
- Coverage: `owlbear_mcp_kanban.server` reported 32% in scoped run (no source edits this cycle).
- ruff: clean (0 violations) on `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` and `serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py`.
- Approach: validated current implementation against latest test-writer retry evidence and confirmed no remaining builder-side implementation defect.
- Evidence summary: this is a test-only retry handoff; task is ready for review re-check.
- Commit: none (no file modifications).
- Post-task reflection:
  - Retry-cycle builder runs should re-verify live scoped quality results before making any additional edits.
  - No-change passes are appropriate when reviewer-directed proof gaps were addressed strictly in tests.
  - Keeping scope to task-local quality checks avoids unrelated suite noise in iterative routing.
[[2026-05-05]]
## Review Evidence
### Test Results
- Scoped quality-runner pass: 18 passed, 0 failed, 0 skipped in [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py)
- Ruff clean on [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py) and [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py)
- Module coverage reported as 32% for [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py). Non-blocking because the task-owned startup slice at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L75), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L82), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L146), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L151), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L155), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L159), and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L162) is exercised directly by the task-local tests.
- Editor diagnostics: no errors in [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py), [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py), or [serve/mcp-kanban/src/owlbear_mcp_kanban/__main__.py](serve/mcp-kanban/src/owlbear_mcp_kanban/__main__.py)
- Code-reader pass: no blocking findings. One proof-quality deduction remains on AC3's config-validation ownership clause, plus one informational doc-drift note.

### Scope Checks
- Builder commit present in [.git/logs/HEAD](.git/logs/HEAD#L1926); retrying test-writer commit present in [.git/logs/HEAD](.git/logs/HEAD#L1933)
- One prior Review Evidence section exists in [.owlbear/kanban/tasks/1349-add-mcp-kanban-dir-board-binding-validation.md](.owlbear/kanban/tasks/1349-add-mcp-kanban-dir-board-binding-validation.md#L177), so this is the second review cycle. The retry specifically addressed the prior AC4/proof gaps.
- Direct `git diff` / dirty-tree contamination checks were not available from this tool surface. I applied a small confidence deduction rather than treating that limitation as a defect in the deliverable.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L75), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L77), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L78), and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L148) implement env override with default fallback; tests pin env override, no-env fallback, and empty-string fallback at [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L104), [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L123), and [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L144). | TestFromAC_KanbanDirBinding | PASS |
| AC2 | [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L79) resolves to an absolute path and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L163) stores it in AppContext; tests pin absolute resolution and storage at [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L165), [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L185), and [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L203). | TestFromAC_KanbanDirBinding | PASS |
| AC3 | Startup validation order is implemented at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L151), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L155), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L159), and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L162). Tests prove missing-board rejection, missing-config failure, missing-tasks-dir rejection, and engine-skip ordering at [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L232), [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L247), [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L353), and [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L381). The “engine owns config.yml validation” clause is proven directly by code but only indirectly by tests, so confidence is slightly reduced. | TestFromAC_StartupValidation | PASS |
| AC4 | Startup failures route through [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L82), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L152), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L157), and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L160); bare propagation remains at [serve/mcp-kanban/src/owlbear_mcp_kanban/__main__.py](serve/mcp-kanban/src/owlbear_mcp_kanban/__main__.py#L8). The retry added discriminating message tests for missing-board, engine-init, and tasks-dir branches at [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L298), [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L313), [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L328), and [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L353). | TestFromAC_StartupValidation | PASS |
| AC5 | [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L162) runs sweep only after validation passes; negative and positive ordering tests are at [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L409), [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L435), and [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L464). | TestFromAC_SweepOrdering | PASS |
| AC6 | The live suite proves default cwd binding, env override, relative-to-absolute resolution, and invalid/missing path failures with actionable messages via the TaskFromAC coverage cited for AC1–AC5. | TestFromAC_KanbanDirBinding; TestFromAC_StartupValidation; TestFromAC_SweepOrdering | PASS |
| AC7 | Docs mention the optional override at [serve/mcp-kanban/README.md](serve/mcp-kanban/README.md#L111), [serve/mcp-kanban/README.md](serve/mcp-kanban/README.md#L113), and [share/skills/h-mcp-kanban/SKILL.md](share/skills/h-mcp-kanban/SKILL.md#L11). Current [seed/.vscode/mcp.json](seed/.vscode/mcp.json) contains no KANBAN_DIR override. | Direct file inspection | PASS |
| AC8 | The resolved board path selected at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L148) is passed into the engine at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L155) and stored in context at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L163), which is sufficient for isolated-board binding without relying on cwd. | Direct code inspection | PASS |

### Findings
- No blocking findings remain. The prior review gaps are closed by the retry tests at [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L328), [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L353), and [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L381).
- Residual proof-quality note: AC3’s “engine owns config.yml validation” clause is implemented correctly at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L155), but the missing-config tests at [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L247) and [serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py](serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py#L328) do not independently guard against a future duplicate pre-check before construction. That is below fail threshold after direct code inspection, but it reduces confidence slightly.

### Deductions
- 0.04: AC3 config-validation ownership is implemented correctly but only indirectly test-proven.
- 0.03: Direct commit diff and dirty-tree overlap checks were unavailable from this tool surface.
- 0.02: TestFromAC immutability confidence is reduced without a diff-based comparison against the pre-builder snapshot.

### Verdict
- PASS with confidence 0.91.
- Advance to docs.

### Informational
- [share/skills/h-mcp-kanban/SKILL.md](share/skills/h-mcp-kanban/SKILL.md#L3) and [share/skills/h-mcp-kanban/SKILL.md](share/skills/h-mcp-kanban/SKILL.md#L17) still say 8 tools, while [serve/mcp-kanban/README.md](serve/mcp-kanban/README.md#L19), [serve/mcp-kanban/README.md](serve/mcp-kanban/README.md#L31), and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L410) show 9 including create_dr.
[[2026-05-05]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Verified | `serve/mcp-kanban/README.md` Configuration table accurately documents `KANBAN_DIR` default, relative-path resolution behaviour, and fallback semantics. No edits required — builder already updated correctly per AC7. |
| 2 | Module docstrings | Yes | Verified | New functions in `server.py`: `_resolve_kanban_dir()` and `_startup_error()` each have accurate docstrings. `AppContext` and `app_lifespan` existing docstrings remain correct. `__main__.py` unchanged; module-level docstring present. No edits required. |
| 3 | External attribution | No | N/A | Cockpit pattern reference is internal; no external repos or articles cited. |
| 4 | Research doc | No | N/A | No research document produced for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` has `describes: serve/kanban/src/**, serve/mcp-kanban/src/**, .owlbear/kanban/**` — matches changed `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`. Footer updated from `eb40716a` → `ad980c4f` (2026-05-05). Committed: `2f5b0fff`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | IN (docstrings) | Verified — no edits required |
| `serve/mcp-kanban/src/owlbear_mcp_kanban/__main__.py` | IN (docstrings) | Verified — no edits required |
| `serve/mcp-kanban/README.md` | IN (package README) | Verified — no edits required |
| `share/skills/h-mcp-kanban/SKILL.md` | OUT (agent-executable) | No action |
| `serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py` | OUT (test file) | No action |
| `share/diagrams/kanban.excalidraw` | IN (diagram, describes-match) | Footer updated |

### Files Updated

- `share/diagrams/kanban.excalidraw` — footer timestamp/hash updated (commit `2f5b0fff`)

### Child Tasks Created

- `#1359` — "Fix tool count drift in h-mcp-kanban SKILL.md (8 → 9 tools)" at `backlog`, priority `nice-to-have`. Reason: `SKILL.md` says "8 tools" but 9 are exposed; flagged informational in both review cycles; OUT of scope for doc-writer, routes to architect.

### Scratch Files Cleaned

- None (no `.owlbear/scratch/1349-*` files found)
[[2026-05-05]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | server.py:L75-78 reads KANBAN_DIR with empty-string fallback; 3 tests (env override, no-env, empty) pass | PASS |
| AC2 | server.py:L79 calls .resolve(); AppContext stores absolute; 3 tests assert is_absolute() | PASS |
| AC3 | server.py:L151 is_dir, L155 engine init (try/except), L159 tasks_dir check; 4 tests + engine-skip ordering test | PASS |
| AC4 | _startup_error() at L82 includes path + KANBAN_DIR guidance; retry tests assert both resolved path AND KANBAN_DIR in all 3 branches | PASS |
| AC5 | engine.sweep() at L162 only after all validation; 3 ordering tests (2 negative, 1 positive) | PASS |
| AC6 | 18 tests cover full matrix (binding, validation, ordering, messages) | PASS |
| AC7 | README.md:L111,113 documents KANBAN_DIR; h-mcp-kanban SKILL.md:L11 mentions it; seed/mcp.json unchanged | PASS |
| AC8 | Resolved path passed to engine (L155) and stored in context (L163), sufficient for isolated binding | PASS |

### Test Results
- Task-scoped: 18 passed, 0 failed, 0 skipped
- Full suite: 4501 passed, 239 failed, 4 skipped (43.52s)
- Full suite failures: all pre-existing (RED tests from unbuilt tasks like 1199, guidance drift from 973, vitest/playwright env issues). Zero failures in task scope or caused by this change.
- Ruff: clean on server.py + test file

### Commits Verified
- f46f7908 test: add RED phase tests (#1349, test-writer)
- 1472b3d6 feat: add KANBAN_DIR startup binding validation (#1349, builder)
- 5d14d112 test: strengthen AC4 proof (#1349, test-writer retry)
- 2f5b0fff docs: update kanban.excalidraw footer (#1349, doc-writer)

### Architect Quality: 5/5
AC lines are specific, complete, and testable. Three-layer validation decomposition (AC3) was well-designed with explicit ownership boundaries. Failure mode map in architecture review covers all codepaths. Challenger concerns were addressed cleanly in the review. No builder improvisation required.

### Deduction Breakdown
- No AC lines without evidence: 0
- Lint violations: 0
- AC quality deduction: 0 (score 5)
- Missing reviewer evidence: 0 (present, detailed, two cycles)
- Full-suite failures in task scope: 0
- (-0.01) AC3 engine-owns-config validation proven by code structure inspection but only indirectly by tests (no isolated test proving absence of pre-check)

### Confidence: 0.99
### Action: archive