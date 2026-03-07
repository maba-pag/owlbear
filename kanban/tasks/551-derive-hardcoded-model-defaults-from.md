---
id: 551
title: Derive hardcoded model defaults from OwlBearSettings
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:54.1072462+01:00
updated: 2026-03-07T01:01:38.2528594+01:00
started: 2026-03-07T00:55:27.8475567+01:00
tags:
    - audit
    - config
    - scope:core
class: standard
---

INT-15: 'gpt-4o' hardcoded in 14 places (4 actionable, 10 docstrings/lookup tables). Research complete. See docs/hardcoded-model-defaults-research.md for full audit and recommendations. Summary: Remove redundant defaults from 3 bootstrap helpers + AgentRegistry.__init__, making chat_model/default_model required. Settings.chat_model is already the single source of truth at call sites.
