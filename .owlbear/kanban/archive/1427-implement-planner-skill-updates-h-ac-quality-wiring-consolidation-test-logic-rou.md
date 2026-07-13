---
id: 1427
title: Implement planner skill updates — h-ac-quality wiring, consolidation-test
  logic, routing enforcement
status: archived
priority: medium
created: 2026-05-08T00:47:38.789879+00:00
updated: 2026-05-08T14:31:00.409939+00:00
tags:
- pipeline
- ws-ac-quality
- scope:agents
- agent
parent: 1405
depends_on:
- 1405
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

P2: `w-task-decomposition/SKILL.md` Step 0 required_reading includes `h-ac-quality` — verified by field-presence check in the file
P2: `w-task-decomposition/SKILL.md` Durability Principles section references `h-ac-quality` as the authoritative expanded schema — verified by artifact inspection
P2: `w-task-decomposition/SKILL.md` contains a consolidation-test creation rule: when ≥2 implementation tasks exist under a common parent in decomposition mode, planner creates one task titled "consolidation test: {feature name}" with deps listing all sibling implementation task IDs — verified by artifact inspection of the new section
P2: `w-task-decomposition/SKILL.md` Step 6 explicitly prohibits creating tasks at `todo` status — verified by artifact inspection
P2: `planner.agent.md` `<required_reading>` section includes `h-ac-quality` — verified by field-presence check
P2: `planner.agent.md` `<critical_rules>` includes rule: "Never create tasks at `todo` — only architect moves `backlog→todo`" — verified by artifact inspection

## Scope

**In scope:** `share/skills/w-task-decomposition/SKILL.md` edits, `share/agents/planner.agent.md` edits
**Out of scope:** h-ac-quality content itself (A1, already done), architect/challenger updates (A3, separate task)

## Reference

Research doc: `.owlbear/research/planner-ac-quality-update.md`
Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)


## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All changes scoped to planner skill/agent wiring |
| Interface clarity | PASS | AC specifies exact text patterns and verification methods |
| Dependency correctness | PASS | h-ac-quality skill exists; parent #1405 archived (prereq done) |
| Module layering | PASS | Agent and skill .md files only, no code dependencies |
| TDD compliance | N/A | Non-implementation (agent/skill files) |
| KISS/YAGNI | PASS | Minimal changes prescribed by brief |
| Premise challenge | PASS | Legitimate wiring — h-ac-quality, consolidation-test, and routing enforcement are brief deliverables |
| Pattern consistency | PASS | Follows existing skill required_reading and agent critical_rules patterns |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | All changes within agent/skill domain |

### Challenge Results
- Challenger: SKIPPED — all AC lines td:0
- Architect response: N/A

### Test Depth
- Max depth: 0
- Test-writer: SKIP (all td:0)

### Verdict: APPROVE
### Action Taken: Added `agent` pass-through tag. All AC lines annotated td:0. Advancing to todo.
[[2026-05-08]]
## Architecture Review

All 6 AC lines verified against workspace files — changes already present in both `share/skills/w-task-decomposition/SKILL.md` and `share/agents/planner.agent.md`. AC is precise, artifact-inspection scoped, single-domain (agent/skill files). All td:0. Added `agent` pass-through tag. Challenger skipped (all td:0).

