---
id: 974
title: Add command-surface selection table to copilot-instructions.md
status: archived
priority: nice-to-have
created: 2026-03-24T01:20:02.30049+01:00
updated: 2026-03-24T02:53:52.7617871+01:00
started: 2026-03-24T02:53:52.7617871+01:00
completed: 2026-03-24T02:53:52.7617871+01:00
tags:
    - docs
    - scope:copilot
    - type:docs
parent: 942
class: standard
---

AC:

- Add a 'Command Surface Selection' section to .github/copilot-instructions.md with the when-to-use decision table from docs/research/prompt-vs-skill-vs-agent-rules.md section 3.2
- Include one OwlBear example per surface (prompt: orchestrate.prompt.md, skill: research-workflow/SKILL.md, agent: reviewer.agent.md)
- State default: user-facing one-shot commands use .prompt.md unless auto-load or co-located resources are needed
- Scope limited to copilot-instructions.md; do not rename or add commands

[[2026-03-24]] Tue 02:53

## Research

- Parent research: #942 (complete), doc: docs/research/prompt-vs-skill-vs-agent-rules.md

- Checklist: all 5 mandatory items validated. Trivial docs change; research already done by parent.

- Sources: 6 sources logged in docs/sources/overview.md (VS Code prompt/agent/skill/customization docs, OwlBear surfaces, #930 research)

- Examples verified: orchestrate.prompt.md, research-workflow/SKILL.md, reviewer.agent.md all exist in repo

- No new research doc needed; no additional follow-up tasks

- Implementation: add Command Surface Selection section to .github/copilot-instructions.md with table from research doc section 3.2, examples from 3.3, and default rule

- Risk: if VS Code merges prompt/skill surfaces, table needs update (small, in-place)

- Confidence: .90 (inherits from parent research)
