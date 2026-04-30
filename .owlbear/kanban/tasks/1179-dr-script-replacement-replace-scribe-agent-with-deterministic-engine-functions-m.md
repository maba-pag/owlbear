---
id: 1179
title: DR Script Replacement — decomposition parent (tracking)
status: backlog
priority: important
created: 2026-04-30T00:48:49.954557+00:00
updated: 2026-04-30T02:55:18.877752+00:00
tags:
- quality
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

[[2026-04-30]]
## Planning
### Decomposition: DR Script Replacement
- Tasks created: 15
- Dependency layers: 5
- Phases: 3 (Engine+MCP → Agent/Skill → Cockpit)

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| 1180 | P1-01: Test decisions.py create_dr + resolve_pending_drs | needed | — | phase-1, scope:kanban, type:test |
| 1181 | P1-02: Implement decisions.py module | critical | 1180 | phase-1, scope:kanban, type:impl |
| 1182 | P1-03: Test create_dr MCP tool | needed | — | phase-1, scope:mcp-kanban, type:test |
| 1183 | P1-04: Implement create_dr MCP tool + guidance text update | needed | 1181, 1182 | phase-1, scope:mcp-kanban, type:impl |
| 1184 | P1-05: Test pick_tasks resolve_pending_drs integration | needed | — | phase-1, scope:kanban, type:test |
| 1185 | P1-06: Implement pick_tasks resolve integration | important | 1181, 1184 | phase-1, scope:kanban, type:impl |
| 1186 | P2-01: Test DR skill replacement structure | needed | — | phase-2, scope:agents, type:test |
| 1187 | P2-02: Create h-decision-requests skill + delete scribe/w-decision-routing | needed | 1186 | phase-2, scope:agents, type:impl |
| 1188 | P2-03: Update agent/skill/instruction references + decisions README | important | 1186, 1187 | phase-2, scope:agents, type:impl |
| 1189 | P3-01: Test decisions API endpoints | needed | — | phase-3, scope:cockpit, type:test |
| 1190 | P3-02: Implement decisions API endpoints | needed | 1181, 1189 | phase-3, scope:cockpit, type:impl |
| 1191 | P3-03: Test DR status indicator + popover components | needed | — | phase-3, scope:cockpit-fe, type:test |
| 1192 | P3-04: Implement DR status indicator + popover | needed | 1190, 1191 | phase-3, scope:cockpit-fe, type:impl |
| 1193 | P3-05: Test resolve modal component | needed | — | phase-3, scope:cockpit-fe, type:test |
| 1194 | P3-06: Implement resolve modal | important | 1192, 1193 | phase-3, scope:cockpit-fe, type:impl |

### Dependency Graph
```mermaid
graph TD
  1180 --> 1181
  1181 --> 1183
  1182 --> 1183
  1181 --> 1185
  1184 --> 1185
  1186 --> 1187
  1186 --> 1188
  1187 --> 1188
  1181 --> 1190
  1189 --> 1190
  1190 --> 1192
  1191 --> 1192
  1192 --> 1194
  1193 --> 1194
```

