---
id: 531
title: Add TypedDict for tool_stats return type
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:36.8877228+01:00
updated: 2026-03-04T07:38:36.8877228+01:00
tags:
    - audit
    - code-quality
    - scope:core
class: standard
---

F-14: tool_stats returns dict[str, dict] but inner dict has specific keys (call_count, error_count, avg_duration_ms). Define ToolStats TypedDict. AC: typed return value, key typos caught by Pylance. See docs/code-quality-audit.md.
