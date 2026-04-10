---
id: 900
title: Add placeholder-task rejection rules to researcher and architect guidance
status: archived
priority: important
created: 2026-03-21T14:35:51.7705537+01:00
updated: 2026-03-21T15:23:23.4321898+01:00
tags:
    - agent
    - docs
    - scope:copilot
    - type:docs
blocked: true
block_reason: 'Split into #901, #902 - work tracked there'
class: standard
---

## Context

Research from docs/research/planner-temp-task-hygiene.md found that empty TEMP tasks can survive long enough to reach the research or architecture stages.

## Acceptance Criteria

- [ ] The researcher and/or architect guidance explicitly treats tasks with titles matching TEMP-* or with empty bodies as invalid inputs that must be blocked, refined, or archived instead of being converted into implementation scope.
- [ ] The rule states that missing scoped body content is a sufficient reason to refuse dispatch.
- [ ] The guidance includes a short handoff or note pattern that points back to the owning task or research note instead of inventing scope.
- [ ] One example in the guidance uses TEMP-planner-test as the rejected pattern.
- [ ] No src/ or tests/ files are modified.

## Research

- Doc: docs/research/placeholder-task-rejection-guidance.md
- Key finding: existing researcher and architect guidance blocks vague work in general but does not explicitly name `TEMP-*` or empty scoped bodies as invalid inputs.
- Key finding: the linked workflow skills are also silent on placeholder-task rejection, so agent-only edits would leave a prompt-drift gap.
- Key finding: GitHub and GitLab prior art favors required structured fields and disabling blank intake paths rather than allowing placeholder tickets.
- Recommendation (.94): update both agent files and both workflow skills; reject `TEMP-*` or empty scoped bodies and point back to the owning task or `docs/research/planner-temp-task-hygiene.md` instead of inventing scope.
- Follow-up task created: #901 Add placeholder-task rejection rules to researcher guidance.
- Follow-up task created: #902 Add placeholder-task rejection rules to architect guidance.
- Attribution: added GitHub issue forms, GitHub template chooser config, and GitLab description templates to docs/sources/overview.md.
- Executed command: `kanban\kanban-md.exe create "Add placeholder-task rejection rules to researcher guidance" --priority important --status ideation --tags "agent,docs,scope:copilot,type:docs"`
- Executed command: `kanban\kanban-md.exe create "Add placeholder-task rejection rules to architect guidance" --priority important --status ideation --tags "agent,docs,scope:copilot,type:docs"`

[[2026-03-21]] Sat 15:23

## Architecture Review

**Verdict:** SPLIT -> #901, #902

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| The researcher and/or architect guidance explicitly treats tasks with titles matching TEMP-* or with empty bodies as invalid inputs that must be blocked, refined, or archived instead of being converted into implementation scope. | Bundles two stage-specific agent and skill contracts and three different dispositions; `and/or` makes the contract non-verifiable. Researcher guidance and architect guidance have different refusal paths. | Split into #901 (researcher guidance) and #902 (architect guidance). |
| The rule states that missing scoped body content is a sufficient reason to refuse dispatch. | Correct invariant, but it must be expressed with the stage-specific behavior for each gate. | Preserve in both child tasks with stage-specific wording. |
| The guidance includes a short handoff or note pattern that points back to the owning task or research note instead of inventing scope. | Valid pattern, but the note belongs in each agent's own contract and example set rather than an umbrella card. | Preserve in both child tasks and point back to the owning task or docs/research/planner-temp-task-hygiene.md. |
| One example in the guidance uses TEMP-planner-test as the rejected pattern. | Verifiable shared example. | Keep in both child tasks. |
| No src/ or tests/ files are modified. | Correct scope guard for a guidance-only change. | Keep in both child tasks. |

### Architecture Notes

- `.github/agents/researcher.agent.md` and `.github/skills/research-workflow/SKILL.md` define the ideation -> backlog research contract. They currently require evidence-backed research and follow-up tasks, but they do not explicitly reject `TEMP-*` titles or empty scoped bodies as invalid inputs.
- `.github/agents/architect.agent.md` and `.github/skills/arch-review/SKILL.md` define the backlog gate, including split/refine/block behavior and the backlog -> ideation rejection path. That is a distinct contract from researcher refusal and handoff behavior.
- Because the two stages use different inputs, outputs, and rejection verbs, one umbrella backlog card invites prompt drift and ambiguous execution. The owning research in `docs/research/placeholder-task-rejection-guidance.md` already decomposed the work into the atomic follow-ups #901 and #902.
- TDD check: not applicable here because the child tasks are markdown-only guidance edits whose AC explicitly forbids `.py`, `.toml`, `src/`, and `tests/` changes.

### Changes Made

- Verified the current researcher and architect agent files plus the `research-workflow` and `arch-review` skills.
- Verified `docs/research/placeholder-task-rejection-guidance.md` already split the work into #901 and #902.
- Blocked #900 as the umbrella backlog card so execution is tracked on the split tasks instead of the combined scope.

### Dependencies

- Verified: #901 and #902 already exist as the correct atomic follow-ups for this research.
- Added/Removed: none.
- TDD: N/A for markdown-only guidance tasks.
