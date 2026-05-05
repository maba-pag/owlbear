---
id: 1347
title: Prove dev-code MCP runtime before main sync
status: review
priority: critical
created: 2026-05-04T18:02:22.883451+00:00
updated: 2026-05-05T21:29:12.348258+00:00
tags:
- sync-blocker
- mcp-kanban
- ci
- dev-experience
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

The dev workspace MCP config launches OwlBear MCP servers with `uv --project ../owlbear`, which points at the sibling consumer checkout rather than the `owlbear-dev` source tree. That is correct for dogfooding consumer behavior, but it is not a valid proof that current dev MCP code is ready to sync. The sibling consumer checkout is also dirty and stale relative to dev, so MCP tool success in the dev editor can be a false green.

Audit decision: add a sync-readiness smoke/proof path that launches and validates MCP from current dev source before main sync.

## Acceptance Criteria

1. Create `serve/mcp-kanban/tests/test_mcp_surface_contract.py` that starts the MCP server through `app_lifespan` against an isolated temporary board fixture (same pattern as `test_mcp_kanban_dir_1349.py`) and introspects the running server's tool registry. (td:2)
2. Assert `owlbear_mcp_kanban.__file__` resolves under the repo working tree. Use the test file's own `__file__` parent chain as the reference root (not a hardcoded path). (td:1)
3. Assert the live tool registry (post-lifespan, post-`_patch_params`) contains exactly these 9 tools: `list_tasks`, `show_task`, `create_task`, `create_dr`, `move_task`, `edit_task`, `start_work`, `end_work`, `pick_tasks`. Update this set when tools are intentionally added/removed. (td:1)
4. Assert `end_work` tool's published parameter schema (post-`_patch_params` mutation, NOT the function signature) includes all 5 `outcome` values: `success`, `fail`, `reject`, `block`, `release`. (td:1)
5. The test imports the module directly and runs lifespan against a temp fixture; no `.vscode/mcp.json` parsing, no VS Code runtime dependency. (td:0)
6. Add a step in `.github/workflows/sync-to-main.yml` (after "Validate selected paths exist on dev", before "Prepare consumer branch", guarded by `if: ${{ inputs.sync_serve }}`) that installs `uv` via `astral-sh/setup-uv` and runs this test from the dev checkout. Failure blocks the sync. (td:0)
7. The test file docstring documents: (a) why editor-runtime MCP success via `../owlbear` does not prove dev-source readiness, (b) that seed-placeholder MCP config in consumer checkouts is a separate concern from dev-code validation, (c) that updating the tool-set constant is required when the deployment contract changes. (td:0)

## Key Files

- `.vscode/mcp.json` — dev editor MCP config (uses `../owlbear`)
- `seed/.vscode/mcp.json` — consumer seed MCP config (placeholder)
- `.github/workflows/sync-to-main.yml` — CI integration point for the gate step
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — MCP server with tool registry + `_patch_params` mutations
- `serve/mcp-kanban/tests/test_mcp_kanban_dir_1349.py` — reference pattern for temp board fixture + lifespan testing

## Architecture Notes

- The test MUST run `app_lifespan` (not just import the module) because `_apply_tool_exclusions` runs at lifespan and `_patch_params` mutates tool schemas at module scope. Registry introspection via `mcp._tool_manager._tools` is an established pattern (used in `test_tool_annotations_494.py`, `test_mcp_create_dr_1182.py`, `test_mcp_server_1090.py`).
- The CI step MUST be guarded by `sync_serve` — during share/setup/infra-only syncs, the serve code is unchanged and the test would validate a stale consumer overlay rather than current dev source.
- The CI step runs on the dev checkout BEFORE the consumer-branch switch (step "Prepare consumer branch") to prove the code that will be synced, not the consumer-branch state.
- Existing tests already cover individual tool behavior but NOT the aggregate deployment contract as a single assertion. This task adds the contract-snapshot gate.

## Source

Deployment audit finding group 5, 2026-05-04.

