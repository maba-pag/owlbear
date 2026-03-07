---
id: 492
title: Improve bootstrap error reporting with structured startup summary
status: backlog
priority: important
created: 2026-03-04T07:38:07.6659001+01:00
updated: 2026-03-06T23:31:00.3431207+01:00
started: 2026-03-06T23:23:21.4960048+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

ARC-22/F-12/P-1: 30+ broad except Exception catches across bootstrap (6), ingest (5), tools (multiple). All silently continue at WARNING level. Misconfigured github_token or wrong DB path invisible to user. Emit structured startup summary listing loaded/failed toolsets. AC: user sees which toolsets loaded/failed at startup. See docs/architecture-audit.md, docs/code-quality-audit.md, docs/resilience-audit.md.
