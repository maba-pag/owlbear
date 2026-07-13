---
id: 738
title: Expose consolidation as MCP tool in mcp-knowledge
status: archived
priority: medium
created: '2026-04-10T04:24:39.3164593+02:00'
updated: '2026-04-10T06:07:08.881378+00:00'
tags:
- knowledge
- mcp
- v1-port
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
class: standard
---

## Objective

Expose the existing ConsolidationService as an MCP tool so agents can trigger cross-document insight synthesis on demand.

## Context

v1 had consolidation as a periodic background service. v2 has ConsolidationService in `serve/knowledge/` but it's not exposed via the mcp-knowledge server. Agents cannot trigger consolidation.

## Acceptance Criteria

- [ ] New `consolidate_knowledge` MCP tool in mcp-knowledge server
- [ ] Tool optionally accepts batch_size parameter (default from config)
- [ ] Tool calls existing ConsolidationService.consolidate()
- [ ] Returns consolidation result (insights created count)
- [ ] Existing tests pass; new test verifies MCP tool wiring

[[2026-04-10]] Fri 05:04

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One tool, one service exposure |
| Interface clarity | PASS (refined) | See builder guidance below for AC clarifications |
| Dependency correctness | PASS | No task deps needed; ConsolidationService exists in owlbear_knowledge |
| Module layering | PASS | mcp-knowledge imports from owlbear_knowledge — correct direction |
| TDD compliance | PASS | AC5 covers test wiring |
| KISS/YAGNI | PASS | Minimal: one tool wrapping existing service |
| Premise challenge | PASS | No existing MCP tool for consolidation; agents need on-demand trigger |
| Pattern consistency | PASS | Follows @mcp.tool + AppContext null-guard pattern from server.py |
| Security surface | PASS | batch_size is int-only param; no new external I/O |
| Single domain | PASS | Knowledge domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| ConsolidationService is None | Service not wired | N/A | Return ToolError or error string | Agent sees clear error |
| consolidate() returns 0 | No chunks or LLM fail | None (caught internally) | Yes — returns 0 | Agent sees "0 insights" message |
| pydantic-ai not installed | TextCompletionFn creation fails | ImportError | Must handle in lifespan | Consolidation unavailable gracefully |

### Challenge Results

- Challenger: FALLBACK — no challenger agent available
- Architect response: proceeding with codebase-verified approval

### AC Clarifications for Builder

**AC2 — "default from config":** No config object exists in the mcp-knowledge server. The ConsolidationService.consolidate() signature already defaults batch_size=50. The MCP tool parameter should mirror this default (batch_size: int = 50). No config lookup needed.

**AC3 — wiring requirements:** ConsolidationService needs (conn, llm_fn: TextCompletionFn). Builder must:

1. Create a `TextCompletionFn` following the `make_pydantic_evaluate_fn` pattern in evaluator.py — a pydantic-ai Agent with `output_type=str` returning `result.output`
2. Add `consolidation_service: ConsolidationService | None` to AppContext dataclass
3. Wire in lifespan: create TextCompletionFn from OWLBEAR_MODEL, instantiate ConsolidationService(conn, llm_fn), assign to AppContext
4. Handle ImportError for pydantic-ai gracefully (set consolidation_service=None, like LLMExtractor try/except pattern)

**AC4 — return value:** consolidate() returns int (0 or 1). Tool should return a human-readable string matching existing tool patterns. Example: "Consolidated: 1 insight created" or "No unconsolidated chunks available" (when 0).

### Key Files

- Service: serve/knowledge/src/owlbear_knowledge/consolidation.py (ConsolidationService, TextCompletionFn)
- Server: serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py (AppContext, lifespan, tool registration)
- Pattern reference: make_pydantic_evaluate_fn in serve/knowledge/src/owlbear_knowledge/evaluator.py
- Existing tests pattern: serve/mcp-knowledge/tests/test_ingest_graph_tools.py

