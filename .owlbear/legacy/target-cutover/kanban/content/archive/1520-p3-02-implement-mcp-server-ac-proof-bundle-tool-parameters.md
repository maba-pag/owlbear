---
id: 1520
title: 'P3-02: Implement MCP server ac/proof_bundle tool parameters'
status: archived
priority: medium
created: 2026-05-13T02:29:42.731951+00:00
updated: 2026-05-13T09:14:23.732223+00:00
tags:
  - phase-3
  - scope:mcp-kanban
  - tdd
  - feature
  - scope:kanban
parent: 1514
depends_on:
  - 1519
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1514

## Scope
In scope: Add ac/proof_bundle/add_ac/remove_ac passthrough to AgentView.create_task() and AgentView.edit_task(); verify MCP server → AgentView → engine path produces correct responses end-to-end
Out of scope: Engine internals (#1518, completed), MCP handler changes (commit 016f548e, completed), migration, skill files, MCP param model drift (deferred to #1524)

## Acceptance Criteria
- AC1: `AgentView.create_task()` accepts `ac: list[str] | None = None` and `proof_bundle: str | None = None` keyword params; given `ac=["x"]` and `proof_bundle="behavioral"`, the returned `SingleTaskResponse.task.ac` equals `["x"]` and `.task.proof_bundle` equals `"behavioral"`
- AC2: `AgentView.edit_task()` accepts `ac: list[str] | None = None`, `add_ac: list[str] | None = None`, `remove_ac: list[str] | None = None`, and `proof_bundle: str | None = None` keyword params; given `proof_bundle="smoke"`, the returned `SingleTaskResponse.task.proof_bundle` equals `"smoke"`; given `add_ac=["y"]`, the returned `.task.ac` contains `"y"`
- AC3: MCP `show_task` response includes `ac` (list[str]) and `proof_bundle` (str|None) fields from `TaskFull` model (already satisfied — regression backstop)

Proof bundle: behavioral

## Previous Cycle (rejected)
Cycle 1 approved with `Proof bundle: existing` pointing at `tests/test_mcp_ac_params_1519.py`. Reviewer found FAIL: `AgentView.create_task()` and `AgentView.edit_task()` lack ac/proof_bundle params, so the live MCP → AgentView path would TypeError. The existing tests use MagicMock for AgentView, masking the signature mismatch. AC3 was satisfied.

### Reviewer Findings (Cycle 1)
- Finding 1 (AC1): MCP create_task handler forwards ac/proof_bundle, but AgentView.create_task() does not accept them — TypeError on real path
- Finding 2 (AC2): MCP edit_task handler forwards all 4 params, but AgentView.edit_task() does not accept them — TypeError on real path
- Finding 3 (Proof quality): test_mcp_ac_params_1519.py uses MagicMock for AgentView — cannot detect real signature mismatch
- AC3: Satisfied via TaskFull model chain
2026-05-13T08:28:27+00:00
## Architecture Review (Cycle 2)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | AgentView passthrough for ac/proof_bundle — one responsibility |
| Interface clarity | PASS | AC refined with observable output assertions (returned task fields), not just kwarg forwarding |
| Dependency correctness | PASS | #1519 archived/completed; #1518 archived/completed; engine and MCP handlers ready |
| Module layering | PASS | MCP server → AgentView → engine — standard downward dependency; AgentView.create_task/edit_task forward to engine equivalents |
| TDD compliance | PASS | Proof bundle escalated to `behavioral`; test-writer will write new tests using real AgentView+engine (not MagicMock) |
| KISS/YAGNI | PASS | Pure passthrough — add 2 params to create_task, 4 params to edit_task, forward to engine calls |
| Premise challenge | PASS | Required by parent AC6; AgentView is the missing bridge between MCP and engine |
| Pattern consistency | PASS | Follows existing forwarding pattern (tags/parent/depends_on in create_task; add_dep/remove_dep/add_tag/remove_tag in edit_task) |
| Security surface | PASS | No new external boundaries; MCP tools are agent-internal |
| Single domain | PASS | scope:kanban (AgentView) + scope:mcp-kanban (already committed); both are passthrough changes on the same data path |

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1 | Rewritten: now requires observable output (`SingleTaskResponse.task.ac`, `.task.proof_bundle` values) instead of just kwarg forwarding | Addresses cycle 1 false-green from mock-only proof |
| AC2 | Rewritten: requires observable output for proof_bundle set and add_ac append operations | Same rationale; concrete input→output pairs per h-ac-quality B2 |
| AC3 | Unchanged — regression backstop, already proven via TaskFull model chain | No action needed |

### Architecture Notes
- **Root cause of cycle 1 failure:** Planner decomposition created engine task (#1518) and MCP task (#1520) but no AgentView bridge task. AgentView is a mandatory middle layer in the MCP→engine path.
- **Scope re-centered on AgentView:** MCP handler changes are already committed (016f548e). Engine already accepts all params (#1518). The remaining work is adding 6 params across 2 AgentView methods and forwarding to engine calls.
- **Implementation pattern:** `AgentView.create_task()` (agent_view.py:520) currently forwards title, body, priority, tags, parent, depends_on → add ac, proof_bundle. `AgentView.edit_task()` (agent_view.py:607) currently forwards 12 params → add ac, add_ac, remove_ac, proof_bundle.
- **Observable output strengthening:** Cycle 1 used forwarding-only AC with MagicMock proof, which masked the real signature gap. Cycle 2 AC requires the returned SingleTaskResponse to contain the provided values — this can only pass with a real engine backing.
- **MCP param model drift:** CreateTaskParams/EditTaskParams in models.py omit the new fields. These are NOT used at runtime (FastMCP derives from function signatures). Deferred to consolidation test #1524.

### Proof-Bundle Validation
- Planner assignment: behavioral (original); de-escalated to existing (cycle 1); escalated back to behavioral (cycle 2)
- Final bundle: behavioral
- Test-writer: PROCEED (must write tests using real AgentView+engine, not MagicMock)
- Rationale: mock-backed existing proof was insufficient — caused false green in cycle 1

### Design Diverge
- Trigger: skipped — single clear approach (add params, forward to engine)

### Challenge Results
- Challenger: reconsider (0.63)
- Accepted: (1) AC quality — rewrote AC1/AC2 to require observable output instead of forwarding-only proof; (2) stale body — replaced body with refined scope/AC/proof-bundle
- Rejected: (3) schema model drift — not runtime, deferred to #1524; (4) AC3 under-specified — regression backstop, write-path round-trip covered by strengthened AC1/AC2
- Override justification: accepted findings address the core risk (mock-masked false green); rejected findings are either non-runtime concerns or redundant with strengthened AC

### Verdict: APPROVE
### Action Taken: Re-scoped from MCP-only to AgentView passthrough. Rewrote AC1/AC2 with observable output assertions. Escalated proof bundle from existing to behavioral. Added scope:kanban tag. Advanced #1520 → todo.
2026-05-13T08:36:14+00:00
## Test-Writer Notes
- Test file: tests/test_agentview_ac_params_1520.py
- Classes: TestFromAC_CreateTaskAcProofBundle, TestFromAC_EditTaskAcProofBundle, TestFromAC_ShowTaskAcProofBundleBackstop
- Tests per category: happy 7, edge 4, boundary 2
- Total: 13 tests, all FAIL (TypeError: unexpected keyword argument on AgentView.create_task/edit_task)
- ruff: clean

AC coverage:
| AC | Tests |
|----|-------|
| AC1 | test_create_task_ac_and_proof_bundle_in_returned_task, test_create_task_ac_param_only, test_create_task_proof_bundle_param_only, test_create_task_multiple_ac_items_all_preserved, test_create_task_empty_ac_list, test_create_task_ac_and_proof_bundle_persisted_on_disk |
| AC2 | test_edit_task_proof_bundle_sets_field, test_edit_task_add_ac_appends_item, test_edit_task_ac_replaces_full_list, test_edit_task_remove_ac_removes_item, test_edit_task_add_ac_and_proof_bundle_combined, test_edit_task_proof_bundle_overwrites_previous_value |
| AC3 | test_show_task_reflects_ac_and_proof_bundle_from_create |

Failure mode: All tests reach real AgentView calls (no MagicMock) — cycle 1 mock-masking root cause addressed.
2026-05-13T08:50:46+00:00
## Builder Notes
- Files changed:
  - serve/kanban/src/owlbear_kanban/agent_view.py
- Implementation:
  - Added `ac` and `proof_bundle` keyword params to `AgentView.create_task()` and forwarded both to `engine.create_task(...)`.
  - Added `ac`, `add_ac`, `remove_ac`, and `proof_bundle` keyword params to `AgentView.edit_task()` and forwarded them via kwargs to `engine.edit_task(...)`.
  - Extended AgentView no-op/change detection to treat AC/proof-bundle mutations as effective changes.
  - Updated method docstrings to include new parameters.
- RED verification (quality-runner):
  - tests/test_agentview_ac_params_1520.py: 0 passed, 13 failed (all `TypeError` unexpected keyword arg on `create_task`/`edit_task`), lint clean.
- GREEN verification (quality-runner, scoped):
  - tests/test_agentview_ac_params_1520.py + tests/test_agent_view_extraction.py + tests/test_agent_view_pick_tasks_1445.py
  - 38 passed, 0 failed, 0 skipped
  - Lint: clean
  - Coverage: `owlbear_kanban.agent_view` 44% (scoped run)
- Additional evidence:
  - Broader probe with serve/kanban/tests/test_engine_coverage.py surfaced 3 unrelated pre-existing failures outside this task scope; final gate uses scoped AC evidence above.
- Commit:
  - b7c3d2dfc56a029347edce6340c982b4d7cb2dc8
2026-05-13T09:06:33+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1520 -> docs | AC mapped to code and evidence sufficient.
- Blocking findings: none.
- AC1: `AgentView.create_task()` now accepts and forwards `ac` / `proof_bundle` through the bridge at `serve/kanban/src/owlbear_kanban/agent_view.py:520-601`; real AgentView tests verify returned values and persistence at `tests/test_agentview_ac_params_1520.py:82-89` and `tests/test_agentview_ac_params_1520.py:120-131`.
- AC2: `AgentView.edit_task()` now accepts and forwards `ac`, `add_ac`, `remove_ac`, and `proof_bundle` at `serve/kanban/src/owlbear_kanban/agent_view.py:613-872`; bridge change-detection also recognizes `add_ac` / `proof_bundle` mutations at `serve/kanban/src/owlbear_kanban/agent_view.py:828-832`. Real AgentView tests verify proof-bundle set, add-ac result membership, remove-ac behavior, and combined update path at `tests/test_agentview_ac_params_1520.py:150-182`. Adjacent durable proof still covers MCP -> AgentView forwarding at `tests/test_mcp_ac_params_1519.py:279-316`.
- AC3: `TaskFull` / `ShowTaskResponse` expose `ac` and `proof_bundle` at `serve/kanban/src/owlbear_kanban/models.py:628-674`; the regression backstop verifies `show_task` round-trip at `tests/test_agentview_ac_params_1520.py:201-211`.
- Builder evidence review: the quality-runner packet is internally consistent with the inspected bridge code and proof surface (`tests/test_agentview_ac_params_1520.py` + adjacent AgentView suites: 38 passed, 0 failed, lint clean, scoped coverage 44% for `owlbear_kanban.agent_view`). VS Code diagnostics are clean for `serve/kanban/src/owlbear_kanban/agent_view.py` and `tests/test_agentview_ac_params_1520.py`. Builder commit `b7c3d2dfc56a029347edce6340c982b4d7cb2dc8` is present in `.git/logs/HEAD`.

## Observations
- The written AC2 contract at `.owlbear/kanban/tasks/1520-p3-02-implement-mcp-server-ac-proof-bundle-tool-parameters.md:31` only requires the returned AC list to contain `"y"`. That is sufficient for this task's literal contract, but stricter append-preservation at the AgentView layer is only indirectly protected by engine-level append tests at `tests/test_engine_ac_1517.py:255-313`. If future work needs bridge-level append semantics to be regression-gated directly, encode that stronger expectation explicitly in the AC instead of relying on architecture-note intent.
2026-05-13T09:09:36+00:00
## Docs Gate

**Verdict: PASS — no documentation changes required**

### Changed files
- `serve/kanban/src/owlbear_kanban/agent_view.py` → convention maps to `serve/kanban/README.md`

### Item 1: README Verification
- `serve/kanban/README.md`: KanbanEngine method table uses `create_task(title, …)` / `edit_task(task_id, …)` with intentional ellipsis — no specific param list documented, no stale content. AgentView section documents only `pick_tasks`; `create_task`/`edit_task` are not separately documented at the AgentView layer. Layer 1 (grep): no removed symbols present. Layer 2 (editorial): no contradictions. PASS — no edits.
- `serve/mcp-kanban/README.md` (spot-check, prior task scope): already carries `ac`, `add_ac`, `remove_ac`, `proof_bundle` in both `create_task` and `edit_task` signatures from commit 016f548e. Consistent with this task's implementation.

### Item 2: External Attribution
N/A — no external attribution needed. Pure internal passthrough implementation.

### Item 3: Research Doc
N/A — no research doc exists for #1520 and none is referenced in the task body.

### Item 4: Deletion Detection
N/A — no files deleted. Single file modified (agent_view.py), additions only.

### Scratch cleanup
No `.owlbear/scratch/1520-*` files found.
2026-05-13T09:14:23+00:00
## Audit
### Regression Detection
- quality-runner mode full: 5082 passed, 20 failed, 25 skipped; ruff clean
- All 20 failures are pre-existing (model_fields_1515 pydantic validation ×3, memory_engine pydantic ×2, end_work_success archival ×2, edit_task_contract body-clear ×2, engine_lazy_agent_map ×1, engine_dispatch_validation ×1, cockpit_pds_build_compat timeout ×2, cockpit_react_compiler ×2, path_neutrality ×1, reviewer_rewrite ×1, python_version_floor ×2). None touch AgentView or any file changed by this task.
- Task tests (test_agentview_ac_params_1520.py, 13 tests) + adjacent AgentView suites: 38 passed, 0 failed
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (single file changed: serve/kanban/src/owlbear_kanban/agent_view.py — within scope:kanban domain)
- purpose match: PASS (adds ac/proof_bundle passthrough to AgentView.create_task and edit_task, matching stated AC)
- extraneous scope: none (builder commit b7c3d2df: +30 lines agent_view.py + 1 memory file)
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
Cycle 2 AC rewrite replaced mock-backed forwarding-only proof with observable output assertions — directly addressed cycle 1 false-green root cause. Minor gap: AC2 contains-check on add_ac rather than full append semantics (noted by reviewer as observation, not blocking). Overall strong for a passthrough task.

### Commit Integrity
- upstream commit presence: PASS (builder: b7c3d2df, test-writer: c3e803a1, both in git log)
- kanban commit packaging: pending (will commit after archival)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive