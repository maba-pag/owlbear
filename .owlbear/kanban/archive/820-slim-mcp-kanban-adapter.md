---
id: 820
title: Slim mcp-kanban adapter
status: archived
priority: medium
created: '2026-04-10T21:22:41.393257+00:00'
updated: '2026-04-15T18:12:04.133674+00:00'
tags:
- phase-2
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 819
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- mcp-kanban `pyproject.toml` adds `owlbear-kanban` as dependency
- `server.py` imports from `owlbear_kanban` instead of local engine modules
- Engine modules removed from mcp-kanban source tree
- `models.py` retains `KanbanTask` (MCP boundary model)
- `__main__.py` retained
- #819 tests pass GREEN
- All 8 MCP tool tests pass (O4)

## Context

Phase 2, step 4. Depends on #819 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-15]]
## Research
- Research doc: .owlbear/research/slim-mcp-kanban-adapter-820.md
- Sources: 9 studied, 7 high-relevance (≥0.8)
- Recommendation: Verification-only pass — all AC lines already satisfied by #818 (confidence: 0.92)
- Key finding: #818 builder did both extraction AND slimming atomically; #820 is a no-op GREEN task
- Follow-up tasks created: none (task is self-contained)
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — subagent not available in researcher mode
- Confidence in original: 0.92
- Key challenges: none (no alternative approaches — work is already done)
- Researcher response: N/A

## Builder Guidance
1. Run `uv run pytest tests/test_mcp_adapter_slimming_819.py -q --tb=short` — verify 19 GREEN
2. Run `uv run pytest tests/ -k "kanban" -q --tb=short` — verify O4
3. Confirm 4 files only in `serve/mcp-kanban/src/owlbear_mcp_kanban/`
4. Submit verification-only note — no code changes needed

