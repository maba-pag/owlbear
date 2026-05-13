---
id: 1519
title: 'P3-01: Tests for MCP server ac/proof_bundle tool parameters'
status: archived
priority: needed
created: 2026-05-13T02:29:38.031602+00:00
updated: 2026-05-13T07:49:51.466336+00:00
tags:
  - phase-3
  - scope:mcp-kanban
  - tdd
  - feature
parent: 1514
depends_on:
  - 1518
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1514

## Scope
In scope: Tests for MCP `create_task`, `edit_task` tool parameter passthrough to AgentView; `show_task` response field verification
Out of scope: Engine internals, migration, skill files, AgentView implementation (tested via mock)

## Acceptance Criteria
- AC1: MCP `create_task` tool exposes `ac: list[str] | None` and `proof_bundle: str | None` params; when provided (non-None), they reach `AgentView.create_task()` as corresponding kwargs
- AC2: MCP `edit_task` tool exposes `ac: list[str] | None`, `add_ac: list[str] | None`, `remove_ac: list[str] | None`, and `proof_bundle: str | None` params; when provided (non-None), they reach `AgentView.edit_task()` as corresponding kwargs
- AC3: `ShowTaskResponse` returned by MCP `show_task` includes `ac` (list[str]) and `proof_bundle` (str|None) fields populated from task frontmatter

