---
id: 855
title: TEMP-planner-test
status: archived
priority: someday
created: 2026-03-18T14:04:09.6188581+01:00
updated: 2026-03-22T19:17:54.9576748+01:00
started: 2026-03-22T19:17:54.9576748+01:00
completed: 2026-03-22T19:17:54.9576748+01:00
blocked: true
block_reason: 'Placeholder task: TEMP-* title with no scoped body or verifiable AC; use follow-up tasks #899 and #900 for actual remediation.'
class: standard
---

[[2026-03-21]] Sat 14:37

## Research

Doc: docs/research/planner-temp-task-hygiene.md

Summary: #855 is a TEMP placeholder with no scoped body content; archived #856 is a duplicate of the same pattern. Recommendation (.93): treat #855 as board-noise evidence, not feature scope, and keep it out of builder flow.

Follow-up created: #899 Add planner guardrails for placeholder task titles and empty bodies; #900 Add placeholder-task rejection rules to researcher and architect guidance.

Commands executed: kanban\\kanban-md.exe create 'Add planner guardrails for placeholder task titles and empty bodies' --priority important --status ideation --tags 'agent,docs,scope:copilot,type:docs' -> #899; kanban\\kanban-md.exe create 'Add placeholder-task rejection rules to researcher and architect guidance' --priority important --status ideation --tags 'agent,docs,scope:copilot,type:docs' -> #900.

Attribution updated: docs/sources/overview.md

[[2026-03-22]] Sun 17:45

## Architecture Review

**Verdict:** Block

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Title `TEMP-planner-test` | Placeholder title; not legitimate executable scope under placeholder-task rejection rules | Block to ideation |
| Body / AC | No scoped body content or verifiable acceptance criteria exist; only a historical research note is present | Block to ideation |
| Research handoff | [docs/research/planner-temp-task-hygiene.md](docs/research/planner-temp-task-hygiene.md) explicitly treats #855 as board-noise evidence and routes real remediation into follow-up tasks #899 and #900 | Keep #855 out of builder flow |

### Architecture Notes

This task is invalid input for the backlog -> todo gate. Architect rules require immediate rejection of `TEMP-*` placeholders and empty or unscoped bodies instead of inventing implementation scope. There is no single-domain implementation contract here, no testable AC to bind a builder, and no valid RED predecessor to pair with implementation work. The correct architectural action is to return the task to `ideation` as blocked evidence while the actual guardrail work proceeds on the dedicated follow-up tasks.

### Changes Made

- Claimed task with `kanban\\kanban-md.exe edit 855 --claim architect-855`
- Appended this architecture review section
- Prepared task for `backlog -> ideation` rejection with a placeholder-input block reason

### Dependencies

- Verified: no implementation dependency analysis needed because the task is a placeholder artifact, not executable work
- Verified: follow-up remediation was already created in research as #899 and #900
