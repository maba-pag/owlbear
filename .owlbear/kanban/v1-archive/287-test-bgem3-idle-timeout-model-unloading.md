---
id: 287
title: Test BgeM3 idle-timeout model unloading
status: archived
priority: important
created: 2026-02-28T23:11:44.9967136+01:00
updated: 2026-03-01T17:08:07.4757312+01:00
started: 2026-02-28T23:12:25.4408241+01:00
completed: 2026-03-01T17:08:07.4757312+01:00
tags:
    - phase-9
    - embedding
    - test
class: standard
---

TDD test task for #261 idle-timeout feature.

AC:
- [ ] Test _last_used timestamp updates on embed() and embed_hybrid() calls
- [ ] Test timer fires unload() after idle_timeout expires (use short timeout like 0.1s in tests)
- [ ] Test unload() sets self._model = None after timeout
- [ ] Test next embed() after timeout transparently re-initializes model
- [ ] Test timer resets when embed() called before timeout
- [ ] Test embedding_idle_timeout config field on OwlBearSettings with default 600
- [ ] Mock BGEM3FlagModel (no real model loading)

Test file: tests/test_embedding_idle_timeout.py
See docs/research/bge-m3-integration.md section 3.8
