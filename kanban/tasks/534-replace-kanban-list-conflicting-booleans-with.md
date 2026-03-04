---
id: 534
title: Replace kanban_list conflicting booleans with block_filter enum
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:39.627003+01:00
updated: 2026-03-04T07:38:39.627003+01:00
tags:
    - audit
    - code-quality
    - tools
class: standard
---

F-24: kanban_list has blocked/not_blocked/unblocked as 3 mutually exclusive booleans. LLM may set conflicting flags. Replace with single block_filter: Literal['blocked','not_blocked','unblocked'] | None. AC: single filter param, no conflicts. See docs/code-quality-audit.md.
