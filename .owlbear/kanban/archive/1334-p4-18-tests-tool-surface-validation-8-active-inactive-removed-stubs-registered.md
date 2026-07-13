---
id: 1334
title: 'P4-18: Tests — Tool surface validation (8 active, inactive removed, stubs
  registered)'
status: archived
priority: medium
created: 2026-05-04T05:48:50.188392+00:00
updated: 2026-05-07T14:57:39.344881+00:00
tags:
- phase-4
- scope:mcp-knowledge
- knowledge
- test
parent: 1316
depends_on:
- 1330
- 1332
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.9)

## Acceptance Criteria

- [ ] Tests verify exactly 8 tools registered in active MCP server (O7)
- [ ] Tests verify active tools: search_knowledge, list_sources, get_stats, ingest_document, refresh_source, get_next_batch, get_consolidation_candidates, store_enrichment
- [ ] Tests verify removed tools not registered: list_entities, bookmark_source, list_bookmarks, update_bookmark_tags, consolidate_knowledge
- [ ] Tests verify 4 scope stubs exist: import_scope, export_scope, sync_from_global, sync_to_global
- [ ] Tests verify scope stubs are not exposed to agents (registered internally but not in tool list)

## Scope

- **In scope:** Tool registration validation, tool count assertion, stub existence check
- **Out of scope:** Scope stub implementation (D12, D16 — deferred)
[[2026-05-07]]
## Research

**Key findings:**
- Current server has 16 registered tools; target is 8 active + 4 scope stubs (functions only, not tools)
- Test pattern: `mcp._tool_manager.list_tools()` — established in test_tool_annotations_501.py
- `get_consolidation_candidates` is currently a bare function (not registered) — #1335 must register it
- Scope stubs currently have @mcp.tool decorators — #1335 must remove them while keeping functions
- 5 tests needed: count=8, active set present, removed set absent, stubs exist, stubs not exposed

**Research doc:** `.owlbear/research/mcp-knowledge-tool-surface-validation.md`
**Tier:** T1 — autonomous (straightforward test validation, no decisions needed)
**No new follow-up tasks needed** — #1334 proceeds to test-writer, #1335 implements cleanup.
[[2026-05-07]]

## Architecture Review

### AC Refinement

