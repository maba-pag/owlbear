---
id: 542
title: Handle channel failure in daemon _recover_from_error
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:46.4992228+01:00
updated: 2026-03-04T07:38:46.4992228+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

CF-2: _recover_from_error sends error to channel. If channel is dead (Slack disconnected), channel.send raises. Chain: turn fails -> recovery fails -> loop continues silently. Errors disappear. AC: recovery handles channel failure with fallback logging. See docs/resilience-audit.md.
