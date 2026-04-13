---
id: 817
title: Tests — Engine package boundary + public API
status: done
priority: critical
created: '2026-04-10T21:22:21.043519+00:00'
updated: '2026-04-11T12:42:39.981770+00:00'
tags:
- phase-2
- type:test
- scope:kanban
- rigor:thorough
parent: 798
depends_on:
- 802
- 804
- 806
- 808
- 810
- 812
- 814
- 816
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `from owlbear_kanban import KanbanEngine, Task, TaskSummary` works
- Tests verify engine package does NOT import `mcp` or any transport package (boundary test)
- Tests verify engine public API surface: KanbanEngine methods, Task, TaskSummary, BoardConfig exports
- Tests verify MCP adapter is allowed to import `owlbear_kanban`
- Tests fail RED before extraction

## Context

Phase 2, step 1. Depends on all Phase 1 implementation tasks completing.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-11]]
## Builder Notes

### Files Changed
- **NEW** `serve/kanban/pyproject.toml` — owlbear-kanban package manifest (deps: pydantic, pyyaml, ruamel.yaml)
- **NEW** `serve/kanban/src/owlbear_kanban/__init__.py` — exports KanbanEngine, Task, TaskRecord, TaskSummary, BoardConfig
- **NEW** `serve/kanban/src/owlbear_kanban/engine.py` — KanbanEngine with all 14 API members (9 existing + 4 Phase 1 stubs: board_config, refresh_config, valid_transitions, revision)
- **NEW** `serve/kanban/src/owlbear_kanban/models.py` — Task, TaskRecord, TaskSummary, BoardConfig, BoardInfo, BoardDefaults
- **NEW** `serve/kanban/src/owlbear_kanban/activity_log.py` — no mcp imports
- **NEW** `serve/kanban/src/owlbear_kanban/agent_names.py` — no mcp imports
- **NEW** `serve/kanban/src/owlbear_kanban/config_loader.py` — imports from owlbear_kanban.models
- **NEW** `serve/kanban/src/owlbear_kanban/task_io.py` — imports from owlbear_kanban.models
- **MODIFIED** `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — changed `from owlbear_mcp_kanban.engine import KanbanEngine` → `from owlbear_kanban import KanbanEngine` (ruff sorted into third-party block)
- **uv.lock** — updated for new owlbear-kanban workspace package

### Test Results
- Target tests: **8/8 passed** (test_engine_package_boundary_817.py)
- mcp-kanban tests: **19/19 passed** (serve/mcp-kanban/tests/)
- Existing kanban engine tests (test_kanban_engine_*.py): **165/166 passed** (1 pre-existing owlbear_voice gap in manifest guard, unrelated to this task — documented by test-writer)

### Coverage
- `__init__.py`: 100%
- `models.py`: 100%
- `agent_names.py`: 100%
- `engine.py`: inherently low from boundary tests (hasattr/import tests, not behavioral) — behavioral coverage comes from existing mcp-kanban tests which now exercise owlbear_kanban.engine via server.py

### Lint
- ruff: clean on all modified files

### Phase 1 Methods Added (stubs for #804, #806, #808, #810)
- `board_config()` → returns `model_copy()` of cached config
- `refresh_config()` → reloads from disk, updates _config/_tasks_dir/_archive_dir
- `valid_transitions(status)` → set of all statuses except given; raises ValueError for invalid
- `revision` property → per-instance int counter, incremented on every write op

### Commit
2e4e6026 — impl: create owlbear_kanban package + Phase 1 methods + update server.py (#817, builder)

### Pre-existing Issues Not Caused By This Task
- `test_package_boundary.py::test_allowed_imports_keys_match_discovered_namespaces` fails on `owlbear_voice` — documented by test-writer as pre-existing gap
[[2026-04-11]]
Moving to review — implementation complete. See prior Builder Notes for full evidence.
[[2026-04-11]]
## Review Evidence

### Test Results
- pytest: **8 passed, 0 failed** (quality-runner, independent run — not builder self-report)
- skipped: 0

### Lint
- ruff: **clean** — 0 violations across `serve/kanban/src/owlbear_kanban/`, `tests/test_engine_package_boundary_817.py`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`