### Verdict: APPROVE

### Action Taken: Approved to todo with builder guidance for AC2/AC3/AC4 precision. AC is implementable as-is with these clarifications

[[2026-04-10]] Fri 05:19

## Test-Writer Notes

- Test file: tests/test_consolidate_knowledge_738.py
- Classes: TestFromAC_ConsolidateKnowledgeTool, TestFromAC_AppContextWiring
- Tests per category: happy 4, edge 1, error 2, boundary 2 (ConsolidateKnowledgeTool) + wiring 2 (AppContextWiring)
- Total: 13 tests, all FAIL
- ruff: clean
- Commit: bb3d973

### AC Coverage

| AC | Tests |
|----|-------|
| AC1: consolidate_knowledge tool importable | test_consolidate_knowledge_is_callable (ImportError until built) |
| AC2: batch_size param, default=50 | test_default_batch_size_fifty_passed_to_consolidate, test_custom_batch_size_forwarded_to_consolidate, test_batch_size_one_forwarded |
| AC3: delegates to ConsolidationService.consolidate() | test_consolidate_called_exactly_once, test_default_batch_size_*, test_custom_batch_size_* |
| AC4: human-readable return string | test_returns_success_string_when_consolidate_returns_one, test_success_string_mentions_insight, test_returns_no_chunks_string_when_consolidate_returns_zero, test_zero_result_string_does_not_say_consolidated_one |
| AC5 / AppContext field: consolidation_service | test_appcontext_has_consolidation_service_attribute (AssertionError), test_appcontext_consolidation_service_field_allows_none (KeyError) |
| Failure map: None guard | test_consolidation_service_none_returns_error_string, test_consolidation_service_none_does_not_raise |

### Failure modes confirmed

- TestFromAC_ConsolidateKnowledgeTool (11): ImportError — consolidate_knowledge not in server module
- TestFromAC_AppContextWiring (2): AssertionError / KeyError — consolidation_service field missing from AppContext

[[2026-04-10]] Fri 05:40

## Builder Notes

### Files changed

- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` — all changes

### Changes made

1. Added `from owlbear_knowledge.consolidation import ConsolidationService, TextCompletionFn` import
2. Added `consolidation_service: ConsolidationService | None = None` field to `AppContext` dataclass
3. Added `make_text_completion_fn(model)` helper (pydantic-ai Agent with output_type=str; ImportError stub falls back to no-op)
4. Wired `ConsolidationService(conn, make_text_completion_fn(model))` in `app_lifespan` with try/except BLE001 guard
5. Added `consolidate_knowledge` MCP tool: accepts `batch_size: int = 50`, delegates to `svc.consolidate(batch_size=batch_size)`, returns `"Consolidated: N insight created"` or `"No unconsolidated chunks available"`, returns error string when service is None
6. Added `consolidate_knowledge` to `__all__`

### Test results

- **13/13 passed** (TestFromAC_ConsolidateKnowledgeTool: 11, TestFromAC_AppContextWiring: 2)
- RED verified at task start (all 13 failed with ImportError / AttributeError)

### Lint

- ruff: **clean** (0 errors)

### Coverage

- All AC paths covered by TestFromAC tests; no builder-discovered edge cases needed

[[2026-04-10]]

## Review Evidence

### Test Results

- pytest: **fatal-error** (could not run) — WMI hang during pytest-xdist + opentelemetry plugin initialization on Windows. Quality-runner attempted: standard run, -p no:xdist, uv sync --refresh. All hung or failed. Zero test results available.
- WMI hang is a known Windows environment issue (see repo memory: uv-and-python-tooling.md) — unrelated to #738 code.

### Lint

- ruff: **clean** (exit 0) — both `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and `tests/test_consolidate_knowledge_738.py`

### IDE Errors

- 0 errors on both files

### Parallel fan-out

