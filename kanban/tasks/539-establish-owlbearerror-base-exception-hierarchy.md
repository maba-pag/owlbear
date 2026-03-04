---
id: 539
title: Establish OwlBearError base exception hierarchy
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:44.0984756+01:00
updated: 2026-03-04T07:38:44.0984756+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

E-1: Only 3 custom exceptions (BlockedCommandError, BlockedURLError, AskUserTimeoutError), no base class. Makes blanket catching difficult without except Exception. Create OwlBearError base class. AC: all custom exceptions inherit from OwlBearError. See docs/resilience-audit.md.