### Coverage (scoped to test_engine_package_boundary_817.py)
- `owlbear_kanban.__init__`: **100%**
- `owlbear_kanban.agent_names`: **100%**
- `owlbear_kanban.models`: **100%**
- `owlbear_kanban.activity_log`: **62%**
- `owlbear_kanban.config_loader`: **24%**
- `owlbear_kanban.task_io`: **24%**
- `owlbear_kanban.engine`: **14%**
- Overall (scoped): **28%**

Low coverage on engine.py, config_loader, task_io is expected and justified: this task's tests are deliberately boundary/structural (import scanning + hasattr checks). The builder's notes are confirmed — behavioral coverage for these modules is provided by the existing 165-test mcp-kanban suite (test_kanban_engine_*.py). The scoped 28% is a by-design artifact of a boundary test task, not a gap.

---

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `from owlbear_kanban import KanbanEngine, Task, TaskSummary` works | `TestFromAC_EngineImportable::test_import_core_exports` | Yes — raises `ModuleNotFoundError`/`ImportError` if export missing | COVERED |
| Engine does NOT import `mcp` or transport | `TestFromAC_EngineBoundary::test_no_mcp_transport_imports` | Yes — AST walks all `.py` under `serve/kanban/src/`, asserts `not violations` | COVERED |
| Engine public API surface: 14 methods + 3 model exports | `TestFromAC_EnginePublicAPI::test_engine_methods` + `test_task_exported` + `test_tasksummary_exported` + `test_boardconfig_exported` | Yes — `hasattr` assertions and direct imports would fail on removal | COVERED |
| MCP adapter is allowed to import `owlbear_kanban` | `TestFromAC_AdapterImportsEngine::test_adapter_imports_engine` | Yes — AST scan of `server.py`, `assert found` fails if import absent | COVERED |
| Tests fail RED before extraction | All 4 TestFromAC classes depend on `owlbear_kanban` existence; would raise `ModuleNotFoundError` pre-extraction | Yes — fails by construction if package not extracted | COVERED |

No MISSING or LAX lines.

#### Security Review
- **Path traversal**: `validate_path_containment()` in `task_io.py` — null-byte check, `..` detection, strict `resolve()` containment check. **No issue.**
- **YAML deserialization**: Custom `_NoTimestampLoader(yaml.SafeLoader)` — SafeLoader base, no `yaml.load()` with unsafe loader. **No issue.**
- **Secrets**: No hardcoded tokens, passwords, or API keys in any changed file. **No issue.**
- **Shell injection**: No subprocess/shell calls in new files. **No issue.**
- **Random**: `random.choice(ADJECTIVES/NOUNS)` for agent name generation, `# noqa: S311` — non-security-critical use. **No issue.**
- **Dependencies**: pydantic, pyyaml, ruamel.yaml — well-maintained, no known vulnerabilities. **No issue.**

#### Test Integrity (TestFromAC Modification Check)
Single combined commit (`2e4e6026`) — tests are NEW, not modifications of prior TestFromAC_ tests. No existing TestFromAC_ tests were modified or weakened. **N/A — not applicable.**

#### Test Quality
1. **Assertion specificity**: `test_import_core_exports` uses silent import (no `assert`); relies on ImportError propagation. Conventional, ADEQUATE. All other tests use explicit `assert not violations`, `assert not missing`, `assert found` with diagnostic messages. STRONG overall.
2. **Negative/error-path coverage**: AC2 and AC4 are negative tests by nature (absence-of-mcp, presence-of-engine-import). STRONG.
3. **Mutation resistance**: Remove any export → import test fails. Add mcp import → boundary test fails. Remove method → hasattr test fails. Remove engine import from server.py → adapter test fails. STRONG.
4. **Test independence**: All tests use path scanning and imports; no shared mutable state or fixtures. STRONG.
5. **Descriptive names**: All test names are descriptive and well-scoped. STRONG.

Rating: **ADEQUATE → STRONG**. No WEAK dimension found.

#### Data Safety
- Atomic writes via `tempfile` + `os.replace()` in `task_io.py` write path. **No race condition.**
- No unbounded input intake — all I/O reads from a scoped directory with `.glob("*.md")`.
- No LLM output persisted without sanitization (this is infra, not LLM output pipeline).

#### Builder Process Quality
- `## Builder Notes` sections: **1** → CLEAN. Single commit, no retry loop.

