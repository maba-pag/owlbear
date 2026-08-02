---
id: 1183
title: 'P1-04: Implement create_dr MCP tool + guidance text update'
status: archived
priority: medium
created: 2026-04-30T00:51:43.218458+00:00
updated: 2026-04-30T11:17:13.565967+00:00
tags:
- phase-1
- scope:mcp-kanban
- type:impl
parent: 1179
depends_on:
- 1181
- 1182
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `create_dr` tool registered in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` (td:0)
- Tool delegates to `decisions.create_dr()` from the kanban engine package (td:0)
- Tool response shape: `{created: true, path: str}` on success, error on failure (td:0)
- request_type validated to enum (decision|action) at MCP layer (td:0)
- Guidance text updated across ALL emission points to: `"⚠️ ACTION REQUIRED: Create a Decision Request via the create_dr tool. Blocks without a DR are invisible to the pipeline."` — affects `guidance.py` `_DR_REQUIRED_MSG`, `engine.py` `AgentView._BLOCK_AR_HINT`, test constants in `test_mcp_guidance_1089.py` and `test_engine_end_work_1080.py`, and prose in `share/skills/h-mcp-kanban/SKILL.md` L96 (td:1)
- All tests from #1182 pass (td:0)

## Scope

- IN: Guidance string constants + corresponding test assertions + skill doc prose
- OUT: decisions.py internals, pick_tasks, MCP tool implementation (already done)

Brief: see parent #1179

[[2026-04-30]]
## Research

**Key finding:** `create_dr` MCP tool is already fully implemented (7/7 #1182 tests pass). Only remaining AC item is guidance text update — 5-file string substitution from "via the scribe agent (see w-decision-routing)" to "via the create_dr tool".

**Impact:** `guidance.py` L14, `engine.py` L1866, 2 test files, 1 skill doc.

**Classification:** T1 — autonomous, trivial change.

**Doc:** `.owlbear/research/create-dr-mcp-guidance-1183.md`
[[2026-04-30]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: align guidance text with implemented tool |
| Interface clarity | PASS | Refined AC5 to specify exact new text, all 5 affected files, and dual emission paths |
| Dependency correctness | PASS | #1181, #1182 both archived/done |
| Module layering | PASS | No new imports or layering changes — string constants only |
| TDD compliance | PASS | Existing test suites cover guidance output; test-writer updates assertions to RED |
| KISS/YAGNI | PASS | Minimal text substitution |
| Premise challenge | PASS | Guidance must match implemented tool — necessary alignment |
| Pattern consistency | PASS | Standard constant-update pattern; runtime set-membership validation for request_type matches MCP tool conventions throughout server.py |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | All within mcp-kanban/kanban guidance subsystem |

### Challenge Results
- Challenger: reconsider (0.67)
- Challenges addressed:
  1. **AC4 enum claim:** Runtime `not in {"decision", "action"}` + ToolError IS enum validation at MCP layer. MCP params are strings by design; runtime rejection is the standard pattern (same as task_id validation at L443). AC4 DONE.
  2. **Dual emitter undercount:** Already documented in research Impact Matrix (5 files). Refined AC5 now explicitly names both `guidance.py` and `engine.py` paths + both test files.
  3. **AC scope vs research scope:** Valid. Refined AC5 to specify exact target text per Brief authority, covering all dropped fragments ("for this block", "(see w-decision-routing)").
- Architect response: Accepted concerns 2 and 3 → refined AC. Rebutted concern 1 with codebase evidence.

### Test Depth
- Max depth: 1
- Test-writer: PROCEED (AC5 is td:1 — update test assertions to new expected text)

### Verdict: APPROVE (via REFINE)
### Action Taken: Refined AC5 to specify exact new text, all 5 affected files (guidance.py, engine.py, 2 test files, 1 skill doc), and updated Scope section. Moved to todo.
[[2026-04-30]]
## Test-Writer Notes
- Test file: tests/test_guidance_text_1183.py
- Classes: TestFromAC_GuidanceTextUpdate
- Tests per category: happy 0, edge 0, error 0, boundary 0 (AC5 is td:1 — 4 smoke tests)
- Total: 4 tests, all FAIL ✓
- ruff: clean ✓

AC coverage:
| AC | Tests |
|----|-------|
| AC1-4 (td:0) | Skipped — depth-zero |
| AC5 (td:1) — guidance text at all emission points | test_dr_required_msg_guidance_py, test_block_ar_hint_engine_py, test_skill_doc_references_create_dr_tool, test_skill_doc_drops_scribe_agent_reference |

Also updated test constants in test_mcp_guidance_1089.py (_BLOCK_AR_HINT) and test_engine_end_work_1080.py (_EXPECTED_BLOCK_AR_HINT) to new canonical text → those suites now FAIL on the guidance assertions, giving the builder clear signal for both source and test file updates.
[[2026-04-30]]
## Builder Notes
- Implementation: updated DR guidance wording to canonical create_dr-tool text in `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py`, `serve/kanban/src/owlbear_kanban/engine.py`, and `share/skills/h-mcp-kanban/SKILL.md`.
- Tests: RED verified first (4 failing in `tests/test_guidance_text_1183.py`), then GREEN verification passed with 37 tests (`tests/test_guidance_text_1183.py`, `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`, `tests/test_engine_end_work_1080.py`).
- Coverage: scoped quality-runner report overall 46% for this run context (`owlbear_mcp_kanban.guidance` 23%, `owlbear_kanban.engine` 49%).
- ruff: clean.
- Approach: surgical string alignment only; no behavior changes beyond message text.

### Post-task Reflection
- Problem faced: guidance phrase drift across runtime constants and documentation prose.
- Workaround applied: used failing TestFromAC assertions to directly map and patch only required sites.
- Pattern discovered: DR-required phrasing should remain a single canonical sentence across engine/MCP/docs.
- Time sink: none notable.
- Quality gap: scoped coverage percentages for broad modules remain below 90% at module level, but task-targeted tests and lint are green.

- Commit: `bcebd3d8` — `fix: align DR guidance with create_dr tool (#1183, builder)`
[[2026-04-30]]
## Review Evidence
### Scope
- Reviewed builder scope reconstructed from task body and live file inspection: `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py`, `serve/kanban/src/owlbear_kanban/engine.py`, and `share/skills/h-mcp-kanban/SKILL.md`.
- No changed public signatures detected; `create_dr` contract in `server.py` remains the same adapter shape tested in #1182.

### Test Results
- Combined quality-runner scoped pass: **44 passed, 0 failed, 0 skipped** across `tests/test_guidance_text_1183.py`, `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`, `tests/test_engine_end_work_1080.py`, and `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py`.
- Isolated #1182 suite: **7 passed, 0 failed, 0 skipped**.
- Isolated guidance-update/regression suites: **37 passed, 0 failed, 0 skipped**.

### Lint
- `ruff`: **clean** on reviewed source and test files in both scoped quality-runner passes.

### Coverage
- Combined scoped run module coverage: `owlbear_mcp_kanban.guidance` **23%**, `owlbear_kanban.engine` **49%**, `owlbear_mcp_kanban.server` **60%**.
- These are whole-module percentages on large pre-existing modules. For this task, the changed lines are direct constant/doc updates and are exercised by exact assertions, so coverage is informational rather than gating.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `create_dr` tool registered in `server.py` | `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py::test_create_dr_tool_is_registered_via_mcp_decorator` | Yes — missing decorator registration or wrong backing callable fails the identity/assertion checks | COVERED |
| Tool delegates to `decisions.create_dr()` | `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py::test_create_dr_success_returns_created_true_and_relative_path` | Yes — test requires patched `decisions.create_dr` to be called and checks forwarded business args | COVERED |
| Response shape `{created: true, path: str}` on success | `...::test_create_dr_success_returns_created_true_and_relative_path` and `...::test_create_dr_collision_path_passthrough` | Yes — tests assert `created is True`, relative path shape, and collision suffix passthrough exactly | COVERED |
| `request_type` validated to enum at MCP layer | `...::test_create_dr_accepts_action_request_type` and `...::test_create_dr_rejects_invalid_request_type` | Yes — invalid value must raise `ToolError` and must not call `decisions.create_dr` | COVERED |
| Guidance text updated across all listed emission points | `tests/test_guidance_text_1183.py` four-test class + regression assertions in `test_mcp_guidance_1089.py` and `test_engine_end_work_1080.py` | Yes — runtime constants are checked by exact equality; skill doc check requires `create_dr tool` and rejects stale `scribe agent` wording | COVERED |
| All tests from #1182 pass | Isolated quality-runner run of `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py` | Yes — any regression in the suite would fail the isolated run | COVERED |

#### Security Review
- No issues found.
- Reviewed code does not add dependencies, secrets, shelling, path joins from user input, or new persistence flows.
- `request_type` validation remains in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:437-439`; delegation remains limited to `decisions.create_dr` in `server.py:456-462`.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `tests/test_guidance_text_1183.py::test_dr_required_msg_guidance_py` | No weakening observed; still exact equality against canonical string | PRESERVED |
| `tests/test_guidance_text_1183.py::test_block_ar_hint_engine_py` | No weakening observed; still exact equality against canonical string | PRESERVED |
| `tests/test_guidance_text_1183.py::test_skill_doc_*` | No weakening observed; positive `create_dr tool` proof plus negative stale-phrase proof preserved | PRESERVED |
| Existing exact-guidance regressions in `test_mcp_guidance_1089.py` / `test_engine_end_work_1080.py` | Exact-list equality assertions still present | PRESERVED |

#### Test Quality
- Assertion specificity: **STRONG** — exact equality in `tests/test_guidance_text_1183.py`, `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`, and `tests/test_engine_end_work_1080.py`; #1182 tests assert concrete dict/path/error behavior.
- Negative/error-path coverage: **ADEQUATE** — #1182 covers invalid `request_type` and not-found error mapping; AC5 is a text-alignment task with no additional runtime branch.
- Manual mutation reasoning: **STRONG** — reverting either runtime constant, stale skill wording, relative-path return, or enum rejection would fail current assertions.
- Test independence: **STRONG** — isolated fixtures/mocks, no shared mutable state dependence.
- Naming: **STRONG** — test names are descriptive and AC-traceable.

#### Data Safety
- No issues found. This task changes guidance/doc text only; no new atomicity, race, or persistence behavior introduced.

#### Implementation-Aware Test Gap Analysis
- No AC-scoped gaps found.
- The changed runtime lines are directly exercised by imports/exact comparisons in `tests/test_guidance_text_1183.py` and exact guidance equality checks in the existing regression suites.

#### Necessity Check
- Not applicable. Task aligns existing guidance with an already-implemented tool; no new dependency or capability added.

#### Builder Process Quality
- **CLEAN** — single builder pass, no prior `## Review Evidence` section, no retry-loop pattern.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `create_dr` tool registered in `server.py` | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:427-428` defines decorated tool; isolated #1182 suite passed 7/7 | `test_create_dr_tool_is_registered_via_mcp_decorator` | PASS |
| Delegates to `decisions.create_dr()` | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:456-462` calls `decisions.create_dr` | `test_create_dr_success_returns_created_true_and_relative_path` | PASS |
| Success response shape `{created: true, path: str}` | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:467-468` returns exact dict shape | `test_create_dr_success_returns_created_true_and_relative_path`, `test_create_dr_collision_path_passthrough` | PASS |
| `request_type` validated to enum (`decision|action`) | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:437-439` rejects invalid values before delegation | `test_create_dr_accepts_action_request_type`, `test_create_dr_rejects_invalid_request_type` | PASS |
| Guidance text updated across all emission points | `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py:13-16`, `serve/kanban/src/owlbear_kanban/engine.py:1866-1869`, `share/skills/h-mcp-kanban/SKILL.md:96`; regression exact-equality assertions remain in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:397` and `tests/test_engine_end_work_1080.py:565` | `tests/test_guidance_text_1183.py` four tests | PASS |
| All tests from #1182 pass | Independent quality-runner run on `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py`: 7 passed, 0 failed | whole #1182 suite | PASS |

### Deductions
- `-0.02` changed-file scope reconstructed from builder note plus live file inspection rather than direct git diff in this environment.
- `-0.01` coverage tooling reports only whole-module percentages on large modules; diff-scoped exercised lines were verified manually.

### Verdict
- **PASS**
- **Confidence:** 0.97
- **Action:** advance to `docs`

### Post-task Reflection
- The only non-trivial review judgment was separating low whole-module coverage from diff-scoped proof on constant-only edits.
- Existing exact-guidance regression suites materially strengthen confidence for this text-alignment task; this is not resting on the 4 task-owned smoke tests alone.
- Guidance drift is now defended at three layers: direct constant checks, MCP adapter regression, and engine regression.
[[2026-04-30]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | `serve/mcp-kanban/README.md` documents `create_dr` tool (accurate, generic guidance field description unchanged). `serve/kanban/README.md` documents `create_dr` engine function (accurate). No README references the specific `_DR_REQUIRED_MSG` / `_BLOCK_AR_HINT` string text. |
| 2 | Module docstrings | Yes | N/A | `guidance.py` module docstring ("Contextual guidance messages for kanban MCP operations.") and `collect_guidance` docstring are accurate. `_DR_REQUIRED_MSG` and `_BLOCK_AR_HINT` are private constants with no docstring requirements. `engine.py` `AgentView._BLOCK_AR_HINT` is a private class attribute; no docstring needed. |
| 3 | External attribution | No | N/A | Task is internal string alignment only; no external patterns sourced. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/create-dr-mcp-guidance-1183.md` exists and is referenced in task body. |
| 5 | Diagram maintenance (describes match) | Yes | Verified | `share/diagrams/kanban.excalidraw` (describes: `serve/kanban/src/**`, `serve/mcp-kanban/src/**`) and `share/diagrams/mcp-topology.excalidraw` (describes: `serve/mcp-*/src/**`, `serve/kanban/src/**`) both matched. Footers already show `Last verified: 2026-04-30 (e2ac09ad)` — confirmed on disk via direct grep; no commit needed. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` | IN (docstrings) | Checked — accurate |
| `serve/kanban/src/owlbear_kanban/engine.py` | IN (docstrings) | Checked — accurate |
| `share/skills/h-mcp-kanban/SKILL.md` | OUT (agent-executable) | No action |
| `tests/test_guidance_text_1183.py` | OUT (test) | N/A |
| `serve/mcp-kanban/tests/test_mcp_guidance_1089.py` | OUT (test) | N/A |
| `tests/test_engine_end_work_1080.py` | OUT (test) | N/A |
| `serve/mcp-kanban/tests/test_mcp_create_dr_1182.py` | OUT (test) | N/A |
| `share/diagrams/kanban.excalidraw` | IN (diagram) | Footer already current (e2ac09ad) |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram) | Footer already current (e2ac09ad) |

### Files Updated
- None (diagram footers already carried current commit hash)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found (no `.owlbear/scratch/1183-*` files)
[[2026-04-30]]
## Audit\n\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| create_dr tool registered in server.py | #1182 suite 7/7 green; reviewer line ref server.py:427-428 | PASS |\n| Tool delegates to decisions.create_dr() | #1182 suite mock-patched delegation test passes | PASS |\n| Response shape {created: true, path: str} | #1182 assertion on dict shape passes | PASS |\n| request_type validated to enum at MCP layer | #1182 test_create_dr_rejects_invalid_request_type passes | PASS |\n| Guidance text updated across all emission points | Grep confirmed create_dr tool in guidance.py:13, engine.py:1868, SKILL.md:96; 4/4 task tests pass | PASS |\n| All tests from #1182 pass | Isolated run: 7 passed, 0 failed | PASS |\n\n### Test Results\n- pytest (full): 3328 passed, 69 failed, 4 skipped (all failures in unrelated areas: BoardConfig schema, migration, React compiler)\n- pytest (task-scoped): 44 passed, 0 failed\n- ruff: clean\n\n### Architect Quality: 4/5\nAC lines are specific with exact target text, file enumeration, and test-depth markers. Minor: AC5 required a REFINE pass to reach final specificity, but the refined version is clear and complete.\n\n### Deduction Breakdown\n- AC lines without evidence: 0 (all 6 mapped)\n- Lint violations: 0\n- AC quality score: 4 (no deduction, threshold is 3 or below)\n- Missing reviewer evidence: 0 (detailed PASS section present)\n- Full-suite failures in task scope: 0 (69 failures all unrelated)\n\n### Confidence: 1.00\n### Action: archive