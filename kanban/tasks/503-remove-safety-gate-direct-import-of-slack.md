---
id: 503
title: Remove safety gate direct import of slack_templates
status: ideation
priority: important
created: 2026-03-04T07:38:16.0494432+01:00
updated: 2026-03-04T07:38:16.0494432+01:00
tags:
    - audit
    - architecture
    - safety
class: standard
---

INT-08: safety/gate.py has top-level import from channels.slack_templates. Creates coupling between safety and Slack. Move behind hasattr check with lazy import. AC: safety package works without slack_sdk. See docs/integration-audit.md.
