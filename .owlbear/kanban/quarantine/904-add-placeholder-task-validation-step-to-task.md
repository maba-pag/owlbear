---
id: 904
title: Add placeholder-task validation step to task-decomposition skill
status: archived
priority: important
created: 2026-03-21T14:47:39.6727589+01:00
updated: 2026-03-22T18:35:49.1144093+01:00
started: 2026-03-22T18:35:21.8005484+01:00
completed: 2026-03-22T18:35:21.8005484+01:00
tags:
    - agent
    - docs
    - scope:copilot
    - type:docs
depends_on:
    - 903
class: standard
---

Source: docs/research/planner-placeholder-guardrails.md

Mirror the canonical placeholder-task rule from .github/agents/kanban-planner.agent.md inside .github/skills/task-decomposition/SKILL.md. This task is limited to that skill file and must not change runtime code, tests, or any other agent or skill file.

AC:

- [ ] A workflow step immediately before command generation in .github/skills/task-decomposition/SKILL.md adds a fail-fast validation check before any `kanban-md create` commands are emitted.
- [ ] That validation text explicitly rejects planned task titles that start with TEMP- and uses TEMP-planner-test as the rejected example.
- [ ] That validation text explicitly rejects task bodies that are empty after frontmatter or that lack scoped task content or concrete acceptance criteria.
- [ ] The same validation text instructs the planner to refine the task or stop instead of emitting a `kanban-md create` command or leaving a placeholder board artifact.
- [ ] The skill text points back to .github/agents/kanban-planner.agent.md as the canonical placeholder-task rule rather than redefining policy in the skill.
- [ ] The task-decomposition self-critique checklist adds a final check that no placeholder task command is emitted.
- [ ] File scope stays limited to .github/skills/task-decomposition/SKILL.md.

[[2026-03-22]] Sun 00:24

## Research

- Doc: docs/research/planner-skill-placeholder-validation.md
- Verified #903 is archived, so the canonical placeholder-task rule already lives in .github/agents/kanban-planner.agent.md; #904 should stay scoped to .github/skills/task-decomposition/SKILL.md.
- Recommendation (.95): add a fail-fast validation step plus self-check or red-flag reinforcement in the skill, explicitly reject TEMP-* titles and empty or unscoped bodies, tell the planner to refine the task or stop, use TEMP-planner-test as the visible example, and point back to .github/agents/kanban-planner.agent.md as the canonical rule.
- Follow-up task commands executed: none. The action split already exists as #903 and #904, and #903 is archived, so creating duplicate ideation tasks would add board noise.
- Attribution updated: docs/sources/overview.md.

[[2026-03-22]] Sun 04:21

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| A workflow step immediately before command generation in .github/skills/task-decomposition/SKILL.md adds a fail-fast validation check before any `kanban-md create` commands are emitted. | The previous wording allowed a checklist-only interpretation. The task-decomposition skill is structured as ordered workflow steps plus a self-critique checklist, so the contract must require pre-output validation in the procedural path. | Rewritten to require an explicit workflow-step guard before command generation. |
| That validation text explicitly rejects planned task titles that start with TEMP- and uses TEMP-planner-test as the rejected example. | Verifiable and aligned with the canonical planner-agent rule already landed in #903 and the historical placeholder artifacts in #855 and #856. | Keep. |
| That validation text explicitly rejects task bodies that are empty after frontmatter or that lack scoped task content or concrete acceptance criteria. | Verifiable and consistent with the existing planner red-flag language for empty or placeholder bodies, but tightened here to match the placeholder-task research more precisely. | Keep. |
| The same validation text instructs the planner to refine the task or stop instead of emitting a `kanban-md create` command or leaving a placeholder board artifact. | This is the binding control-flow requirement. Without it, the builder could add descriptive prose without actually preventing placeholder output. | Keep. |
| The skill text points back to .github/agents/kanban-planner.agent.md as the canonical placeholder-task rule rather than redefining policy in the skill. | Correct source-of-truth boundary. #903 established the agent file as canonical; #904 should mirror behavior procedurally, not create a competing policy definition. | Keep. |
| The task-decomposition self-critique checklist adds a final check that no placeholder task command is emitted. | Research for #904 recommends a final self-check in addition to the fail-fast step to defend against prompt drift or partial edits. | Added. |
| File scope stays limited to .github/skills/task-decomposition/SKILL.md. | Correct scope guard for a docs-only agent-config task. It prevents spillover into the already-archived canonical agent rule or unrelated runtime files. | Keep. |

