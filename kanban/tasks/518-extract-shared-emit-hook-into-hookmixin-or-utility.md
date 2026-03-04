---
id: 518
title: Extract shared _emit_hook into HookMixin or utility
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:28.1302217+01:00
updated: 2026-03-04T07:38:28.1302217+01:00
tags:
    - audit
    - dry
    - refactor
    - tools
class: standard
---

DRY-02/F-10: _emit_hook identical 4-line method in git_local.py, kanban.py, github_api.py. Extract HookMixin or module-level emit_pre_tool_use() utility. AC: single implementation, all toolsets use it. See docs/software-design-audit.md, docs/code-quality-audit.md.