AC4/AC5 contained contradictory wording ("registered internally but not in tool list" vs research's "functions only, not tools"). FastMCP has no concept of hidden-but-registered tools — `ToolManager.list_tools()` returns ALL registered tools. The intended contract from research + #1335 is clear: scope stubs lose `@mcp.tool` decorators, remain as bare callables.

**Revised AC (replaces original):**

- [ ] Tests verify exactly 8 tools in `mcp._tool_manager.list_tools()` at import time (td:1)
- [ ] Tests verify active tool set contains: search_knowledge, list_sources, get_stats, ingest_document, refresh_source, get_next_batch, get_consolidation_candidates, store_enrichment (td:1)
- [ ] Tests verify removed tools absent from tool list: list_entities, bookmark_source, list_bookmarks, update_bookmark_tags, consolidate_knowledge (td:1)
- [ ] Tests verify 4 scope stub functions exist as callables in server module: import_scope, export_scope, sync_from_global, sync_to_global (td:1)
- [ ] Tests verify scope stub names are NOT in `mcp._tool_manager.list_tools()` results (td:1)

**Notes:**
- Test pattern: `mcp._tool_manager.list_tools()` returns tool objects with `.name` attribute (established in test_tool_annotations_501.py)
- Tests validate import-time state (no lifespan startup needed). `_apply_tool_exclusions()` is env-var-driven runtime removal — orthogonal to this contract.
- All tests will FAIL against current 16-tool server and pass GREEN after #1335 removes decorators and registers `get_consolidation_candidates`.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Only test assertions, no implementation |
| Interface clarity | PASS | After refinement — exact tool names, mechanism, assertion targets |
| Dependency correctness | PASS | #1330 archived, #1332 archived |
| Module layering | PASS | Tests import from owlbear_mcp_knowledge.server only |
| TDD compliance | PASS | This IS the RED phase; #1335 is GREEN |
| KISS/YAGNI | PASS | 5 test cases with simple assertions |
| Premise challenge | PASS | Tool surface lock needed before implementation |
| Pattern consistency | PASS | Follows test_tool_annotations_501.py pattern |
| Security surface | N/A | Test-only task |
| Single domain | PASS | mcp-knowledge scope exclusively |

### Challenge Results
- Challenger: reconsider (confidence 0.34)
- Key finding: AC5 "registered internally but not in tool list" contradicts FastMCP's model
- Architect response: ACCEPTED — refined AC4/AC5 to eliminate ambiguity. "Registered internally" replaced with "exist as callables in server module" and "NOT in list_tools() results"

### Test Depth
- Max depth: 1
- Test-writer: SKIP (tagged `test` — builder writes test file directly)

### Verdict: APPROVE
### Action Taken: Refined AC4/AC5 to resolve scope-stub contract ambiguity, approved to todo
[[2026-05-07]]
Architecture review complete. Refined AC4/AC5 to resolve scope-stub contract ambiguity identified by challenger (FastMCP has no hidden-registration concept). All criteria PASS. Approved to todo.
[[2026-05-07]]
## Test-Writer Notes

**Test file:** `tests/test_mcp_knowledge_tool_surface_1334.py`
**Commit:** `632ae98f`

### Test class: `TestFromAC_ToolSurfaceValidation`

| Category | Tests | Count |
|----------|-------|-------|
| Structural (count) | `test_exactly_eight_tools_registered` | 1 |
| Happy path (active set) | `test_all_active_tools_present` | 1 |
| Negative/absence | `test_removed_tools_not_registered` | 1 |
| Combined callable+absence | `test_scope_stubs_are_callable_and_not_registered_as_tools` | 1 |
| **Total** | | **4 tests, all FAIL** |

### AC coverage table

| AC | Test | Fails in RED? |
|----|------|---------------|
| AC1: exactly 8 tools | `test_exactly_eight_tools_registered` | YES — count is 16 |
| AC2: active tools present | `test_all_active_tools_present` | YES — `get_consolidation_candidates` missing |
| AC3: removed tools absent | `test_removed_tools_not_registered` | YES — 5 deprecated tools still registered |
| AC4: stubs are callables | `test_scope_stubs_are_callable_and_not_registered_as_tools` (combined) | YES — via AC5 assertion |
| AC5: stubs not in tool list | `test_scope_stubs_are_callable_and_not_registered_as_tools` (combined) | YES — 4 scope stubs still registered as tools |

### AC4/AC5 design note
FastMCP's `@mcp.tool()` decorator is side-effect-only — it returns the original function unchanged, so `callable()` returns True both before and after removing the decorator. Standalone AC4 would PASS in RED; merged AC4+AC5 into one test where the failing assertion is "not in tool list."

### RED phase confirmation
pytest result: 4 failed, 0 passed. ruff: clean.
[[2026-05-07]]
## Builder Notes
- Implementation: updated [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py) to align tool surface with AC.
- Fixes applied:
  - Registered `get_consolidation_candidates` as an MCP tool at import time (matching the same registration pattern used for `get_next_batch`/`store_enrichment`).
  - Removed `@mcp.tool(...)` decorators from deprecated tools: `list_entities`, `bookmark_source`, `list_bookmarks`, `update_bookmark_tags`, `consolidate_knowledge`.
  - Removed `@mcp.tool(...)` decorators from scope-stub functions while keeping them callable: `import_scope`, `export_scope`, `sync_from_global`, `sync_to_global`.
- Test evidence (quality-runner, scoped):
  - `tests/test_mcp_knowledge_tool_surface_1334.py`: 4 passed, 0 failed.
  - RED re-check before implementation confirmed all 4 `TestFromAC_*` assertions failing as expected.
- Lint evidence (quality-runner, scoped):
  - ruff clean for [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py) and [tests/test_mcp_knowledge_tool_surface_1334.py](tests/test_mcp_knowledge_tool_surface_1334.py).
- Coverage (scoped report):
  - `owlbear_mcp_knowledge.server`: 29.54% in task-scoped run.
- Additional regression signal (out of AC scope):
  - Running extra package tests found 1 failure in [serve/mcp-knowledge/tests/test_tool_annotations_501.py](serve/mcp-knowledge/tests/test_tool_annotations_501.py) expecting `list_entities` to still be a registered MCP tool with annotations. This conflicts with #1334 AC (tool removed from exposed list) and should be reconciled in review/test curation.
- Commit: `430ccbdd`
[[2026-05-07]]
## Review Evidence
### Test Results
- quality-runner scoped pass: `tests/test_mcp_knowledge_tool_surface_1334.py` -> 4 passed, 0 failed.
- quality-runner focused adjacent regression: 4 failed, 0 passed on durable tests that still expect `list_entities` to remain an MCP-registered tool:
  - `serve/mcp-knowledge/tests/test_tool_annotations_501.py::TestFromAC_KnowledgeToolAnnotations::test_list_entities_idempotent_hint_true` -> `list_entities has no ToolAnnotations; readOnlyHint=True already present but idempotentHint=True must also be added`
  - `serve/mcp-knowledge/tests/test_outputschema_541.py::TestFromAC_ListToolOutputSchemas::test_list_entities_output_schema_has_defs_with_entity_info` -> `list_entities tool or fn_metadata not found`
  - `serve/mcp-knowledge/tests/test_ingest_graph_tools.py::TestFromAC_ToolDescriptions::test_list_entities_description_is_verb_first` -> `'list_entities' description should start with a verb, got: ''`
  - `serve/mcp-knowledge/tests/test_ingest_graph_tools.py::TestFromAC_ToolReadOnlyHints::test_list_entities_has_read_only_hint_true` -> `list_entities has no ToolAnnotations; readOnlyHint=True must be set`

### Lint Results
- quality-runner scoped lint: ruff clean for `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and `tests/test_mcp_knowledge_tool_surface_1334.py`.

### Coverage
- quality-runner scoped coverage: `owlbear_mcp_knowledge.server` 30.0% module coverage.
- Non-blocking for this narrow registration-surface task: the changed surface is exercised directly by exact-name registry assertions rather than broad runtime-path coverage.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Exactly 8 tools in `mcp._tool_manager.list_tools()` at import time | Focused task suite green; registry surface checked directly against live `mcp._tool_manager.list_tools()`; `get_consolidation_candidates` registered via `mcp.tool(...)` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | `test_exactly_eight_tools_registered` | PASS |
| Active tool set contains the 8 expected names | Focused task suite green against the exact active-name set | `test_all_active_tools_present` | PASS |
| Removed tools absent from tool list | Focused task suite green; removed names are now bare callables rather than decorated tools in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (`list_entities`, `bookmark_source`, `list_bookmarks`, `update_bookmark_tags`, `consolidate_knowledge`) | `test_removed_tools_not_registered` | PASS |
| Scope stubs exist as callables in server module | Focused task suite green; `import_scope`, `export_scope`, `sync_from_global`, `sync_to_global` remain callable functions in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | `test_scope_stubs_are_callable_and_not_registered_as_tools` | PASS |
| Scope stub names are NOT in `mcp._tool_manager.list_tools()` results | Same focused task suite green; decorators removed so stubs are no longer registry entries | `test_scope_stubs_are_callable_and_not_registered_as_tools` | PASS |

### Findings
- The task-owned `TestFromAC_ToolSurfaceValidation` suite is discriminating and green against the live snapshot.
- The live server implementation matches the refined task authority: `get_consolidation_candidates` is registered, while `list_entities`, the deprecated bookmark/consolidation helpers, and the four scope stubs are bare callables rather than MCP tools.
- The repo still contains durable tests that assert the old `list_entities` MCP-registration contract. Those tests now fail on the live snapshot, so the verification corpus is internally inconsistent.
- Only test-file changes remain. The correct fix is to migrate the durable tests, not to re-register `list_entities` and undo the refined 8-tool surface.

### Deductions
- -0.03: commit-diff / TestFromAC immutability could not be verified from the available tool surface, so preservation is high-confidence from live file inspection rather than commit proof.
- -0.13: focused adjacent regression still fails on durable registry-dependent tests, leaving the package test corpus inconsistent with the refined contract.

### Verdict
- Confidence: 0.84
- FAIL -> todo

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Update legacy annotation expectations so removed tool `list_entities` is no longer asserted as an MCP-registered tool | `serve/mcp-knowledge/tests/test_tool_annotations_501.py` | Focused quality-runner failure: `test_list_entities_idempotent_hint_true` |
| 2 | test-writer | Remove or rewrite output-schema assertions that still look up `list_entities` through FastMCP tool metadata | `serve/mcp-knowledge/tests/test_outputschema_541.py` | Focused quality-runner failure: `test_list_entities_output_schema_has_defs_with_entity_info` |
| 3 | test-writer | Rewrite durable description/readOnlyHint checks that still fetch `list_entities` from `mcp._tool_manager.list_tools()` | `serve/mcp-knowledge/tests/test_ingest_graph_tools.py` | Focused quality-runner failures: `test_list_entities_description_is_verb_first`, `test_list_entities_has_read_only_hint_true` |

### Informational
- Broad adjacent regression also surfaced older `get_stats` output-schema failures in `serve/mcp-knowledge/tests/test_outputschema_541.py`; those were excluded from the routing decision because the focused rerun isolated the task-caused `list_entities` contract breakage.
- Current source changes overlap task #1335's planned cleanup scope; if #1334 passes on retry, #1335 should be reconciled so the board does not carry duplicate implementation scope.

### Post-task Reflection
- Broad durable-suite reruns mixed task-caused breakage with older unrelated failures; a focused node-level rerun was necessary to route accurately.
- The refined AC is authoritative here: `list_entities` removal from the MCP registry is intentional, so durable tests must migrate instead of forcing compatibility back in.
- Review confidence is slightly reduced because commit-diff and dirty-tree contamination checks were not available through the current tool surface.
[[2026-05-07]]
## Test-Writer Notes

**Retry — reviewer Required Follow-up: remove legacy list_entities MCP-registry assertions**

### Changes made

| File | Action | Tests removed |
|------|--------|---------------|
| `serve/mcp-knowledge/tests/test_tool_annotations_501.py` | Removed `test_list_entities_idempotent_hint_true` | 1 |
| `serve/mcp-knowledge/tests/test_outputschema_541.py` | Removed AC3 section: `test_list_entities_output_schema_has_defs_with_entity_info` + 3 EntityInfo field tests | 4 |
| `serve/mcp-knowledge/tests/test_ingest_graph_tools.py` | Removed `test_list_entities_description_is_verb_first` and `test_list_entities_has_read_only_hint_true` | 2 |

**Total removed:** 7 tests — all fetched `list_entities` from `mcp._tool_manager.list_tools()`, which now returns None since the tool was removed from the registry in task #1334's implementation.

### Verification (scoped rerun after changes)
- `tests/test_mcp_knowledge_tool_surface_1334.py` — **4 passed, 0 failed** ✓
- `serve/mcp-knowledge/tests/test_tool_annotations_501.py` — passed ✓
- `serve/mcp-knowledge/tests/test_ingest_graph_tools.py` — passed ✓
- `serve/mcp-knowledge/tests/test_outputschema_541.py` — 4 pre-existing `get_stats` TypedDict failures (informational, pre-existing per review, not caused by #1334)
- ruff: clean ✓

### Direct-to-review advance (Step 1b.1)
All reviewer Required Follow-up items were test-proof gaps only. All remaining tests pass. Advancing directly to review.

**Commit:** `16727199`
[[2026-05-07]]
## Builder Notes
- Implementation: no source-code changes required in this build pass.
- Reason: task-owned `TestFromAC_*` suite is already green after the test-only retry cycle; no failing AC-bound tests remained to drive additional GREEN implementation.
- Tests: `tests/test_mcp_knowledge_tool_surface_1334.py` -> 4 passed, 0 failed (scoped quality-runner).
- Lint: ruff clean for `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and `tests/test_mcp_knowledge_tool_surface_1334.py` (scoped quality-runner).
- Coverage: `owlbear_mcp_knowledge.server` 30% in scoped run (captured as evidence; no new code touched in this pass).
- Regression note: durable-suite inconsistencies previously cited for `list_entities` were addressed in test-writer retry notes; this builder pass confirms the AC-bound contract is currently satisfied.

### Evidence Summary
- quality-runner scoped pytest exit code: 0
- quality-runner scoped ruff exit code: 0
- Working tree check: no local changes in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` or `tests/test_mcp_knowledge_tool_surface_1334.py`

### Post-task Reflection
- In retry cycles where review findings are test-only, a builder verification pass may be purely evidentiary rather than implementation.
- Scoping verification to task-owned tests avoids noise from unrelated durable-suite failures.
- Confirming target-file cleanliness before release prevents accidental mixed-deliverable routing.
[[2026-05-07]]
## Review Evidence
### Test Results
- quality-runner scoped pass: [tests/test_mcp_knowledge_tool_surface_1334.py](tests/test_mcp_knowledge_tool_surface_1334.py#L105) -> 4 passed, 0 failed.
- quality-runner adjacent regression: 69 passed, 4 failed across [serve/mcp-knowledge/tests/test_tool_annotations_501.py](serve/mcp-knowledge/tests/test_tool_annotations_501.py), [serve/mcp-knowledge/tests/test_outputschema_541.py](serve/mcp-knowledge/tests/test_outputschema_541.py), and [serve/mcp-knowledge/tests/test_ingest_graph_tools.py](serve/mcp-knowledge/tests/test_ingest_graph_tools.py).
- Remaining adjacent failures are all in [serve/mcp-knowledge/tests/test_outputschema_541.py](serve/mcp-knowledge/tests/test_outputschema_541.py#L175), [serve/mcp-knowledge/tests/test_outputschema_541.py](serve/mcp-knowledge/tests/test_outputschema_541.py#L186), [serve/mcp-knowledge/tests/test_outputschema_541.py](serve/mcp-knowledge/tests/test_outputschema_541.py#L198), and [serve/mcp-knowledge/tests/test_outputschema_541.py](serve/mcp-knowledge/tests/test_outputschema_541.py#L210). They concern the unrelated `get_stats` output-schema contract, not `list_entities` or the 8-tool surface.

### Lint Results
- quality-runner scoped lint: clean for [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L792) and [tests/test_mcp_knowledge_tool_surface_1334.py](tests/test_mcp_knowledge_tool_surface_1334.py#L49).
- Adjacent regression lint: clean for the three durable test files above.

### Coverage
- quality-runner scoped coverage: `owlbear_mcp_knowledge.server` at 43.85%.
- Non-blocking for this narrow import-time registry task: the AC is exercised by exact registry assertions plus structural inspection of the server registration points.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Exactly 8 tools in `mcp._tool_manager.list_tools()` at import time | Fresh quality-runner scoped pass; task helper reads live registry via [tests/test_mcp_knowledge_tool_surface_1334.py](tests/test_mcp_knowledge_tool_surface_1334.py#L49). Server has 3 post-def registrations at [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L792), [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L795), [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L798) and 5 decorated tool defs at [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L829), [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L864), [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L879), [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L941), [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L1194). | [tests/test_mcp_knowledge_tool_surface_1334.py](tests/test_mcp_knowledge_tool_surface_1334.py#L105) | PASS |
| Active tool set contains the 8 expected names | Fresh scoped pass on the exact active-name assertion; `get_consolidation_candidates` is now registered at [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L795). | [tests/test_mcp_knowledge_tool_surface_1334.py](tests/test_mcp_knowledge_tool_surface_1334.py#L122) | PASS |
| Removed tools absent from tool list | Fresh scoped pass on removed-name absence; removed functions remain callable definitions at [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L909), [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L1005), [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L1027), [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L1049), and [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L1240) with no `@mcp.tool` registration points. | [tests/test_mcp_knowledge_tool_surface_1334.py](tests/test_mcp_knowledge_tool_surface_1334.py#L139) | PASS |
| Scope stub functions exist as callables in server module | Fresh scoped pass; callable stub defs remain present at [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L1074), [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L1096), [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L1115), and [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L1153). | [tests/test_mcp_knowledge_tool_surface_1334.py](tests/test_mcp_knowledge_tool_surface_1334.py#L157) | PASS |
| Scope stub names are NOT in `mcp._tool_manager.list_tools()` results | Same combined test passed; structural check shows only the 8 registration points above, and none of the stub defs carry `@mcp.tool`. | [tests/test_mcp_knowledge_tool_surface_1334.py](tests/test_mcp_knowledge_tool_surface_1334.py#L157) | PASS |

### Findings
- No blocking review findings.
- The task-owned `TestFromAC_ToolSurfaceValidation` suite is discriminating: count, active-set, removed-set, and callable-plus-unregistered stub checks would each fail on the pre-fix server state.
- The prior `list_entities` durable-suite breakage is resolved. Current adjacent failures are limited to older `get_stats` schema assertions in [serve/mcp-knowledge/tests/test_outputschema_541.py](serve/mcp-knowledge/tests/test_outputschema_541.py#L175), unrelated to this task’s refined authority.
- Non-blocking downstream drift remains for docs/skill text: [serve/mcp-knowledge/README.md](serve/mcp-knowledge/README.md#L24) still lists removed tools, and [share/skills/h-knowledge-ops/SKILL.md](share/skills/h-knowledge-ops/SKILL.md#L36) plus [share/skills/h-knowledge-ops/SKILL.md](share/skills/h-knowledge-ops/SKILL.md#L183) still describe removed or deferred tools as active. This should be reconciled in the docs stage, not as a review blocker.

### Deductions
- -0.02: commit-diff / dirty-tree contamination could not be independently proven with the available review tool surface, so ownership relies on live file inspection plus fresh quality-runner evidence.
- -0.03: downstream docs/skill text still reflects the pre-cleanup tool surface and could mislead manual consumers until the docs stage updates it.

### Verdict
- Confidence: 0.95
- PASS -> docs

### Informational
- One prior `## Review Evidence` section exists in the task body; this pass confirms the second-cycle test-only retry resolved the earlier `list_entities` registry regression.
- The refined Architecture Review AC is authoritative for this task. Stale prose elsewhere that still describes scope stubs as registered-but-hidden does not override the refined `callable but unregistered` contract.

### Post-task Reflection
- Separating task-owned evidence from adjacent durable regressions was necessary; a single broader pass would have mixed current proof with older `get_stats` schema debt.
- For registry-surface tasks, structural inspection of the concrete registration points is a useful cross-check alongside green task-local tests.
- Docs and skill inventories are the main remaining drift after the code/test surface itself is corrected.
[[2026-05-07]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/mcp-knowledge/README.md` tools table listed 17 tools including all removed tools (`list_entities`, `bookmark_source`, `list_bookmarks`, `update_bookmark_tags`, `consolidate_knowledge`) and scope stubs (`import_scope`, `export_scope`, `sync_from_global`, `sync_to_global`) as active. Reduced to 8 active tools. Top-level description updated to remove "entity graph queries, bookmarking, and cross-project scope transfer" |
| 2 | Module docstrings | Yes | N/A | `server.py` modified; spot-checked all changed functions (`get_consolidation_candidates`, removed-tool functions, scope stubs). Function-level docstrings describe behavior accurately — decorator removal does not affect callable semantics |
| 3 | External attribution | No | N/A | No external patterns used; test-only + tool-registration task |
| 4 | Research doc | Yes | Verified | `.owlbear/research/mcp-knowledge-tool-surface-validation.md` exists and is linked from task body |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/mcp-topology.excalidraw` has `describes: serve/mcp-*/src/**` which matches changed `server.py`. Footer updated from `(56520054)` to `(16727199)` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted; decorator removal only — no orphaned IN-scope docs referencing deleted files |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | IN (docstrings) | N/A — no docstring changes needed |
| `serve/mcp-knowledge/README.md` | IN (package README) | Updated — tools table and description |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram) | Footer updated |
| `tests/test_mcp_knowledge_tool_surface_1334.py` | OUT (test file) | N/A |
| `serve/mcp-knowledge/tests/test_tool_annotations_501.py` | OUT (test file) | N/A |
| `serve/mcp-knowledge/tests/test_outputschema_541.py` | OUT (test file) | N/A |
| `serve/mcp-knowledge/tests/test_ingest_graph_tools.py` | OUT (test file) | N/A |
| `share/skills/h-knowledge-ops/SKILL.md` | OUT (agent-executable) | N/A — reviewer noted drift; stale agent-executable files route to architect |

### Files Updated
- `serve/mcp-knowledge/README.md` — tools table reduced to 8 active tools; description updated
- `share/diagrams/mcp-topology.excalidraw` — footer updated to commit `16727199`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1334-*` scratch files existed)
[[2026-05-07]]
## Audit\n\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| AC1: exactly 8 tools registered | `test_exactly_eight_tools_registered` asserts `len(tool_names) == 8` against live registry; green in full suite | PASS |\n| AC2: active tool set contains 8 names | `test_all_active_tools_present` asserts `_ACTIVE_TOOLS - tool_names` is empty; green | PASS |\n| AC3: removed tools absent | `test_removed_tools_not_registered` asserts `_REMOVED_TOOLS & tool_names` is empty; green | PASS |\n| AC4: scope stubs callable | Combined test verifies `getattr(server_mod, name)` is callable for all 4 stubs; green | PASS |\n| AC5: stubs not in tool list | Same combined test asserts stub names not in `_registered_tool_names()`; green | PASS |\n\n### Test Results\n- pytest (full suite): 4781 passed, 223 failed (pre-existing, unrelated modules), 6 errors (pre-existing)\n- Task tests: 4/4 green (`tests/test_mcp_knowledge_tool_surface_1334.py`)\n- ruff: 12 violations (all pre-existing, none in task scope)\n\n### Commit Integrity\n| Commit | Type | Attribution |\n|--------|------|-------------|\n| 632ae98f | test (RED) | test-writer |\n| 430ccbdd | feat (GREEN) | builder |\n| 16727199 | test (retry cleanup) | test-writer |\n| f48d0851 | docs (README, diagram) | doc-writer |\n\nWorking tree clean for all deliverable files.\n\n### Architect Quality: 4/5\nOriginal AC4/AC5 contradicted FastMCP semantics (no hidden-but-registered concept). Challenger caught it; architect refined cleanly. Refined AC is specific, testable, and led to discriminating tests.\n\n### Deduction Breakdown\n- Start: 1.00\n- -.02: 4 adjacent `get_stats` failures in `test_outputschema_541.py` (same package) assessed pre-existing per reviewer/builder attestation but not independently verified via commit archaeology\n- No other deductions apply (all AC evidenced, lint clean in scope, reviewer evidence present and detailed, no task-scope failures)\n\n### Confidence: 0.98\n### Action: archive