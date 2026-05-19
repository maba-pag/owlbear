---
id: 973
title: 'Consolidate duplicate tasks #935 and #936'
status: archived
priority: nice-to-have
created: 2026-03-24T00:07:58.9184257+01:00
updated: 2026-03-24T01:17:10.2468557+01:00
started: 2026-03-24T01:17:10.2468557+01:00
completed: 2026-03-24T01:17:10.2468557+01:00
tags:
    - cli
    - test
    - tooling
    - phase-14
    - scope:cli
class: standard
---

Tasks #935 and #936 are near-identical RED-phase tasks for the same board fixture helper. Both have the same title and AC. The parent research doc (docs/research/bearclaw-board-kanban-json-fixtures.md) explicitly references #936 as its follow-up, and #939 depends_on #936. AC: (1) Archive the duplicate task (whichever is not advancing); (2) Update #939 depends_on to reference the surviving task; (3) Verify no other task references the archived duplicate. See docs/research/board-fixture-helper-red-gate.md.
