---
id: 683
title: 'Test-writer agent: adversarial test creation from AC'
status: archived
priority: needed
created: 2026-03-08T15:45:12.4348505+01:00
updated: 2026-03-09T05:08:39.3944552+01:00
started: 2026-03-08T16:07:10.9987869+01:00
completed: 2026-03-09T05:08:39.3944552+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
class: standard
---

## Status: SPLIT by architect\n\nThis compound task was split into 4 atomic tasks:\n\n- #690 — Create test-writer.agent.md (no deps)\n- #691 — Create tdd-red skill (depends on #690)\n- #692 — Update builder.agent.md + tdd-workflow for GREEN-only (depends on #690)\n- #693 — Update reviewer.agent.md + code-review skill for test comparison (depends on #692)\n\nOrchestrator dispatch table update (adding test-writer) deferred to #682 (orchestrator rewrite).\n\n## Original Context

Currently the builder writes both tests and implementation. This has two problems: (1) the builder's tests are biased toward the implementation it's about to write — it tests what it plans to build, not what the AC requires, (2) test-writing instructions get buried in the builder's already-crowded context.

Splitting test-writing into a separate agent fixes both: the test-writer tests the CONTRACT (AC), not the code, and each agent has a smaller, more focused job.

## Model: grey separation, not black-and-white

The test-writer creates the initial test suite from AC. The builder implements to make those tests pass, but CAN refine/extend tests when it discovers edge cases during implementation (e.g., "this function receives None in practice"). The reviewer then assesses whether the builder's test changes weakened the test-writer's original intent.

This gives the builder flexibility without losing the adversarial benefit. The reviewer is the check: if the builder gutted a test to make it easier to pass, the reviewer catches it.

## Pipeline

test-writer (RED) -> builder (GREEN, may refine tests) -> reviewer (VERIFY, scrutinizes builder test changes)

## Acceptance Criteria

- [ ] New test-writer.agent.md: reads AC + existing codebase, writes comprehensive failing tests
- [ ] Test-writer focuses on AC contract: happy paths, edge cases, error paths, boundary conditions
- [ ] Test-writer writes tests to task-referenced test file(s), appends summary to task body
- [ ] Builder.agent.md updated: primary job is GREEN phase (make tests pass), may add/refine tests for discovered edge cases
- [ ] Builder must mark any test changes it makes (e.g., comment `# builder-added` or separate test class) so reviewer can distinguish
- [ ] Reviewer.agent.md updated: explicitly compares test-writer's original tests vs builder's final tests, flags weakened assertions
- [ ] tdd-workflow skill rewritten for two-agent TDD: test-writer skill (RED) + builder skill (GREEN+refine)
- [ ] If builder cannot implement the interface the test-writer assumed, builder returns BLOCK with explanation — evaluator routes back through architect for AC revision, NOT back to test-writer directly

## Notes

- The test-writer's adversarial value comes from NOT knowing the implementation. It should never see the builder's code — only AC and existing codebase for context.
- The reviewer's job gets easier: it compares two independently-produced artifacts (tests vs implementation) instead of reviewing a single agent's self-consistent output.

[[2026-03-08]] Sun 23:51
Wave 4, agent: auditor

[[2026-03-09]] Mon 04:57
Wave 1, agent: auditor

[[2026-03-09]] Mon 05:08
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| New test-writer.agent.md | File exists with adversarial persona, tdd-red ref | PASS |
| Test-writer AC contract focus | tdd-red Step 3: 4 categories | PASS |
| Test-writer appends summary | tdd-red Steps 4+6 | PASS |
| Builder GREEN phase | Persona L27, critical rule L40 | PASS |
| Builder marks test changes | TestBuilderDiscovered L41 | PASS |
| Reviewer test comparison | code-review Step 5c, output_format | PASS |
| tdd-workflow two-agent TDD | tdd-red (RED) + tdd-workflow (GREEN) | PASS |
| Builder BLOCK protocol | Critical rule L42 + output BLOCK L110 | PASS |

### Test Results
- pytest: 453 passed, 1 failed (pre-existing slack dep), 20 skipped
- ruff: 3 pre-existing errors in unrelated files

### Confidence: .95
### Action: archive
