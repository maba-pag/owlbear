---
id: 170
title: Update stale agent path in agent-audit prompt
status: archived
priority: medium
created: 2026-03-29 19:49:39.629722+02:00
updated: 2026-03-30 15:36:02.082696+02:00
started: 2026-03-30 15:18:49.532401+02:00
completed: 2026-03-30 15:18:49.532401+02:00
tags:
- phase-1
- scope:docs
- type:docs
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Update stale .github/agents/ reference in agent-audit.prompt.md to point to agents/ at root.

## AC
- [ ] agent-audit.prompt.md L16: change .github/agents/*.agent.md to agents/*.agent.md
- [ ] Grep verify no remaining .github/agents/ references in prompt files

## Context
See docs/research/github-v1-cleanup.md sec 3.

[[2026-03-29]] Sun 20:47
## Research
N/A -- trivial path fix. Checklist 1-3: agents live at agents/ not .github/agents/ since #8.

### Duplicate
#170 duplicates #173 (identical title, AC, context). #173 already at backlog.

### Scope verification (AC2)
Grep confirmed: only 1 .github/agents/ ref in prompt files (agent-audit.prompt.md L16).

### Broader findings
Stale .github/agents/ refs not covered by existing tasks:
- skills/task-decomposition/SKILL.md L74, L87
- instructions/agent-common.instructions.md L113
- 4 v1-era test files

Follow-up tasks created:
- #187: Fix stale refs in skill/instruction files
- #188: Fix stale paths in v1-era test files

## Audit (manual archival 2026-03-30) Duplicate of #173 (archived at 1.0 confidence). Path fixed in commit 62da80f. Confidence 1.0.
