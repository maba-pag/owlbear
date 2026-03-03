---
id: 419
title: Unit tests for Slack interactive features
status: archived
priority: important
created: 2026-03-01T20:21:01.0436377+01:00
updated: 2026-03-03T15:02:59.0415826+01:00
started: 2026-03-01T20:24:10.8131551+01:00
completed: 2026-03-03T15:02:59.0415826+01:00
tags:
    - phase-13
    - test
    - slack
    - channels
class: standard
---

From #307 slack-structured-proposals-research.md. Tests: mock interactive payloads (block_actions), template output validation (valid Block Kit JSON), thread registry (create/get/auto-thread), fallback paths (CLI gets text, Slack gets blocks), approval gate enrichment (isinstance routing). AC: Interactive payload routing tested; templates produce valid blocks; thread registry tested; fallback paths verified; >= 90%% coverage for new Slack interactive code. Depends on #307.
