# Architectural Stance — Dep-Status Guidance in start_work

## Architectural Stance

**Inline the dep iteration pattern in `start_work()`.** Do not extract a shared helper.

## Structural Reasoning

### Inline vs. Extract

The dep iteration pattern (~8-10 LoC: iterate `depends_on`, catch 4-exception tuple, partition into `active_ids`/`archived_reasons`) exists in `show_task()` and would be duplicated in `start_work()`. Two consumers.

**Inline wins** for three reasons:

1. **Tier-budget discipline.** D2 sets tool-tier, ~15 LoC total change. Extracting a helper requires a new method (~12 LoC), refactoring `show_task()` (-10/+2), and adding to `start_work()` (~5 LoC) — touching ~20 LoC across two methods. Inlining touches one method, ~12-15 LoC. Extraction inflates scope 30-40% beyond the tier budget.

2. **Two-consumer threshold.** The project convention is "avoid abstractions until the third repetition." The AgentView-level dep iteration (calling `engine.show_task()` per dep) exists in one place today. Adding a second instance is within the duplication threshold. Extract at three.

3. **Containment.** Inline keeps the entire change within `start_work()`. No callers of `show_task()` are affected. No method signature changes. The blast radius is one method.

### Placement: After the Claim

Compute dep_status **after** the successful `engine.start_work()` call, not before.

- If the claim fails (archived, blocked, concurrent), dep computation is skipped entirely — no wasted I/O on the failure path.
- The post-claim `task` object carries the same `depends_on` as the pre-claim `task_record`. Dep files are separate from the claimed task file.
- Pattern: mutate first, enrich the response second. Consistent with how `_skip_transition_guidance()` is computed after the move in other methods.

### Guidance Integration

The implementation should follow the existing `_skip_transition_guidance()` pattern:
1. After successful claim, iterate `task.depends_on` using `show_task()` per dep
2. Call `engine._compute_dep_status()` with the partition
3. If `"blocked"`, format a single `⚠` guidance string listing dep IDs
4. Pass `guidance=[...]` to `_to_single_response(task, guidance=guidance)`

## Key Trade-offs

| Choice | Upside | Downside |
|--------|--------|----------|
| Inline duplication | Contained diff, tool-tier budget, no show_task refactor | Exception tuple duplicated in two places |
| After-claim placement | No wasted I/O on failure paths | Post-claim enrichment failure returns no guidance (but this IS today's behavior) |
| Blocked-only scope (per D3) | Minimal logic, no redirect handling | Redirect case unhandled (accepted: redirect means deps are done) |

## Warnings

1. **Consolidation test required.** The exception tuple `(FileNotFoundError, CorruptionError, ValueError, KeyError)` is a subtle resilience contract. With two copies, add a consolidation test (matching the existing `test_consolidate_helpers.py` pattern) that asserts both `show_task()` and `start_work()` handle the same exception set for dep lookups. This catches divergence cheaply.

2. **MCP-layer test coverage.** Non-empty AgentView guidance passes through to MCP consumers verbatim via the `start_work` tool handler (confirmed in `server.py`). The guidance message is wire-visible. Tests must cover both AgentView-level and MCP-level with exact-value assertions — not just envelope-shape checks. The repo has prior false-green history with loose guidance assertions.

3. **Guidance message format is contract.** The `⚠` string format and dep-ID listing become part of the observable MCP contract once shipped. Choose the format deliberately (not an afterthought) and pin it in tests.

## Confidence

**0.82** — Strong structural fit. All primitives exist. Inline is the right call at two consumers. The three warnings above are real operational concerns but don't change the structural recommendation.
