---
id: 1453
title: 'P4-16: Wire create_dr end to end for agents and guidance'
status: archived
priority: needed
created: 2026-05-08T19:32:28.041895+00:00
updated: 2026-05-11T11:37:27.307271+00:00
tags:
- phase-4
- scope:agents
- type:build
- create-dr
- guidance
- deployment-readiness
parent: 1437
depends_on:
- 1452
- 1447
- 1451
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: create_dr MCP exposure, guidance generation, and pipeline-agent instruction references.
Out of scope: resolve_drs internals, Cockpit decision UI, and deployment docs.

## Acceptance Criteria
1. create_dr is available in the kanban MCP tool registry with task_id, agent, request_type, and body inputs and returns a structured created/path response. (td:0)
2. Blocking guidance emitted by kanban mutation paths names create_dr and the h-decision-requests skill documents the task_id, agent, request_type, and body fields required from a pipeline agent. (td:0)
3. Pipeline agent guidance and skills that discuss decision or action requests instruct agents to call create_dr instead of writing files under decisions directories. (td:0)
4. create_dr guidance remains compatible with resolve_drs from #1447 by using the same pending and resolved directory contract. (td:0)
5. Builder verifies AC-1 through AC-4 using the probe artifacts from #1452 and does not use pytest or vitest as the functional proof. (td:0)

[[2026-05-11]]


## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: verify create_dr end-to-end wiring |
| Interface clarity | PASS | AC refined for AC-2 ambiguity (see below) |
| Dependency correctness | PASS | #1452 (probe), #1447 (resolve_drs), #1451 (MCP normalize) — all archived/done |
| Module layering | PASS | No new imports; create_dr in mcp-kanban calls decisions.py in kanban — correct direction |
| TDD compliance | PASS | Probe-based verification (AC-5); no pytest needed |
| KISS/YAGNI | PASS | Verification gate — no over-engineering |
| Premise challenge | CONDITIONAL PASS | All wiring already implemented by prior P4 tasks (#1182, #1447, #1451). Task remains valid as verification certification gate per Phase 4 pattern. |
| Pattern consistency | PASS | Follows P4 probe→build verification pattern |
| Security surface | PASS | No new system boundaries; create_dr validates request_type ∈ {decision, action} |
| Single domain | PASS | scope:agents — single domain |

### AC Refinements

**AC-2 clarification:** "includes the task_id, agent, request_type, and body fields" — interpreted as the guidance ecosystem (guidance message naming create_dr + h-decision-requests skill documenting required parameters), matching probe #1452 evidence. The guidance message itself does not enumerate individual parameter names; agents load h-decision-requests for the parameter contract.

### Test-Depth Annotations

All AC lines: td:0 — probe-based verification per AC-5, no pytest/vitest. Test-writer: SKIP.

### Notes

The full create_dr stack is already implemented:
- MCP tool: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L366–393
- Engine: `serve/kanban/src/owlbear_kanban/decisions.py` L89–150
- Guidance: `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` L13–16 (_DR_REQUIRED_MSG)
- Skills: r-pipeline-protocol L57, h-decision-requests full contract
- Agent tool lists: all 7 pipeline agents include ob-kanban/create_dr
- Tests: `serve/mcp-kanban/tests/test_mcp_create_dr.py`, `test_guidance.py`

Builder's job is verification-only: confirm probe #1452 findings hold by code inspection.
[[2026-05-11]]
Architecture review complete. All 5 AC lines verified against codebase — full create_dr wiring already implemented by prior P4 tasks. AC-2 refined to clarify "includes fields" means guidance ecosystem (message + skill docs), matching probe #1452 evidence. All AC td:0 (probe-based verification per AC-5). Test-writer: SKIP. Builder: verification-only via code inspection.
[[2026-05-11]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- AC-5 explicitly requires probe-based verification only; no pytest/vitest applicable.
- Passing through to builder.
[[2026-05-11]]
## Builder Notes
- Implementation: no file changes (verification-only task).
- Tests: not executed by design (AC-5 requires probe/code-inspection evidence, not pytest/vitest functional proof).
- Coverage: not applicable (no code changes, no test execution).
- ruff: not run (no code changes).

### AC Evidence (Probe-aligned)
- AC-1 (create_dr registry + inputs + structured response): verified in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py (`create_dr` tool with required args `task_id`, `agent`, `request_type`, `body`; returns `{created: True, path: ...}`) and reinforced by serve/mcp-kanban/tests/test_mcp_create_dr.py.
- AC-2 (blocking guidance names create_dr + skill documents required fields): verified `_DR_REQUIRED_MSG` in serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py and `## create_dr Contract` in share/skills/h-decision-requests/SKILL.md documenting `task_id`, `agent`, `request_type`, `body`.
- AC-3 (pipeline guidance/skills instruct create_dr instead of direct decisions-file writes): verified in share/skills/r-pipeline-protocol/SKILL.md and share/skills/h-decision-requests/SKILL.md (explicit "Never write .owlbear/decisions/ directly" and use `create_dr`).
- AC-4 (create_dr compatible with resolve_drs pending/resolved contract): verified in serve/kanban/src/owlbear_kanban/decisions.py (`create_dr` writes to `pending/`; `resolve_pending_drs` moves resolved outcomes to `resolved/`) and server wiring in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py.
- AC-5 (use probe artifacts, no pytest/vitest functional proof): satisfied via probe-aligned static verification and prior probe lineage referenced in task context (#1452); no functional test runners used for acceptance proof.

### Evidence Summary
- create_dr wiring is complete end-to-end (MCP tool -> kanban decisions helper -> guidance/skills contract).
- No regressions or code deltas introduced in this builder pass; task is a certification gate and is ready for reviewer confirmation.
[[2026-05-11]]
## Review Evidence
### Test Results
- quality-runner not applicable for this td:0 verification-only task. AC-5 requires probe/code-inspection proof rather than pytest/vitest functional proof.
- Existing probe artifacts were inspected directly: `serve/mcp-kanban/tests/test_mcp_create_dr.py:83`, `serve/mcp-kanban/tests/test_mcp_surface_contract.py:42`, `serve/mcp-kanban/tests/test_guidance.py:930`, `tests/test_mcp_resolve_drs_1447.py:212`, and `tests/test_mcp_resolve_drs_1447.py:716`.

### Lint Results
- Not run. No task-scoped code changes and no executable lint gate declared by the AC.

### Coverage
- Not applicable. td:0 verification-only task with no code deltas.

### Builder Process Quality
- CLEAN: one `## Builder Notes` section, no retry loop.
- No prior `## Review Evidence` sections in the task history.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| 1. create_dr is available in the kanban MCP tool registry with task_id, agent, request_type, and body inputs and returns a structured created/path response. | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:364` defines `@mcp.tool create_dr(ctx, task_id, agent, request_type, body)` with enum validation and returns `{"created": True, "path": relative_path}` at `server.py:387`. Probe artifacts in `serve/mcp-kanban/tests/test_mcp_create_dr.py:83` and `serve/mcp-kanban/tests/test_mcp_surface_contract.py:42` / `:218` pin both registration and live registry membership. | PASS |
| 2. Blocking guidance emitted by kanban mutation paths names create_dr and the h-decision-requests skill documents the required fields. | Engine emits `Create a Decision Request via the create_dr tool` in `serve/kanban/src/owlbear_kanban/agent_view.py:42` and reuses it on block outcome at `agent_view.py:1224`. MCP guidance emits the same message in `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py:13` and `guidance.py:81`. `share/skills/h-decision-requests/SKILL.md:30` documents `task_id`, `agent`, `request_type`, and `body`. `serve/mcp-kanban/tests/test_guidance.py:930` pins the guidance content. | PASS |
| 3. Pipeline agent guidance and skills that discuss decision or action requests instruct agents to call create_dr instead of writing files under decisions directories. | No `\bscribe\b` matches were found under active `share/**`. Active guidance instructs `create_dr` in `share/skills/r-pipeline-protocol/SKILL.md:57` and `:315`, `share/instructions/pipeline-agents.instructions.md:25`, `share/skills/w-arch-review/SKILL.md:45`, `share/skills/w-research/SKILL.md:110`, and `share/skills/h-decision-requests/SKILL.md:82`. `r-pipeline-protocol` and `h-decision-requests` explicitly say never write `.owlbear/decisions/` directly. | PASS |
| 4. create_dr guidance remains compatible with resolve_drs from #1447 by using the same pending and resolved directory contract. | `serve/kanban/src/owlbear_kanban/decisions.py:89` writes pending DR files under `decisions/pending/`; `decisions.py:145` moves resolved items to `decisions/resolved/`, appends canonical `## Decision Request` summary, and unblocks approved/rejected tasks. `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:390` returns relative moved paths from `resolve_drs`. `tests/test_mcp_resolve_drs_1447.py:212` and `:803` statically prove `decisions/resolved/...` output and no duplicate summary on repeat resolution. | PASS |
| 5. Builder verifies AC-1 through AC-4 using the probe artifacts from #1452 and does not use pytest or vitest as the functional proof. | Task record `1453-p4-16-wire-create-dr-end-to-end-for-agents-and-guidance.md:89` states no tests/coverage/ruff were run by design, and `:95` records probe-aligned static verification only. The cited probe artifacts exist in the repo and match the builder’s references. | PASS |

### Security / Quality Notes
- No in-scope security finding. `request_type` is validated to `decision|action`, create_dr writes only under the decisions directory contract, and resolver moves only to `resolved/` with canonical task summary behavior.
- Historical `.owlbear/briefs` and research artifacts still mention `scribe`, but the active `share/**` guidance surface does not. That is out of scope for this task and does not contradict AC-3.

### Deductions
- `-0.03`: no builder commit hash or diff was recorded in the task body, so commit-integrity / dirty-tree contamination could not be fully reconstructed from the available read-only tools.
- `-0.02`: td:0 review used direct artifact inspection instead of quality-runner because AC-5 makes executable functional proof inapplicable.

### Verdict
- PASS. Confidence: 0.95.

### Action
- Advance to `docs`.
[[2026-05-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Verification-only task; zero file changes made by builder |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | Research doc | No | N/A | No research phase; task was a certification gate |
| 5 | Diagram maintenance (describes match) | No | N/A | No changed files; no diagram describes-match possible |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| (none) | — | Changed-files set is empty; builder performed static code inspection only |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1453-* scratch files existed)
[[2026-05-11]]
## Audit\n### Regression Detection\n- quality-runner mode full: 4421 passed, 201 failed (pre-existing), 4 skipped, 5 errors; vitest 1386 passed, 1 failed (pre-existing)\n- Zero code changes from this task — all failures are pre-existing background debt\n- regression verdict: PASS\n\n### Intent Verification\n- scope alignment: PASS (verification-only certification gate; zero files changed; domain scope:agents correct)\n- purpose match: PASS (task purpose is end-to-end wiring verification of create_dr; builder performed static code inspection matching AC intent)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 4/5\nAC lines are specific and testable for a certification gate. AC-2 required refinement (architect documented clarification in architecture review). AC-5 correctly constrains verification method to probe artifacts. Minor gap: AC-2's original wording was ambiguous enough to require interpretation, preventing a 5.\n\n### Commit Integrity\n- upstream commit presence: PASS (no commits expected — zero code changes, all AC td:0, test-writer skipped)\n- kanban commit packaging: pending (this archival cycle)\n\n### Deduction Breakdown\nNo deductions applied:\n- No regressions (zero code changes)\n- No lint violations attributable to task\n- Reviewer evidence section present and detailed\n- AC quality 4/5 (above ≤3 threshold)\n- No intent mismatch\n- No evidence integrity concerns\n\n### Confidence: 1.00\n### Action: archive