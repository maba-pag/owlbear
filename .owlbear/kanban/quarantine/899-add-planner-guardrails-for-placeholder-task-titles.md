---
id: 899
title: Add planner guardrails for placeholder task titles and empty bodies
status: archived
priority: important
created: 2026-03-21T14:35:45.3156429+01:00
updated: 2026-03-22T19:10:19.4816438+01:00
started: 2026-03-22T19:10:19.4816438+01:00
completed: 2026-03-22T19:10:19.4816438+01:00
tags:
    - agent
    - docs
    - scope:copilot
    - type:docs
blocked: true
block_reason: 'Split into #903, #904 - work tracked there'
class: standard
---

## Context

Research from docs/research/planner-temp-task-hygiene.md found that #855 and archived duplicate #856 are placeholder TEMP tasks with no scoped body content.

## Acceptance Criteria

- [ ] The planner guidance in .github/agents/kanban-planner.agent.md and/or the related planning skill explicitly forbids emitting tasks whose title starts with TEMP-.
- [ ] The same guidance explicitly forbids emitting tasks whose body is empty after frontmatter or otherwise lacks scoped task content.
- [ ] The guidance tells the planner to refine the task or stop instead of leaving a placeholder board artifact.
- [ ] One example in the guidance uses TEMP-planner-test as the rejected pattern.
- [ ] No src/ or tests/ files are modified.

[[2026-03-21]] Sat 14:48

## Research | Doc: docs/research/planner-placeholder-guardrails.md | Summary: Local planner guidance, prior placeholder evidence (#855/#856), and external intake-validation prior art all point to the same structure: keep the canonical placeholder rejection rule in kanban-planner.agent.md and mirror it in task-decomposition so placeholder titles and empty or scopeless bodies are rejected before task output. Recommendation (.92): use a prompt task plus a dependent skill task rather than a shared-instructions change. | Follow-up created: #903 Add placeholder-task rejection rules to kanban-planner.agent.md; #904 Add placeholder-task validation step to task-decomposition skill. | Commands executed: kanban\\kanban-md.exe create 'Add placeholder-task rejection rules to kanban-planner.agent.md' --priority important --status ideation --tags 'agent,docs,scope:copilot,type:docs' -> #903; kanban\\kanban-md.exe create 'Add placeholder-task validation step to task-decomposition skill' --priority important --status ideation --tags 'agent,docs,scope:copilot,type:docs' --depends-on 903 -> #904. | Attribution updated: docs/sources/overview.md

[[2026-03-21]] Sat 15:22

## Architecture Review

**Verdict:** SPLIT -> #903, #904

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| The planner guidance in .github/agents/kanban-planner.agent.md and/or the related planning skill explicitly forbids emitting tasks whose title starts with TEMP-. | The and/or wording is ambiguous and spans two distinct guidance surfaces. Repo pattern and research both place the canonical rule in kanban-planner.agent.md and the mirrored procedural check in task-decomposition. | Split execution across #903 and #904 instead of routing this umbrella card. |
| The same guidance explicitly forbids emitting tasks whose body is empty after frontmatter or otherwise lacks scoped task content. | Same structural issue: this belongs in both the planner prompt contract and the decomposition checklist, not as one combined implementation unit. The live planner agent already has adjacent quality rules but no explicit TEMP or scopeless-body rejection. | Track the canonical rule in #903 and the mirrored validation step in #904. |
| The guidance tells the planner to refine the task or stop instead of leaving a placeholder board artifact. | Correct invariant, but it must be enforced at both the canonical guidance layer and the procedural self-check layer. | Preserve this stop or refine behavior in both child tasks. |
| One example in the guidance uses TEMP-planner-test as the rejected pattern. | Verifiable and useful, but still part of the split canonical-plus-mirror structure recommended by the research. | Require the example in the child tasks rather than keeping it on the umbrella. |
| No src/ or tests/ files are modified. | Valid scope constraint. This is a docs or agent-config change only, not application code. | Preserve as a binding invariant on #903 and #904. |

### Architecture Notes

- .github/agents/kanban-planner.agent.md is the canonical home for planner constraints today: critical_rules, boundaries, examples, and self-critique all live there.
- .github/skills/task-decomposition/SKILL.md is the procedural checklist. It currently has no placeholder-title or empty-body validation step, so the mirror belongs there as a separate follow-up.
- The research doc and prior planner-quality precedent in docs/research/task-decomposition-rules.md and #694 use the same pattern: canonical rule in the agent file, mirrored enforcement in the supporting skill.
- Single-domain check passes at the repo level because all affected files sit in agent-config, but #899 is still non-atomic because it bundles two file-specific contracts with an explicit dependency chain already captured as #903 -> #904.
- TDD check is not applicable here because the AC explicitly limits scope to markdown guidance files and forbids src or tests edits.

### Changes Made

- Claimed #899 as architect-899.
- Appended this Architecture Review section.
- Blocked #899 as the umbrella so follow-up work is tracked on #903 and #904.

### Dependencies

- Verified: #903 exists for the canonical kanban-planner.agent.md rule.
- Verified: #904 exists for the mirrored task-decomposition skill validation.
- Verified: #904 already depends on #903.
