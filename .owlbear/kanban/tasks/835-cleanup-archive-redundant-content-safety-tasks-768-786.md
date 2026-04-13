---
id: 835
title: 'Cleanup: archive redundant content safety tasks (#768, #786)'
status: research
priority: nice-to-have
created: '2026-04-11T15:24:19.483409+00:00'
updated: '2026-04-11T15:24:19.483409+00:00'
tags:
- phase-1
- scope:knowledge
- cleanup
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- [ ] Archive #768 (P1-15: Tests — Content safety) — fully superseded by its own research; AC1+AC2 covered by existing tests, AC3 carved to #833/#834
- [ ] Archive #786 (Content safety predicate inversion) — duplicate of work already shipped in content_safety.py via #751 builder commit 2dfae28b; also has stale dep on deleted #781

## Context
- Research: .owlbear/research/769-content-safety-wrapping.md
- Both tasks describe work already implemented and tested (27+ tests passing)
