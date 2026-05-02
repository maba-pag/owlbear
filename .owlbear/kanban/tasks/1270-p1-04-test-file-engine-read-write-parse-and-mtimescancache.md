---
id: 1270
title: 'P1-04: Malformed memory file handling — test + fix'
status: in-progress
priority: needed
created: 2026-05-02T03:43:31.733852+00:00
updated: 2026-05-02T15:49:13.894092+00:00
tags:
- phase-1
- scope:mcp-memory
- tests
parent: 1266
depends_on:
- 1269
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Write failing tests that define the file engine contract: reading .md files with YAML frontmatter, writing with atomic ops, slug generation, directory scanning, and MtimeScanCache behavior.

Brief: see parent #1266

## Scope

**In scope:**
- Test file: `tests/test_memory_engine.py` (workspace root tests/)
- Parse `.md` file with YAML frontmatter into MemoryEntry
- Serialize MemoryEntry back to frontmatter+body .md format
- Slug generation from title (kebab-case, truncated, 6-char suffix)
- Load all entries from a temp directory
- Atomic write (file appears fully-formed or not at all)
- MtimeScanCache: skip re-parse when dir mtime unchanged
- MtimeScanCache: re-parse when dir mtime changes (file added/removed/modified)
- Handle empty directory (no entries)
- Handle malformed files gracefully (skip with warning, don't crash)

**Out of scope:**
- MCP tool behavior (tested in #1272)
- Access control / mutation rules (tested in #1272)
- Model validation itself (tested in #1268)

## Acceptance Criteria

- [ ] Tests import MemoryEngine from `owlbear_mcp_memory.engine`
- [ ] Tests FAIL (RED) — engine module does not yet exist
- [ ] Round-trip test: write entry → read entry → fields match
- [ ] Slug test: title "Ruff Import Sorting Pitfall" → slug starts with "ruff-import-sorting-pitfall-" + 6 alphanum
- [ ] Cache hit test: two consecutive loads without file change → second skips parse
- [ ] Cache miss test: add file between loads → second re-parses
- [ ] Malformed file test: invalid YAML → entry skipped, no exception raised
- [ ] Empty dir test: returns empty list
[[2026-05-02]]
## Test-Writer Notes
- Test file: tests/test_memory_engine_1270.py
- Class: TestFromAC_FileEngine (4 tests)
- Tests per category: error 4 (malformed-file handling)
- Total: 4 tests, all FAIL ✓
- ruff: clean
- Commit: 1eb46340

## AC Coverage

| AC Line | Tests | Verdict |
|---------|-------|---------|
| Malformed file: invalid YAML → entry skipped, no exception raised | test_invalid_yaml_syntax_in_frontmatter_skipped | FAIL ✓ |
| Malformed file: missing required fields → skipped, no exception | test_missing_required_fields_skipped | FAIL ✓ |
| Malformed file: empty frontmatter → skipped, no exception | test_empty_frontmatter_skipped | FAIL ✓ |
| Valid entries alongside malformed file still returned | test_valid_entries_alongside_malformed_file_still_returned | FAIL ✓ |

## RED Evidence
- pytest: 0 passed, 4 failed — all failures are yaml.parser.ParserError or pydantic_core.ValidationError propagating from _load_file() uncaught
- ruff: exit 0, clean
- Commit: 1eb46340

## Implementation Gap
engine._load_file() does not wrap yaml.safe_load() or MemoryEntry(**data) in try/except — any malformed file crashes the entire load() call. Builder must add:
  try/except (yaml.YAMLError, ValidationError) → return None (+ optional warning)

## Scope Note
Round-trip, slug, cache hit/miss, and empty-dir behaviors are already implemented on parent task #1266 and would pass against the current engine — excluded per RED-phase rules (no tests for existing behavior). The engine module EXISTS (bypassing decomposition at parent #1266), so only unimplemented behavior (malformed-file handling) is covered here.
[[2026-05-02]]
## Builder Notes
- Implementation: added malformed-file guards in serve/mcp-memory/src/owlbear_mcp_memory/engine.py (`_load_file` now catches `yaml.YAMLError` and `pydantic.ValidationError` and skips bad files by returning `None`).
- Fixes applied: malformed YAML frontmatter no longer crashes `load()`; entries with missing/empty frontmatter are skipped; valid entries still load when malformed siblings exist.
- Tests: 4/4 TestFromAC tests passed in `tests/test_memory_engine_1270.py`.
- Verification suite: 64 passed, 0 failed across `tests/test_memory_engine_1270.py` + `tests/test_mcp_memory_1266.py`.
- Coverage: `owlbear_mcp_memory.engine` at 95% (overall 90% on scoped run).
- Lint: ruff clean for touched source + related test files.
- Commit: ffcd7b27 (`fix: skip malformed memory files (#1270, builder)`).
[[2026-05-02]]
## Review Evidence
### Scope
- Current task authority is the live task body for #1270. There is no prior `## Review Evidence` or architecture-refinement section on this task that narrows the written AC.
- Runtime behavior for the implemented malformed-file slice is green, but this review gates the task against the AC still written on the board.

### Test Results
- quality-runner task-local scope: pytest 4 passed, 0 failed, 0 skipped on `tests/test_memory_engine_1270.py`
- quality-runner regression context: pytest 64 passed, 0 failed, 0 skipped on `tests/test_memory_engine_1270.py` + `tests/test_mcp_memory_1266.py`

### Lint
- ruff: clean on `serve/mcp-memory/src/owlbear_mcp_memory/engine.py` and `tests/test_memory_engine_1270.py`

### Coverage
- task-local scope: `owlbear_mcp_memory.engine` 73%
- regression context: `owlbear_mcp_memory.engine` 95%
- Coverage is informational here: the builder's changed lines are the malformed-file guards, and the low task-local percentage is driven by broad engine behaviors that this task-local suite does not exercise.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|----------------|----------------------------|---------|
| Tests import `MemoryEngine` from `owlbear_mcp_memory.engine` | `tests/test_memory_engine_1270.py:18` | Yes - import would fail immediately if the symbol/path changed | COVERED |
| Tests FAIL (RED) - engine module does not yet exist | none; task still states this at `.owlbear/kanban/tasks/1270-p1-04-test-file-engine-read-write-parse-and-mtimescancache.md:50` | No. The live repo already has `serve/mcp-memory/src/owlbear_mcp_memory/engine.py`, and the task-local test file explicitly says broader engine behaviors were already implemented on the parent task at `tests/test_memory_engine_1270.py:9` | MISSING |
| Round-trip test: write entry -> read entry -> fields match | none in `tests/test_memory_engine_1270.py`; adjacent proof exists only at `tests/test_mcp_memory_1266.py:265` | No for this task. The task-local suite does not contain a round-trip proof | MISSING |
| Slug test: title `Ruff Import Sorting Pitfall` -> slug starts with `ruff-import-sorting-pitfall-` + 6 alphanum | none in `tests/test_memory_engine_1270.py`; adjacent proof exists only at `tests/test_mcp_memory_1266.py:300` | No for this task. The task-local suite does not contain a slug proof | MISSING |
| Cache hit test: two consecutive loads without file change -> second skips parse | none in `tests/test_memory_engine_1270.py`; adjacent proof exists only at `tests/test_mcp_memory_1266.py:325` | No for this task. The task-local suite does not contain a cache-hit proof | MISSING |
| Cache miss test: add file between loads -> second re-parses | none in `tests/test_memory_engine_1270.py`; adjacent proof exists only at `tests/test_mcp_memory_1266.py:343` | No for this task. The task-local suite does not contain a cache-miss proof | MISSING |
| Malformed file test: invalid YAML -> entry skipped, no exception raised | `tests/test_memory_engine_1270.py:46`, plus sibling malformed-file coverage at `:60`, `:73`, `:82` | Yes. The invalid-YAML and validation-error cases would fail if `_load_file()` stopped catching malformed input | COVERED |
| Empty dir test: returns empty list | none in `tests/test_memory_engine_1270.py`; adjacent proof exists only at `tests/test_mcp_memory_1266.py:295` | No for this task. The task-local suite does not contain an empty-dir proof | MISSING |

#### Security Review
- No OWASP-class issue observed in the scoped source change.
- `serve/mcp-memory/src/owlbear_mcp_memory/engine.py:112-125` only adds local YAML/validation guards and does not introduce new input sinks, shelling, path traversal, or secret handling.

#### Test Integrity
- No live evidence of weakened or removed `TestFromAC_*` assertions in `tests/test_memory_engine_1270.py`.
- Commit existence is confirmed in `.git/logs/HEAD` for the test-writer (`1eb46340`) and builder (`ffcd7b27`), but diff-level immutability of the task test file could not be fully proven from available tooling. Minor confidence deduction only.

#### Test Quality
- STRONG for the malformed-file slice: the four task-local tests use exact `entries == []` / exact entry-count and ID assertions, not truthiness checks.
- FAIL at the task level: the suite itself declares that round-trip, slug, cache hit/miss, and empty-dir coverage were pushed to the parent task (`tests/test_memory_engine_1270.py:9`), so this task-local file cannot prove the broader AC still written on the board.

#### Data Safety
- No blocking data-safety issue observed in the scoped source change.
- The live implementation correctly skips malformed files by returning `None` from `_load_file()` after `yaml.YAMLError` or `ValidationError` in `serve/mcp-memory/src/owlbear_mcp_memory/engine.py:120` and `:125`.

#### Implementation-Aware Gaps
- The builder's implementation for the malformed-file bug is correct in the live code: `_load_file()` now catches malformed YAML and model validation failures at `serve/mcp-memory/src/owlbear_mcp_memory/engine.py:112-125`.
- The missing behavior is not a runtime bug. It is a task-contract mismatch: the task-local file `tests/test_memory_engine_1270.py` only defines four malformed-file tests at lines 46, 60, 73, and 82, while the board AC still requires round-trip, slug, cache-hit, cache-miss, and empty-dir coverage.
- The adjacent parent suite `tests/test_mcp_memory_1266.py` does contain those broader engine/cache proofs at lines 265, 295, 300, 325, and 343. That confirms the repo behavior is covered somewhere, but not by this task's own deliverable.

#### Builder Process Quality
- CLEAN. No prior `## Review Evidence` section exists on task #1270, so this is the first review failure.
- The builder did not create the failure here; the failure is that the task artifact is stale / internally inconsistent with current ownership and scope.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Tests import `MemoryEngine` from `owlbear_mcp_memory.engine` | `tests/test_memory_engine_1270.py:18` imports the correct symbol; task-local quality-runner scope passes 4/4 | `tests/test_memory_engine_1270.py` | PASS |
| Tests FAIL (RED) - engine module does not yet exist | Task still says this at `.owlbear/kanban/tasks/1270-p1-04-test-file-engine-read-write-parse-and-mtimescancache.md:50`, but the live engine exists and the test file itself documents scope drift at `tests/test_memory_engine_1270.py:9` | none | FAIL |
| Round-trip test: write entry -> read entry -> fields match | No task-local round-trip test exists; only adjacent parent coverage at `tests/test_mcp_memory_1266.py:265` | none in task-local suite | FAIL |
| Slug test: title `Ruff Import Sorting Pitfall` -> slug starts with `ruff-import-sorting-pitfall-` + 6 alphanum | No task-local slug test exists; only adjacent parent coverage at `tests/test_mcp_memory_1266.py:300` | none in task-local suite | FAIL |
| Cache hit test: two consecutive loads without file change -> second skips parse | No task-local cache-hit test exists; only adjacent parent coverage at `tests/test_mcp_memory_1266.py:325` | none in task-local suite | FAIL |
| Cache miss test: add file between loads -> second re-parses | No task-local cache-miss test exists; only adjacent parent coverage at `tests/test_mcp_memory_1266.py:343` | none in task-local suite | FAIL |
| Malformed file test: invalid YAML -> entry skipped, no exception raised | `_load_file()` catches malformed input at `serve/mcp-memory/src/owlbear_mcp_memory/engine.py:120` and `:125`; task-local tests pass at `tests/test_memory_engine_1270.py:46`, `:60`, `:73`, `:82` | `TestFromAC_FileEngine` | PASS |
| Empty dir test: returns empty list | No task-local empty-dir test exists; only adjacent parent coverage at `tests/test_mcp_memory_1266.py:295` | none in task-local suite | FAIL |

### Deductions
- -0.24 task-local AC coverage gap: five written AC lines (round-trip, slug, cache hit, cache miss, empty dir) are not present in `tests/test_memory_engine_1270.py`
- -0.13 stale RED contract: the task still requires a missing-module RED condition that does not match the live repo or the task-local test-writer note
- -0.05 scope/ownership mismatch: the task-local file explicitly shifts broad engine/cache coverage to parent task #1266, so the board contract needs refinement before this task can be gated cleanly
- -0.03 commit-diff uncertainty on `TestFromAC_*` immutability
- Confidence: 0.55

### Verdict
- FAIL. The malformed-file implementation is correct, but this task cannot pass as written because the task-local deliverable does not prove most of the AC still recorded on the board.

### Action
- Route to `backlog` for architecture cleanup, not `in-progress`: this is a task-definition / AC-quality failure rather than a builder bug.
- Required follow-up:
  1. Refine task #1270 to match its real scope (malformed-file handling only), or close it as duplicate coverage of parent task #1266.
  2. If task #1270 remains active, rewrite the AC so every active line has task-local proof requirements, then re-run the test-writer/builder cycle as needed.
  3. Do not ask the builder for another source-code change until the task contract is corrected.

### Post-task Reflection
- A green implementation slice can still be a review FAIL when the board AC is stale and the task-local proof was silently pushed into another task.
- Adjacent durable suites are useful regression context, but they do not automatically satisfy a child test task whose own deliverable is narrower than the board contract.
- The task file itself is the authority unless an architecture-refinement section explicitly narrows it.
[[2026-05-02]]

## Architecture Review

**Verdict:** REFINE → APPROVE

### AC Assessment

The original AC was written for the full engine test contract (round-trip, slug, cache, empty dir, malformed files). During RED phase, the test-writer correctly narrowed to malformed-file handling because all other behaviors were already implemented and tested on parent #1266 (`tests/test_mcp_memory_1266.py`). The builder then implemented the fix on this task. The reviewer correctly identified the AC-scope mismatch and returned to backlog.

| Original AC Line | Assessment | Action |
|---|---|---|
| Tests import MemoryEngine from `owlbear_mcp_memory.engine` | Mechanical import — still valid | KEEP (td:0) |
| Tests FAIL (RED) — engine module does not yet exist | Stale — engine exists since parent #1266 | REMOVE |
| Round-trip test | Covered by parent suite `test_mcp_memory_1266.py:265` | REMOVE — not in task scope |
| Slug test | Covered by parent suite `test_mcp_memory_1266.py:300` | REMOVE — not in task scope |
| Cache hit test | Covered by parent suite `test_mcp_memory_1266.py:330` | REMOVE — not in task scope |
| Cache miss test | Covered by parent suite `test_mcp_memory_1266.py:343` | REMOVE — not in task scope |
| Malformed file: invalid YAML → entry skipped | Implemented and tested — 4 tests in `test_memory_engine_1270.py` | KEEP (td:2) |
| Empty dir test | Covered by parent suite `test_mcp_memory_1266.py:295` | REMOVE — not in task scope |

### Refined AC (authoritative — replaces original AC section)

- [ ] Tests import MemoryEngine from `owlbear_mcp_memory.engine` (td:0)
- [ ] Invalid YAML syntax in frontmatter → entry skipped, no exception raised (td:2)
- [ ] Missing required MemoryEntry fields → entry skipped, no exception (td:2)
- [ ] Empty YAML frontmatter block → entry skipped, no exception (td:2)
- [x] Valid entries returned alongside malformed files in same directory (td:2)
- [ ] Non-mapping YAML frontmatter (list, scalar, int) → entry skipped, no exception (td:2) **[NEW — challenger finding: `data["content"]` at engine.py:122 raises TypeError when yaml.safe_load returns non-dict]**

### Architecture Notes

- **Scope narrowing rationale:** Parent #1266 (archived) delivered the full engine with tests in `test_mcp_memory_1266.py`. Only malformed-file handling was unimplemented, so #1270 correctly narrowed to that slice. The builder's implementation (yaml.YAMLError + ValidationError catches in `_load_file()`) is correct for those cases.
- **New gap (challenger):** `yaml.safe_load` on non-dict YAML (e.g., `- list item`) returns a truthy non-dict value. The `or {}` fallback only handles None. `data["content"] = body.strip()` then raises TypeError. Fix: add `if not isinstance(data, dict): return None` after the safe_load try/except.
- **Warning/logging:** Scope says "skip with warning" but implementation returns None silently. Logging belongs to #1271's scope ("Malformed files logged and skipped without raising"). Not blocking for #1270.
- **Test file:** `tests/test_memory_engine_1270.py` — 4 existing tests + 1 new test needed for non-mapping edge case.

### Dependency Analysis

- **#1269 (dep):** Not found (archived/done) — satisfied.
- **#1271 (downstream, depends on #1270):** In `todo`, says "All tests from #1270 pass GREEN." After this refinement, #1271 only needs the narrowed malformed-file tests to pass. Note: #1271's scope overlaps with parent's already-delivered engine — may need its own architecture review to reconcile.
- **#1272 (downstream, depends on #1271):** Scope says "Engine internals tested in #1270" — still true for malformed-file internals.

### Challenger Results

- Confidence: 0.38 (recommended block)
- Key finding accepted: non-mapping YAML path (TypeError) — added as new AC line
- Slug/cache-hit coverage equivalence concern: acknowledged but those items are parent-suite responsibility, not #1270
- Warning requirement concern: deferred to #1271 (implementation task) — not blocking
- Task ownership drift: addressed by title + AC refinement; downstream impact noted

**Architect override on block recommendation:** The challenger's primary actionable finding (non-mapping YAML crash) is incorporated as a new AC line. The remaining concerns (coverage equivalence of removed items, warning behavior, decomposition drift) are real but either belong to downstream tasks or are resolved by this refinement. Proceeding with APPROVE after incorporating the challenger's gap.

Test-writer: process normally (4 AC lines at td:2 + 1 new AC line at td:2)

[[2026-05-02]]
REFINE → APPROVE. Narrowed AC from 8 lines (full engine contract) to 6 lines (malformed-file handling only). Added 1 new AC line for non-mapping YAML frontmatter crash (challenger finding: TypeError at engine.py:122 when yaml.safe_load returns list/scalar). Round-trip, slug, cache, and empty-dir lines removed — already covered by parent suite test_mcp_memory_1266.py. Title updated to reflect actual scope.
[[2026-05-02]]
## Test-Writer Notes
- Retry: added 1 new failing test for non-mapping YAML frontmatter (challenger finding from architecture review)
- Test file: tests/test_memory_engine_1270.py
- Class: TestFromAC_FileEngine (5 tests total)
- New test: `test_non_mapping_yaml_frontmatter_skipped` — FAIL (TypeError: list indices must be integers or slices, not str at engine.py:122 when yaml.safe_load returns a list)
- Existing 4 tests: PASS (malformed-file guards already implemented by builder)
- Tests per category: error 5 (malformed-file handling)
- Total: 5 tests — 4 PASS (existing), 1 FAIL (new non-mapping YAML gap)
- ruff: clean
- Commit: 1846766f

## AC Coverage (Refined AC from Architecture Review)

| AC Line | Tests | Verdict |
|---------|-------|---------|
| Tests import MemoryEngine from owlbear_mcp_memory.engine (td:0) | import at line 18 | COVERED |
| Invalid YAML syntax in frontmatter → entry skipped, no exception | test_invalid_yaml_syntax_in_frontmatter_skipped | PASS (existing) |
| Missing required MemoryEntry fields → entry skipped, no exception | test_missing_required_fields_skipped | PASS (existing) |
| Empty YAML frontmatter block → entry skipped, no exception | test_empty_frontmatter_skipped | PASS (existing) |
| Valid entries returned alongside malformed files | test_valid_entries_alongside_malformed_file_still_returned | PASS (existing) |
| Non-mapping YAML frontmatter (list, scalar, int) → entry skipped, no exception | test_non_mapping_yaml_frontmatter_skipped | FAIL ✓ (RED) |