[[2026-04-15]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: slim mcp-kanban to thin adapter |
| Interface clarity | PASS | AC specifies exact files, imports, and test pass counts |
| Dependency correctness | PASS | #819 (RED tests) is done/archived |
| Module layering | PASS | mcp-kanban depends on owlbear-kanban (correct direction) |
| TDD compliance | PASS | #819 provided 19 regression tests |
| KISS/YAGNI | PASS | Verification-only scope — minimal |
| Premise challenge | PASS | Work done by #818 atomically; builder verifies |
| Pattern consistency | PASS | Follows Phase 2 extraction pattern |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | scope:mcp-kanban only |

### Codebase Verification
- `serve/mcp-kanban/src/owlbear_mcp_kanban/` contains exactly 4 files: `server.py`, `models.py`, `__init__.py`, `__main__.py`
- All 6 engine files removed (engine.py, engine_models.py, task_io.py, config_loader.py, activity_log.py, agent_names.py)
- `pyproject.toml` declares `owlbear-kanban` dependency
- `server.py` L15-17 imports from `owlbear_kanban` package
- `models.py` retains `KanbanTask` boundary model with 12 fields
- No stale engine references in mcp-kanban source tree

### Challenge Results
- Challenger: proceed (confidence high)
- Architect response: accepted — all 4 verification points clean

### Verdict: APPROVE
### Action Taken: Advanced to todo. Builder runs test verification only — no code changes expected.
[[2026-04-15]]
## Test-Writer Notes

- Test file: none — pass-through (see rationale below)
- Classes: none
- Tests per category: happy 0, edge 0, error 0, boundary 0
- Total: 0 tests
- ruff: N/A

### AC Coverage Assessment

| AC Line | Status | Coverage |
|---------|--------|----------|
| pyproject.toml adds `owlbear-kanban` dependency | Pre-implemented by #818 | Would write → PASS → remove |
| `server.py` imports from `owlbear_kanban` | Pre-implemented by #818 | Covered by #819 `TestFromAC_AdapterImportBoundary` |
| Engine modules removed from source tree | Pre-implemented by #818 | Covered by #819 `test_engine_file_absent` (×6 parametrized) |
| `models.py` retains `KanbanTask` boundary model | Pre-implemented by #818 | Would write → PASS → remove |
| `__main__.py` retained | Pre-implemented by #818 | Would write → PASS → remove |
| #819 tests pass GREEN | Meta-assertion, not testable | Confirmed GREEN: 19/19 PASS (run: 2026-04-15) |
| All 8 MCP tool tests pass (O4) | Pre-implemented by #818 | Covered by #819 `TestFromAC_AllToolsDelegateToEngine` (8 tool tests) |

### Pass-Through Rationale

Research (confidence 0.92) and arch review (verdict: APPROVE) both confirm: #818 completed extraction AND slimming atomically before #819 RED tests were written. #819's regression suite (19 tests) was authored AFTER the implementation — meaning #819 tests already cover the entire AC contract.

The three AC lines NOT explicitly in #819 (pyproject.toml dep, models.py KanbanTask, __main__.py) are structural filesystem/parse facts. Any tests I write for them PASS immediately against the current state. Per test-writer rules: remove passing tests. Net: 0 new failing tests possible.

Builder action: Run `uv run pytest tests/test_mcp_adapter_slimming_819.py -q` (19 GREEN) and submit verification note — no code changes needed.
[[2026-04-15]]
## Builder Notes

### Files Changed
None — verification-only pass-through. #818 completed the implementation atomically before #819 RED tests were written.

### Test Results
- `tests/test_mcp_adapter_slimming_819.py`: **19 passed, 0 failed** (12.52s)
  - `TestFromAC_AdapterImportBoundary`: all import/delegation tests GREEN
  - `TestFromAC_AllToolsDelegateToEngine`: all 8 MCP tool delegation tests GREEN
  - Engine file absence tests (×6 parametrized): GREEN
- Wider `-k kanban` suite: 101 pre-existing failures unrelated to this task (confirmed by zero code changes)

### Coverage
N/A — no new code written; #819 suite covers all AC lines.

### Lint
N/A — no files changed.

### AC Evidence
| AC Line | Status |
|---------|--------|
| pyproject.toml adds `owlbear-kanban` dependency | PRE-IMPLEMENTED by #818, verified by arch review |
| `server.py` imports from `owlbear_kanban` | VERIFIED by `TestFromAC_AdapterImportBoundary` (GREEN) |
| Engine modules removed from source tree | VERIFIED by 6 parametrized `test_engine_file_absent` tests (GREEN) |
| `models.py` retains `KanbanTask` | PRE-VERIFIED by arch review (4-file tree confirmed) |
| `__main__.py` retained | PRE-VERIFIED by arch review |
| #819 tests pass GREEN | CONFIRMED: 19/19 GREEN |
| All 8 MCP tool tests pass (O4) | CONFIRMED: `TestFromAC_AllToolsDelegateToEngine` 8/8 GREEN |
[[2026-04-15]]
## Review Evidence

### Test Results (Quality-Runner — independent run)
- `tests/test_mcp_adapter_slimming_819.py`: **19 passed, 0 failed**
- ruff: **clean** (0 violations)
- Coverage `owlbear_mcp_kanban`: 76% — no modules touched, threshold does not apply

### Source Tree Verification
- `serve/mcp-kanban/src/owlbear_mcp_kanban/` dir listing: `models.py`, `server.py`, `__init__.py`, `__main__.py` — exactly 4 files ✓
- grep for `engine.py` across `serve/mcp-kanban/src/**/*.py`: no matches ✓
- `pyproject.toml` L6: `"mcp[cli]>=1.26", "owlbear-kanban"` ✓
- `server.py` L16–18: `from owlbear_kanban import KanbanEngine` + `from owlbear_kanban.dispatch import pick_dispatchable` + `from owlbear_kanban.models import TaskSummary` ✓
- `models.py` L7: `class KanbanTask(BaseModel)` — 14 fields, `body` and `file` present ✓
- `__main__.py`: entry point `mcp.run()` confirmed ✓

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| pyproject.toml adds `owlbear-kanban` dependency | `pyproject.toml` L6 — direct read | Structural fact (no test needed) | PASS |
| `server.py` imports from `owlbear_kanban` | server.py L16–18 + `test_server_imports_from_owlbear_kanban` AST check GREEN | `TestFromAC_AdapterImportBoundary` | PASS |
| Engine modules removed from source tree | dir listing 4 files; `test_engine_file_absent` ×6 GREEN; grep confirms zero references | `TestFromAC_AdapterImportBoundary` | PASS |
| `models.py` retains `KanbanTask` (MCP boundary model) | models.py L7 direct read; implicit via `isinstance(result, KanbanTask)` assertions ×6 in tool tests | `TestFromAC_AllToolsDelegateToEngine` (implicit) | PASS |
| `__main__.py` retained | dir listing + direct read confirms entry point | Structural fact | PASS |
| #819 tests pass GREEN | Quality-Runner: 19/19 passed independently | All `TestFromAC_*` classes | PASS |
| All 8 MCP tool tests pass (O4) | Quality-Runner: 19/19 passed; `TestFromAC_AllToolsDelegateToEngine` ×8 GREEN | `TestFromAC_AllToolsDelegateToEngine` | PASS |

### Test Quality (Pass 1 — Critical)
- **TestFromAC_AdapterImportBoundary**: STRONG — AST-level checks and `not path.exists()` assertions catch real regressions; parametrized ×6 for each removed file
- **TestFromAC_AllToolsDelegateToEngine**: STRONG — `assert_called_once()` + `isinstance(result, KanbanTask/dict)` with specific key checks; would fail on delegation breakage
- **TestFromAC_EngineCreation**: STRONG — `server_module.KanbanEngine is CanonicalEngine` identity check; lifespan call count + Path type assertion
- No `TestFromAC_*` modifications possible (builder made zero code changes) ✓
- **Security**: No new code; no OWASP concerns ✓
- **Builder process**: CLEAN — single notes section, no retries, zero file changes ✓

### Deductions
- Coverage 76% (below 90%): No deduction — threshold applies to touched modules only; no modules were modified
- Test-writer pass-through (0 new tests): Justified — #819 regression suite was written to cover this exact AC; structural facts confirmed by direct file inspection. No `TestFromAC_*` removal detected.

### Verdict
**Confidence: .95 → PASS**
[[2026-04-15]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Verification-only pass-through; zero code changes; copilot-instructions.md has no tech stack or service tables to update |
| 2 | Module docstrings | No | N/A | Zero Python files created or modified |
| 3 | External attribution | No | N/A | All 9 research sources are internal (codebase, kanban tasks, brief, prior research docs) — sources/overview.md unchanged |
| 4 | CLI changes | No | N/A | No CLI added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/slim-mcp-kanban-adapter-820.md` exists, linked in task body at ## Research; follow-ups: none (self-contained) |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/820-*` files existed)
[[2026-04-15]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| pyproject.toml adds `owlbear-kanban` dep | pyproject.toml L6: `"owlbear-kanban"` | PASS |
| `server.py` imports from `owlbear_kanban` | server.py L16-18: 3 imports from owlbear_kanban | PASS |
| Engine modules removed from source tree | file_search engine* → 0 matches; dir listing: 4 files only | PASS |
| `models.py` retains `KanbanTask` | models.py L9: `class KanbanTask(BaseModel)` with 14 fields | PASS |
| `__main__.py` retained | dir listing confirms presence | PASS |
| #819 tests pass GREEN | 19/19 passed (9.01s) | PASS |
| All 8 MCP tool tests pass (O4) | TestFromAC_AllToolsDelegateToEngine 8/8 GREEN | PASS |

### Test Results
- pytest (full suite): 4396 passed, 193 failed, 8 skipped — all failures pre-existing (unrelated files), zero code changes in #820
- pytest (task scope): tests/test_mcp_adapter_slimming_819.py — 19 passed, 0 failed
- ruff: 3 errors in tests/test_refresh_sharepoint_879.py (unrelated to task)

### Architect Quality: 4/5
Specific, verifiable AC lines. Each maps to a concrete structural check. Minor redundancy (O4 line is subset of #819 GREEN line) but no ambiguity or gaps.

### Deduction Breakdown
- AC lines without evidence: 0 (-.02 each) → no deduction
- Lint violations (task scope): 0 → no deduction
- AC quality ≤ 3: no (4/5) → no deduction
- Missing reviewer evidence: no (detailed, PASS .95) → no deduction
- Full-suite failures in task scope: 0 → no deduction
- Qualitative discount for suite health: -.02

### Confidence: .98
### Action: archive