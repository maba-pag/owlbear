---
id: 1405
title: 'A2: Planner skill update — AC drafting via h-ac-quality, consolidation-test
  creation, routing'
status: archived
priority: medium
created: 2026-05-07T23:16:25.183704+00:00
updated: 2026-05-08T07:05:58.466239+00:00
tags:
- pipeline
- ws-ac-quality
- scope:agents
- agent
parent: 1403
depends_on:
- 1404
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)

## Acceptance Criteria

P1: `w-task-decomposition/SKILL.md` adds `h-ac-quality` to Step 0 required_reading and references it as the authoritative AC validation checklist in the Durability Principles section (td:0)
P2: Consolidation-test creation logic added to `w-task-decomposition/SKILL.md` — when decomposition produces ≥2 implementation tasks (not test tasks) under a common parent, planner creates one consolidation-test task with: title pattern "consolidation test: {feature name}", tag `consolidation-test`, `depends_on` listing all sibling implementation task IDs, status `backlog` (td:0)
P2: Explicit `todo` prohibition added to `w-task-decomposition/SKILL.md` Step 6 — planner must never create tasks at `todo` status; decomposition mode defaults remain `research`, shortcut mode defaults remain `backlog` or `research` per caller (td:0)
P2: `planner.agent.md` `<required_reading>` updated to include `h-ac-quality`, and `<critical_rules>` updated to include: "Never create tasks at `todo` — only architect moves `backlog→todo`" (td:0)
P3: Verification by diff comparison of modified skill/agent files against these AC lines (td:0)

## Scope

**In scope:** `w-task-decomposition` skill update, `planner.agent.md` mode instruction update, consolidation-test creation logic
**Out of scope:** h-ac-quality content (A1), architect/challenger validation (A3), retroactive consolidation-test creation for existing task chains (separate concern)


## Transition Note

After this task deploys, #1420 resets all `todo` tasks to `backlog` for architect re-gate under new AC rules.
[[2026-05-08]]
## Research

### Key Findings
- `h-ac-quality` skill confirmed complete (A1 dependency satisfied)
- Neither `w-task-decomposition` nor `planner.agent.md` currently reference h-ac-quality or consolidation-test logic
- Current status routing defaults are mostly correct (decomposition→research, shortcut→backlog) but lacks explicit `todo` prohibition
- Implementation is 4 targeted .md edits with clear insertion points identified

### Trade-off Matrix
N/A — T1 prescribed modification from approved brief. No alternative approaches to evaluate.

### Follow-up Tasks Created
- #1427: Implement planner skill updates — h-ac-quality wiring, consolidation-test logic, routing enforcement (at backlog)

### Research Doc
`.owlbear/research/planner-ac-quality-update.md`

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All changes serve one goal: wire h-ac-quality into planner workflow |
| Interface clarity | PASS | AC now specifies exact tag, title pattern, deps, and routing defaults per mode |
| Dependency correctness | PASS | #1404 (h-ac-quality creation) verified complete — skill file exists |
| Module layering | PASS | Pure .md skill/agent edits, no code module concerns |
| TDD compliance | PASS | Tagged `agent` for test-writer pass-through — no testable Python code |
| KISS/YAGNI | PASS | Minimal prescribed changes from approved brief |
| Premise challenge | PASS | Planner currently has no AC quality guidance — gap is real |
| Pattern consistency | PASS | Adding to required_reading and critical_rules follows existing agent/skill patterns |
| Security surface | PASS | No system boundaries affected |
| Single domain | PASS | Agent skills domain only |

### Challenge Results
- Challenger: reconsider (confidence 0.36)
- Key issues raised: (1) consolidation-test tag missing from AC — downstream w-tdd-red keys off tag not title; (2) routing AC ambiguous — sounded like all tasks must be `backlog` vs actual intent of `todo` prohibition
- Architect response: accepted both — refined AC to add explicit `consolidation-test` tag requirement and clarified routing defaults per mode remain unchanged (decomposition=research, shortcut=backlog)

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Refined AC for tag requirement and routing clarity, added `agent` pass-through tag, advancing to todo

[[2026-05-08]]
Architecture review complete. Refined AC to fix two challenger-identified gaps: (1) added explicit `consolidation-test` tag requirement for downstream w-tdd-red compatibility, (2) clarified routing — `todo` prohibition only, existing mode defaults unchanged. Added `agent` pass-through tag. All td:0, test-writer SKIP.
[[2026-05-08]]
## Test-Writer Notes

**Pass-through — no tests written.**

All AC lines (P1–P3) describe edits to `w-task-decomposition/SKILL.md` and `planner.agent.md` — pure `.md` file modifications with no testable Python interfaces.

