---
id: 491
title: Fix dual error handling on ON_ERROR events
status: ideation
priority: important
created: 2026-03-04T07:38:06.9326328+01:00
updated: 2026-03-04T07:38:06.9326328+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

ARC-21: EscalationHook and daemon _recover_from_error both handle errors, causing double user prompts. Hook runs first (inside turn()), then daemon recovery after exception propagates. Choose one authority. AC: user sees exactly one error prompt per failure. See docs/architecture-audit.md.
