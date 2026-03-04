---
id: 551
title: Derive hardcoded model defaults from OwlBearSettings
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:54.1072462+01:00
updated: 2026-03-04T07:38:54.1072462+01:00
tags:
    - audit
    - config
    - scope:core
class: standard
---

INT-15: 'gpt-4o' hardcoded in 3+ places (bootstrap, agent_registry). Should derive from OwlBearSettings.chat_model. AC: single source of truth for default model. See docs/integration-audit.md.
