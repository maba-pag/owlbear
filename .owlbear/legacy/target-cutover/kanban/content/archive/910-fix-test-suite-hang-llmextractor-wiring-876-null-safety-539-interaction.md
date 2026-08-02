---
id: 910
title: 'Fix test suite hang: llmextractor_wiring_876 → null_safety_539 interaction'
status: archived
priority: medium
created: 2026-04-17T10:47:30.444794+00:00
updated: 2026-04-17T20:04:08.476128+00:00
tags:
- scope:test
- type:test
- debt
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Context

Running test suite in serial mode (`-n 0`) hangs at ~97% completion. Root cause: state leakage from `test_llmextractor_wiring_876.py` prevents `test_null_safety_539.py` from starting. Both files pass individually; combined they deadlock.

Session memory has detailed investigation in `owlbear-deadlock-investigation.md`.

## Acceptance Criteria

- [ ] `uv run pytest tests/ serve/ -n 0 -q --tb=no` completes without hanging (timeout 300s)
- [ ] Both test files continue to pass individually

## Notes

Not macOS-specific. Blocks full test suite completion on any platform.