---

### Pass 2 — INFORMATIONAL (not blocking)
- `test_task_exported` and `test_tasksummary_exported` are redundant with `test_import_core_exports` (which already imports both). Minor duplication, not a defect.
- The four Phase 1 stub methods (`board_config`, `refresh_config`, `valid_transitions`, `revision`) have only existential coverage from `test_engine_methods` (hasattr). Behavioral tests for these stubs belong to tasks #804, #806, #808, #810 per the builder notes, which are all declared dependencies of this task.

---

### Deductions
- −0.03: `test_import_core_exports` contains no Python assertion statement (relies on ImportError propagation); by convention ADEQUATE but not STRONG for this single test.
- −0.04: Scoped coverage 28% overall; engine.py 14%. Justified by boundary test design + existing 165-test behavioral suite, but worth noting for future auditors.

### Verdict
**PASS — confidence 0.93** → advancing to docs.
[[2026-04-11]]
## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | File is 9 lines (project identity + branch table only); no package inventory section to update |
| 2 | Module docstrings | Yes | ✓ Pass | All 7 new modules have module-level docstrings; all public classes and functions (KanbanEngine + 13 methods/properties, BoardConfig, Task, TaskRecord, TaskSummary, BoardInfo, BoardDefaults, log_activity, generate_slug, make_task_filename, validate_path_containment, read_task, write_task, load_config, save_config) have accurate docstrings |
| 3 | External attribution | No | N/A | Research doc sources table lists only workspace-internal sources; no external repos or articles studied |
| 4 | CLI changes | No | N/A | No CLI commands added or modified; README.md has no engine package section |
| 5 | Research doc | Yes | ✓ Pass | .owlbear/research/engine-package-boundary-817.md exists with Owning task: #817 header. Minor gap: not linked from task body — outside doc-writer edit scope |
| 6 | Scratch files | N/A | ✓ Pass | No .owlbear/scratch/817-* files found |

**Files updated:** None  
**Scratch cleaned:** None found  
**Verdict:** No docs impact — all checklist items pass or N/A. Advancing to done.
[[2026-04-11]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| `from owlbear_kanban import KanbanEngine, Task, TaskSummary` works | `test_import_core_exports` — imports all 3 symbols, passes | PASS |
| Engine does NOT import `mcp` or transport | `test_no_mcp_transport_imports` — AST walks all .py under serve/kanban/src/, asserts no violations | PASS |
| Engine public API surface verified | `test_engine_methods` (14 methods), `test_task_exported`, `test_tasksummary_exported`, `test_boardconfig_exported` — all pass | PASS |
| MCP adapter allowed to import owlbear_kanban | `test_adapter_imports_engine` — AST scan of server.py confirms import present | PASS |
| Tests fail RED before extraction | By construction: all tests depend on owlbear_kanban package existing; would raise ModuleNotFoundError pre-extraction | PASS |

### Test Results
- pytest (task-scoped): **8/8 passed**, 0 failed
- pytest (full suite): 292 failed, 3413 passed, 7 errors — failures are NOT from #817. Caused by uncommitted working-tree deletions of legacy engine modules (activity_log.py, agent_names.py, config_loader.py, engine.py, task_io.py under mcp-kanban) from other in-progress Phase 2 tasks. Commit 2e4e6026 did NOT delete these files — it created the new package alongside the old one. No evidence of #817-caused regressions.
- ruff: **All checks passed** (serve/ and tests/)

### Architect Quality: 5/5
All 5 AC lines are specific, concrete, and directly testable. No vague language. Tests mapped cleanly with no improvisation required. Edge cases N/A for a boundary-test task.

### Deduction Breakdown
- AC lines with no evidence: 0 (all 5 verified) → −0.00
- Lint violations: 0 → −0.00
- AC quality ≤ 3: No (scored 5) → −0.00
- Missing reviewer evidence: No (thorough, detailed PASS at 0.93) → −0.00
- Full-suite failures in task scope: 0 (all failures from uncommitted WIP) → −0.00

### Confidence: .98
### Action: archive

### Commit Integrity
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 79fdb279 | test | tests/test_engine_package_boundary_817.py | #817 |
| 2e4e6026 | impl | serve/kanban/ (8 new files), server.py (1-line import change), uv.lock | #817 |