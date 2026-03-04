---
id: 555
title: Extract shared test helpers to conftest.py
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:57.7640987+01:00
updated: 2026-03-04T07:38:57.7640987+01:00
tags:
    - audit
    - test
class: standard
---

M3/L1: conftest.py has only 1 fixture. At least 8 test files define identical _run(coro) helper. Common patterns (make_channel, make_settings) reinvented per file. Extract to conftest.py. AC: no duplicated _run helpers. See docs/test-quality-audit.md.
