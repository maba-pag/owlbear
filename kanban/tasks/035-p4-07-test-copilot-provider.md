---
id: 35
title: 'P4-07: Test Copilot provider'
status: backlog
priority: high
created: 2026-02-24T15:16:21.1836537+01:00
updated: 2026-02-26T18:53:07.4136349+01:00
started: 2026-02-26T20:48:32.1143172+01:00
tags:
    - phase-4
    - test
    - agent
depends_on:
    - 32
    - 10
class: standard
---

AC: Create tests/test_providers/__init__.py and tests/test_providers/test_copilot.py. Test cases (minimum 5): (1) create_copilot_client returns AsyncOpenAI instance with correct base_url, (2) create_copilot_client sets Copilot-Integration-Id header, (3) create_copilot_client uses token from auth module (mock), (4) factory integrates with OwlBearSettings defaults, (5) factory raises clear error when token not found. All tests use unittest.mock. Files: tests/test_providers/__init__.py, tests/test_providers/test_copilot.py
