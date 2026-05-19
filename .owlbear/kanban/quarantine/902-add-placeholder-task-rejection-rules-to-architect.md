---
id: 902
title: Add placeholder-task rejection rules to architect guidance
status: archived
priority: important
created: 2026-03-21T14:44:50.1245242+01:00
updated: 2026-03-22T04:26:07.0007526+01:00
started: 2026-03-22T04:25:33.2316069+01:00
completed: 2026-03-22T04:25:33.2316069+01:00
tags:
    - agent
    - docs
    - scope:copilot
    - type:docs
class: standard
---

## Context

Update the architect role guidance so placeholder tasks are rejected instead of being refined into imagined implementation scope.
See docs/research/placeholder-task-rejection-guidance.md and docs/research/planner-temp-task-hygiene.md.

## Acceptance Criteria

- [ ] .github/agents/architect.agent.md explicitly treats titles matching TEMP-* as invalid backlog inputs.
- [ ] .github/skills/arch-review/SKILL.md explicitly treats empty or unscoped task bodies as sufficient reason to refuse dispatch.
- [ ] Guidance states that missing scoped body content alone is enough to block the task back to ideation instead of approving or refining invented scope.
- [ ] At least one example uses TEMP-planner-test and points back to the owning task or docs/research/planner-temp-task-hygiene.md.
- [ ] No .py, .toml, src/, or tests/ files are modified.

[[2026-03-21]] Sat 15:29

## Research

