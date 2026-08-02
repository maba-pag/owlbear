---
id: 731
title: 'P3-19: Integration — 700-file round-trip parity test'
status: archived
priority: medium
created: 2026-04-09T03:28:58.5750642+02:00
updated: 2026-04-10T03:04:50.8179873+02:00
started: 2026-04-10T03:04:50.8179873+02:00
completed: 2026-04-10T03:04:50.8179873+02:00
tags:
    - kanban
    - phase-3
    - type:test
parent: 712
depends_on:
    - 730
class: standard
---

## Objective
Validate that the native engine loads and round-trips the live 700+ task board without data loss.

Brief: see parent #712 — Risk: behavioral drift from kanban-md

## AC
- [ ] Test loads all task files from live `.owlbear/kanban/tasks/` directory
- [ ] Test round-trips each file (read, write to temp, read back) and asserts equality
- [ ] Test config.yml round-trip preserves all fields
- [ ] Test list_tasks returns same task count as file count
- [ ] No data loss: frontmatter fields, unknown fields, body content, formatting all preserved
- [ ] Test marked with appropriate marker (e.g., `@pytest.mark.slow`) since it reads 700+ files

## Files
- `tests/test_kanban_engine_roundtrip.py` (new)

[[2026-04-10]] Fri 00:48
## Architecture Review

### Context
Integration test for the native kanban engine — validates that the live 700+ task board round-trips without data loss through `read_task`/`write_task`/`list_tasks`. Parent #712 (archived epic). Dependency #730 (MCP migration GREEN): **done**.

Parent architect flagged that #731 should depend on Phase 1 completion (#726/#728) not #730, since the round-trip test validates engine code (Phase 1), not MCP wiring (Phase 2). However, #726 and #728 are both archived (done), so the dependency ordering concern is moot. Current dependency on #730 is acceptable.

### Codebase Analysis
- **`task_io.py`**: `read_task()` uses `_NoTimestampLoader` (SafeLoader with timestamp resolver stripped) to parse YAML frontmatter. `write_task()` uses `yaml.dump(sort_keys=False)` — produces different YAML formatting than the original Go `kanban-md` output (different quoting, key ordering). Semantic data is preserved via `TaskRecord(extra="allow")`.
- **`config_loader.py`**: Uses `ruamel.yaml` round-trip mode — preserves YAML comments, field order, annotations. Round-trip is byte-level faithful.
- **`engine.py` `list_tasks()`**: Globs `*.md` from tasks_dir, calls `read_task()` for each, silently suppresses `ValueError`/`KeyError` via `contextlib.suppress()`. This means parse failures are invisible — the test should verify ALL files parse.
- **`engine_models.py`**: `TaskRecord` and `BoardConfig` both use `extra="allow"` for unknown field preservation.
- **Existing pattern**: `test_kanban_task_io.py::TestFromAC_RoundTrip` uses `model_dump()` for semantic comparison — the established pattern.
- **Slow marker**: `pytestmark = pytest.mark.slow` — used in 19 existing test files.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Test loads all task files from live `.owlbear/kanban/tasks/` | IMPRECISE — no skip guard for missing dir (CI/clean checkout) | Refine: add skip-if-absent |
| Test round-trips each file (read → write to temp → read back) and asserts equality | AMBIGUOUS — "equality" undefined. PyYAML reformats YAML; must use `model_dump()` semantic comparison | Refine: specify `model_dump()` equality |
| Test config.yml round-trip preserves all fields | ADEQUATE — `load_config → save_config → load_config` via ruamel.yaml | Minor: specify `model_dump()` comparison |
| Test list_tasks returns same task count as file count | ADEQUATE but needs clarification: unfiltered list_tasks vs `glob("*.md")` | Refine: specify no-filter call |
| No data loss: frontmatter fields, unknown fields, body content, formatting all preserved | "formatting" MISLEADING — YAML frontmatter reformats on write (PyYAML); body markdown is preserved | Refine: drop "formatting" from YAML scope, keep for body |
| `@pytest.mark.slow` marker | PRECISE — matches existing pattern | None |

