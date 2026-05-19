---
id: 1675
title: 'Storage repair: 606-update-mcp-kanban-path-resolution-for-owlbear.md'
status: done
priority: important
created: 2026-05-19T12:38:16.786988+02:00
updated: 2026-05-19T12:48:36.713856+02:00
tags:
  - type:user-action
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Quarantined file

- code: ERR_CORRUPT_ENCODING
- path: /Users/markus/Projects/owlbear-dev/.owlbear/kanban/quarantine/606-update-mcp-kanban-path-resolution-for-owlbear.md
- detail: quarantined to /Users/markus/Projects/owlbear-dev/.owlbear/kanban/quarantine/606-update-mcp-kanban-path-resolution-for-owlbear.md

[[2026-05-19T12:48:36+02:00]]
## Research

**Diagnosis:** 2 archived task files (606, 608) contained Windows-1252 em-dash/en-dash bytes (0x96, 0x97) in otherwise UTF-8 content. The kanban engine's corruption checker correctly flagged them as ERR_CORRUPT_ENCODING and quarantined them.

**Root cause:** Isolated CP1252 bytes from early pipeline output (April 2026). Only 2 of 600+ archived tasks affected — one-time occurrence, no systemic issue.

**Repair:** Transcoded corrupt bytes to proper UTF-8 em-dash (U+2014) / en-dash (U+2013). Files restored to archive/. Also fixed sibling #1676 (same issue).

**Prevention:** Existing corruption detection in `serve/kanban/src/owlbear_kanban/corruption.py` is adequate. No follow-up tasks needed.

Commit: 4706e13d