- Doc: docs/research/architect-placeholder-task-rejection-rules.md
- Key finding: #902 should stay a single architect-stage task; unlike the planner split, the architect agent file and arch-review skill define one backlog-gate contract and both need complementary rule text.
- Key finding: local evidence (#900, #695) plus external workflow-validation prior art all support rejecting placeholder or unscoped tasks at the gate instead of refining invented scope.
- Recommendation (.95): add the named TEMP-* invalid-input rule in .github/agents/architect.agent.md, add the empty/unscoped-body refusal path in .github/skills/arch-review/SKILL.md, and use TEMP-planner-test as the rejection example pointing to the owning task or docs/research/planner-temp-task-hygiene.md.
- Follow-up: no new kanban tasks created. #902 already is the concrete architect-stage follow-up created by #900; splitting agent and skill again would duplicate the same gate change.
- Attribution updated: docs/sources/overview.md

[[2026-03-21]] Sat 16:16

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| .github/agents/architect.agent.md explicitly treats titles matching TEMP-* as invalid backlog inputs. | Verifiable and correctly scoped to the architect role file. The current file has no explicit TEMP-* invalid-input rule today. | Keep. |
| .github/skills/arch-review/SKILL.md explicitly treats empty or unscoped task bodies as sufficient reason to refuse dispatch. | Verifiable and correctly scoped to the workflow skill. The current skill reads and refines tasks but does not explicitly reject empty or unscoped architect inputs. | Keep. |
| Guidance states that missing scoped body content alone is enough to block the task back to ideation instead of approving or refining invented scope. | Verifiable and aligned with the architect rejection path already defined in the agent guidance. The implementation should express this as a direct backlog -> ideation refusal rule, not soft prose. | Keep. |
| At least one example uses TEMP-planner-test and points back to the owning task or docs/research/planner-temp-task-hygiene.md. | Verifiable example anchored to the existing placeholder artifact in #855 and archived #856. | Keep. |
| No .py, .toml, src/, or tests/ files are modified. | Correct scope guard for a docs-only guidance change. | Keep. |

### Architecture Notes

- Single domain verified: this is one architect-gate contract spanning .github/agents/architect.agent.md and .github/skills/arch-review/SKILL.md, not planner, researcher, or runtime application work.
- Existing architect guidance currently has no explicit TEMP-*, placeholder, empty-body, or unscoped-body rejection rule, so the task closes a real gap rather than duplicating behavior.
- Placement contract: put the named invalid-input rule and the visible TEMP-planner-test example in .github/agents/architect.agent.md; put the fail-fast refusal path and explicit backlog -> ideation block for empty or unscoped bodies in .github/skills/arch-review/SKILL.md.
- Verified historical evidence: kanban task #855 TEMP-planner-test is a placeholder with no scoped body content, and docs/research/planner-temp-task-hygiene.md already defines the expected pointer back to the owning task or research note.
- TDD pairing: not required. This is a markdown-only guidance task whose AC explicitly forbids .py, .toml, src/, and tests/ changes.
- Security surface and failure mode map: not applicable; no new runtime codepaths or external boundaries are introduced.

### Changes Made

- Claimed #902 as architect-902.
- Verified docs/research/architect-placeholder-task-rejection-rules.md and docs/research/planner-temp-task-hygiene.md.
- Verified current architect guidance files and the TEMP-planner-test evidence before approval.
- Approved #902 for todo.

### Dependencies

- Verified: no code or RED-test predecessor is required for this docs-only guidance task.
- Verified evidence source: #855 TEMP-planner-test and docs/research/planner-temp-task-hygiene.md.
- Added/Removed: none.

[[2026-03-21]] Sat 17:12

## Test-Writer Notes

Non-implementation task (docs-only, tagged: agent, docs). The AC explicitly forbids .py, .toml, src/, and tests/ modifications — no testable code will be produced. Architecture review confirmed TDD pairing is not required. Passing through to builder.

[[2026-03-21]] Sat 23:15

## Builder Notes

- Files changed: .github/agents/architect.agent.md, .github/skills/arch-review/SKILL.md
- Tests: N/A (docs-only task; no .py, .toml, src/, or tests/ files modified)
- Lint: N/A (markdown only)
- Evidence: commit 98faf40 — 2 files changed, 9 insertions
- Fixes applied: Added TEMP-*invalid-input rule + empty/unscoped body block rule to critical_rules in architect.agent.md; added TEMP-* red flag and failure rationalization row to boundaries; added Step 1 placeholder rejection check and Step 4 placeholder block path note to arch-review/SKILL.md; TEMP-planner-test example with pointer to docs/research/planner-temp-task-hygiene.md in both files.

[[2026-03-21]] Sat 23:47

## Review Evidence

## Review: #902 - Add placeholder-task rejection rules to architect guidance

### Test Results

- `uv run pytest tests/test_agent_definitions.py tests/test_agent_def.py -q --tb=short` -> 96 passed, 0 failed, 2 warnings.
- Warnings are optional dependency skips from `tests/conftest.py` (`qdrant_client` not installed).

### Lint Results

- `uv run ruff check tests/test_agent_definitions.py tests/test_agent_def.py` -> All checks passed.
- `uv run ruff check src/ tests/` -> 451 errors in unrelated files (existing repo-wide baseline debt, not introduced by #902).

### Coverage

- Not applicable: docs-only task; no Python source was modified.

### Pass 1 - CRITICAL

#### Security Review

- No security issues found. Changes are instruction/skill markdown updates only.

#### Test Integrity (TestFromAC comparison)

- Not applicable for this task: no TestFromAC classes are associated with #902 and builder commit `98faf40` modifies only `.github/agents/architect.agent.md` and `.github/skills/arch-review/SKILL.md`.

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | N/A | Docs-only task; no new runtime tests required by AC. |
| Negative/error paths | N/A | Docs-only task; AC is policy text verification. |
| Mutation reasoning | N/A | Behavior is governed by static agent/skill instructions. |
| Test independence | N/A | Docs-only task; no task-specific test authoring. |
| Descriptive names | N/A | Docs-only task; no task-specific test authoring. |

#### Data Safety

- No data safety issues found. No data handling or persistence code changed.

### Pass 2 - INFORMATIONAL

- Repo-wide ruff currently has unrelated failures in many existing test files; scoped lint used for this review is clean.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `.github/agents/architect.agent.md` explicitly treats titles matching `TEMP-*` as invalid backlog inputs | `.github/agents/architect.agent.md:42` adds explicit `TEMP-*` invalid-input rule and ideation block behavior. | N/A (static instruction text) | PASS |
| `.github/skills/arch-review/SKILL.md` explicitly treats empty or unscoped task bodies as sufficient reason to refuse dispatch | `.github/skills/arch-review/SKILL.md:35` adds explicit reject-placeholder/unscoped-body rule; `.github/skills/arch-review/SKILL.md:91` reinforces entry-condition failure. | N/A (static skill text) | PASS |
| Guidance states missing scoped body content alone is enough to block back to ideation instead of approving/refining invented scope | `.github/agents/architect.agent.md:43` and `.github/skills/arch-review/SKILL.md:91` explicitly require blocking to ideation and prohibit inventing AC. | N/A (static instruction text) | PASS |
| At least one example uses `TEMP-planner-test` and points back to the owning task or `docs/research/planner-temp-task-hygiene.md` | `.github/agents/architect.agent.md:42` and `.github/skills/arch-review/SKILL.md:91` both include `TEMP-planner-test` and reference `docs/research/planner-temp-task-hygiene.md` / owning task guidance. | N/A (static example text) | PASS |
| No `.py`, `.toml`, `src/`, or `tests/` files are modified | `git show --name-status --stat 98faf40` lists only `.github/agents/architect.agent.md` and `.github/skills/arch-review/SKILL.md`. | N/A (commit scope verification) | PASS |

### Verdict: PASS

- Confidence: .95

### Action Taken

- Appended review evidence to task body.

[[2026-03-22]] Sun 00:15

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Agent guidance files are self-contained; copilot-instructions.md does not enumerate per-agent critical rules |
| 2 | Docstrings complete | No | N/A | No .py files modified (docs-only task, AC explicitly forbids src/ changes) |
| 3 | sources/overview.md | Yes | Pass | Section '## Architect Placeholder Rejection Rules (Task #902)' at line 143 with 4 attribution rows already present |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc linked | Yes | Pass | docs/research/architect-placeholder-task-rejection-rules.md exists and linked in task body |
| 6 | No impact default | N/A | N/A | Items 3+5 did apply; all verified present |

### Files Updated

- None (all required docs were already updated by researcher/builder)

### Scratch Files Cleaned

- None (no docs/scratch/902-* files found)

[[2026-03-22]] Sun 04:26

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 76d3c2b | chore | kanban/tasks/902-*.md | #902 |
