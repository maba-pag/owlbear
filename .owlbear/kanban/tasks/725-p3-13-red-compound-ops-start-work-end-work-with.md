---
id: 725
title: 'P3-13: RED — compound ops (start_work, end_work) with status advancement'
status: backlog
priority: critical
created: 2026-04-09T03:27:23.3581319+02:00
updated: 2026-04-09T03:27:23.3581319+02:00
tags:
    - kanban
    - phase-3
    - type:test
parent: 712
depends_on:
    - 724
    - 720
class: standard
---

## Objective
Write failing tests for compound operations: start_work (blocked guard, claim, return) and end_work (note append, status advance/block/reject, release).

Brief: see parent #712 — Decision D3: compound ops in engine

## AC
- [ ] Test start_work: blocked guard, claim, return full task
- [ ] Test end_work(success): append timestamped note, advance to next status, release claim
- [ ] Test end_work(success) on last status: archive task
- [ ] Test end_work(fail): append note, keep status, release claim
- [ ] Test end_work(block): append note, set blocked + reason, release claim
- [ ] Test end_work(reject): append note, move to specified status, release claim
- [ ] Test end_work without block_reason when outcome=block raises error
- [ ] All tests fail

## Files
- `tests/test_kanban_engine_compound.py` (new)