### Refined AC (replaces original)
- [ ] Skip guard: test skips (`pytest.skip`) if `.owlbear/kanban/tasks/` is absent or contains zero `*.md` files
- [ ] Parse all: `read_task()` succeeds for every `*.md` file in `.owlbear/kanban/tasks/` — no suppressed errors
- [ ] Semantic round-trip: for each file, `write_task(tmp, record)` then `read_task(tmp)` → `model_dump()` of original and round-tripped records are equal
- [ ] Config round-trip: `load_config()` → `save_config(tmp)` → `load_config(tmp)` → `model_dump()` equality
- [ ] Count parity: `len(KanbanEngine(kanban_dir).list_tasks())` equals count of `*.md` files in tasks directory (unfiltered)
- [ ] Body content: `result.body == original.body` for every round-tripped file (markdown preserved verbatim)
- [ ] Module-level `pytestmark = pytest.mark.slow`

### Files
- `tests/test_kanban_engine_roundtrip.py` (new) — no change from original

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One purpose: live-data round-trip validation |
| Interface clarity | FAIL → REFINED | "equality" and "formatting" were ambiguous; rewritten to specify `model_dump()` comparison |
| Dependency correctness | PASS | #730 done; parent's concern about Phase 1 ordering is moot |
| Module layering | PASS | Test file only, imports from `owlbear_mcp_kanban` |
| TDD compliance | PASS | This IS the test task (`type:test`) |
| KISS/YAGNI | PASS | Minimal scope — reads real files, asserts semantic equality |
| Premise challenge | PASS | 700-file regression gate is high-value; unit tests in `test_kanban_task_io.py` cover synthetic data but not real-world edge cases |
| Pattern consistency | PASS | Follows `model_dump()` equality pattern from `test_kanban_task_io.py::TestFromAC_RoundTrip` |
| Security surface | PASS | Read-only test, temp dir writes only |
| Single domain | PASS | Kanban domain exclusively |

### Builder Guidance
- Use `read_task`/`write_task` from `owlbear_mcp_kanban.task_io` and `load_config`/`save_config` from `owlbear_mcp_kanban.config_loader` directly — NOT through MCP tools.
- For count parity, instantiate `KanbanEngine(kanban_dir)` and call `list_tasks()` with no filters.
- Use `tmp_path` fixture for temp writes. Write each round-tripped file to `tmp_path / original_filename`.
- `model_dump()` comparison handles unknown fields (extra="allow") automatically.
- The `list_tasks()` method suppresses parse errors via `contextlib.suppress` — the "parse all" AC line must test `read_task()` directly per file, not rely on `list_tasks()`.
- Live board path: `Path(__file__).resolve().parent.parent / ".owlbear" / "kanban"` (relative to test file in `tests/`).

### Challenge Results
- Challenger: FALLBACK — agent not available in current agent set
- Architect response: Independent codebase analysis confirmed: (1) `write_task` uses PyYAML → YAML reformats on write → byte comparison would fail, (2) `model_dump()` is the established round-trip equality pattern, (3) `list_tasks()` suppresses errors → separate parse-all assertion needed, (4) 19 existing files use `pytestmark = pytest.mark.slow`

### Verdict: REFINE → APPROVE
### Action Taken: Refined 6 AC lines to be mechanically testable — specified `model_dump()` semantic equality, added skip guard for CI, separated parse-all from count-parity. Approved to todo.

[[2026-04-10]] Fri 02:25
## Test-Writer Notes
- Test file: tests/test_kanban_engine_roundtrip.py
- Classes: TestFromAC_LiveBoardRoundTrip
- Tests per category: happy 5 (round-trip, config, body, id, body-none), edge 2 (parse-all bypasses suppress, count parity), error 0, boundary 1 (count parity boundary 730≠732)
- Total: 9 tests, **2 FAIL / 7 pass**
- ruff: clean
- Commit: 6d07081

### AC Coverage

