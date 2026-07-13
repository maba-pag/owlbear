---
id: 1187
title: 'P2-02: Create h-decision-requests skill + delete scribe and w-decision-routing'
status: archived
priority: medium
created: 2026-04-30T00:52:00.447027+00:00
updated: 2026-04-30T05:17:14.679275+00:00
tags:
- phase-2
- scope:agents
- type:impl
- agent
parent: 1179
depends_on:
- 1186
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `share/skills/h-decision-requests/SKILL.md` created (~50 lines) documenting: when to create DR, how (create_dr tool params), body format, fire-and-forget semantics (td:0)
- `share/agents/scribe.agent.md` deleted (td:0)
- `share/skills/w-decision-routing/SKILL.md` deleted (td:0)
- New skill has valid frontmatter (name: h-decision-requests, description, user-invocable: false) (td:0)
- All tests from #1186 pass (deletion and existence checks) (td:0)

## Scope

- IN: new skill creation + two file deletions
- OUT: reference updates in other files (handled by #1188)

Brief: see parent #1179

[[2026-04-30]]
## Research
- Research doc: none (trivial — file expansion per existing brief spec)
- Sources: 2 studied (brief `draft-dr-script-replacement/brief.md`, `serve/kanban/src/owlbear_kanban/decisions.py`), 2 high-relevance
- Recommendation: expand current 18-line SKILL.md to ~50 lines per brief Phase 2 spec (confidence: 0.95)
- Follow-up tasks created: none (this task IS the implementation)
- Decision requests: none

## Findings
- All #1186 tests already pass (9/9 green)
- `scribe.agent.md` and `w-decision-routing/SKILL.md` already deleted
- Current `h-decision-requests/SKILL.md` exists with valid frontmatter but only 18 lines — AC requires ~50 lines documenting: when to create DR, create_dr params (task_id, agent, request_type in {decision|action}, body), body format (context + options + question), fire-and-forget semantics (auto-block, no follow-up, resolved on next pick_tasks)
- Implementation source: brief Phase 2 spec + decisions.py create_dr signature

## Challenge Results
- Challenger: SKIPPED — trivial markdown expansion with clear spec, no design decisions

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One deliverable: expand skill content |
| Interface clarity | PASS | Brief specifies exactly what to document (when, params, format, semantics) |
| Dependency correctness | PASS | #1186 archived (done) |
| Module layering | PASS | N/A — markdown skill file only |
| TDD compliance | PASS | #1186 suite covers structural assertions |
| KISS/YAGNI | PASS | Minimal scope, brief-specified content |
| Premise challenge | PASS | Brief Phase 2 requires this step |
| Pattern consistency | PASS | Follows existing h-* skill handbook pattern |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | scope:agents (agent skill docs) |

### Challenge Results
- Challenger: SKIPPED — all td:0, no design decisions

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Added `agent` pass-through tag, annotated all AC lines td:0. Advancing to todo.
[[2026-04-30]]
Architecture review complete. All AC lines td:0 (structural tests exist in #1186 suite, content expansion is documentation). Added `agent` pass-through tag. Test-writer: SKIP.
[[2026-04-30]]
## Test-Writer Notes

**Pass-through** — non-implementation task, no tests written.

**Evidence:**
- All 5 AC lines marked `td:0` by architect
- Architecture review explicitly states "Test-writer: SKIP"
- Task tagged `agent` (pass-through signal)
- Deliverable is a markdown skill file expansion + file deletions — no testable Python interfaces
- Structural tests for this task's deliverables already exist in the #1186 suite (9/9 green per architect research findings)

**AC Coverage:** N/A — pass-through
[[2026-04-30]]
## Builder Notes
- Implementation: expanded [share/skills/h-decision-requests/SKILL.md](share/skills/h-decision-requests/SKILL.md) from minimal placeholder content to full handbook coverage for DR creation criteria, `create_dr` parameters, body format, and fire-and-forget lifecycle semantics.
- Files changed: [share/skills/h-decision-requests/SKILL.md](share/skills/h-decision-requests/SKILL.md)
- AC verification: confirmed [share/agents/scribe.agent.md](share/agents/scribe.agent.md) absent and [share/skills/w-decision-routing/SKILL.md](share/skills/w-decision-routing/SKILL.md) absent; updated skill now 83 lines and retains valid frontmatter (`name`, `description`, `user-invocable: false`).
- Tests: quality-runner scoped run on [tests/test_dr_skill_replacement_1186.py](tests/test_dr_skill_replacement_1186.py): 9 passed, 0 failed, 0 skipped.
- Coverage: N/A for this scoped structural test run (no module coverage data collected).
- Lint: clean (ruff exit code 0; no violations).
- Commit: `33da94c5` (`docs: expand decision request handbook (#1187, builder)`).

- Reflection: AC and predecessor notes indicated td:0/pass-through, but a direct file read exposed a residual content gap; verifying actual file state before pass-through prevented a false completion.
- Reflection: Keeping the change to one markdown file preserved surgical scope while satisfying all remaining acceptance criteria.
- Reflection: Running quality-runner despite td:0 maintained consistent green evidence and avoided protocol drift.
[[2026-04-30]]
## Review Evidence
### Test Results
- pytest: 9 passed, 0 failed, 0 skipped on tests/test_dr_skill_replacement_1186.py via quality-runner

### Lint
- ruff: clean on tests/test_dr_skill_replacement_1186.py via quality-runner

### Coverage
- N/A for this review. The scoped structural suite does not exercise instrumented source packages.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- Inherited structural suite exists and remained unmodified by the builder. Relevant checks still present in tests/test_dr_skill_replacement_1186.py: test_h_decision_requests_skill_exists, test_h_decision_requests_skill_has_valid_frontmatter, test_scribe_agent_does_not_exist, test_w_decision_routing_skill_does_not_exist, and the cross-reference assertions.
- No builder edits to TestFromAC_DRSkillReplacement were detected.

#### Security Review
- No security findings in this docs-only change.

#### Test Integrity
- PRESERVED. Builder changed the handbook file only; the inherited #1186 structural test file was not modified.

#### Test Quality
- Scoped suite is structurally adequate for the explicit deletion/existence regressions it covers, but it does not validate the handbook's live helper contract. This is noted as review context, not the primary gate reason.

#### Data Safety
- No issues found.

#### Implementation-Aware Test Gap Analysis
- No additional blocking gap beyond the implementation defect below.

#### Necessity Check
- N/A. No new dependency, integration, or external capability added in this task.

#### Builder Process Quality
- CLEAN. Single builder cycle; no retry loop evidence.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `share/skills/h-decision-requests/SKILL.md` created (~50 lines) documenting when/how/body/fire-and-forget | Handbook exists and includes the requested sections: create_dr contract, body format, and fire-and-forget lifecycle in share/skills/h-decision-requests/SKILL.md at lines 29, 31, 38, 71. However the same file also states unsupported helper behavior: `create_dr(...)` can "create or query" at line 11 and `resolve_decision(...)` exists at lines 12 and 76. The live MCP tool surface exposes only create_dr(task_id, agent, request_type, body) in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py at lines 429-434, and the engine resolver is resolve_pending_drs in serve/kanban/src/owlbear_kanban/decisions.py at line 136. The brief for this task requires create_dr parameters and next-pick_tasks resolution, not a `resolve_decision(...)` helper (.owlbear/briefs/draft-dr-script-replacement/brief.md at lines 141-144). | tests/test_dr_skill_replacement_1186.py::test_h_decision_requests_skill_exists | FAIL |
| `share/agents/scribe.agent.md` deleted | Path absent in workspace; file search returned no result. | tests/test_dr_skill_replacement_1186.py::test_scribe_agent_does_not_exist | PASS |
| `share/skills/w-decision-routing/SKILL.md` deleted | Path absent in workspace; file search returned no result. | tests/test_dr_skill_replacement_1186.py::test_w_decision_routing_skill_does_not_exist | PASS |
| New skill has valid frontmatter | Frontmatter fields present in share/skills/h-decision-requests/SKILL.md at lines 2-4. | tests/test_dr_skill_replacement_1186.py::test_h_decision_requests_skill_has_valid_frontmatter | PASS |
| All tests from #1186 pass | quality-runner report: 9 passed, 0 failed, 0 skipped. Relevant suite entry points remain in tests/test_dr_skill_replacement_1186.py at lines 44, 52, 72, 81, 113, 121, 132, 141. | tests/test_dr_skill_replacement_1186.py | PASS |

### Deductions
- -0.16 handbook content diverges from the live decision-helper contract by documenting query behavior for create_dr and a `resolve_decision(...)` helper that is not exposed by the live MCP tool surface.

### Verdict
- FAIL. Confidence: 0.82

### Action
- Routed to in-progress for builder correction.
- Required follow-up:
  1. Remove or correct the unsupported `create or query` claim unless and until the live create_dr tool actually supports query/check modes.
  2. Replace `resolve_decision(...)` references with wording grounded in the implemented flow: create_dr is fire-and-forget, and resolution is picked up on the next pick_tasks cycle via the engine's pending-DR resolver.
  3. Re-run the inherited #1186 structural suite after the handbook wording is corrected.

### Review Notes
- This is a docs-only task, so the green structural suite was necessary but not sufficient. The live handbook content had to be checked directly against the current brief and the live create_dr/resolve_pending_drs implementation.
[[2026-04-30]]
## Builder Notes
- Implementation: corrected handbook contract wording in [share/skills/h-decision-requests/SKILL.md](share/skills/h-decision-requests/SKILL.md) to remove unsupported API claims.
- Files changed: [share/skills/h-decision-requests/SKILL.md](share/skills/h-decision-requests/SKILL.md)
- Fixes applied: replaced "create or query" phrasing with create-only behavior for `create_dr(...)`; removed `resolve_decision(...)` helper references; documented resolution as engine handling on next `pick_tasks` cycle.
- Tests: quality-runner scoped run on [tests/test_dr_skill_replacement_1186.py](tests/test_dr_skill_replacement_1186.py): 9 passed, 0 failed, 0 skipped.
- Coverage: N/A (scoped structural/doc checks; no instrumented module output).
- Lint: ruff clean on [tests/test_dr_skill_replacement_1186.py](tests/test_dr_skill_replacement_1186.py) and [share/skills/h-decision-requests/SKILL.md](share/skills/h-decision-requests/SKILL.md).
- Commit: `76656e53b4e7695001fe2fd1121d38d97a8adad4` (`docs: align decision request handbook with live API (#1187, builder)`).

- Reflection: Direct contract comparison against live tool/engine code prevented repeating a false-green structural pass.
- Reflection: A single-file, wording-only edit resolved the review finding while preserving surgical scope.
- Reflection: Scoped quality-runner evidence remained green and confirmed no regressions in #1186 structural checks.
[[2026-04-30]]
## Review Evidence
### Test Results
- pytest: 9 passed, 0 failed, 0 skipped on tests/test_dr_skill_replacement_1186.py via quality-runner (`9 passed in 0.38s`).

### Lint
- ruff: clean on tests/test_dr_skill_replacement_1186.py and share/skills/h-decision-requests/SKILL.md via quality-runner.

### Coverage
- N/A. This td:0 docs task was reviewed with the inherited structural suite plus lint only; no coverage run was requested.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- Skipped as a gate per td:0 workflow. I still ran the inherited #1186 structural suite because AC5 explicitly requires it to pass.
- Current inherited structural suite remains present at tests/test_dr_skill_replacement_1186.py:39 with the relevant checks at lines 44, 52, 72, and 81.

#### Security Review
- No security findings. The verified change surface is a handbook file only, and the documented helper contract now matches the live MCP and engine implementation cited below.

#### Test Integrity
- No weakening is visible in the current inherited structural suite. The current snapshot still contains TestFromAC_DRSkillReplacement and the relevant assertions at tests/test_dr_skill_replacement_1186.py:39, 44, 52, 72, and 81.
- Builder-reported fix scope is handbook-only, and commit 76656e53b4e7695001fe2fd1121d38d97a8adad4 is present in .git/logs/refs/heads/dev:1025 and .git/logs/HEAD:1063.

#### Test Quality
- ADEQUATE for this td:0 docs task. The inherited suite proves the deletion/existence regressions it claims to cover, and reviewer manual inspection covered the live contract wording that caused the prior FAIL.

#### Data Safety
- No issues found.

#### Implementation-Aware Test Gap Analysis
- No blocking gap remains. The prior contract drift is corrected: share/skills/h-decision-requests/SKILL.md now documents the create_dr contract at lines 28-35 and no longer advertises query or resolve_decision helpers.
- The documented parameters match the live wrapper and engine signatures in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:429-434 and serve/kanban/src/owlbear_kanban/decisions.py:84-91.
- Fire-and-forget lifecycle is grounded in live behavior: create_dr blocks the task with reason DR pending at serve/kanban/src/owlbear_kanban/decisions.py:127, and AgentView.pick_tasks resolves pending DRs before dispatch in serve/kanban/src/owlbear_kanban/engine.py:2279-2328 together with serve/kanban/src/owlbear_kanban/decisions.py:136-170.

#### Necessity Check
- N/A. No new dependency, integration, or external capability was added.

#### Builder Process Quality
- CLEAN. The task file shows one prior review section at .owlbear/kanban/tasks/1187-p2-02-create-h-decision-requests-skill-delete-scribe-and-w-decision-routing.md:109 and two builder sections at lines 96 and 170; the second builder pass corrected the live contract mismatch rather than repeating the same failed wording.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| share/skills/h-decision-requests/SKILL.md created (~50 lines) documenting when/how/body/fire-and-forget | Handbook sections exist at share/skills/h-decision-requests/SKILL.md:13, :28, :40, :63, and :78; the file extends through line 82; the documented create_dr parameters and lifecycle align with serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:429-434, serve/kanban/src/owlbear_kanban/decisions.py:84-127, and serve/kanban/src/owlbear_kanban/engine.py:2279-2328. | tests/test_dr_skill_replacement_1186.py::test_h_decision_requests_skill_exists (existence proof); content and live-contract alignment verified manually | PASS |
| share/agents/scribe.agent.md deleted | Workspace file search returned no match for share/agents/scribe.agent.md. | tests/test_dr_skill_replacement_1186.py::test_scribe_agent_does_not_exist | PASS |
| share/skills/w-decision-routing/SKILL.md deleted | Workspace file search returned no match for share/skills/w-decision-routing/SKILL.md. | tests/test_dr_skill_replacement_1186.py::test_w_decision_routing_skill_does_not_exist | PASS |
| New skill has valid frontmatter (name: h-decision-requests, description, user-invocable: false) | Frontmatter fields are present at share/skills/h-decision-requests/SKILL.md:2-4. | tests/test_dr_skill_replacement_1186.py::test_h_decision_requests_skill_has_valid_frontmatter (name/description) plus reviewer verification of user-invocable: false | PASS |
| All tests from #1186 pass | quality-runner report: 9 passed, 0 failed, 0 skipped on tests/test_dr_skill_replacement_1186.py. | tests/test_dr_skill_replacement_1186.py | PASS |

### Deductions
- -0.03 changed-file scope was reconstructed from builder notes plus commit-log presence rather than a direct git diff in the current tool surface.

### Verdict
- PASS. Confidence: 0.95

### Action
- Advancing to docs.

### Review Notes
- The prior FAIL was resolved. The handbook no longer advertises unsupported query/resolve helpers, and the remaining lifecycle wording is consistent with the live create_dr plus resolve_pending_drs flow.

### Reflection
- Green inherited structural tests were necessary but not sufficient here; the handbook still needed a live contract audit.
- The authoritative resolution hook for this DR lifecycle is the engine dispatch path in AgentView.pick_tasks(), not the MCP entry point alone.
- Commit presence was verified through .git/logs because direct git diff inspection was not available in this tool surface.
[[2026-04-30]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed files are all OUT-scope agent-executables (SKILL.md, .agent.md). No IN-scope prose docs (root README, serve/*/README, setup guides, share/README) reference scribe, w-decision-routing, or h-decision-requests. |
| 2 | Module docstrings | No | N/A | No .py files changed. |
| 3 | External attribution | No | N/A | Task body states "Research doc: none (trivial)"; no external patterns cited. |
| 4 | Research doc | No | N/A | Task body confirms "Research doc: none." |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `pipeline.excalidraw` describes `share/agents/*.agent.md` (matches deleted scribe.agent.md). `project-overview.excalidraw` describes `share/**` (matches all changed files). Both footers updated: 3c5aa926/42a098d3 → f7c02f9a. Commit 04992804. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body. |
| 7 | Deletion detection | No | N/A | Deleted files (scribe.agent.md, w-decision-routing/SKILL.md) are OUT-scope agent-executables. No IN-scope descriptive docs reference them (grep confirmed only .owlbear/decisions/README.md and share/WIRING.md — both OUT-scope). |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| share/skills/h-decision-requests/SKILL.md | OUT (agent-executable SKILL.md) | N/A |
| share/agents/scribe.agent.md | OUT (agent-executable .agent.md) | N/A |
| share/skills/w-decision-routing/SKILL.md | OUT (agent-executable SKILL.md) | N/A |
| share/diagrams/pipeline.excalidraw | IN (diagram) | Footer updated |
| share/diagrams/project-overview.excalidraw | IN (diagram) | Footer updated |

### Files Updated
- share/diagrams/pipeline.excalidraw (footer: 3c5aa926 → f7c02f9a)
- share/diagrams/project-overview.excalidraw (footer: 42a098d3 → f7c02f9a)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no .owlbear/scratch/1187-* files found)
[[2026-04-30]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| SKILL.md created (~50 lines) documenting when/how/body/fire-and-forget | File exists at 82 lines; sections: When To Create (L13), create_dr Contract (L28), Body Format (L40), Fire-And-Forget (L63), Operational Rules (L78). Content aligns with live API (reviewer verified against server.py:429-434 and decisions.py:84-127). | PASS |
| scribe.agent.md deleted | file_search returned no match | PASS |
| w-decision-routing/SKILL.md deleted | file_search returned no match | PASS |
| Valid frontmatter (name, description, user-invocable: false) | Present at lines 2-4 | PASS |
| All tests from #1186 pass | quality-runner full run: test_dr_skill_replacement_1186.py not in 65 failures (9/9 green) | PASS |

### Test Results
- pytest: 3264 passed, 65 failed, 4 skipped. Zero failures in task scope. All 65 are pre-existing background debt in unrelated modules (engine_init_1068, storage_1050, cockpit_react_compiler_1015, engine_atomicity_1104, migrate, outputschema_541, engine_dead_code_1112, cockpit_decisions_api_1189).
- ruff: 4 violations, none in task-scoped files (all in knowledge, mcp-knowledge, mcp-memory, orchestrator).

### Architect Quality: 4/5
AC lines are specific, verifiable, and scope-bounded. Minor gap: AC did not explicitly require live-API alignment for handbook content (reviewer caught this on first pass), but encoding contract accuracy for docs tasks is inherently difficult. Adequate.

### Deduction Breakdown
- AC lines without evidence: 0 (all 5 verified) = 0.00
- Lint in task scope: 0 = 0.00
- AC quality (4/5, above threshold): 0.00
- Reviewer evidence: present and detailed (two passes, second PASS at 0.95): 0.00
- Full-suite failures in task scope: 0 = 0.00

### Confidence: 0.98
### Action: archive