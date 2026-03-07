---
id: 609
title: Fix enum identity failures in test_error_recovery.py
status: archived
priority: critical
created: 2026-03-07T03:08:45.1616044+01:00
updated: 2026-03-07T18:08:18.8508618+01:00
started: 2026-03-07T04:24:35.543431+01:00
completed: 2026-03-07T18:08:18.8508618+01:00
tags:
    - test
    - bugfix
    - phase-9
class: standard
---

## Root Cause
8 tests in test_error_recovery.py use `is` for enum identity comparison (`is ErrorCategory.PERMANENT`). When modules get reimported through different paths in multi-file test runs, enum members become different objects and identity fails.

## Fix Applied
Changed `is ErrorCategory.X` to `== ErrorCategory.X` (8 comparisons).

## AC
- [ ] All 8 affected tests pass in full suite (not just individually)
- [ ] test_error_recovery.py passes with 0 failures in full suite
- [ ] Changes are == not is for enum comparisons only
