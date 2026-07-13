---
id: 1273
title: 'P1-07: Implement MCP tool layer with access control'
status: archived
priority: medium
created: 2026-05-02T03:43:38.542522+00:00
updated: 2026-05-03T13:28:22.933473+00:00
tags:
- phase-1
- scope:mcp-memory
parent: 1266
depends_on:
- 1272
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Implement the 5 MCP tools with access control, state transition enforcement, and query logic. Must pass all tests from #1272.

Brief: see parent #1266

## Scope

**In scope:**
- Rewrite `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` — 5 tool functions
- `store_learning(title, content, categories, confidence, scope_agents?)` → creates pending entry via engine
- `query_memory(categories?, scope_agents?, min_confidence?, limit?)` → filtered retrieval, default curated+approved, sorted approved-first then confidence desc
- `update_entry(entry_id, content?, categories?, confidence?, promote?)` → curator-only edits, pending→curated promotion
- `delete_entry(entry_id)` → curator-only, sets state=deleted
- `approve_entry(entry_id)` → user-only, curated→approved promotion
- State transition enforcement: reject invalid transitions with clear error messages
- `allowed_agents` config: tool-level restriction mechanism (curator tools reject non-curator callers)
- Wire tools into MCP server (`server.py` or equivalent registration)
- Update `__main__.py` to start the new server

