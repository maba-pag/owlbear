---
id: 607
title: Test import guard for bookmark_pipeline trafilatura
status: archived
priority: important
created: 2026-03-06T19:41:36.5389924+01:00
updated: 2026-03-07T18:08:17.8420697+01:00
started: 2026-03-06T20:14:17.3512166+01:00
completed: 2026-03-07T18:08:17.8420697+01:00
tags:
    - audit
    - config
    - knowledge
    - test
class: standard
---

TDD test task for #500. File: tests/test_bookmark_pipeline.py (extend existing).

AC:
- [ ] Test that importing _default_web_read and calling it when trafilatura is unavailable raises ImportError
- [ ] Test that the ImportError message contains the install command `uv pip install 'owlbear[search]'`
- [ ] Uses unittest.mock to simulate missing trafilatura (patch builtins.__import__ or sys.modules)
- [ ] Follows existing test pattern in test_bookmark_pipeline.py
