---
id: 32
title: 'P4-04: Port Copilot provider integration'
status: done
priority: high
created: 2026-02-24T15:15:48.1667425+01:00
updated: 2026-02-26T22:17:39.7791924+01:00
started: 2026-02-26T21:21:58.9589216+01:00
completed: 2026-02-26T22:17:39.7791924+01:00
tags:
    - phase-4
    - auth
    - agent
depends_on:
    - 30
    - 7
class: standard
---

AC: Create src/owlbear/providers/copilot.py ported from Graphicator agent factory. Include: (1) create_copilot_client() that returns AsyncOpenAI with Copilot token as api_key, derived base_url, and Copilot-Integration-Id header, (2) Integration with owlbear.auth.copilot for token loading, (3) Integration with owlbear.config.OwlBearSettings for configuration, (4) Future extensibility point for LM Studio provider (just a comment/TODO, not implemented). Use openai SDK AsyncOpenAI. Type hints, from __future__ import annotations. File: src/owlbear/providers/copilot.py
