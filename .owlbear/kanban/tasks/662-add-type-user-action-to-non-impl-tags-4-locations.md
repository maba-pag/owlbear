---
id: 662
title: Add type:user-action to NON_IMPL_TAGS (gates.py + server.py)
status: review
priority: needed
created: 2026-04-06T16:39:07.1761895+02:00
updated: 2026-04-07T01:04:34.3737008+02:00
tags:
    - phase-3
    - scope:orchestrator
    - type:config
parent: 661
depends_on:
    - 665
class: standard
---

## Objective\nAdd `type:user-action` to the NON_IMPL_TAGS set in both Python gate locations for TDD gate exemption.\n\n## Context\nFrom #661 research: `type:user-action` tag convention for manual user-action tasks needs TDD gate exemption so the test-writer passes through cleanly after user completes the action.\nSkill doc updates split to #666.\n\n## Acceptance Criteria\n- [ ] Add `type:user-action` to `_NON_IMPL_TAGS` in serve/orchestrator/src/owlbear/planner/gates.py\n- [ ] Add `type:user-action` to `_PICK_NON_IMPL_TAGS` in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py\n- [ ] Existing tests pass (no regressions)\n\n## Files Affected\n- serve/orchestrator/src/owlbear/planner/gates.py\n- serve/mcp-kanban/src/owlbear_mcp_kanban/server.py

[[2026-04-06]] Mon 23:49
## Research
- Research doc: N/A (trivial config task — parent .owlbear/research/user-action-required-pipeline-handling.md covers this)
- Sources: 3 studied, 3 high-relevance (gates.py L22-25, server.py L531-535, test_user_action_non_impl_661.py)
- Recommendation: No further work needed — implementation already complete (confidence: .99)
- Follow-up tasks created: none
- Decision requests: none (T1 — trivial config, already implemented)

### Verification
- `type:user-action` confirmed present in `_NON_IMPL_TAGS` (gates.py L25) and `_PICK_NON_IMPL_TAGS` (server.py L534)
- 7/7 tests pass (test_user_action_non_impl_661.py)
- No regressions: 6 failures in adjacent test files are pre-existing (decomp_override agent rename + atomicity gate — unrelated to type:user-action)
- Implementation commit: 6ee05d3 (completed during parent #661 builder phase)

### Note
This subtask's code was already implemented during the parent #661 lifecycle. The planner created #662 after the builder had executed. All 3 AC items are satisfied by existing code. Task is ready for the downstream pipeline to verify and close.

[[2026-04-07]] Tue 00:16
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: add tag to two coordinated constant sets |
| Interface clarity | PASS | AC specifies exact files and constant names |
| Dependency correctness | PASS | #665 (test task) archived/done |
| Module layering | PASS | Leaf-level config constants, no new imports |
| TDD compliance | PASS | Test task #665 exists and is archived |
| KISS/YAGNI | PASS | Minimal scope: one string added to two sets |
| Premise challenge | PASS | Parent #661 research established need |
| Pattern consistency | PASS | Follows existing frozenset tag pattern in both files |
| Security surface | PASS | No new system boundaries, config constants only |
| Single domain | PASS | orchestrator domain (two files in same functional area) |

### Codebase Verification
- gates.py L24-29: `_NON_IMPL_TAGS` frozenset contains `type:user-action` (confirmed)
- server.py L531-539: `_PICK_NON_IMPL_TAGS` frozenset contains `type:user-action` (confirmed)
- Implementation already landed in commit 6ee05d3 during parent #661 builder phase
- Non-impl tag `type:config` already present on task

### Challenge Results
- Challenger: FALLBACK (challenger agent not in available roster)
- Architect response: Proceeded without challenge; trivial config addition with verified implementation

### Verdict: APPROVE
### Action Taken: Advanced to todo. Implementation already complete; downstream pipeline will verify and close.

[[2026-04-07]] Tue 00:42
## Test-Writer Notes
- Non-implementation task (tagged `type:config`) — no tests applicable.
- Passing through to builder.

[[2026-04-07]] Tue 01:04
## Builder Notes
- Non-implementation task — no code changes needed.
- Implementation already landed in commit 6ee05d3 during parent #661 builder phase.
- Verified: `type:user-action` present in `_NON_IMPL_TAGS` (gates.py) and `_PICK_NON_IMPL_TAGS` (server.py).
- Passing through to review.