Verdict: APPROVE
[[2026-05-08]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Implementation: no code changes required.
- Evidence: verified AC directly in `share/skills/w-task-decomposition/SKILL.md` and `share/agents/planner.agent.md`.
- AC checks confirmed:
  - `w-task-decomposition` Step 0 required_reading includes `h-ac-quality`.
  - `w-task-decomposition` Durability Principles references `h-ac-quality` as authoritative checklist.
  - `w-task-decomposition` includes consolidation-test rule for decomposition mode with >=2 implementation siblings under common parent, title pattern `consolidation test: {feature name}`, and deps on sibling implementation task IDs.
  - `w-task-decomposition` Step 6 explicitly prohibits creating tasks at `todo` status.
  - `planner.agent.md` `<required_reading>` includes `h-ac-quality`.
  - `planner.agent.md` `<critical_rules>` includes `Never create tasks at `todo` — only architect moves `backlog→todo`.`
- Tests: N/A (td:0 non-implementation pass-through from test-writer).
- Lint/Coverage: N/A (no source/test modifications).
- Approach: validated existing artifacts against AC and advanced without unnecessary edits.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner skipped: td:0 artifact-only review. Scope is markdown/agent-skill files only and introduces no executable task-local test surface.

### Lint Results
- quality-runner skipped: review scope is `share/skills/w-task-decomposition/SKILL.md` and `share/agents/planner.agent.md`; no runnable Python/TS lint surface is owned by this task.

### Coverage
- N/A (td:0 artifact task).

### Scope and Duplicate Evidence
- First review cycle: no prior `## Review Evidence` section exists in this task file.
- Current task body states the work was already present before builder pickup: `.owlbear/kanban/tasks/1427-implement-planner-skill-updates-h-ac-quality-wiring-consolidation-test-logic-rou.md:72` says the changes were already present in both scoped files, and `:81` says `Implementation: no code changes required.`
- Archived task `#1405` is the same A2 deliverable: `.owlbear/kanban/archive/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md:2-5`.
- That archived task explicitly created follow-up `#1427` during research at `.owlbear/kanban/archive/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md:56`, then recorded builder commits at `:103` and `:171`, passed review to docs at `:220`, and reached audit at `:257`.
- Result: `#1427` has no independent implementation delta left to review. This is a stale duplicate child / routing defect, not a builder bug.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| `w-task-decomposition/SKILL.md` Step 0 required_reading includes `h-ac-quality` | `share/skills/w-task-decomposition/SKILL.md:16` | PASS |
| Durability Principles references `h-ac-quality` as authoritative expanded schema | `share/skills/w-task-decomposition/SKILL.md:75` | PASS |
| Consolidation-test creation rule exists with required title/deps semantics | `share/skills/w-task-decomposition/SKILL.md:150`, `:152`, `:154` | PASS |
| Step 6 explicitly prohibits creating tasks at `todo` status | `share/skills/w-task-decomposition/SKILL.md:148` | PASS |
| `planner.agent.md` `<required_reading>` includes `h-ac-quality` | `share/agents/planner.agent.md:34` | PASS |
| `planner.agent.md` `<critical_rules>` includes architect-only `todo` rule | `share/agents/planner.agent.md:42` | PASS |

### Findings
1. Duplicate/stale child task: archived `#1405` already implemented and archived the same A2 planner update, while `#1427` remained open and reached review with zero independent builder delta. Approving this task would rubber-stamp duplicate delivery rather than a fresh implementation.

### Deductions
- 0.08: task is structurally non-reviewable as a fresh builder deliverable because archived `#1405` already owns and completed the same scope.
- 0.02: direct git diff / dirty-tree checks were unavailable in the current tool surface; verdict is anchored to kanban archive state plus live artifact inspection.

### Verdict
- FAIL -> backlog
- Confidence: 0.88

### Action
- Rejecting to backlog for architect cleanup / re-scope. Do not send back to builder; the repository already contains the A2 deliverable under archived `#1405`.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Archive/close `#1427` as a duplicate of archived `#1405`, or rewrite `#1427` so it names a distinct unfinished deliverable before it re-enters the pipeline | `.owlbear/kanban/tasks/1427-implement-planner-skill-updates-h-ac-quality-wiring-consolidation-test-logic-rou.md`, `.owlbear/kanban/archive/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md` | Duplicate evidence at archived `#1405`: `:2-5`, `:56`, `:103`, `:171`, `:220`, `:257`; active `#1427`: `:72`, `:81` |
| 2 | architect | If new planner work is still intended, create or retitle a task whose AC differ from archived `#1405`’s A2 contract instead of reusing the already-satisfied planner wiring scope | `share/skills/w-task-decomposition/SKILL.md`, `share/agents/planner.agent.md` | Archived `#1405` AC at `.owlbear/kanban/archive/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md:28-31` already match live artifacts at `share/skills/w-task-decomposition/SKILL.md:16`, `:75`, `:148`, `:150`, `:152`, `:154`, and `share/agents/planner.agent.md:34`, `:42` |
[[2026-05-08]]
## Architecture Review (Duplicate Closure)

**Verdict: APPROVE (duplicate — fast-track closure)**

All 6 AC lines are already satisfied in live workspace artifacts, delivered by archived parent #1405. This task is a stale duplicate child created during #1405's research phase but never rescoped after #1405 completed the identical deliverables.

### AC Verification (confirmed against live files)
| AC Line | File:Line | Status |
|---|---|---|
| Step 0 required_reading includes h-ac-quality | w-task-decomposition/SKILL.md:16 | SATISFIED |
| Durability Principles references h-ac-quality | w-task-decomposition/SKILL.md:75 | SATISFIED |
| Consolidation-test creation rule | w-task-decomposition/SKILL.md:148-155 | SATISFIED |
| Step 6 prohibits todo status | w-task-decomposition/SKILL.md:148 | SATISFIED |
| planner.agent.md required_reading includes h-ac-quality | planner.agent.md:34 | SATISFIED |
| planner.agent.md critical_rules todo prohibition | planner.agent.md:42 | SATISFIED |

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All changes scoped to planner skill/agent wiring |
| Interface clarity | PASS | AC artifact-inspection verified |
| Dependency correctness | PASS | Parent #1405 archived (prereq done) |
| Module layering | PASS | .md files only |
| TDD compliance | N/A | Non-implementation (agent/skill) |
| KISS/YAGNI | PASS | No new changes needed |
| Premise challenge | PASS — duplicate | Work already delivered under #1405 |
| Pattern consistency | PASS | Existing patterns followed |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | Agent/skill domain only |

### Test Depth
- All AC lines: td:0
- Test-writer: SKIP

### Challenge
- Challenger: SKIPPED (all td:0)

### Routing Note
Duplicate of archived #1405. All AC pre-satisfied. Downstream agents (test-writer, builder, reviewer) should pass through with zero work.
[[2026-05-08]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Task tagged `agent`; all 6 AC lines are non-implementation artifact-inspection checks (SKILL.md / .agent.md files only).
- Latest Architecture Review (Duplicate Closure) explicitly routes: "Test-writer: SKIP".
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Non-implementation task (td:0 artifact verification only) — no code changes needed.
- Verified AC artifacts already present in scope files:
  - `share/skills/w-task-decomposition/SKILL.md` includes `h-ac-quality` in Step 0 required reading and Durability Principles reference.
  - `share/skills/w-task-decomposition/SKILL.md` includes consolidation-test creation rule and explicit prohibition on creating tasks at `todo`.
  - `share/agents/planner.agent.md` includes `h-ac-quality` in `<required_reading>` and the architect-only `backlog→todo` rule in `<critical_rules>`.
- Tests: N/A (td:0 non-implementation pass-through from test-writer).
- Lint/Coverage: N/A (no source or test file changes).
- Passing through to review.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner not applicable: td:0 artifact-only task. The AC covers only `share/skills/w-task-decomposition/SKILL.md` and `share/agents/planner.agent.md` and introduces no executable test surface.

### Lint Results
- quality-runner not applicable for td:0 artifact scope.
- Editor diagnostics are clean for `share/skills/w-task-decomposition/SKILL.md` and `share/agents/planner.agent.md`.

### Coverage
- N/A (td:0 artifact task).

### Scope and Duplicate Evaluation
- This is the second review cycle: the prior `## Review Evidence` section begins at `.owlbear/kanban/tasks/1427-implement-planner-skill-updates-h-ac-quality-wiring-consolidation-test-logic-rou.md:94`.
- The prior fail was a duplicate-task concern, but the latest binding refinement is `## Architecture Review (Duplicate Closure)` at `.owlbear/kanban/tasks/1427-implement-planner-skill-updates-h-ac-quality-wiring-consolidation-test-logic-rou.md:141`. That section states all AC are already satisfied and explicitly routes downstream agents to pass through with zero work at `:179`.
- Duplicate ownership is verified directly in the archived parent deliverable: `.owlbear/kanban/archive/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md:28-32` contains materially equivalent AC, `:56` created follow-up `#1427`, `:103` and `:171` record the builder commits, and `:257` plus `:280` show the task reached audit and archive.
- Active task history also shows the scoped artifacts were already present before builder pickup: `.owlbear/kanban/tasks/1427-implement-planner-skill-updates-h-ac-quality-wiring-consolidation-test-logic-rou.md:72` and `:81`.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| `w-task-decomposition/SKILL.md` Step 0 required_reading includes `h-ac-quality` | `share/skills/w-task-decomposition/SKILL.md:16` | PASS |
| `w-task-decomposition/SKILL.md` Durability Principles references `h-ac-quality` as the authoritative expanded schema | `share/skills/w-task-decomposition/SKILL.md:75` | PASS |
| `w-task-decomposition/SKILL.md` contains the consolidation-test creation rule with required trigger/title/deps/status semantics | `share/skills/w-task-decomposition/SKILL.md:150`, `:152`, `:154`, `:155` | PASS |
| `w-task-decomposition/SKILL.md` Step 6 explicitly prohibits creating tasks at `todo` status | `share/skills/w-task-decomposition/SKILL.md:148` | PASS |
| `planner.agent.md` `<required_reading>` includes `h-ac-quality` | `share/agents/planner.agent.md:34` | PASS |
| `planner.agent.md` `<critical_rules>` includes the architect-only `todo` rule | `share/agents/planner.agent.md:42` | PASS |

### Findings
- No AC violations found.
- Informational: this task remains a stale duplicate of archived `#1405`, but the latest Architecture Review explicitly resolved that concern by converting the current cycle to duplicate-closure pass-through. Repeating the earlier fail would no longer track an unsatisfied AC.

### Deductions
- 0.04: td:0 artifact-only scope means there is no executable quality-runner evidence; the verdict relies on direct artifact inspection plus clean editor diagnostics.
- 0.02: direct git diff / dirty-tree checks were unavailable in the current tool surface, so duplicate ownership is reconstructed from kanban archive evidence plus live file inspection.

### Verdict
- PASS -> docs
- Confidence: 0.93

### Action
- Advancing to docs. Downstream handling should treat this as duplicate-closure pass-through unless the task is later rewritten to a distinct unfinished scope.
[[2026-05-08]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed files are `share/skills/w-task-decomposition/SKILL.md` and `share/agents/planner.agent.md` — both OUT of scope (agent-executables). No IN-scope prose docs reference these files by name. |
| 2 | Module docstrings | No | N/A | No Python modules modified. |
| 3 | External attribution | No | N/A | No external patterns used; duplicate-closure pass-through task. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/planner-ac-quality-update.md` exists, linked in task body under `## Reference`. Owning task is `#1405`; follow-up `#1427` recorded there. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/pipeline.excalidraw` describes `share/agents/*.agent.md` — matches `share/agents/planner.agent.md`. Footer updated to `Last verified: 2026-05-08 (4b7c9960)`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No deleted files in changed-files set. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `share/skills/w-task-decomposition/SKILL.md` | OUT (agent-executable SKILL.md) | N/A |
| `share/agents/planner.agent.md` | OUT (agent-executable .agent.md) | N/A — diagram describes-match triggered Item 5 |
| `share/diagrams/pipeline.excalidraw` | IN (diagram) | Footer updated |
| `.owlbear/research/planner-ac-quality-update.md` | IN (research doc) | Verified exists |

### Files Updated
- `share/diagrams/pipeline.excalidraw` — footer updated to `Last verified: 2026-05-08 (4b7c9960)` (commit `3b519af1`)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1427-*` scratch files existed)
[[2026-05-08]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Step 0 required_reading includes h-ac-quality | w-task-decomposition/SKILL.md:16 (spot-checked) | PASS |
| Durability Principles references h-ac-quality as authoritative | w-task-decomposition/SKILL.md:75 (spot-checked) | PASS |
| Consolidation-test creation rule with title/deps/status | w-task-decomposition/SKILL.md:150-155 (spot-checked) | PASS |
| Step 6 prohibits todo status | w-task-decomposition/SKILL.md:148 (spot-checked) | PASS |
| planner.agent.md required_reading includes h-ac-quality | planner.agent.md:34 (spot-checked) | PASS |
| planner.agent.md critical_rules todo prohibition | planner.agent.md:42 (spot-checked) | PASS |

### Test Results
- pytest: 2968 passed, 172 failed, 4 skipped. All 172 failures are pre-existing background debt unrelated to task scope (0 code changes in this td:0 artifact task).
- ruff (task scope): clean. 12 violations in serve/ packages unrelated to task scope.

### Upstream Commits
- 9a9e5e10 feat: update planner AC quality and routing rules (#1405, builder)
- 6065cb02 fix: enforce shortcut todo normalization (#1405, builder)
- 3b519af1 docs: update pipeline diagram footer for #1427 (doc-writer)
Deliverables committed under parent #1405; docs gate committed under #1427. Verified.

### Architect Quality: 4/5
AC is specific, verifiable, artifact-scoped. Minor process defect: parent #1405 created this child then completed the same scope itself, causing duplicate pipeline cycles. AC quality itself is good.

### Deduction Breakdown
- AC lines without evidence: 0 (all 6 verified) = -0.00
- Lint violations in scope: none = -0.00
- AC quality (4/5, above threshold): -0.00
- Missing reviewer evidence: not missing = -0.00
- Full-suite failures in task scope: none = -0.00
- Duplicate-closure routing uncertainty: -0.02

### Confidence: 0.98
### Action: archive