### Architecture Notes

- Single domain verified: this task changes one agent-config skill file under .github/skills/ and does not cross into runtime code, tests, or shared instructions.
- Existing pattern verified: .github/skills/task-decomposition/SKILL.md is organized as ordered workflow steps plus a self-critique checklist, while .github/agents/kanban-planner.agent.md holds the canonical hard rule. The right mirror is a fail-fast procedural step plus a checklist backstop.
- Dependency verified: #903 is archived and already listed in depends_on, so the canonical rule exists before this mirror task advances.
- TDD pairing: not required. This is a markdown-only docs task with explicit file-scope limits and no runtime codepath changes.
- Security surface and failure mode map: not applicable; the task changes guidance text only and introduces no new execution boundary.

### Changes Made

- Claimed #904 as architect-904.
- Rewrote the task body so the builder contract requires both the pre-output validation step and the final self-critique guard.
- Verified .github/skills/task-decomposition/SKILL.md, .github/agents/kanban-planner.agent.md, docs/research/planner-placeholder-guardrails.md, and docs/research/planner-skill-placeholder-validation.md before approval.
- Approved #904 for todo.

### Dependencies

- Verified: #903 is archived and already wired via depends_on.
- Verified: no RED-test predecessor is required for this docs-only agent-config task.
- Added/Removed: none.

[[2026-03-22]] Sun 17:09

## Test-Writer Notes

- Non-implementation task (tagged type:docs) — no tests applicable.
- Architecture review explicitly states: 'TDD pairing: not required. This is a markdown-only docs task.'
- File scope limited to .github/skills/task-decomposition/SKILL.md (agent-config markdown only).
- Passing through to builder.

[[2026-03-22]] Sun 17:33

## Builder Notes

- Files changed: .github/skills/task-decomposition/SKILL.md only
- Added Step 5a (fail-fast validation) immediately before Step 6 (Generate commands)
- Rejects TEMP- titles (TEMP-planner-test as example) and empty/unscoped bodies
- Instructs planner to refine or stop, not emit kanban-md create for placeholders
- Points back to .github/agents/kanban-planner.agent.md as canonical policy source
- Self-critique checklist: added final item for no placeholder task commands
- No runtime code, tests, or other files touched (docs-only, type:docs)
- Commit: ddcefd2

[[2026-03-22]] Sun 17:47

## Review Evidence

## Review: #904 - Add placeholder-task validation step to task-decomposition skill

### Test Results

- uv run pytest tests/test_agent_definitions.py -q --tb=short -> 84 passed, 0 failed (2 optional-dependency warnings).
- uv run pytest tests/test_skills.py -q --tb=short -> 30 passed, 3 failed.
- Failing tests are all in TestFromAC_RealSkillsDiscovery and assert a stale hard-coded count (expected 19 skills, discovered 20). This appears unrelated to #904 because builder commit ddcefd2 modifies only one existing skill file and does not add/remove skill files.

### Lint Results

- uv run ruff check src/ tests/ -> fails with broad pre-existing/test-suite-wide docstring and noqa debt (RUF100, D205, D209, D403, etc.).
- uv run ruff check src/owlbear/core/agent_def.py src/owlbear/core/agent_registry.py tests/test_agent_definitions.py -> All checks passed.

### Coverage

- Not applicable for #904: docs-only skill-file change (.github/skills/task-decomposition/SKILL.md), no runtime Python module changes.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

- Not applicable. #904 is a docs-only skill-contract task and task notes already mark tests as not required for implementation.

#### Security Review

- No security issues found. Change is constrained to skill guidance text and does not alter runtime code paths, dependencies, or execution boundaries.

#### Test Integrity

- No TestFromAC_* classes were introduced or modified by this task.

#### Test Quality

- Not applicable for this docs-only task.

#### Data Safety

- No data-safety issues found. No persistence, concurrency, or I/O logic changed.

#### Implementation-Aware Test Gaps

- Not applicable for this docs-only task.

### Pass 2 - INFORMATIONAL