[[2026-04-30]]
## Architecture Review\nDecomposition parent — planner completed successfully. 15 child tasks created across 3 phases (Engine+MCP → Agent/Skill → Cockpit) with 5 dependency layers. Child tasks #1180–#1194 carry the actual work and will be individually reviewed at backlog.\n\n### Verdict: APPROVE\n### Action Taken: Advanced decomposition parent after planner completion.
[[2026-04-30]]
## Test-Writer Notes
- Non-impl pass-through: decomposition parent task with no Acceptance Criteria and no testable Python interfaces.
- All implementation and testing work delegated to child tasks #1180–#1194.
- Passing through to builder.
[[2026-04-30]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Scope is decomposition only; all executable work is owned by child tasks #1180–#1194.
- Tests: not applicable for parent pass-through task.
- Lint/Coverage: not applicable for parent pass-through task.
- Passing through to review.
[[2026-04-30]]
## Review Evidence
### Test Results
- quality-runner (scoped no-op): 0 passed, 0 failed, 0 skipped.
- No task-scoped test paths applied because this parent task produced no executable deliverables.

### Lint
- quality-runner: clean.
- No lint paths applied because this parent task produced no code or test files.

### Coverage
- Not applicable for this parent task.

### Pass 1 — CRITICAL
#### Split / Closeout Contract
| Contract Item | Evidence | Status |
|---|---|---|
| Split parent must be decomposed, then updated or deleted and released instead of flowing downstream unchanged | [share/skills/w-arch-review/SKILL.md](share/skills/w-arch-review/SKILL.md#L138) requires planner decomposition, dependency updates, then edit/delete original and release. The stored parent task still records the decomposition output at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L20) and the child list at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L30), while its architecture note says the child tasks carry the actual work at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L66). | FAIL |
| Review is not a non-implementation pass-through gate | [share/skills/w-arch-review/SKILL.md](share/skills/w-arch-review/SKILL.md#L152) marks review as a real quality gate with no non-impl pass-through. The parent still uses pass-through notes from test-writer and builder at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L68) and [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L73). | FAIL |
| Non-testable tasks require a pass-through tag before approval | [share/skills/w-arch-review/SKILL.md](share/skills/w-arch-review/SKILL.md#L158) requires a pass-through tag for tasks with no testable code. The parent frontmatter still has empty tags at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L9), while the test-writer note explicitly says the task has no Acceptance Criteria and no testable Python interfaces at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L69). | FAIL |

#### Active Child Evidence
- The split children are real active descendants, so the parent is not a finished closeout artifact: [1180 review status](.owlbear/kanban/tasks/1180-p1-01-test-decisions-py-create-dr-resolve-pending-drs.md#L4) with [parent link](.owlbear/kanban/tasks/1180-p1-01-test-decisions-py-create-dr-resolve-pending-drs.md#L12), and [1181 research status](.owlbear/kanban/tasks/1181-p1-02-implement-decisions-py-module.md#L4) with [parent link](.owlbear/kanban/tasks/1181-p1-02-implement-decisions-py-module.md#L12).

### AC Compliance
- No Acceptance Criteria section exists on the stored parent task body. It jumps directly into planner output at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L20).
- The parent was not rewritten into explicit closeout or tracking criteria after decomposition. It still carries the original feature title at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L3) and delegates executable work to child tasks at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L70).

### Deductions
- -0.45 split parent advanced downstream without rewrite or release
- -0.25 unauthorized non-implementation pass-through through review
- -0.10 missing pass-through tag for a non-testable task
- Confidence: 0.20

### Verdict
- FAIL. This is a routing and contract defect, not an implementation defect.

### Required Follow-up
- Architect must either release/remove this parent from the delivery pipeline or rewrite it into an explicit closeout or tracking task with td:0-style criteria and a valid pass-through tag before it can advance again.

### Action
- Rejected to backlog.
[[2026-04-30]]

## Acceptance Criteria (Closeout)
- [ ] 15 child tasks (#1180–#1194) exist in kanban with correct parent references (td:0)
- [ ] Dependency graph wired per Planning section above (td:0)
- [ ] This parent retains decomposition record for traceability (td:0)

## Architecture Review (Re-review after reviewer rejection)
### Context
Reviewer rejected this parent because it flowed through the pipeline without AC, pass-through tag, or closeout rewrite. This re-review rewrites it as a proper closeout task.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tracking parent — one concern |
| Interface clarity | PASS | No code interfaces; AC is mechanical verification |
| Dependency correctness | PASS | No deps — children carry deps among themselves |
| Module layering | PASS | N/A — no code |
| TDD compliance | PASS | All AC td:0, pass-through tag applied |
| KISS/YAGNI | PASS | Minimal closeout AC |
| Premise challenge | PASS | Parent must exist for traceability of 15-task decomposition |
| Pattern consistency | PASS | quality tag matches non-impl pass-through convention |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | Pure tracking |

### Challenge Results
- Challenger: SKIPPED — all td:0

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Rewrote as closeout task with td:0 AC and `quality` pass-through tag. Advancing to todo.

[[2026-04-30]]
Re-review after reviewer rejection. Rewrote decomposition parent as closeout task: added explicit td:0 AC (child existence, dependency graph, traceability record), applied `quality` pass-through tag, renamed to clarify tracking role. All criteria PASS. Challenger skipped (all td:0). Advancing to todo.
[[2026-04-30]]
## Test-Writer Notes
- Test file: none
- Non-impl pass-through: all AC are `td:0` (tracking criteria — child existence, dependency graph, traceability record). No testable Python interfaces exist.
- No tests written. No pytest run required.
- Passing through to builder.
[[2026-04-30]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Scope: decomposition parent closeout tracking only (all AC are td:0).
- Files changed: none.
- Tests: not applicable (no TestFromAC scope for builder).
- Coverage: not applicable.
- Lint: not applicable.
- Evidence summary: task body explicitly marks non-impl pass-through and td:0 closeout criteria only (child existence, dependency wiring, traceability retention).
- Fixes applied: none.
[[2026-04-30]]
## Review Evidence
### Test Results
- quality-runner: 0 passed, 0 failed, 0 skipped.
- No commands run because test_paths was empty for this td:0 closeout task.

### Lint
- quality-runner: clean.
- No commands run because lint_paths was empty for this td:0 closeout task.

### Coverage
- Not applicable.
- No commands run because coverage_modules was empty for this td:0 closeout task.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Skipped correctly. All three AC lines are td:0 closeout checks at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L123) and [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L126). No TestFromAC classes or executable interfaces exist for this parent task.

#### Security Review
- No issues. Review scope is kanban metadata only; no code, dependency package, or runtime boundary changes were delivered in this task.

#### Test Integrity
- Skipped. No TestFromAC classes exist for this td:0 task.

#### Test Quality
- N/A for td:0. No task-scoped tests are expected.

#### Data Safety
- No issues in scope. No executable code or persisted runtime-path changes were delivered.

#### Implementation-Aware Gaps
- FAIL. The parent says 15 tasks were created at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L23) and explicitly lists child tasks 1184 and 1186 at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L34) and [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L36). A scan of active task files found 13 children with `parent: 1179`, including [.owlbear/kanban/tasks/1180-p1-01-test-decisions-py-create-dr-resolve-pending-drs.md](.owlbear/kanban/tasks/1180-p1-01-test-decisions-py-create-dr-resolve-pending-drs.md#L12) and [.owlbear/kanban/tasks/1194-p3-06-implement-resolve-modal.md](.owlbear/kanban/tasks/1194-p3-06-implement-resolve-modal.md#L12), but no task files exist for 1184 or 1186 in tasks or archive, and show_task failed for both IDs with "Task not found".

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 2 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Partial fix verified: the parent now carries the quality tag at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L9) and explicit closeout AC at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L123) and [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L126). The remaining blocker is live board completeness, not pass-through tagging.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| 15 child tasks (#1180–#1194) exist in kanban with correct parent references (td:0) | Parent declares 15 created at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L23) and lists 1184 / 1186 at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L34) and [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L36). Active board scan found 13 `parent: 1179` children and file searches for 1184 / 1186 returned no files in tasks or archive; show_task for both IDs returned not found. | quality-runner N/A (td:0) | FAIL |
| Dependency graph wired per Planning section above (td:0) | The plan still expects 1184 / 1186 as graph nodes at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L34) and [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L36). Existing children still depend on those missing IDs at [.owlbear/kanban/tasks/1185-p1-06-implement-pick-tasks-resolve-integration.md](.owlbear/kanban/tasks/1185-p1-06-implement-pick-tasks-resolve-integration.md#L15), [.owlbear/kanban/tasks/1187-p2-02-create-h-decision-requests-skill-delete-scribe-and-w-decision-routing.md](.owlbear/kanban/tasks/1187-p2-02-create-h-decision-requests-skill-delete-scribe-and-w-decision-routing.md#L14), and [.owlbear/kanban/tasks/1188-p2-03-update-agent-skill-instruction-references-decisions-readme.md](.owlbear/kanban/tasks/1188-p2-03-update-agent-skill-instruction-references-decisions-readme.md#L14). | quality-runner N/A (td:0) | FAIL |
| This parent retains decomposition record for traceability (td:0) | Planning, task list, and dependency graph remain present at [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L21), [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L27), and [.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md](.owlbear/kanban/tasks/1179-dr-script-replacement-replace-scribe-agent-with-deterministic-engine-functions-m.md#L46). | quality-runner N/A (td:0) | PASS |

### Deductions
- -0.45 closeout AC 1 fails because child tasks 1184 and 1186 are missing from the live board
- -0.30 closeout AC 2 fails because existing children still depend on those missing IDs
- -0.10 this is a second review failure on the same task

### Post-task Reflection
- Closeout rewrites need live-board proof, not just a new title, tag, and td:0 AC block.
- A directory-wide parent scan is the fastest way to verify split-parent completeness.
- Missing child task IDs can invalidate sibling dependency headers even when the parent body looks internally consistent.
- td:0 tasks still need independent quality-runner evidence, but the decisive proof here came from kanban metadata.

### Confidence: 0.15
### Verdict: FAIL
### Action
- Rejected to backlog. Architect must restore or recreate 1184 and 1186 with parent 1179, or revise the recorded decomposition so the live board matches the closeout contract.