**Out of scope:**
- Engine changes (completed in #1271)
- Model changes (completed in #1269)
- Skill documentation (handled by #1274)

## Acceptance Criteria

- [ ] All tests from #1272 pass GREEN
- [ ] 5 tools registered and callable via MCP
- [ ] store_learning creates entries with state=pending
- [ ] query_memory default excludes pending/deleted, sorts correctly
- [ ] update_entry enforces curator-only access
- [ ] delete_entry enforces curator-only access
- [ ] approve_entry enforces curated→approved only (rejects other states)
- [ ] Invalid state transitions produce ToolError with descriptive message
- [ ] Server starts via `uv run` entry point
[[2026-05-03]]
## Test-Writer Notes
- Test file: tests/test_mcp_memory_tools_1273.py
- Classes: TestFromAC_UpdateEntryFieldValidation, TestFromAC_QueryMemoryLimit
- Tests per category: happy 0, edge 2 (limit boundary), error 4 (validation failures, TypeError), boundary 0
- Total: 6 tests, all FAIL
- ruff: clean

**AC mapping:**
| AC line | Tests |
|---|---|
| update_entry enforces curator-only access | 2 field-validation tests (model_copy bypass bug) |
| query_memory default excludes pending/deleted, sorts correctly | 4 limit-parameter tests (scope interface gap) |
| All tests from #1272 pass GREEN | Verified — 71 existing tests PASS |
| store_learning creates entries with state=pending | Covered in test_mcp_memory_1266.py — no duplication |
| delete_entry enforces curator-only access | Covered in test_mcp_memory_1266.py |
| approve_entry enforces curated→approved only | Covered in test_mcp_memory_1266.py |
| Invalid state transitions produce ToolError with descriptive message | Message-content tests PASS (impl already correct) — removed per RED-phase rule |

**Root causes for failures:**
1. `update_entry` uses `model_copy(update=..., validate=False)` (Pydantic v2 default) — field validators (ge=0.7, min_length=1) are bypassed, invalid data written to disk silently. Fix: use `model_copy(..., validate=True)` and wrap ValidationError as ToolError.
2. `query_memory` missing `limit?` parameter (specified in scope interface) — TypeError on any call with `limit=`. Fix: add `limit: int | None = None` parameter and apply slice after sort.
[[2026-05-03]]
## Builder Notes
- Implementation: updated [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py) and [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py).
- Fixes applied:
  - Added `limit: int | None = None` to `query_memory` tool function and applied limit after filtering/sorting.
  - Propagated `limit` through MCP server `query_memory` wrapper so the tool is callable with the scoped interface.
  - Reworked `update_entry` mutation validation to construct a full payload and validate via `MemoryEntry.model_validate(...)`, wrapping `ValidationError` as `ToolError`.
- RED verification (pre-change): 6/6 task tests failed in [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py) with expected errors (`TypeError` for missing `limit`, missing `ToolError` on invalid field updates).
- GREEN verification (scoped):
  - `quality-runner` pass 1 (task + durable): 66 passed, 0 failed, ruff clean, module coverage 89%.
  - `quality-runner` pass 2 (expanded scoped set): 77 passed, 0 failed, ruff clean, `owlbear_mcp_memory.tools` coverage 93%.
- Lint: clean for touched files.
- Coverage: 93% on touched module `owlbear_mcp_memory.tools` (>=90 gate satisfied).
- Commit: `03315323` with only the two task-scoped files.

## Builder Reflection
- Problem faced: `model_copy(validate=True)` is unsupported in the active Pydantic version; this caused runtime `TypeError` despite correct intent.
- Workaround applied: switched to explicit full-object revalidation using `MemoryEntry.model_validate(payload)` to preserve field constraints.
- Pattern discovered: adding MCP wrapper params can trigger `PLR0913`; use targeted noqa for thin wrappers that intentionally mirror tool signatures.
- Quality gap observed: task test coverage alone left module at 89%; including adjacent task-scoped durable tests raised coverage to gate-compliant 93%.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner broad regression pass: 75 passed, 2 failed.
- Broad failures were `tests/test_mcp_memory_1266.py::TestFromAC_ConsumerDrift::test_agent_audit_prompt_does_not_call_get_knowledge` and `tests/test_mcp_memory_1266.py::TestFromAC_ConsumerDrift::test_agent_audit_prompt_references_query_memory`; both fail because the prompt-path assertion in [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L829) / [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L873) no longer matches the branch state. These are outside the builder diff and were not used as the routing reason.
- quality-runner focused gate on the builder-touched behavior: 47 passed, 0 failed on [tests/test_memory_tools_1272.py](tests/test_memory_tools_1272.py), [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py), and the relevant `TestFromAC_*` classes in [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py).

### Lint
- quality-runner: clean

### Coverage
- Focused coverage: [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py) 93%, [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py) 100%.
- Caveat: `app_lifespan` and all five server wrappers are excluded with `# pragma: no cover` at [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L64), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L84), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L105), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L128), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L143), and [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L149), so the server percentage does not prove MCP-surface behavior.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| All tests from #1272 pass GREEN | Focused quality-runner included [tests/test_memory_tools_1272.py](tests/test_memory_tools_1272.py) | Yes | COVERED |
| 5 tools registered and callable via MCP | None. Existing memory tests call pure tool functions directly; the only memory-suite touch of the server module is an import-only assertion at [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L794) | No | MISSING |
| store_learning creates entries with state=pending | [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L369) | Yes | COVERED |
| query_memory default excludes pending/deleted, sorts correctly | [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L685), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L713), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L739), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L760), plus limit-path checks at [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L145) | Yes for the default retrieval contract | COVERED |
| update_entry enforces curator-only access | [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L643), [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L110), [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L129) | Yes | COVERED |
| delete_entry enforces curator-only access | [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L654) | Yes | COVERED |
| approve_entry enforces curated->approved only (rejects other states) | [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L426), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L481) | Yes | COVERED |
| Invalid state transitions produce ToolError with descriptive message | Approved-entry branches assert `match="approved"` at [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L543), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L561), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L572), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L583), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L594), and [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L605), but pending->approved at [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L481) and deleted->curated at [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L528) assert only `ToolError` while implementation emits branch-specific text at [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L90) and [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L223) | Not always | LAX |
| Server starts via `uv run` entry point | Static wiring exists at [serve/mcp-memory/src/owlbear_mcp_memory/__main__.py](serve/mcp-memory/src/owlbear_mcp_memory/__main__.py#L5), [serve/mcp-memory/src/owlbear_mcp_memory/__main__.py](serve/mcp-memory/src/owlbear_mcp_memory/__main__.py#L8), [serve/mcp-memory/README.md](serve/mcp-memory/README.md#L12), and [.vscode/mcp.json](.vscode/mcp.json#L28), but there is no `TestFromAC_*` coverage for it | No automated proof | MISSING |

#### Security Review
- No hardcoded secrets, injection sinks, path traversal, unsafe deserialization, or unbounded input introduced in [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py) or [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py).

#### Test Integrity
- Preserved. Builder commit `03315323` is recorded in the task body at [.owlbear/kanban/tasks/1273-p1-07-implement-mcp-tool-layer-with-access-control.md](.owlbear/kanban/tasks/1273-p1-07-implement-mcp-tool-layer-with-access-control.md#L92), and `git diff --name-only 03315323~1 03315323` showed only [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py) and [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py). No `TestFromAC_*` files were modified.

#### Test Quality
- FAIL: the suite proves pure tool behavior but not the MCP server contract. Because the wrapper surface is both untested and excluded from coverage, a registration or wrapper-signature break could slip through as a false green.
- FAIL: the descriptive-message branch is only partially asserted. A generic or empty `ToolError` would still satisfy the pending->approved and deleted->curated tests.

#### Data Safety
- No issues found in the implementation diff. The revalidation change at [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L195) is the correct safety fix for the field-validator bypass.

#### Test Gaps
- Add MCP-surface tests that inspect the FastMCP registry and invoke the registered wrappers, not just the pure functions in [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py).
- Minimum proof needed:
  - Assert all five tool names are present on `mcp`.
  - Exercise the server-side `query_memory` wrapper with `limit=` to prove the MCP-visible signature includes the new parameter and forwards it.
  - Exercise `app_lifespan` to prove caller/env wiring reaches the wrapper path.
  - Add an entrypoint smoke/import test for [serve/mcp-memory/src/owlbear_mcp_memory/__main__.py](serve/mcp-memory/src/owlbear_mcp_memory/__main__.py).
  - Tighten invalid-transition tests to assert message text for pending->approved and deleted->curated.

#### Necessity Check
- N/A. No new dependency or external integration introduced.

#### Builder Process Quality
- CLEAN. One builder cycle, scoped diff, no loop pattern.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| All tests from #1272 pass GREEN | Focused quality-runner: 47 passed, 0 failed; includes [tests/test_memory_tools_1272.py](tests/test_memory_tools_1272.py) | [tests/test_memory_tools_1272.py](tests/test_memory_tools_1272.py) | PASS |
| 5 tools registered and callable via MCP | Wrappers exist at [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L75), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L96), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L117), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L142), and [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L148), but no memory test asserts registry membership or MCP invocation | none | FAIL |
| store_learning creates entries with state=pending | [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L369) passed in focused gate | pending-state test | PASS |
| query_memory default excludes pending/deleted, sorts correctly | Default retrieval tests in [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L685), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L713), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L739), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L760) | retrieval tests | PASS |
| update_entry enforces curator-only access | Focused gate includes [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L643), [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L110), [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L129) | access + validation tests | PASS |
| delete_entry enforces curator-only access | Focused gate includes [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L654) | access-control test | PASS |
| approve_entry enforces curated->approved only (rejects other states) | Focused gate includes [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L426), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L481) | transition tests | PASS |
| Invalid state transitions produce ToolError with descriptive message | Implementation has explicit messages at [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L90), [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L177), and [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L223), but the pending->approved and deleted->curated tests do not assert message text | partial | FAIL |
| Server starts via `uv run` entry point | Static wiring is present at [serve/mcp-memory/src/owlbear_mcp_memory/__main__.py](serve/mcp-memory/src/owlbear_mcp_memory/__main__.py#L5), [serve/mcp-memory/src/owlbear_mcp_memory/__main__.py](serve/mcp-memory/src/owlbear_mcp_memory/__main__.py#L8), [serve/mcp-memory/README.md](serve/mcp-memory/README.md#L12), and [.vscode/mcp.json](.vscode/mcp.json#L28), but there is no executable `TestFromAC_*` proof | none | FAIL |

### Deductions
- -0.04: broad durable regression run surfaced unrelated prompt-path drift; not used for routing after focused rerun.
- -0.08: MCP server-surface AC is untested; current green is vulnerable to false green on registration/wrapper breakage.
- -0.03: descriptive-message AC is only partially asserted.

### Verdict
- Confidence: 0.81
- FAIL -> todo
- Reason: implementation diff is green on focused tests, but the task still lacks executable proof for the MCP-visible server/entrypoint contract, and the descriptive-message branch is only partially asserted.

### Required Follow-up
- Test-writer: add `TestFromAC_*` coverage for MCP registration/wrapper invocation and the module entrypoint.
- Test-writer: strengthen invalid-transition tests to assert message content for pending->approved and deleted->curated.
[[2026-05-03]]
## Test-Writer Notes
- Retry: added 6 new tests for reviewer gaps. All 6 new tests PASS against current impl.
- Builder skip: test-only retry, all tests green → advancing directly to review (Step 1b.1).
- Test file: tests/test_mcp_memory_tools_1273.py
- New classes: TestFromAC_MCPRegistration, TestFromAC_MCPEntrypoint, TestFromAC_InvalidTransitionMessages
- Tests per category (new): happy 0, edge 2 (server wrapper + lifespan env wiring), error 2 (message-content assertions), boundary 2 (module import + registry check)
- Total new: 6 tests, all PASS (impl already correct)
- Total file: 12 tests, 12 PASS
- ruff: clean
- Commit: feb1c0c8

**AC coverage (retry gaps):**
| Reviewer gap | New test | Verdict |
|---|---|---|
| 5 tools registered and callable via MCP | TestFromAC_MCPRegistration::test_all_five_tool_names_registered | COVERED |
| server query_memory wrapper accepts limit= | TestFromAC_MCPRegistration::test_server_query_memory_wrapper_accepts_limit_and_forwards | COVERED |
| entrypoint smoke/import test for __main__ | TestFromAC_MCPEntrypoint::test_main_module_importable_and_exposes_mcp | COVERED |
| app_lifespan wires env vars to context | TestFromAC_MCPEntrypoint::test_app_lifespan_wires_env_to_context | COVERED |
| pending→approved ToolError message content | TestFromAC_InvalidTransitionMessages::test_approve_pending_entry_error_message_mentions_curated | COVERED |
| deleted→curated ToolError message content | TestFromAC_InvalidTransitionMessages::test_update_deleted_to_curated_error_message_describes_transition | COVERED |
[[2026-05-03]]
## Builder Notes
- No new code changes were required in this cycle; implementation and tests were already in place from prior builder/test-writer iterations.
- Verified GREEN with task-focused quality runs and routed based on passing scoped evidence.

### Verification Evidence
- Targeted gate command:
  - `uv run pytest tests/test_memory_tools_1272.py tests/test_mcp_memory_tools_1273.py tests/test_mcp_memory_1266.py -k 'not ConsumerDrift' --cov=serve/mcp-memory/src/owlbear_mcp_memory/tools --cov=serve/mcp-memory/src/owlbear_mcp_memory/server --cov-report=term-missing --cov-fail-under=0 -q --tb=short`
  - `uv run ruff check serve/mcp-memory/src/owlbear_mcp_memory/tools.py serve/mcp-memory/src/owlbear_mcp_memory/server.py tests/test_mcp_memory_tools_1273.py`
- Results:
  - Tests: **77 passed, 0 failed**
  - Coverage: `tools.py` **93%** (103 stmts, 7 miss), `server.py` **100%** (20 stmts, 0 miss)
  - Lint: **ruff clean**

### Context on broader regression noise
- A broader run including full `tests/test_mcp_memory_1266.py` surfaced two unrelated `ConsumerDrift` failures tied to missing `share/prompts/agent-audit.prompt.md`.
- Per scoped-gate discipline, routing used the targeted run above to validate task-owned behavior.

### AC Evidence Summary
- All tests from #1272 pass GREEN in scoped gate.
- MCP tool-layer behavior (registration/wrapper/entrypoint/transition messages) is covered by `tests/test_mcp_memory_tools_1273.py` and passes.
- Access-control and transition enforcement behavior remains green in covered suites.

Routing: ready for review.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner expanded scoped gate: 81 passed, 2 failed across [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py), [tests/test_memory_tools_1272.py](tests/test_memory_tools_1272.py), and [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py). The only failures were ConsumerDrift checks in [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L835) and [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L879) for missing [share/prompts/agent-audit.prompt.md](share/prompts/agent-audit.prompt.md), outside the builder diff and outside this task's AC.
- quality-runner focused gate: 23 passed, 0 failed on [tests/test_memory_tools_1272.py](tests/test_memory_tools_1272.py) and [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py).
- Reviewer startup smoke: running uv run python -m owlbear_mcp_memory with isolated OWLBEAR_MEMORY_DIR and OWLBEAR_MEMORY_CALLER stayed alive past a 2s timeout with no immediate traceback, then was terminated manually. That is sufficient runtime proof that the module entrypoint launches cleanly.

### Lint
- quality-runner: ruff clean on [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py), [tests/test_memory_tools_1272.py](tests/test_memory_tools_1272.py), and [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py).
- Editor diagnostics: no errors in [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py), or [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py).

### Coverage
- Expanded scoped quality-runner coverage: [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py) 93%, [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py) 100%, overall 89%.
- Focused gate coverage dropped [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py) to 74% only because it excludes the durable AC proofs in [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py); the expanded scoped run is the correct coverage gate for this task.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| All tests from #1272 pass GREEN | [tests/test_memory_tools_1272.py](tests/test_memory_tools_1272.py) in the focused quality-runner pass | Yes | COVERED |
| 5 tools registered and callable via MCP | [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L242), [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L256), plus the registered wrappers at [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L76), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L97), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L118), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L143), and [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L149) | Yes | COVERED |
| store_learning creates entries with state=pending | [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L369) | Yes | COVERED |
| query_memory default excludes pending/deleted, sorts correctly | [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L685), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L713), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L741), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L767), and limit-path checks at [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L147), [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L167), [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L178), [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L197) | Yes | COVERED |
| update_entry enforces curator-only access | [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L643), plus field-validation proof at [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L98) and [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L116) for the changed write path at [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L161) | Yes | COVERED |
| delete_entry enforces curator-only access | [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L654) | Yes | COVERED |
| approve_entry enforces curated->approved only (rejects other states) | [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L426), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L473), and descriptive-message tightening at [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L322) for the branch in [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L216) | Yes | COVERED |
| Invalid state transitions produce ToolError with descriptive message | [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L322) and [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L340) against [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L90) and [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L223) | Yes | COVERED |
| Server starts via uv run entry point | Import-level smoke at [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L292), env-wiring check at [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L300) for [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L64), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L66), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L67), and direct reviewer launch proof through [serve/mcp-memory/src/owlbear_mcp_memory/__main__.py](serve/mcp-memory/src/owlbear_mcp_memory/__main__.py#L7) and [serve/mcp-memory/src/owlbear_mcp_memory/__main__.py](serve/mcp-memory/src/owlbear_mcp_memory/__main__.py#L8) | Yes | COVERED |

#### Security Review
- No hardcoded secrets, injection sinks, path traversal, unsafe deserialization, or unbounded input introduced in [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py) or [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py).

#### Test Integrity
- Preserved. Builder commit 03315323 changed only [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py) and [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py).
- Test-writer retry commit feb1c0c8 changed only [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py).
- No builder modification to TestFromAC assertions was detected.

#### Test Quality
- STRONG: validator-bypass fixes are guarded by discriminating error-path tests at [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L98) and [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L116); silent acceptance of invalid values would fail.
- STRONG: limit behavior is guarded across boundary and filtered cases at [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L147), [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L167), [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L178), and [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L197); missing or misordered post-filter slicing would fail.
- ADEQUATE: the entrypoint test is import-level rather than a direct run-branch assertion, but the reviewer startup smoke closes that proof gap for this review.
- STRONG: test names are descriptive and tests are isolated via per-test temp directories.

#### Data Safety
- No issues found. The changed write path revalidates the full payload at [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L161) before persisting, which fixes the prior silent-corruption path.

#### Test Gaps
- None remaining in task scope after the retry and reviewer startup smoke.

#### Necessity Check
- N/A. No new dependency or external integration introduced.

#### Builder Process Quality
- CLEAN. One builder code cycle, one test-only retry, no loop pattern in implementation work.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| All tests from #1272 pass GREEN | Focused quality-runner: 23 passed, 0 failed, including [tests/test_memory_tools_1272.py](tests/test_memory_tools_1272.py) | [tests/test_memory_tools_1272.py](tests/test_memory_tools_1272.py) | PASS |
| 5 tools registered and callable via MCP | Registry assertion at [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L242); wrapper call with limit forwarding at [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L256); all five wrappers present in [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L76), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L97), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L118), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L143), [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L149) | registration + wrapper test | PASS |
| store_learning creates entries with state=pending | Passing durable proof at [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L369) in the expanded quality-runner run | pending-state test | PASS |
| query_memory default excludes pending/deleted, sorts correctly | Passing durable proofs at [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L685), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L713), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L741), [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L767), plus limit forwarding/slicing proofs at [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L147), [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L167), [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L178), [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L197), and the implementation at [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L124) / [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L156) | retrieval + limit tests | PASS |
| update_entry enforces curator-only access | Access-control proof at [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L643); changed validation path proven by [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L98) and [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L116) against [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L161) | access + validation tests | PASS |
| delete_entry enforces curator-only access | Passing durable proof at [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L654) | access-control test | PASS |
| approve_entry enforces curated->approved only (rejects other states) | Success path at [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L426); rejection path at [tests/test_mcp_memory_1266.py](tests/test_mcp_memory_1266.py#L473); message branch tightened at [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L322) and implemented at [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L223) | promotion + rejection tests | PASS |
| Invalid state transitions produce ToolError with descriptive message | Descriptive-message proofs at [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L322) and [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L340) against [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L90) and [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L223) | message tests | PASS |
| Server starts via uv run entry point | Direct reviewer launch smoke stayed running without immediate traceback through [serve/mcp-memory/src/owlbear_mcp_memory/__main__.py](serve/mcp-memory/src/owlbear_mcp_memory/__main__.py#L7) and [serve/mcp-memory/src/owlbear_mcp_memory/__main__.py](serve/mcp-memory/src/owlbear_mcp_memory/__main__.py#L8); env wiring also covered at [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L66) and [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L67) with [tests/test_mcp_memory_tools_1273.py](tests/test_mcp_memory_tools_1273.py#L300) | entrypoint smoke + env wiring | PASS |

### Deductions
- -0.03: expanded scoped regression still contains unrelated ConsumerDrift failures tied to missing [share/prompts/agent-audit.prompt.md](share/prompts/agent-audit.prompt.md).
- -0.02: automated startup proof is import-level; reviewer shell smoke supplied the decisive runtime check.

### Verdict
- Confidence: 0.95
- PASS -> docs
- Reason: task-owned MCP tool behavior, wrapper surface, validation enforcement, and startup path are all now proven with passing scoped tests, clean lint, sufficient coverage on the touched modules, preserved TestFromAC integrity, and a direct reviewer launch smoke.

### Reflection
- problem faced: the durable memory suite still contains unrelated ConsumerDrift failures caused by a missing prompt artifact outside this task.
- workaround applied: used the expanded run for regression context and the focused run for task routing, consistent with review scoping discipline.
- pattern discovered: startup ACs are more reliable when backed by a direct launch smoke, not only an import-level test.
[[2026-05-03]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/mcp-memory/README.md` Tools table: `query_memory` row did not mention the `limit` parameter added in this task — updated |
| 2 | Module docstrings | Yes | Verified | All public functions in `tools.py` and `server.py` carry accurate one-line docstrings; no changes needed |
| 3 | External attribution | No | N/A | No external patterns or articles referenced |
| 4 | Research doc | No | N/A | No research doc produced for this task |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `memory-layers.excalidraw` (describes `serve/mcp-memory/src/**`) and `mcp-topology.excalidraw` (describes `serve/mcp-*/src/**`) both matched; footer commit hashes updated from stale to `bc1cd508` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested |
| 7 | Deletion detection | No | N/A | No files deleted in this task |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/mcp-memory/src/owlbear_mcp_memory/tools.py | IN | Docstrings verified OK |
| serve/mcp-memory/src/owlbear_mcp_memory/server.py | IN | Docstrings verified OK |
| serve/mcp-memory/README.md | IN | Updated: added `limit` to query_memory description |
| share/diagrams/memory-layers.excalidraw | IN | Footer updated to bc1cd508 |
| share/diagrams/mcp-topology.excalidraw | IN | Footer updated to bc1cd508 |
| tests/test_mcp_memory_tools_1273.py | OUT | Test file — not edited |
| tests/test_memory_tools_1272.py | OUT | Test file — not edited |
| tests/test_mcp_memory_1266.py | OUT | Test file — not edited |

### Files Updated
- serve/mcp-memory/README.md
- share/diagrams/memory-layers.excalidraw
- share/diagrams/mcp-topology.excalidraw

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found
[[2026-05-03]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| All tests from #1272 pass GREEN | Task-scoped run: 23 passed incl. test_memory_tools_1272.py | PASS |
| 5 tools registered and callable via MCP | TestFromAC_MCPRegistration in test_mcp_memory_tools_1273.py L242, L256 | PASS |
| store_learning creates entries with state=pending | test_mcp_memory_1266.py L369 passing | PASS |
| query_memory default excludes pending/deleted, sorts correctly | test_mcp_memory_1266.py L685/L713/L741/L767 + limit tests L147/L167/L178/L197 | PASS |
| update_entry enforces curator-only access | test_mcp_memory_1266.py L643 + field-validation L98/L116 | PASS |
| delete_entry enforces curator-only access | test_mcp_memory_1266.py L654 | PASS |
| approve_entry enforces curated→approved only | test_mcp_memory_1266.py L426/L473 + message test L322 | PASS |
| Invalid state transitions produce ToolError with descriptive message | test_mcp_memory_tools_1273.py L322/L340 | PASS |
| Server starts via uv run entry point | test_mcp_memory_tools_1273.py L292/L300 + reviewer manual launch smoke | PASS |

### Test Results
- pytest (task-scoped): 23 passed, 0 failed
- pytest (memory-adjacent): 81 passed, 2 failed (ConsumerDrift — missing agent-audit.prompt.md, unrelated)
- pytest (full suite): 3789 passed, 136 failed — all failures in unrelated modules (kanban engine, cockpit events, etc.)
- ruff: clean

### Architect Quality: 4/5
AC lines were specific and verifiable. Two AC items (MCP registration and entrypoint) initially lacked test proof — caught correctly by 1st review cycle. Minor: no td:N annotations (defaulted to td:1). Overall well-written AC that enabled effective verification.

### Deduction Breakdown
- AC lines without evidence: 0 × -.02 = 0
- Lint violations: none → 0
- AC quality ≤ 3: no (4/5) → 0
- Missing reviewer evidence: no → 0
- Full-suite failures in task scope: none → 0

### Confidence: .98
(.02 conservatism: 136 background failures create noise floor that reduces cross-task regression certainty, though no task-scoped failures detected)

### Action: archive