- ests/test_skills.py currently contains a stale expected skills count (19 vs discovered 20). This is unrelated to #904 scope, but should be corrected in a separate task to keep skill-regression tests trustworthy.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Add fail-fast validation step immediately before command generation in task-decomposition skill | Step 5a inserted directly before Step 6 - Generate commands at .github/skills/task-decomposition/SKILL.md:70 | N/A (docs contract) | PASS |
| Validation rejects planned task titles starting with TEMP- and uses TEMP-planner-test example | Explicit bullet at .github/skills/task-decomposition/SKILL.md:77 includes TEMP-planner-test | N/A (docs contract) | PASS |
| Validation rejects task bodies empty after frontmatter or lacking scoped content/concrete AC | Explicit bullet at .github/skills/task-decomposition/SKILL.md:79 | N/A (docs contract) | PASS |
| Validation instructs planner to refine/stop instead of emitting placeholder kanban-md create command or leaving placeholder artifact | Explicit fail-fast instruction at .github/skills/task-decomposition/SKILL.md:82 and .github/skills/task-decomposition/SKILL.md:83 | N/A (docs contract) | PASS |
| Skill text points to .github/agents/kanban-planner.agent.md as canonical placeholder-task rule source | Policy-source pointer at .github/skills/task-decomposition/SKILL.md:86 | N/A (docs contract) | PASS |
| Self-critique checklist includes final check for no placeholder task command emission | Final checklist line at .github/skills/task-decomposition/SKILL.md:125 | N/A (docs contract) | PASS |
| File scope limited to .github/skills/task-decomposition/SKILL.md | git show --stat ddcefd2 reports: 1 file changed, .github/skills/task-decomposition/SKILL.md only | N/A (scope check) | PASS |

### Verdict: PASS

- Confidence: .93

### Action Taken

- Append review evidence and advance to docs gate.

[[2026-03-22]] Sun 17:58

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Skill-internal workflow step only; no behavior, API, or convention change documented in copilot-instructions.md |
| 2 | Docstrings | No | N/A | docs-only task; no Python files changed |
| 3 | docs/sources/overview.md | Yes | Pass | Section 'Planner Skill Placeholder Validation (Task #904)' already present (lines 1800-1807) with 4 attribution rows added by researcher |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc linked | Yes | Pass | docs/research/planner-skill-placeholder-validation.md exists; linked in task body Source field |
| 6 | No impact | N/A | N/A | Items 1-5 covered above |

### Files Updated

- None (no documentation updates required; sources/overview.md already updated by researcher)

### Scratch Files Cleaned

- docs/scratch/904-architect-body.tmp (deleted)
- docs/scratch/904-architect-review.tmp (deleted)

[[2026-03-22]] Sun 18:35

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Fail-fast validation step before command generation | Step 5a at SKILL.md:68-88, directly before Step 6 | PASS |
| Rejects TEMP- titles with TEMP-planner-test example | Explicit bullet at SKILL.md:77 | PASS |
| Rejects empty/unscoped bodies | Explicit bullet at SKILL.md:79 | PASS |
| Instructs to refine/stop instead of emitting create | Fail-fast instruction at SKILL.md:82-83 | PASS |
| Points to kanban-planner.agent.md as canonical source | Policy-source blockquote at SKILL.md:86-88 | PASS |
| Self-critique checklist adds placeholder check | Final checklist item at SKILL.md:125 | PASS |
| File scope limited to SKILL.md | git log confirms ddcefd2 changes 1 file only | PASS |

### Test Results

- pytest: 3751 passed, 109 failed (all pre-existing: numpy compat, condenser unpacking, frontend design skill, intent routing), 20 skipped. No failures attributable to #904.
- ruff: 448 pre-existing errors (RUF100, D205, D209, D403). No new lint issues from docs-only change.

### Upstream Commit Verified

- ddcefd2 docs: add placeholder-task validation step to task-decomposition skill (#904, builder)

### Architect Quality

- AC specificity: 7 concrete, verifiable items with no vague criteria
- Edge case coverage: no gaps discovered by builder or reviewer
- Design direction: single-file docs-only scope was correct and efficient
- AC quality score: 5/5

### Confidence: .97

### Action: archive

[[2026-03-22]] Sun 18:35

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 303c8d1 | chore | kanban/tasks/904-*.md | #904 |