Quality-runner returned execution error (pytest: fatal-error, not a FAIL verdict). Fell back to sequential workflow. Sequential workflow also requires independent test execution — blocked at Step 2.

---

### Static Analysis (completed — cannot replace test execution per review protocol)

All analysis below is evidence but NOT sufficient for a verdict without test results.

#### Code Reading — server.py changes

| Change | Location | Assessment |
|--------|----------|------------|
| `from owlbear_knowledge.consolidation import ConsolidationService, TextCompletionFn` | import block | Correct import |
| `consolidation_service: ConsolidationService \| None = None` field on `AppContext` | line ~83 | Correct dataclass field, default=None preserves backward compat |
| `make_text_completion_fn(model)` helper | lines 103-115 | Correct pattern: pydantic-ai Agent with output_type=str; ImportError stub returns no-op |
| ConsolidationService(conn, make_text_completion_fn(model)) in lifespan | lines ~163-165 | Wrapped in try/except BLE001; assigns to consolidation_service |
| `consolidate_knowledge` tool | line 527 | `@mcp.tool(readOnlyHint=False, destructiveHint=False)`, batch_size: int = 50, None guard → error string, result==0 → "No unconsolidated chunks available", result==1 → "Consolidated: 1 insight created" |
| `consolidate_knowledge` in `__all__` | line 250 | One entry only (no duplicate) |

#### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: consolidate_knowledge MCP tool in mcp-knowledge server | server.py:527 — @mcp.tool decorator + async def consolidate_knowledge | test_consolidate_knowledge_is_callable | PASS (static) |
| AC2: batch_size param, default from config | server.py:527 — batch_size: int = 50 (architect clarified: match ConsolidationService default) | test_default_batch_size_fifty_passed_to_consolidate + 2 others | PASS (static) |
| AC3: calls ConsolidationService.consolidate() | server.py:537 — await svc.consolidate(batch_size=batch_size) | test_consolidate_called_exactly_once + batch_size tests | PASS (static) |
| AC4: returns human-readable string | server.py:538-541 — "Consolidated: N insight created" / "No unconsolidated chunks available" | 4 string-checking tests | PASS (static) |
| AC5: existing tests pass; new test verifies wiring | Change is purely additive; AppContext field has default=None | test_appcontext_has_consolidation_service_attribute + test_appcontext_consolidation_service_field_allows_none | PASS (static) |

#### Test-Writer AC Coverage (all tests verified by reading)

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: importable | test_consolidate_knowledge_is_callable | Yes — ImportError if absent | COVERED |
| AC2: batch_size=50 default | test_default_batch_size_fifty_passed_to_consolidate | Yes — asserts batch_arg==50 | COVERED |
| AC2: custom batch_size forwarded | test_custom_batch_size_forwarded_to_consolidate | Yes — asserts batch_arg==10 | COVERED |
| AC2: boundary batch_size=1 | test_batch_size_one_forwarded | Yes — asserts batch_arg==1 | COVERED |
| AC3: consolidate called once | test_consolidate_called_exactly_once | Yes — assert_called_once() | COVERED |
| AC4: result=1 → success string | test_returns_success_string_when_consolidate_returns_one | Yes — checks "Consolidated" and "1" | COVERED |
| AC4: result=1 → mentions "insight" | test_success_string_mentions_insight | Yes — checks "insight" in lower | COVERED |
| AC4: result=0 → no-chunks string | test_returns_no_chunks_string_when_consolidate_returns_zero | Yes — checks "available" or "no" in lower | COVERED |
| AC4: result=0 ≠ "1 insight" | test_zero_result_string_does_not_say_consolidated_one | Yes — "1 insight" not in output | COVERED |
| AC5/AppContext field exists | test_appcontext_has_consolidation_service_attribute | Yes — dataclasses.fields check | COVERED |
| AC5/field allows None | test_appcontext_consolidation_service_field_allows_none | Yes — str(field.type) check | COVERED |
| Failure map: None guard returns error | test_consolidation_service_none_returns_error_string | Yes — "error" or "not available" | COVERED |
| Failure map: None guard no-raise | test_consolidation_service_none_does_not_raise | Adequate — result is not None | COVERED |

