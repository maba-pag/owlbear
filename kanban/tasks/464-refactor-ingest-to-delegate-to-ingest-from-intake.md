---
id: 464
title: Refactor ingest() to delegate to _ingest_from_intake()
status: ideation
priority: needed
created: 2026-03-04T07:37:44.6993203+01:00
updated: 2026-03-04T07:37:44.6993203+01:00
tags:
    - audit
    - dry
    - refactor
    - knowledge
class: standard
---

DRY-10/F-05: ingest() reimplements ~70 lines of pipeline steps identical to _ingest_from_intake(). After intake+delta-check, ingest() should call _ingest_from_intake(). ingest_text() already follows this pattern. AC: ingest() delegates post-intake steps, no duplicated pipeline code. See docs/software-design-audit.md, docs/code-quality-audit.md.
