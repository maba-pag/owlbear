---
id: 567
title: Add dedup key to ErrorJournal entries
status: backlog
priority: someday
created: 2026-03-04T07:39:09.7566652+01:00
updated: 2026-03-07T04:35:25.8986217+01:00
started: 2026-03-07T04:35:02.5427717+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

I-3: ErrorJournal.log() append-only, no dedup key. Retry writes duplicate entries. Minor since journal not yet wired (see J-1 task). See docs/resilience-audit.md.

Research complete: See docs/research/error-journal-dedup.md. Recommendation: hash-based dedup_key (sha256[:16] of error_type+tool_name+exc_message) with 60s in-memory time-windowed cache. Confidence .80.

## AC

- [x] Research doc at docs/research/error-journal-dedup.md
- [x] Recommendation: hash-based dedup_key with 60s time-windowed cache (.80 confidence)
- [x] Follow-up implementation tasks created
