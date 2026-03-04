---
id: 548
title: Move BlockedCommandError to core/errors.py
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:51.556187+01:00
updated: 2026-03-04T07:38:51.556187+01:00
tags:
    - audit
    - architecture
    - scope:core
class: standard
---

INT-09: core/errors.py imports BlockedCommandError from command_guard. Inverted dependency -- errors module depends on command_guard. Move exception class to errors.py. AC: no circular/inverted dependency. See docs/integration-audit.md.
