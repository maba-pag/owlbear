---
id: 465
title: Extract generic JsonlStore base class
status: ideation
priority: needed
created: 2026-03-04T07:37:45.4384051+01:00
updated: 2026-03-04T07:37:45.4384051+01:00
tags:
    - audit
    - dry
    - refactor
    - scope:core
class: standard
---

DRY-06: UsageTracker, EventStore, and ErrorJournal all implement identical append-only JSONL persistence (~40 lines each): append with mkdir+serialize+open('a'), load with exists+read_text+splitlines+deserialize, query with datetime cutoff. AC: generic JsonlStore[T] base class, all 3 stores inherit, no duplicated file I/O. See docs/software-design-audit.md.