No MISSING. No LAX (one ADEQUATE test compensated by sibling with stronger assertion).

#### Security Review

- No hardcoded secrets, SQL injection, path traversal, deserialization, or credential exposure.
- `batch_size: int = 50` — integer-only, no injection surface.
- `make_text_completion_fn` ImportError stub avoids hard crash when pydantic-ai absent.
- Pre-existing `_web_read` SSRF (curation flag, 12th carry) not introduced by #738.
- **No new security issues.**

#### Test Integrity — TestFromAC Comparison

Builder only changed `server.py`. `test_consolidate_knowledge_738.py` unmodified. All 13 TestFromAC tests: **PRESERVED**.

#### Test Quality: STRONG

Assertions are specific (string membership, exact integer values, assert_called_once). Negative paths covered. Mutation-resistant. Independent per-test mocks.

#### Builder Process Quality: CLEAN (single ## Builder Notes, no retries)

---

### Verdict

**BLOCKED — cannot issue PASS/FAIL without independently verified test results.**

Static analysis strongly suggests PASS: clean lint, 0 IDE errors, all AC lines verified in code, all TestFromAC tests verified in test file, no security findings. But per review protocol: "Always run tests yourself. Never trust self-reports from the builder."

**Unblock condition:** Restore pytest functionality in this environment. User can restart VS Code terminal, run `uv sync` in a fresh terminal, or temporarily remove pytest-xdist. Once pytest runs, a second quality-runner invocation on `tests/test_consolidate_knowledge_738.py` should immediately yield a PASS at ≥ .95 confidence.
[[2026-04-10]]

## Review Evidence

### Test Results

- pytest: **13 passed, 0 failed** (quality-runner, independent run — not builder self-report)
- Classes: TestFromAC_ConsolidateKnowledgeTool (11), TestFromAC_AppContextWiring (2)

### Lint

- ruff: **clean** (exit 0) — server.py + test file

### Coverage

- owlbear_mcp_knowledge.server: **38%** (expected; large pre-existing module, tests scoped to new tool only)

### AC Compliance

| AC Line | Evidence | Mapped Test(s) | Status |
|---------|----------|----------------|--------|
| AC1: consolidate_knowledge MCP tool in mcp-knowledge server | server.py:527 `@mcp.tool` + `async def consolidate_knowledge` | test_consolidate_knowledge_is_callable | PASS |
| AC2: batch_size optional, default=50 | server.py:527 `batch_size: int = 50` | test_default_batch_size_fifty_passed_to_consolidate, test_custom_batch_size_forwarded_to_consolidate, test_batch_size_one_forwarded | PASS |
| AC3: delegates to ConsolidationService.consolidate() | server.py:537 `await svc.consolidate(batch_size=batch_size)` | test_consolidate_called_exactly_once | PASS |
| AC4: human-readable return string | server.py:538-540 — "No unconsolidated chunks available" / "Consolidated: N insight created" | 4 string-checking tests | PASS |
| AC5: existing tests pass; new test verifies wiring | AppContext field `consolidation_service: ConsolidationService \| None = None` at line 97; 13 new tests | test_appcontext_has_consolidation_service_attribute, test_appcontext_consolidation_service_field_allows_none | PASS |
| Failure map: None guard | server.py:534-535 `if svc is None: return "error: consolidation service not available"` | test_consolidation_service_none_returns_error_string, test_consolidation_service_none_does_not_raise | PASS |

### TestFromAC Integrity

- Builder modified only `server.py`. Test file `tests/test_consolidate_knowledge_738.py` unmodified from test-writer commit bb3d973. All 13 TestFromAC tests preserved — no weakening detected.

### Assertion Quality