Architecture review explicitly tagged `agent` with Test Depth 0 and Test-writer SKIP. Heuristic pass-through confirmed: no `implement`, `function`, `class`, or `src/*.py` references in any AC line.

Advancing to in-progress for builder.
[[2026-05-08]]
## Builder Notes
- Implementation: updated [share/skills/w-task-decomposition/SKILL.md](share/skills/w-task-decomposition/SKILL.md) and [share/agents/planner.agent.md](share/agents/planner.agent.md)
- Commit: `9a9e5e10`
- Tests: td:0 pass-through task (agent/skill markdown changes only); no executable test targets introduced by this AC
- Coverage: N/A (non-code workflow/agent policy edits)
- Lint: N/A (markdown policy update scope)
- Approach: surgical AC alignment edits only

### AC Evidence
- P1: Added `h-ac-quality` setup/read guidance and explicit "authoritative AC validation checklist" wording in decomposition skill, including Durability Principles checklist reference.
- P2: Added consolidation-test creation rule in Step 6 with all required semantics:
  - title pattern `consolidation test: {feature name}`
  - tag `consolidation-test`
  - `depends_on` all sibling implementation task IDs
  - status `backlog`
- P2: Added explicit prohibition against creating `todo` tasks in both files:
  - planner critical rule: "Never create tasks at `todo` — only architect moves `backlog→todo`."
  - decomposition Step 6: never create `todo`; decomposition defaults remain `research`, shortcut defaults remain `backlog`/`research`.
- P3: Verified by targeted diff + pattern checks over both modified files before commit.

### Post-task Reflection
- Initial patch was accidentally applied to sibling repo path (`owlbear`) due to absolute-path mismatch; corrected by reapplying the exact diff in active workspace (`owlbear-dev`) and re-verifying.
- AC wording and status-routing constraints fit naturally into existing Step 0 / Durability Principles / Step 6 locations with minimal churn.
- Keeping consolidation-test logic as explicit rule text (not procedural pseudocode) preserved current skill style while satisfying required semantics.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner skipped: td:0 markdown-only task. The AC covers two documentation-style workflow artifacts (`share/skills/w-task-decomposition/SKILL.md`, `share/agents/planner.agent.md`) and introduces no executable test target.

### Lint Results
- ruff/quality-runner skipped: review scope is markdown-only; no applicable Python lint target for this task.

### Coverage
- N/A (td:0 process/agent-skill task)

### Scope and Evidence Limits
- Builder recorded commit `9a9e5e10` at task body line 103 and the reviewed file scope at line 102.
- Direct `git diff --name-only 9a9e5e10~1 9a9e5e10` and dirty-tree contamination checks were not available in the current tool surface, so changed-file scope was reconstructed from the task body and verified against the live artifacts. Small confidence deduction applied.
- Prior review failures: none detected (`## Review Evidence` absent before this review), so this is the first review FAIL.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| P1 [.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md:28] Add `h-ac-quality` to Step 0 and reference it as authoritative checklist in Durability Principles | `share/skills/w-task-decomposition/SKILL.md:16` adds Step 0 guidance; `share/skills/w-task-decomposition/SKILL.md:75` adds the authoritative checklist reference in Durability Principles | PASS |
| P2 [.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md:29] Add consolidation-test creation logic | `share/skills/w-task-decomposition/SKILL.md:150` defines the trigger; `:152-155` specify title, tag, `depends_on`, and `backlog` status | PASS |
| P2 [.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md:30] Enforce `todo` prohibition while preserving valid routing defaults | `share/skills/w-task-decomposition/SKILL.md:146-148` adds the new defaults/prohibition, but `share/skills/w-task-decomposition/SKILL.md:42` still says to preserve caller-provided `requested status` verbatim. That leaves shortcut mode internally contradictory and still permissive toward a caller-supplied `todo` value. | FAIL |
| P2 [.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md:31] Update planner required reading and critical rules | `share/agents/planner.agent.md:34` adds `h-ac-quality`; `share/agents/planner.agent.md:42` adds the architect-only `todo` rule | PASS |
| P3 [.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md:32] Verification by diff comparison of modified files | Builder recorded targeted diff verification in task body at `.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md:119`; live artifact inspection matches the claimed edit surface. | PASS |

### Findings
1. Routing enforcement is incomplete in `share/skills/w-task-decomposition/SKILL.md`. The new Step 6 prohibition at line 148 says planner must never create `todo`, but the existing shortcut instruction at line 42 still tells the planner to preserve any caller-provided requested status verbatim. Those instructions conflict on the exact AC this task was meant to harden.

