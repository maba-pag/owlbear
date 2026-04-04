---
id: 591
title: Add PreToolUse path guard hook to doc-writer agent (Phase 5)
status: ideation
priority: someday
created: 2026-04-04T07:56:05.2542536+02:00
updated: 2026-04-04T07:56:05.2542536+02:00
tags:
    - scope:agents
    - hooks
    - type:build
depends_on:
    - 589
class: standard
---

## Context
See docs/research/agent-scoped-hooks.md §3.1 and §3.3 for guard catalog and boundary analysis.
Phase 5 of VS Code agent-scoped hooks adoption. Doc-writer should not write to packages/ (source code). Reuses the deny-src-writes.ps1 script from Phase 3 (#589).

## Acceptance Criteria
- [ ] Add PreToolUse hook to agents/doc-writer.agent.md frontmatter: type: command, command: key pointing to scripts/hooks/deny-src-writes.ps1
- [ ] Reuses existing deny-src-writes.ps1 from #589 (no new script needed)
- [ ] Agent file parses as valid YAML frontmatter
- [ ] Depends on: #589
