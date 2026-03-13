---
id: 560
title: Rename ks_ CLI functions to full knowledge_source_ prefix
status: backlog
priority: someday
created: 2026-03-04T07:39:03.1672553+01:00
updated: 2026-03-07T02:26:30.7539514+01:00
started: 2026-03-07T02:20:42.6453801+01:00
tags:
    - audit
    - naming
    - scope:cli
class: standard
---

## Research Findings

See docs/research/ks-rename.md. Rename confirmed as correct approach (.85 confidence).

### Scope

- 4 function renames in src/bearclaw/cli.py (internal Python names only)
- CLI command names unchanged (users still type `bearclaw knowledge-source add`)
- Zero test changes expected (tests invoke via CLI string, not function name)
- Interacts with #481 (CLI split) but no blocking dependency

## Acceptance Criteria

- [ ] Rename ks_add -> knowledge_source_add
- [ ] Rename ks_list -> knowledge_source_list
- [ ] Rename ks_show -> knowledge_source_show
- [ ] Rename ks_remove -> knowledge_source_remove
- [ ] CLI command names unchanged (add, list, show, remove)
- [ ] All tests pass (no test changes expected)
- [ ] ruff clean
- [ ] Update docs/code-quality-audit.md F-17 as resolved