### Deductions
- 0.12: AC P2 routing-enforcement miss due to conflicting shortcut-mode instruction in the same skill.
- 0.03: Direct git diff / dirty-tree contamination evidence unavailable; changed-file scope reconstructed from task body plus artifact inspection.

### Verdict
- FAIL -> in-progress
- Confidence: 0.82

### Action
- Builder retry required. Fix the shortcut-mode status instruction so caller-provided status cannot preserve or create `todo`, then re-verify the two-file diff against the task AC.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Narrow the shortcut-mode status instruction so requested status cannot preserve `todo`; make Step 1a consistent with the Step 6 architect-only `todo` rule | share/skills/w-task-decomposition/SKILL.md | AC line `.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md:30`; conflicting guidance at `share/skills/w-task-decomposition/SKILL.md:42` vs `share/skills/w-task-decomposition/SKILL.md:148` |
[[2026-05-08]]
## Builder Notes
- Implementation: updated [share/skills/w-task-decomposition/SKILL.md](share/skills/w-task-decomposition/SKILL.md) only
- Commit: `6065cb02`
- Tests: td:0 markdown-only task (no executable test target)
- Coverage: N/A (policy/skill markdown update scope)
- Lint: N/A (markdown-only scope)
- Approach: surgical retry to remove shortcut-mode routing contradiction identified in review

### AC Evidence
- P2 routing enforcement fix: updated Step 1a so shortcut mode no longer preserves caller-requested status verbatim; metadata preservation now covers only title/parent/tags.
- P2 `todo` prohibition alignment: Step 1a now explicitly states planner never creates `todo` and normalizes caller-requested `todo` to `backlog` (or `research` for researcher follow-ups), matching Step 6 architect-gated routing.
- P3 verification: confirmed final diff scope is single file (`share/skills/w-task-decomposition/SKILL.md`) and commit contains only this change.

### Post-task Reflection
- Root cause was an internal wording conflict between Step 1a and Step 6, not missing logic elsewhere.
- Minimal textual narrowing in Step 1a resolved the contradiction without changing decomposition defaults.
- Scoped single-file commit avoided reopening already-passing AC lines (P1, consolidation-test rule, planner agent updates).
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner skipped: td:0 markdown-only task. The AC covers workflow/agent artifacts only and introduces no executable test target.

### Lint Results
- quality-runner skipped for td:0 scope with no runnable test target.
- Editor diagnostics check is clean for [share/skills/w-task-decomposition/SKILL.md](share/skills/w-task-decomposition/SKILL.md) and [share/agents/planner.agent.md](share/agents/planner.agent.md).

### Coverage
- N/A (td:0 process and agent-skill task)

