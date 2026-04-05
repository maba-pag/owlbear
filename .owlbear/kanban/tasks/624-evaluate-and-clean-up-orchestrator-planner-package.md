---
id: 624
title: Evaluate and clean up orchestrator planner/ package
status: todo
priority: important
created: 2026-04-05T01:31:32.2092633+02:00
updated: 2026-04-05T16:55:20.4280878+02:00
tags:
    - scope:orchestrator
    - phase-2
    - type:build
    - docs
parent: 619
depends_on:
    - 621
    - 622
class: standard
---

## Acceptance Criteria

- Evaluate serve/orchestrator/src/owlbear/planner/ for removal vs retention:
  - Verify whether loop.py, cli.py, and/or waves.py still have direct planner/ imports (headless ACP path)
  - Conclude KEEP if any active in-process imports exist; REMOVE only if pick_tasks fully replaces all Python usage
- If kept (expected per research, .95 confidence):
  - Add module-level docstring in planner/__init__.py explaining dual-path architecture:
    - In-process path: loop.py/cli.py use planner/ directly for headless ACP dispatch
    - MCP path: VS Code agents use pick_tasks tool in owlbear-kanban server
    - Include reference to parent task #619
  - Document evaluation result in task body
- If removed (only if no active imports remain):
  - All imports in orchestrator/ updated (loop.py, cli.py, waves.py)
  - Tests that covered planner/ gates/selector logic verified to still pass via MCP tool tests (#620)
  - No dead imports remaining

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

[[2026-04-05]] Sun 16:46
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: evaluate planner/ disposition and add dual-path documentation |
| Interface clarity | PASS (refined) | AC restructured with explicit evaluation criteria and conditional paths |
| Dependency correctness | PASS | #621 done, #622 in-progress; dispatch gates handle ordering |
| Module layering | PASS | Changes within orchestrator domain only (planner/ is sub-package) |
| TDD compliance | PASS | Non-impl task (docs tag); deliverable is a docstring, not testable code |
| KISS/YAGNI | PASS | Minimal scope: one docstring addition to __init__.py |
| Premise challenge | PASS | Necessary cleanup step in #619 migration plan |
| Pattern consistency | PASS | No new patterns introduced |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | scope:orchestrator only |

### Failure Mode Map
N/A — no failure-mode codepaths introduced or modified.

### Challenge Results
- Challenger: proceed (via Explore subagent)
- Confidence: high — unanimous evidence across 8 sources
- Key validations: (1) all planner/ imports confirmed active in loop.py L17-18, cli.py L15-16, waves.py L12; (2) #622 modifies agent/skill files only, not Python imports; (3) no dead code in planner/
- Architect response: accepted; all refinement suggestions aligned with initial assessment

### AC Refinements Applied
1. Removed "Document decision in parent task #619 body" — violates pipeline claiming rules (builder cannot edit unclaimed tasks). Replaced with "Document evaluation result in task body."
2. Added cli.py to "If removed" path (was missing from original AC).
3. Restructured "If kept" AC with explicit sub-bullets for docstring content requirements.
4. Added `docs` pass-through tag — deliverable is a docstring, not testable Python code.

### Verdict: APPROVE
### Action: AC refined, docs tag added, backlog to todo
