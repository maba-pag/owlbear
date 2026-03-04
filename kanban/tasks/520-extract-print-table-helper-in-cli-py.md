---
id: 520
title: Extract _print_table helper in cli.py
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:29.4319581+01:00
updated: 2026-03-04T07:38:29.4319581+01:00
tags:
    - audit
    - dry
    - refactor
    - scope:cli
class: standard
---

DRY-04/F-03: Table formatting (col_widths, fmt, header, separator, rows) duplicated 3 times in cli.py. Extract _print_table(headers, rows) helper. AC: single implementation, 3 call sites use it. See docs/software-design-audit.md, docs/code-quality-audit.md.
