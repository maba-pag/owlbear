---
id: 567
title: Add dedup key to ErrorJournal entries
status: ideation
priority: someday
created: 2026-03-04T07:39:09.7566652+01:00
updated: 2026-03-04T07:39:09.7566652+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

I-3: ErrorJournal.log() append-only, no dedup key. Retry writes duplicate entries. Minor since journal not yet wired (see J-1 task). AC: duplicate entries prevented. See docs/resilience-audit.md.
