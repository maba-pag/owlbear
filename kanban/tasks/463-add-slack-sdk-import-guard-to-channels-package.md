---
id: 463
title: Add slack_sdk import guard to channels package
status: ideation
priority: critical
created: 2026-03-04T07:37:43.9369413+01:00
updated: 2026-03-04T07:37:43.9369413+01:00
tags:
    - audit
    - bugfix
    - config
    - channels
class: standard
---

F-03(Config)/F-07(Docs): channels/slack.py imports slack_sdk at top level with no try/except guard. channels/__init__.py re-exports SlackChannel unconditionally. Any import of owlbear.channels crashes without slack_sdk. Fix: remove SlackChannel from __init__.py, add try/except ImportError guard in slack.py. AC: import owlbear.channels succeeds without slack_sdk. See docs/config-dependency-audit.md, docs/documentation-audit.md.
