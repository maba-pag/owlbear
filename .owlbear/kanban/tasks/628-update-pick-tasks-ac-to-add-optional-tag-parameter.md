---
id: 628
title: Update pick_tasks AC to add optional tag parameter
status: todo
priority: needed
created: 2026-04-05T10:41:53.2291189+02:00
updated: 2026-04-05T16:31:10.429756+02:00
tags:
    - scope:mcp
    - phase-2
    - type:build
parent: 619
depends_on:
    - 621
class: standard
---

## Acceptance Criteria

- `pick_tasks` tool signature extended to `pick_tasks(limit: int = 25, tag: str = "") → dict`
- When `tag` is non-empty, append `--tag {value}` to the `_run_kanban` args before the board-read call
- Default `""` preserves zero-config semantics — no `--tag` arg passed when empty
- Follows the `list_tasks` tag passthrough pattern (`if tag: args += ["--tag", tag]`) in the same file
- All existing #620 and #621 tests continue to pass (no behavioral change when tag is not provided)

## Context

Research (.owlbear/research/wire-pick-tasks-orchestrator.md §3.3) found that the orchestrator needs tag-based scope filtering for user commands like "Orchestrate: phase-2". Without a tag parameter, pick_tasks returns all eligible tasks and the orchestrator can't filter without 25 show_task calls.

T2 advisory — modifies the "zero-config" design principle from #619. The tag param is a minimal _run_kanban passthrough, not orchestrator logic leaking into the tool.

[[2026-04-05]] Sun 15:35
## Research
- Research doc: .owlbear/research/pick-tasks-tag-parameter.md
- Sources: 6 studied, 6 high-relevance (all codebase-internal)
- Recommendation: Proceed with tag passthrough using list_tasks pattern; prefer str="" for consistency (confidence: .88)
- Follow-up tasks created: none (dependency chain #621-#628-#622 already complete)
- Decision requests: none, T1 autonomous, T2 advisory already communicated via #622 research

## Challenge Results
- Challenger: SKIP, trivial validation of existing researched finding
- Tier: T1 (autonomous), 3-LOC passthrough of existing CLI flag
- Key finding: #620 tests don't assume absence of tag param; no test updates needed
- Key finding: recommend str="" over str|None=None for consistency with list_tasks in same file

[[2026-04-05]] Sun 16:31
## Architecture Review

### AC Refinement
Original AC had 3 issues refined:
1. **Type signature**: Pinned to `tag: str = ""` (was `str | None = None`) — matches `list_tasks` pattern in same file (server.py L186-187). Guard becomes `if tag:` not `if tag is not None:`
2. **Cross-task edits removed**: AC items editing #621/#619/#620 bodies violate pipeline protocol ("never edit tasks you don't own"). Deferred to #619 auditor/doc-writer
3. **Conditional no-op removed**: AC5 ("update #620 tests if they assume no tag") already resolved as "not needed" by research

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One parameter addition to one tool |
| Interface clarity | PASS | Input: tag:str="". Guard: `if tag:`. Output unchanged. Pattern: copy list_tasks L186-187 |
| Dependency correctness | PASS | depends_on [621] — base pick_tasks exists (status: docs). #622 depends on [621, 628] |
| Module layering | PASS | All changes within mcp-kanban server.py |
| TDD compliance | PASS | Test-writer processes at todo; ~4-5 tests derivable from AC |
| KISS/YAGNI | PASS | 3 LOC change following existing pattern |
| Premise challenge | PASS | Orchestrator needs tag filtering per research (wire-pick-tasks-orchestrator.md §3.3) |
| Pattern consistency | PASS | Copies list_tasks --tag passthrough exactly (server.py L186-187) |
| Security surface | PASS | create_subprocess_exec prevents injection; str validated by FastMCP |
| Single domain | PASS | scope:mcp — all changes in mcp-kanban |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| --tag {invalid} | kanban-md rc!=0 | ToolError | Yes (existing) | Error to caller |
| --tag "" (empty) | Not reached | N/A | Yes (if tag: guard) | No filter applied |

### Codebase Evidence
- list_tasks tag pattern: server.py L186-187 (`if tag: args += ["--tag", tag]`)
- _run_kanban: server.py L141-161 (create_subprocess_exec, no shell)
- pick_tasks current: server.py L549-580 (limit only, no tag)
- Research: .owlbear/research/pick-tasks-tag-parameter.md (confidence .88)

### Challenge Results
- Challenger: FALLBACK — challenger agent not in workspace agent roster
- Architect response: Proceed, T1 implementation (3-LOC passthrough of existing pattern)

### Verdict: APPROVE (after refinement)
### Action: AC refined (type pinned to str="", cross-task edits removed), backlog to todo
