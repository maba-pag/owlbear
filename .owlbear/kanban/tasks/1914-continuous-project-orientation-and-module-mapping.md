---
id: 1914
title: Continuous project orientation and module mapping
status: collect
priority: medium
created: 2026-07-12T03:04:06.678099+02:00
updated: 2026-07-12T03:04:06.678099+02:00
tags:
  - scope:tools
  - scope:agent-config
  - feature
parent:
depends_on:
  - 1912
  - 1913
ac:
  - Python and ECMAScript source indexes are available as separate generated 
    artifacts and commands.
  - Pipeline agents continuously use a shared project-orientation ladder and a 
    shaped Change Module Map.
  - Deep-module guidance is applied during shaping, with replacement-ideation 
    integration explicitly retained as future work.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Problem
Agents need a compact, continuously used model of documentation and source structure, and shaping should prefer deep modules while preserving a verified map of planned module changes.

## Decisions
- Separate committed advisory artifacts: `doc-index`, `py-index`, and `ts-index`.
- `ts-index` covers TS, TSX, JS, and JSX.
- Rename `h-code-orientation` to `h-project-orientation` and make it regular reading for shaper, builder, and verifier.
- Defer integration with the replacement ideation flow; do not modify the retiring ideation or spec-kit systems.