[[2026-05-05]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: MCP surface contract validation + CI gate |
| Interface clarity | PASS | AC refined — lifespan launch, published schema inspection, CI guard condition all specified |
| Dependency correctness | PASS | Removed stale deps (1340, 1352 — not in task store). Task is self-contained |
| Module layering | PASS | Test in serve/mcp-kanban/tests/ testing its own package; CI step in sync workflow |
| TDD compliance | PASS | td:2 and td:1 lines present; test-writer processes normally |
| KISS/YAGNI | PASS | Minimal: one test file + one CI step. No new abstractions |
| Premise challenge | PASS | Real gap confirmed — existing tests cover individual tools but no aggregate contract snapshot or source-origin proof exists |
| Pattern consistency | PASS | Follows established patterns: temp board fixture, `mcp._tool_manager._tools` introspection, lifespan testing from test_mcp_kanban_dir_1349.py |
| Security surface | N/A | Read-only introspection test |
| Single domain | PASS | mcp-kanban package + its CI gate |

### Challenger Results
- Confidence: 0.44 → recommended block
- Critical issues raised: (1) initial AC dropped launch requirement, (2) CI step must be conditional on sync_serve
- Resolution: AC rewritten to require `app_lifespan` launch (not import-only), CI step guarded by `inputs.sync_serve`, step placement before consumer-branch switch. Both critical issues addressed in refined AC.
- Override justification: Challenger concerns were valid for the INITIAL refinement but are resolved in the final AC. The "block" recommendation targeted deficiencies now corrected.

### Key Refinements Applied
- AC now requires `app_lifespan` launch (not just import-time introspection)
- AC4 specifies post-`_patch_params` published schema (not function signature)
- CI step guarded by `sync_serve` and placed before consumer-branch switch
- Documentation AC covers both `../owlbear` and seed-placeholder configs
- Stale dependencies removed (1340, 1352 not in task store)
[[2026-05-05]]
## Test-Writer Notes
- Test file: `serve/mcp-kanban/tests/test_mcp_surface_contract.py`
- Classes: `TestFromAC_LifespanStartup`, `TestFromAC_ModuleSourceOrigin`, `TestFromAC_ToolRegistryContract`, `TestFromAC_EndWorkOutcomeSchema`
- Tests per category: happy 5, edge 0, error 0, boundary 0
- Total: 5 tests
- ruff: clean

**RED-phase note:** All 5 tests PASS against current implementation. This is a contract-snapshot task, not a classic TDD-RED task. AC1–AC4 verify invariants that the MCP server already satisfies:
- AC1: `app_lifespan` already starts correctly against temp boards
- AC2: Module already resolves under dev repo tree
- AC3: Server already registers exactly 9 tools
- AC4: `end_work` `outcome` schema already exposes all 5 Literal values as `enum`

The builder's sole remaining deliverable is **AC6 (td:0)**: add the guarded CI step to `.github/workflows/sync-to-main.yml`. No source changes to `owlbear_mcp_kanban` are required.

**AC coverage:**
| AC | Status |
|----|--------|
| AC1 (td:2) | 2 tests: lifespan yields AppContext; AppContext.engine + kanban_dir |
| AC2 (td:1) | 1 test: module __file__ under repo root via __file__ parent chain |
| AC3 (td:1) | 1 test: tool registry == EXPECTED_TOOLS after lifespan |
| AC4 (td:1) | 1 test: end_work outcome schema ⊇ EXPECTED_OUTCOMES |
| AC5 (td:0) | pass-through — no VS Code runtime deps (verified by construction) |
| AC6 (td:0) | pass-through — CI step for builder |
| AC7 (td:0) | pass-through — docstring included in test file |
[[2026-05-05]]
## Builder Notes
- Implementation: added guarded dev-source MCP gate steps in .github/workflows/sync-to-main.yml immediately after "Validate selected paths exist on dev" and before "Prepare consumer branch".
- Files changed: .github/workflows/sync-to-main.yml
- CI gate behavior: when inputs.sync_serve is true, workflow now installs uv via astral-sh/setup-uv and runs `uv run pytest serve/mcp-kanban/tests/test_mcp_surface_contract.py -q --tb=short`; failures block sync.
- Tests: 5 passed, 0 failed (scoped quality-runner on serve/mcp-kanban/tests/test_mcp_surface_contract.py)
- Coverage: 23% overall for scoped run; module owlbear_mcp_kanban.server at 30% (informational for contract snapshot test, no server-source edits in this task)
- ruff: clean (0 violations)
- Evidence summary: AC6 implemented with required placement and guard; AC1-AC5 and AC7 already satisfied by existing test-writer deliverable.
- Commit: 30298a83 with message `ci: gate sync on dev MCP surface contract test (#1347, builder)`

### Post-task Reflection
- Existing task-scoped RED tests were already green because this task is a contract-snapshot/gating change, so builder work remained surgical to workflow-only.
- Keeping the gate before branch switch ensures the validated artifact is dev source, not consumer overlay state.
- quality-runner provided consistent evidence quickly; no environment fallback needed.
[[2026-05-05]]
## Review Evidence
### Test Results
- quality-runner scoped run: 5 passed, 0 failed, 0 skipped on `serve/mcp-kanban/tests/test_mcp_surface_contract.py`.
- The task suite is green against the current tree.

### Lint Results
- quality-runner: ruff clean for `serve/mcp-kanban/tests/test_mcp_surface_contract.py`.
- quality-runner could not lint `.github/workflows/sync-to-main.yml` because only Python/ruff linting was available in that environment.
- VS Code diagnostics report no errors in `serve/mcp-kanban/tests/test_mcp_surface_contract.py` or `.github/workflows/sync-to-main.yml`.

### Coverage
- quality-runner: `owlbear_mcp_kanban.server` 30% module coverage, 23% overall for the scoped run.
- Informational only here: the builder change is workflow-only (`.github/workflows/sync-to-main.yml`), so low module-level coverage is not a gate for this review.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | `serve/mcp-kanban/tests/test_mcp_surface_contract.py:148`, `:164`, `:158`, `:176`; `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:146`; quality-runner 5/5 green | `test_lifespan_yields_app_context_with_temp_board`, `test_app_context_exposes_engine_and_resolved_kanban_dir` | PASS |
| AC2 | `serve/mcp-kanban/tests/test_mcp_surface_contract.py:124`, `:127`, `:194`, `:203`; quality-runner green | `test_module_file_resolves_under_repo_working_tree` | PASS |
| AC3 | `serve/mcp-kanban/tests/test_mcp_surface_contract.py:42`, `:220`, `:244`; quality-runner green | `test_live_registry_contains_exactly_nine_tools` | PASS |
| AC4 | `serve/mcp-kanban/tests/test_mcp_surface_contract.py:56`, `:261`, `:270`, `:277`, `:292`; quality-runner green | `test_end_work_published_outcome_schema_includes_all_five_values` | PASS |
| AC5 | direct module imports at `serve/mcp-kanban/tests/test_mcp_surface_contract.py:34-35`; no `.vscode/mcp.json` parsing in the test body | construction + green suite | PASS |
| AC6 | `.github/workflows/sync-to-main.yml:84`, `:126`, `:127`, `:130`, `:131`, `:138` place the gate after path validation, before consumer-branch prep, and guard it with `inputs.sync_serve` | manual workflow inspection | FAIL |
| AC7 | docstring content at `serve/mcp-kanban/tests/test_mcp_surface_contract.py:3-4`, `:10`, `:15` covers `../owlbear`, seed placeholder config, and tool-set constant maintenance | file inspection | PASS |

### Findings
- FAIL trigger: `.github/workflows/sync-to-main.yml:127` adds `astral-sh/setup-uv@v6`, a mutable third-party action reference, inside a workflow with `contents: write` permission at `.github/workflows/sync-to-main.yml:36-37`.
- The same workflow already pins other third-party actions to immutable SHAs at `.github/workflows/sync-to-main.yml:71` and `.github/workflows/sync-to-main.yml:212`. Introducing an unpinned action in the sync/release path is an avoidable supply-chain regression.
- AC6 is only partially satisfied: placement, guard, and command are correct, but the implementation weakens the workflow's security posture.

### Deductions
- Confidence deduction: no commit diff was available in-tool, so TestFromAC immutability was assessed from builder notes plus task scope rather than a direct commit diff. Builder commit `30298a83` is present in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`, which supports the claimed workflow-only change surface.
- Not counted against the task: code-reader's concern about `_server_mock()` was rejected because the AC explicitly points to the `test_mcp_kanban_dir_1349.py` pattern, which uses the same lifespan-helper shape. The AC4 superset assertion (`includes all 5 outcome values`) also matches the task wording and is not a proof defect.

### Verdict
- FAIL -> in-progress
- Confidence: 0.88
- Action: builder retry to pin the new `setup-uv` action to an immutable commit SHA and keep the existing gate placement/guard unchanged.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Replace mutable `astral-sh/setup-uv@v6` with an immutable commit SHA pin in the new dev-source gate step | `.github/workflows/sync-to-main.yml` | Security review: mutable action ref at `:127` in a write-enabled workflow (`:36-37`); existing third-party actions are SHA-pinned at `:71` and `:212` |

[[2026-05-05]]
## Builder Notes
- Applied reviewer-requested security fix: pinned the dev-source gate action ref in `.github/workflows/sync-to-main.yml` from mutable `astral-sh/setup-uv@v6` to immutable `astral-sh/setup-uv@d0d8abe699bfb85fec6de9f7adb5ae17292296ff` (`# v6`).
- Scope of change: workflow-only, single-line edit; gate placement/guard/command unchanged.

- Files changed:
  - `.github/workflows/sync-to-main.yml`

- Test results (quality-runner scoped):
  - `serve/mcp-kanban/tests/test_mcp_surface_contract.py`: 5 passed, 0 failed, 0 skipped
  - Coverage: overall 23%; `owlbear_mcp_kanban.server` 30% (informational for scoped contract test)

- Lint status:
  - `ruff` clean on `serve/mcp-kanban/tests/test_mcp_surface_contract.py` (0 violations)

- Evidence summary:
  - AC6 remains correctly implemented (step stays after selected-path validation, before consumer-branch prep, and guarded by `inputs.sync_serve`), and now no longer uses a mutable third-party action reference in a write-permission workflow.