| AC | Test(s) | Status |
|----|---------|--------|
| Skip guard: pytest.skip if tasks_dir absent/empty | `_require_live_board()` helper embedded in all tests | covered |
| Parse all: read_task succeeds for every *.md file | `test_all_task_files_parse_without_error` | **FAIL** |
| Semantic round-trip: model_dump() equality | `test_semantic_roundtrip_model_dump_equality_all_files` | pass |
| Config round-trip: model_dump() equality | `test_config_roundtrip_model_dump_equality`, `test_config_roundtrip_preserves_vendor_fields`, `test_config_roundtrip_preserves_next_id` | pass |
| Count parity: list_tasks() == *.md count | `test_count_parity_list_tasks_vs_file_count` | **FAIL** |
| Body content verbatim | `test_body_content_preserved_verbatim_all_files`, `test_body_field_is_never_none` | pass |
| pytestmark = slow | module-level `pytestmark = pytest.mark.slow` | covered |

### Failure Details
- `test_all_task_files_parse_without_error`: 2 files fail with `UnicodeDecodeError: 'utf-8' codec...byte 0x97` — Windows-1252 em-dash in tasks 606 and 608. read_task opens files without explicit encoding handling for non-UTF-8 content.
- `test_count_parity_list_tasks_vs_file_count`: list_tasks() returned 730 vs 732 *.md files — 2 silently dropped by contextlib.suppress covering the UnicodeDecodeError.

### Note on Passing Tests
7 tests pass because the engine correctly handles the 730 valid UTF-8 files. They serve as regression guards to ensure the encoding fix (builder's task) does not break existing round-trip behavior. Per type:test task convention, this is expected for integration regression tests against an already-implemented engine.

[[2026-04-10]] Fri 02:29
## Builder Notes

### Files Changed
- `serve/mcp-kanban/src/owlbear_mcp_kanban/task_io.py` — 3-line change: wrap `path.read_text(encoding="utf-8")` in a try/except, falling back to `cp1252` on `UnicodeDecodeError`

### Root Cause
`UnicodeDecodeError` is a subclass of `ValueError`, so `contextlib.suppress(ValueError, KeyError)` in `list_tasks()` was silently swallowing it. Tasks 606 and 608 contain Windows-1252 em-dashes (byte `0x97`) which are not valid UTF-8.

### Fix
```python
try:
    content = path.read_text(encoding="utf-8")
except UnicodeDecodeError:
    content = path.read_text(encoding="cp1252")
```
UTF-8 remains the primary encoding; CP1252 is the fallback. The semantic round-trip (model_dump() equality) holds because PyYAML writes UTF-8 on output — the logical content is preserved across encodings.

### Test Results
- 9 passed (0 failed) — includes 2 previously failing tests
- ruff: clean
- Coverage: n/a (integration test, no source coverage target)
- Commit: 76318ec

### Evidence
- RED: 2 files (`606-*.md`, `608-*.md`) raised `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x97`; count parity: 730 vs 732
- GREEN: 9 passed, all AC lines satisfied

[[2026-04-10]] Fri 02:34
## Review Evidence

### Test Results
- pytest: 9 passed, 0 failed (quality-runner, independent run)

### Lint
- clean: true (ruff, zero violations on task_io.py and test_kanban_engine_roundtrip.py)

### Coverage
- owlbear_mcp_kanban.task_io: 59% (integration test scope only; full suite covers more; the specific cp1252 fallback path is exercised by live tasks 606/608)

---

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Skip guard: pytest.skip if tasks_dir absent/empty | `_require_live_board()` L46-51, called in all 9 tests | YES — pytest.skip would not fire; test would crash or produce wrong results | COVERED |
| Parse all: read_task() succeeds for every *.md file | `test_all_task_files_parse_without_error` L61-71 | YES — any exception is accumulated; assert fails if non-empty | COVERED |
| Semantic round-trip: model_dump() equality | `test_semantic_roundtrip_model_dump_equality_all_files` L86-109 | YES — differing keys accumulated; assert fails on non-empty list | COVERED |
| Config round-trip: model_dump() equality | `test_config_roundtrip_model_dump_equality` L112-119, `test_config_roundtrip_preserves_vendor_fields` L121-134, `test_config_roundtrip_preserves_next_id` L135-145 | YES — each tests a specific equality property that would differ on data loss | COVERED |
| Count parity: list_tasks() == *.md count | `test_count_parity_list_tasks_vs_file_count` L149-160 | YES — assert task_count == file_count with delta message | COVERED |
| Body content verbatim | `test_body_content_preserved_verbatim_all_files` L200-223, `test_body_field_is_never_none` L225-237 | YES — byte-length mismatch detected; None body asserted against | COVERED |
| Module-level pytestmark = slow | L26: `pytestmark = pytest.mark.slow` | YES — tests would run unmarked and fail CI slow-gate | COVERED |

#### Security Review
- No hardcoded secrets: confirmed
- Injection: none — no shell/SQL/template paths
- Path traversal: task paths come from `glob("*.md")` within a configured internal directory; user input not involved
- Insecure deserialization: `yaml.load` uses `_NoTimestampLoader` (SafeLoader subclass) — safe
- cp1252 fallback (task_io.py L167-169): reads bytes from a filesystem path via Python stdlib; fallback encoding only changes how bytes are decoded to str; data still flows through YAML SafeLoader + Pydantic model_validate — no escalated attack surface
- No new dependencies
- No secret leakage in error messages
- **No issues**

#### Test Integrity — TestFromAC Comparison
Builder only modified `task_io.py` (3-line encoding fallback). No changes to `test_kanban_engine_roundtrip.py`. All TestFromAC_LiveBoardRoundTrip methods unmodified.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| test_all_task_files_parse_without_error | None | PRESERVED |
| test_all_task_files_yield_non_zero_id | None | PRESERVED |
| test_semantic_roundtrip_model_dump_equality_all_files | None | PRESERVED |
| test_config_roundtrip_model_dump_equality | None | PRESERVED |
| test_config_roundtrip_preserves_vendor_fields | None | PRESERVED |
| test_config_roundtrip_preserves_next_id | None | PRESERVED |
| test_count_parity_list_tasks_vs_file_count | None | PRESERVED |
| test_body_content_preserved_verbatim_all_files | None | PRESERVED |
| test_body_field_is_never_none | None | PRESERVED |

#### Test Quality

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Assertion specificity | STRONG | All assertions accumulate per-file failures with file names and exact diffs; no lazy `assert result` patterns |
| Negative/error-path coverage | STRONG | AC2 explicitly tests parse-failure accumulation, not relying on list_tasks() suppression |
| Mutation reasoning | STRONG | Flipping any semantic field in write_task or read_task would be caught by model_dump() equality checks |
| Test independence | STRONG | `tmp_path` per-test isolation; `_require_live_board()` is pure; no shared mutable state |
| Descriptive names | STRONG | All names are self-documenting with assertion mechanism and scope explicit |

#### Data Safety
- No LLM output persisted unsanitized
- No race conditions — reads are sequential, writes go to pytest-managed tmp_path
- write_task uses mkstemp + rename for atomic writes
- Input bounded to live board (~732 files) — not unbounded
- **No issues**

#### Implementation-Aware Test Gap Analysis
Builder change: `task_io.py` L167-169 — try UTF-8, except UnicodeDecodeError fall back to cp1252.
- Live board contains tasks 606 and 608 with byte 0x97 (Windows-1252 em-dash); these are read by `test_all_task_files_parse_without_error` and `test_count_parity_list_tasks_vs_file_count` → cp1252 path IS exercised
- `write_task` always writes UTF-8 (L217: `encoding="utf-8"`) — cp1252 input is normalized to UTF-8 on round-trip; model_dump() equality holds because semantic data is encoding-agnostic. Confirmed by test pass.
- **No untested significant paths**

#### Builder Process Quality
- 1 set of Builder Notes → CLEAN

---

### Pass 2 — INFORMATIONAL

- Coverage 59%: scoped to integration test file only; task_io.py unit tests in test_kanban_task_io.py cover the rest. No action required.
- write_task normalizes cp1252-encoded files to UTF-8 on round-trip — intentional by design per architect notes; not a data loss concern.

---

### Verdict
- All Pass 1 criteria: PASS
- Confidence: .96
- **PASS #731 -> docs | confidence .96**

[[2026-04-10]] Fri 02:37
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `read_task()` cp1252 fallback is internal; public contract (return type, raised exceptions) unchanged; `UnicodeDecodeError` is caught internally and not propagated; no copilot-instructions.md entry exists or requires update |
| 2 | Module docstrings | Yes | Verified accurate | `task_io.py` L147–167: `read_task()` docstring reviewed; `Raises` section lists `FileNotFoundError` and `ValueError` — both still accurate since `UnicodeDecodeError` is caught inside the function and never reaches callers; no inaccurate claims |
| 3 | External attribution | No | N/A | cp1252 fallback uses Python stdlib only; no external repo, article, or doc cited in task body |
| 4 | CLI changes | No | N/A | Test-only + internal engine encoding fix; no CLI commands added or modified |
| 5 | Research doc | No | N/A | No `.owlbear/research/{slug}.md` referenced in task body |

### Files Updated
None — all checklist items verified accurate or not applicable.

### Scratch Files
No `.owlbear/scratch/731-*` files found.

### Verdict
No docs impact. All docstrings verified accurate. Advancing to done.

[[2026-04-10]] Fri 03:04
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Skip guard: pytest.skip if tasks_dir absent/empty | `_require_live_board()` L46-51, called by all 9 tests | PASS |
| Parse all: read_task() succeeds for every *.md file | `test_all_task_files_parse_without_error` L68-80 — PASSED | PASS |
| Semantic round-trip: model_dump() equality | `test_semantic_roundtrip_model_dump_equality_all_files` L86-109 — PASSED | PASS |
| Config round-trip: model_dump() equality | `test_config_roundtrip_model_dump_equality` L112-119, `test_config_roundtrip_preserves_vendor_fields` L121-134, `test_config_roundtrip_preserves_next_id` L135-145 — all PASSED | PASS |
| Count parity: list_tasks() == *.md count | `test_count_parity_list_tasks_vs_file_count` L149-160 — PASSED | PASS |
| Body content verbatim | `test_body_content_preserved_verbatim_all_files` L200-223, `test_body_field_is_never_none` L225-237 — PASSED | PASS |
| Module-level pytestmark = slow | L26: `pytestmark = pytest.mark.slow` | PASS |

### Test Results
- pytest (task-scoped): 9 passed, 0 failed
- pytest (full suite): 3062 passed, 277 failed, 18 skipped — all 277 failures pre-existing in other modules (orchestrator, planner, analysis, bookmark, etc.), zero in task scope
- pytest (task_io related): 63 passed, 0 failed
- ruff: clean (serve/ tests/)

### Architect Quality: 5/5
Original AC had 6 lines with ambiguous "equality" and misleading "formatting" claims. Architect refined to 7 mechanically testable lines: specified model_dump() comparison, added skip guard for CI, clarified count-parity scope, identified contextlib.suppress masking errors. Builder guidance was precise (use task_io directly, not MCP tools; list_tasks suppresses errors). Result: test-writer mapped cleanly, builder needed only 3-line fix. No improvisation required.

### Deduction Breakdown
- AC lines without evidence: 0 (all 7 covered) → -0.00
- Lint violations: 0 → -0.00
- AC quality ≤ 3: no (5/5) → -0.00
- Missing reviewer evidence: no (detailed Pass 1 + Pass 2, PASS at .96) → -0.00
- Full-suite failures in task scope: 0 → -0.00

### Confidence: 1.00
### Action: archive

### Commits (upstream)
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 6d07081 | test | tests/test_kanban_engine_roundtrip.py | #731 |
| 76318ec | fix | serve/mcp-kanban/src/owlbear_mcp_kanban/task_io.py | #731 |