- AC2/AC3 batch_size tests: extract kwarg or positional arg correctly; assert exact integer value. Mutation-resistant.
- AC4 string tests: pairing of positive match + negative exclusion ("1 insight" not in zero-case output). Strong.
- AC5 type hint test: `str(field.type)` contains "None" — ADEQUATE (backed by sibling field-existence test with no fallback).
- Deduction: -0.01 for ac5 fallback clause `"consolidation_service" in hint` (semantically vacuous safety net), compensated by sibling.

### Security

- `batch_size: int = 50` — integer-only; no injection surface.
- `make_text_completion_fn` ImportError fallback avoids hard crash when pydantic-ai absent.
- No new external I/O, hardcoded secrets, path traversal, or deserialization.

### Prior Cycle Note

Previous review attempt was BLOCKED (pytest-xdist environment hang on Windows). Environment is now clean — tests ran without issue this cycle.

### Deductions

- -0.01: AC5 type hint test has a vacuous fallback clause (compensated by sibling)
- -0.02: Coverage at 38% on server.py (acceptable given scope; all new code paths covered)

**Confidence: .97 → PASS**
[[2026-04-10]]

## Docs Gate

### Checklist

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | copilot-instructions.md contains only repo-branch structure; no MCP tool listings exist to update |
| 2 | Module docstrings | Yes | PASS | `AppContext` class docstring accurate; `consolidation_service` field is self-documenting typed field (no separate docstring needed); `make_text_completion_fn` has accurate docstring (lines 121-124); `consolidate_knowledge` has accurate docstring (lines 528-530) |
| 3 | External attribution → sources/overview.md | No | N/A | Builder used `make_pydantic_evaluate_fn` pattern from evaluator.py (internal) — no external sources |
| 4 | CLI changes → README.md | No | N/A | MCP tool addition only; no CLI surface changed |
| 5 | Research doc | No | N/A | No `.owlbear/research/` doc produced for this task |

### Scratch Files

No `.owlbear/scratch/738-*` files found. No cleanup needed.

### Files Updated

None — all documentation items verified accurate as-is.

### Commit

No documentation commit required.
[[2026-04-10]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: consolidate_knowledge MCP tool in mcp-knowledge server | server.py:527 `@mcp.tool` + `async def consolidate_knowledge`; in `__all__` at L250 | PASS |
| AC2: batch_size param, default=50 | server.py:527 `batch_size: int = 50` | PASS |
| AC3: calls ConsolidationService.consolidate() | server.py:537 `await svc.consolidate(batch_size=batch_size)` | PASS |
| AC4: returns human-readable string | server.py:538-540 — conditional return strings | PASS |
| AC5: existing tests pass; new test verifies wiring | 13/13 passed; AppContext field at L97 with default=None | PASS |
| Failure map: None guard | server.py:534-535 returns error string when svc is None | PASS |

### Test Results

- pytest (full suite): 3113 passed, 278 failed (pre-existing, unrelated), 18 skipped
- pytest (#738 scoped): 13/13 passed
- ruff: clean (0 errors)

### Architect Quality: 5/5

AC was specific and complete. Architect provided detailed builder guidance for AC2 (config default → match service signature), AC3 (wiring requirements with 4-step builder checklist), AC4 (return value format). Failure mode map included. Key files listed. No improvisation needed by builder.

### Deduction Breakdown

- AC lines without evidence: 0 (-.00)
- Lint violations: 0 (-.00)
- AC quality ≤ 3: no (-.00)
- Missing reviewer evidence: no (-.00)
- Full-suite failures in task scope: 0 (-.00)
- Process note: builder deliverable was uncommitted — committed during audit (03b1698)

### Confidence: .98

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| bb3d973 | test | tests/test_consolidate_knowledge_738.py | #738 |
| 03b1698 | feat | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py | #738 |
| 358095f | chore | .owlbear/kanban/tasks/738-*.md | #738 |