Proof bundle: behavioral
2026-05-13T06:57:48+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests MCP tool parameter passthrough only |
| Interface clarity | PASS | AC refined with explicit nullable types (`list[str] | None`, `str | None`) and forwarding semantics ("when non-None, reach AgentView") |
| Dependency correctness | PASS | #1518 archived/completed; engine already has ac/proof_bundle in create_task and edit_task |
| Module layering | PASS | Tests MCP → AgentView boundary; follows existing test pattern in test_mcp_mutation_tools.py (mocked AgentView) |
| TDD compliance | PASS | This IS the TDD RED phase task; AC1/AC2 tests will fail (MCP handlers don't have params yet); AC3 is regression backstop (already GREEN via model inheritance) |
| KISS/YAGNI | PASS | 3 focused AC lines, no abstractions |
| Premise challenge | PASS | MCP tool exposure required by parent AC6 |
| Pattern consistency | PASS | Follows existing add_tag/remove_tag passthrough pattern; add_ac naming consistent with engine (engine uses add_ac, not add_acs) |
| Security surface | PASS | No new external boundaries; MCP tools are agent-internal |
| Single domain | PASS | scope:mcp-kanban only |

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1 | Refined: added explicit types (`list[str] | None`, `str | None`), forwarding clause ("when non-None, reach AgentView.create_task()") | Types from parent #1514 arch review note applied |
| AC2 | Refined: added explicit types for all 4 params per parent review note; `add_ac: list[str] | None` (not `str` as Brief incorrectly specified) | Aligned with existing `add_tag: list[str]` pattern |
| AC3 | No change needed: `ShowTaskResponse` inherits `ac` from `TaskFull` and `proof_bundle` from `TaskSummary`; AC3 tests will be GREEN as regression backstop | Documented as regression backstop |

### Scope Refinement
- "Unit tests" in original scope was misleading; tests span MCP handler → AgentView mock boundary
- Updated scope to: "Tests for MCP create_task, edit_task tool parameter passthrough to AgentView; show_task response field verification"

### Architecture Notes
- MCP `show_task` path already surfaces `ac` and `proof_bundle` via `ShowTaskResponse` → `TaskFull` → `TaskSummary` model chain — AC3 tests confirm existing behavior
- For AC1/AC2, existing test pattern: mock AgentView, call MCP handler, assert kwargs received (see test_mcp_mutation_tools.py)
- AgentView param naming: `add_ac`/`remove_ac` stay as-is (engine uses same names, unlike add_tag→add_tags)

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — single clear approach following existing test patterns

### Challenge Results
- Challenger: reconsider (0.62)
- Accepted findings: (1) artifact drift — applied refined AC to task body before advancing; (2) scope section misleading — updated "unit tests" to describe actual MCP→AgentView test boundary; (3) nullable forwarding semantics — added "when provided (non-None)" clause to AC1/AC2
- Rejected findings: (4) RED-phase overstatement — AC3 being GREEN is intentional regression backstop, documented; (5) schema contract coverage — schema assertions are implementation-level detail for test-writer, not AC-level concern
- Architect response: revised AC and scope to address accepted findings; approval proceeds after refinement

### Verdict: APPROVE
### Action Taken: Refined AC with explicit types and forwarding semantics. Updated scope section. Advanced #1519 → todo.
2026-05-13T07:06:13+00:00
## Test-Writer Notes
- Test file: tests/test_mcp_ac_params_1519.py
- Classes: TestFromAC_CreateTaskACParams, TestFromAC_EditTaskACParams, TestFromAC_ShowTaskResponseFields
- Tests per category:
  - happy: 4 (forwarding: ac, proof_bundle, add_ac, remove_ac)
  - edge: 1 (ac=[] empty list)
  - error: 0
  - boundary: 0
  - signature/structure: 8 (inspect.signature checks for each missing param)
  - regression backstop: 4 (AC3, intentionally GREEN — see below)
- Total: 17 tests
- AC1/AC2: 13 FAIL (TypeError — params do not exist on create_task/edit_task tools)
- AC3: 4 PASS (intentional regression backstops — architect pre-approved; ShowTaskResponse already carries ac/proof_bundle via TaskFull/TaskSummary; challenger finding (4) rejected in arch-review)
- ruff: clean

### AC coverage table
| AC | Tests | Status |
|----|-------|--------|
| AC1: create_task exposes ac/proof_bundle | test_create_task_exposes_ac_param, test_create_task_exposes_proof_bundle_param, test_create_task_forwards_ac_when_provided, test_create_task_forwards_proof_bundle_when_provided, test_create_task_forwards_ac_empty_list | FAIL ✓ |
| AC2: edit_task exposes ac/add_ac/remove_ac/proof_bundle | test_edit_task_exposes_{ac,add_ac,remove_ac,proof_bundle}_param, test_edit_task_forwards_{ac,add_ac,remove_ac,proof_bundle}_when_provided | FAIL ✓ |
| AC3: ShowTaskResponse ac/proof_bundle from frontmatter | test_show_task_response_model_has_{ac,proof_bundle}_field, test_show_task_response_{ac,proof_bundle}_accepts_* | PASS (intentional backstop) |
2026-05-13T07:24:17+00:00
## Builder Notes
- Implementation: updated `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
  - `create_task` now exposes `ac: list[str] | None` and `proof_bundle: str | None`
  - `edit_task` now exposes `ac`, `add_ac`, `remove_ac`, `proof_bundle` params
  - Forwarding semantics are non-None passthrough only (matches AC wording and preserves existing behavior when omitted)
- RED verification (quality-runner): `tests/test_mcp_ac_params_1519.py` -> 17 total, 13 failed, 4 passed (expected AC3 backstop)
- GREEN verification (quality-runner): `tests/test_mcp_ac_params_1519.py` -> 17 passed, 0 failed
- Durable module regression (quality-runner): `serve/mcp-kanban/tests/test_mcp_mutation_tools.py` -> 24 passed, 0 failed
- Coverage/lint evidence (quality-runner): scoped MCP server suite (347 tests) -> 347 passed, 0 failed, coverage `owlbear_mcp_kanban.server` = 91%, ruff clean
- Commit: `016f548e` with only `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- Evidence summary: AC1/AC2 signature + passthrough behavior now implemented; AC3 remained regression-green as expected; no test files modified.
2026-05-13T07:40:03+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1519 to docs | AC mapped to code and evidence sufficient.
- Evidence map:

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L340), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L362), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L364) | [tests/test_mcp_ac_params_1519.py](tests/test_mcp_ac_params_1519.py#L152), [tests/test_mcp_ac_params_1519.py](tests/test_mcp_ac_params_1519.py#L160), [tests/test_mcp_ac_params_1519.py](tests/test_mcp_ac_params_1519.py#L171), [tests/test_mcp_ac_params_1519.py](tests/test_mcp_ac_params_1519.py#L185), [tests/test_mcp_ac_params_1519.py](tests/test_mcp_ac_params_1519.py#L201) | PASS |
| AC2 | [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L445), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L486), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L488), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L490), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L492) | [tests/test_mcp_ac_params_1519.py](tests/test_mcp_ac_params_1519.py#L230), [tests/test_mcp_ac_params_1519.py](tests/test_mcp_ac_params_1519.py#L238), [tests/test_mcp_ac_params_1519.py](tests/test_mcp_ac_params_1519.py#L246), [tests/test_mcp_ac_params_1519.py](tests/test_mcp_ac_params_1519.py#L254), [tests/test_mcp_ac_params_1519.py](tests/test_mcp_ac_params_1519.py#L265), [tests/test_mcp_ac_params_1519.py](tests/test_mcp_ac_params_1519.py#L279), [tests/test_mcp_ac_params_1519.py](tests/test_mcp_ac_params_1519.py#L293), [tests/test_mcp_ac_params_1519.py](tests/test_mcp_ac_params_1519.py#L307) | PASS |
| AC3 | [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L449), [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L450), [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L525), [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L628), [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L660), [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L312), [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L344), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L880), [serve/kanban/src/owlbear_kanban/agent_view.py](serve/kanban/src/owlbear_kanban/agent_view.py#L214), [serve/kanban/src/owlbear_kanban/agent_view.py](serve/kanban/src/owlbear_kanban/agent_view.py#L241), [serve/kanban/src/owlbear_kanban/agent_view.py](serve/kanban/src/owlbear_kanban/agent_view.py#L296), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L324) | task-local backstop [tests/test_mcp_ac_params_1519.py](tests/test_mcp_ac_params_1519.py#L334), [tests/test_mcp_ac_params_1519.py](tests/test_mcp_ac_params_1519.py#L341), [tests/test_mcp_ac_params_1519.py](tests/test_mcp_ac_params_1519.py#L348), [tests/test_mcp_ac_params_1519.py](tests/test_mcp_ac_params_1519.py#L377), plus durable passthrough [serve/mcp-kanban/tests/test_mcp_read_tools.py](serve/mcp-kanban/tests/test_mcp_read_tools.py#L578), [serve/mcp-kanban/tests/test_mcp_read_tools.py](serve/mcp-kanban/tests/test_mcp_read_tools.py#L648), and real path [serve/kanban/tests/test_engine_coverage.py](serve/kanban/tests/test_engine_coverage.py#L2022) | PASS |

- Builder evidence review: task body evidence is internally consistent. Reported RED, GREEN, durable regression, scoped suite, coverage, and lint evidence align with the reviewed source.
- Safety/security: no new dependency or external boundary; the change is a mechanical passthrough to AgentView.

## Observations
- AC3 proof is sufficient but indirect under the accepted task scope. The task-local tests cover envelope field presence and typing, while the adjacent durable suite covers the show_task passthrough path. A future hardening pass could add one disk-backed MCP show_task assertion for ac and proof_bundle, but that is not blocking for this review.
2026-05-13T07:42:18+00:00
## Docs Gate

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| Item 1: README Verification | FIXED | `serve/mcp-kanban/README.md` tools table had stale signatures for `create_task` (missing `ac`, `proof_bundle`) and `edit_task` (missing `ac`, `add_ac`, `remove_ac`, `proof_bundle`). Updated both rows to match `server.py` L340–L492. `TaskSummary`/`TaskFull` sections already documented `proof_bundle`/`ac` — no changes needed there. Layer 1 grep confirms new params present; Layer 2 editorial confirms no contradictions. |
| Item 2: External Attribution | N/A | No external sources influenced implementation. |
| Item 3: Research Doc | N/A | No research doc linked from task body. |
| Item 4: Deletion Detection | N/A | No source files deleted in this task. |

### Files Updated
- `serve/mcp-kanban/README.md` — updated `create_task` and `edit_task` tool signatures in the Tools table.

### Scratch Cleanup
- No `.owlbear/scratch/1519-*` files found.
2026-05-13T07:49:51+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: 4497 passed, 216 failed, 14 skipped, 5 errors (54.52s)\n- All 216 failures confirmed PRE-EXISTING: reverting server.py to pre-1519 state reproduces identical failures. The single MCP-kanban domain failure (test_guidance.py::test_validation_error_maps_to_tool_error) also pre-dates this task.\n- Task-scoped tests: 17/17 passed. MCP-kanban domain suite: 365/366 passed (1 pre-existing).\n- regression verdict: PASS\n\n### Intent Verification\n- scope alignment: PASS (changed file: serve/mcp-kanban/src/owlbear_mcp_kanban/server.py, within scope:mcp-kanban)\n- purpose match: PASS (adds ac/proof_bundle params to MCP create_task and edit_task tools, matching stated AC)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 4/5\n- AC specificity: explicit types (list[str] | None, str | None), forwarding semantics refined through challenger feedback\n- Edge case coverage: empty list edge case covered (AC1 test_create_task_forwards_ac_empty_list)\n- Design direction: architect notes on existing model chain inheritance (AC3 backstop) were helpful and accurate\n- Minor gap: forwarding semantics clause was absent from original AC, added only after challenger review (0.62 reconsider)\n\n### Commit Integrity\n- upstream commit presence: PASS (builder: 016f548e, test-writer: 8a4bfa38)\n- Process concern: doc-writer README update (serve/mcp-kanban/README.md) is uncommitted. Doc-writer should commit deliverables before advancing to done.\n- kanban commit packaging: pending (Step 6)\n\n### Deduction Breakdown\nNo deductions applied:\n- No task-introduced regressions (pre-existing confirmed)\n- Intent aligned with scope and purpose\n- AC quality 4/5 (above threshold)\n- Reviewer evidence present and detailed (PASS verdict with full AC-to-code mapping)\n- Lint clean\n- Evidence internally consistent\n\n### Confidence: 1.00\n### Action: archive