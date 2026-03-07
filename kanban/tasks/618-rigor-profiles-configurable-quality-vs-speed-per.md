---
id: 618
title: 'Rigor profiles: configurable quality-vs-speed per task type'
status: backlog
priority: important
created: 2026-03-07T05:20:49.5381093+01:00
updated: 2026-03-07T06:31:08.0652413+01:00
started: 2026-03-07T06:31:08.0652413+01:00
tags:
    - scope:core
    - config
class: standard
---

Add rigor profile system to owlbear.toml with presets (lean/standard/thorough). Profile controls: review enabled, TDD depth, turn budget. Read at bootstrap, passed into agent deps. See docs/orchestration-agent-frameworks-research.md S3.2 and docs/nwave-research.md S3.3

AC:
- [ ] 3 preset profiles in config (lean/standard/thorough)
- [ ] Per-task override via kanban tag (rigor:lean, rigor:thorough)
- [ ] Profile affects turn budget and review gate
- [ ] Default profile: standard

Architecture notes:
- Extends OwlBearSettings (pydantic-settings)
- Consumed by orchestrator when dispatching agents
- Follows existing config patterns in config.py
