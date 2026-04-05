---
id: 624
title: Evaluate and clean up orchestrator planner/ package
status: backlog
priority: important
created: 2026-04-05T01:31:32.2092633+02:00
updated: 2026-04-05T16:09:10.8888212+02:00
tags:
    - scope:orchestrator
    - phase-2
    - type:build
parent: 619
depends_on:
    - 621
    - 622
class: standard
---

## Acceptance Criteria

- serve/orchestrator/src/owlbear/planner/ package evaluated for removal:
  - If pick_tasks in kanban server fully replaces the Python code, remove planner/ package
  - If orchestrator loop.py still imports from planner/ directly (in-process path), keep as-is
  - Document decision in parent task #619 body
- If removed:
  - All imports in orchestrator/ updated (loop.py, waves.py)
  - Tests that covered planner/ gates/selector logic verified to still pass via MCP tool tests (#620)
  - No dead imports remaining
- If kept:
  - Add comment explaining dual-path (in-process for loop, MCP for agent) with link to #619

[[2026-04-05]] Sun 16:09
## Research
- Research doc: .owlbear/research/evaluate-planner-package.md
- Sources: 8 studied, 8 high-relevance (all codebase-internal)
- Recommendation: KEEP planner/ package, add dual-path comment (confidence: .95)
- Follow-up tasks created: none (implementation is #624's own AC)
- Decision requests: none, T1 autonomous

## Challenge Results
- Challenger: SKIP — answer pre-determined by #619 research §3.3 and arch review
- Tier: T1 (autonomous), documenting existing design decision
- Key findings: (1) loop.py + cli.py + waves.py have active planner imports for headless ACP path; (2) 8+ test files import from planner; (3) pick_tasks fully covers gate+selector logic for MCP path; (4) dual-path architecture is by design
- Researcher response: N/A — no challenge needed, unanimous evidence