### Scope and Evidence Limits
- This review follows one prior review fail at [.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md](.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md#L126). The current retry addresses that single finding.
- Git log evidence confirms both builder commits exist: initial task commit at line [.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md#L103](.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md#L103) and retry commit at [.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md#L171](.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md#L171).
- Dirty-tree contamination check is clean for the review-scope artifacts: [share/skills/w-task-decomposition/SKILL.md](share/skills/w-task-decomposition/SKILL.md) and [share/agents/planner.agent.md](share/agents/planner.agent.md).
- Direct git diff output was not available in this tool surface, so the final diff scope was reconstructed from git-log evidence plus live artifact inspection. Small confidence deduction applied.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| P1 at [.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md#L28](.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md#L28) | [share/skills/w-task-decomposition/SKILL.md#L16](share/skills/w-task-decomposition/SKILL.md#L16) adds h-ac-quality in Step 0 and [share/skills/w-task-decomposition/SKILL.md#L75](share/skills/w-task-decomposition/SKILL.md#L75) makes it the authoritative checklist in Durability Principles | PASS |
| P2 consolidation-test rule at [.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md#L29](.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md#L29) | [share/skills/w-task-decomposition/SKILL.md#L150](share/skills/w-task-decomposition/SKILL.md#L150) defines the trigger and [share/skills/w-task-decomposition/SKILL.md#L152](share/skills/w-task-decomposition/SKILL.md#L152), [share/skills/w-task-decomposition/SKILL.md#L153](share/skills/w-task-decomposition/SKILL.md#L153), [share/skills/w-task-decomposition/SKILL.md#L154](share/skills/w-task-decomposition/SKILL.md#L154), [share/skills/w-task-decomposition/SKILL.md#L155](share/skills/w-task-decomposition/SKILL.md#L155) specify title pattern, tag, depends_on, and backlog status | PASS |
| P2 todo prohibition and routing defaults at [.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md#L30](.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md#L30) | [share/skills/w-task-decomposition/SKILL.md#L42](share/skills/w-task-decomposition/SKILL.md#L42) narrows preserved shortcut metadata to title, parent, and tags; [share/skills/w-task-decomposition/SKILL.md#L43](share/skills/w-task-decomposition/SKILL.md#L43) explicitly normalizes caller-requested todo; [share/skills/w-task-decomposition/SKILL.md#L146](share/skills/w-task-decomposition/SKILL.md#L146), [share/skills/w-task-decomposition/SKILL.md#L147](share/skills/w-task-decomposition/SKILL.md#L147), [share/skills/w-task-decomposition/SKILL.md#L148](share/skills/w-task-decomposition/SKILL.md#L148) preserve decomposition and shortcut defaults while keeping todo architect-gated | PASS |
| P2 planner agent wiring at [.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md#L31](.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md#L31) | [share/agents/planner.agent.md#L34](share/agents/planner.agent.md#L34) adds h-ac-quality to required reading and [share/agents/planner.agent.md#L42](share/agents/planner.agent.md#L42) adds the architect-only todo rule | PASS |
| P3 diff-verification requirement at [.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md#L32](.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md#L32) | Builder retry note at [.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md#L180](.owlbear/kanban/tasks/1405-a2-planner-skill-update-ac-drafting-via-h-ac-quality-consolidation-test-creation.md#L180) records final diff-scope verification; git-log evidence confirms retry commit 6065cb02 exists and the reviewed files are currently clean | PASS |

### Findings
- No issues found. The builder retry resolved the only prior review defect: the shortcut-mode status wording is now consistent with the Step 6 todo prohibition.

### Deductions
- 0.03: direct git diff output unavailable in the current tool surface; commit scope reconstructed from git-log evidence plus live artifact inspection.

### Verdict
- PASS -> docs
- Confidence: 0.95

### Action
- Advancing to docs.
[[2026-05-08]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed files are share/skills/w-task-decomposition/SKILL.md and share/agents/planner.agent.md — both OUT-of-scope agent-executables; no IN-scope README or setup guide references planner routing internals |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | Task body references no external repos, articles, or patterns |
| 4 | Research doc | Yes | Verified | .owlbear/research/planner-ac-quality-update.md exists on disk; linked from task body Research section; follow-up #1427 created |
| 5 | Diagram maintenance (describes match) | Yes | Updated | pipeline.excalidraw (describes: share/agents/*.agent.md) matches planner.agent.md; project-overview.excalidraw (describes: share/**) matches both changed files. Both footers updated to `Last verified: 2026-05-08 (ce95a391)` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| share/skills/w-task-decomposition/SKILL.md | OUT (agent-executable SKILL.md) | N/A |
| share/agents/planner.agent.md | OUT (agent-executable .agent.md) | N/A |
| share/diagrams/pipeline.excalidraw | IN (diagram) | Footer updated |
| share/diagrams/project-overview.excalidraw | IN (diagram) | Footer updated |

### Files Updated
- share/diagrams/pipeline.excalidraw (footer: 2026-05-05 → 2026-05-08 ce95a391)
- share/diagrams/project-overview.excalidraw (footer: c474918e → ce95a391, same date)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1405-* scratch files found)
[[2026-05-08]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| P1: h-ac-quality in Step 0 + Durability Principles | SKILL.md:16 (Step 0 guidance), SKILL.md:75 (authoritative checklist ref) | PASS |
| P2: Consolidation-test creation logic | SKILL.md:150 (trigger), :152-155 (title/tag/deps/status) | PASS |
| P2: todo prohibition + routing defaults | SKILL.md:42-43 (shortcut normalization), :146-148 (Step 6 prohibition) | PASS |
| P2: Planner agent wiring | planner.agent.md:34 (required_reading), :42 (critical_rules) | PASS |
| P3: Diff verification | Builder commits 9a9e5e10 + 6065cb02 confirmed in git log | PASS |

### Test Results
- pytest: 4845 passed, 229 failed, 4 skipped, 1 error — all failures pre-existing in unrelated modules (cockpit decisions, kanban engine, MCP memory, etc.); zero failures in task scope (markdown-only changes)
- ruff: 12 violations — all pre-existing in unrelated packages (knowledge, tools); none in task scope
- vitest: 1089 passed, 3 failed — all failures pre-existing (shell/health badge text mismatches)
- eslint: 4 violations — all pre-existing

### Architect Quality: 3/5
Three gaps required downstream correction: (1) missing consolidation-test tag spec caught by challenger, (2) ambiguous routing language caught by challenger, (3) shortcut-mode Step 1a/Step 6 contradiction left unresolved until reviewer first-pass fail. AC was adequate after refinement but the initial draft caused a full builder retry cycle.

### Deduction Breakdown
- -.03: AC quality ≤ 3 (three architect gaps required challenger + reviewer correction)

### Confidence: .97
### Action: archive