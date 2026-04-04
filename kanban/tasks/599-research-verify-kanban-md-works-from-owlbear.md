---
id: 599
title: 'Research: Verify kanban-md works from .owlbear/kanban/'
status: in-progress
priority: needed
created: 2026-04-04T20:30:11.3710718+02:00
updated: 2026-04-04T22:55:39.2342606+02:00
tags:
    - scope:infra
    - type:research
    - phase-2
parent: 598
class: standard
---

## Summary

Verify that kanban-md.exe works correctly when invoked from a directory OTHER than kanban/ or when config.yml and tasks/ are in a non-standard path like .owlbear/kanban/.

## Acceptance Criteria

- [ ] AC1: Create a test board at .owlbear/kanban/ (config.yml + tasks/ subdir) and verify all CRUD operations via the --dir flag:
  - AC1a: `kanban-md --dir .owlbear/kanban/ create "Test task"` (relative path from project root)
  - AC1b: `kanban-md --dir <absolute-path>/.owlbear/kanban/ list --json` (absolute path)
  - AC1c: `kanban-md --dir .owlbear/kanban/ show <id>` returns task details
  - AC1d: `kanban-md --dir .owlbear/kanban/ move <id> <status>` changes status
  - AC1e: `kanban-md --dir .owlbear/kanban/ edit <id> -a "body text"` appends body content
  - Each command exits 0 and produces parseable output (use --json where applicable)
- [ ] AC2: Document any path assumptions or limitations found (directory name constraints, Windows backslash handling, relative vs absolute path behavior)
- [ ] AC3: If kanban-md hardcodes kanban/ or has path restrictions, document workaround (symlink, wrapper script, config override)
- [ ] AC4: Add a "Kanban Path Verification" section to docs/decisions/pending/owlbear-folder-restructure.md with factual test results (pass/fail per operation, observed behavior, any limitations)

## Notes

This is a blocker for the entire migration. If kanban-md cannot work from .owlbear/kanban/, we need a workaround before proceeding.

Existing codebase evidence suggests success: integration tests in packages/mcp-kanban/tests/test_integration.py and tests/test_dispatch_integration.py already exercise kanban-md with --dir pointing to arbitrary tmp_path directories (not named kanban/), and all pass. This research confirms that behavior with the specific .owlbear/kanban/ path and documents results for the decision record.

Note: MCP server path resolution (KANBAN_DIR env var, default path changes) is handled by #606, not this task. This task verifies the kanban-md binary only.

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Focused research: verify one binary's path behavior |
| Interface clarity | PASS (refined) | AC1 expanded to 5 explicit CRUD test scenarios with exit-code + parseable-output criteria |
| Dependency correctness | PASS | No dependencies. Leaf starter in the task graph, correctly positioned before #603 |
| Module layering | N/A | Research task, no code changes |
| TDD compliance | PASS | Tagged type:research (pass-through) |
| KISS/YAGNI | PASS | Minimal scope: test binary, document findings |
| Premise challenge | PASS | Integration tests suggest success but explicit verification with .owlbear/kanban/ path and documented results still valuable for the decision record |
| Pattern consistency | PASS | Follows w-research workflow pattern |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | scope:infra only |

### Challenge Results

- Challenger: reconsider (confidence: 0.68)
- Key concerns: (1) AC1 lacked specificity, (2) AC4 scope creep, (3) MCP server is the real blocker
- Architect response: Override with refinement
  - AC1 expanded into 5 explicit test scenarios AC1a-AC1e with exit-code criteria (accepted)
  - AC4 clarified to factual test results, not architectural decisions (refined)
  - MCP server path resolution correctly scoped to #606 (rebutted)

### Verdict: APPROVE
### Action Taken: Refined AC1 into explicit CRUD test scenarios. Clarified AC4 as factual documentation. Added codebase evidence notes for researcher context. Advanced to todo.

[[2026-04-04]] Sat 22:01
APPROVED #599 to todo | Refined AC1 into 5 explicit CRUD test scenarios (relative/absolute path, create/list/show/move/edit). Clarified AC4 as factual findings only. Added codebase evidence context for researcher. Challenger overridden: MCP server path resolution is #606 scope, not this task.

[[2026-04-04]] Sat 22:55
## Test-Writer Notes
- Non-implementation task (tagged type:research) — no tests applicable.
- AC1 describes manual CLI verification (run kanban-md commands, observe results).
- AC2/AC3/AC4 are documentation/findings deliverables with no testable Python interfaces.
- Architecture review in body confirms: "TDD compliance | PASS | Tagged type:research (pass-through)".
- Passing through to builder.
