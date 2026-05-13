# Architect Debate Log — Dep-Status Guidance in start_work

## Cycle 1

### Draft Position

1. **Inline** the dep iteration pattern (~8-10 LoC) in `start_work()` rather than extracting a shared helper
2. Compute dep_status **after** the claim (success path only)
3. No new coupling or testability concerns beyond existing patterns

### Critic Challenges

#### C1 — Post-claim failure mode (Critical)

Claim persists before returning. If dep enrichment fails after the mutation, task is claimed but no guidance returned. Draft didn't address this partial-success state.

**Response: Acknowledged but inconsequential.** The dep iteration catches `(FileNotFoundError, CorruptionError, ValueError, KeyError)` — the same 4-exception tuple used by `show_task()`. A failure outside this set would be a programming error (e.g. `AttributeError`), not a runtime scenario. And the fallback behavior (no guidance, task claimed) is exactly today's behavior. The partial-success mode is "current production behavior." No regression risk. **Position held.**

#### C2 — Subtle exception tuple contract (Critical)

The 4-exception tuple is a deliberate resilience contract tested by discriminating tests. Duplicating it creates a maintenance hazard if the tuple evolves.

**Response: Genuine concern, but contained by scope.** This is the strongest challenge. The tuple IS subtle and test-pinned. However: (a) the tuple has been stable since the dep-lookup suite was written, (b) extracting a helper to DRY this means also refactoring `show_task()` — a scope expansion that violates the tool-tier ~15 LoC budget, (c) a consolidation test for `start_work` dep delegation (matching the existing `test_consolidate_helpers.py` pattern) would catch divergence between the two call sites at near-zero cost. **Position held with added warning: a consolidation test is structurally necessary.**

#### C3 — "Only two consumers" undercounts (Moderate)

`list_tasks` in the engine also uses `_compute_dep_status`. The codebase already values canonicalization (`test_consolidate_helpers.py`).

**Response: Partially valid but misframed.** `list_tasks` does dep iteration inside the engine, not in `agent_view`. The pattern in question is specifically the AgentView-level iteration calling `engine.show_task()` per dep. That pattern exists in one place today (`show_task`), would become two (`start_work`). The canonicalization the repo enforces is for `_compute_dep_status` delegation (engine method), not for the iteration loop. Two consumers of the loop pattern is below the extraction threshold — extract at three. **Position held.**

#### C4 — Race model weakens timing claim (Moderate)

The codebase already models dep resolution as race-prone. "Deps don't change during claim" is weaker than the test suite assumes.

**Response: Challenge is about timing window, but the window is identical regardless of ordering.** Whether dep iteration happens before or after the claim, the same `engine.show_task(dep_id)` calls happen in the same racy environment. The timing choice is "skip unnecessary work on failure" not "avoid races." The race exists regardless of ordering. **Position held.**

#### C5 — MCP contract impact (Critical)

Non-empty AgentView guidance passes through to MCP consumers verbatim. This is externally observable behavior, not internal-only.

**Response: Genuine blind spot — updated stance.** The guidance field IS designed for this (that's its entire purpose), so the structural choice is correct. But I missed that this is wire-visible to MCP consumers. This means: (a) the change needs MCP-layer test assertions, not just AgentView-level tests, and (b) the guidance message format is part of the contract. **Added as a warning in the final stance.**

#### C6 — Test exactness bar (Moderate)

Repo has prior false-green history with loose guidance assertions. Exact-value assertions are required.

**Response: Valid operational concern.** The test strategy needs exact-value assertions matching the repo's established pattern in `test_guidance.py`. Added as a warning. **Position updated.**

### Post-Cycle Assessment

Three challenges strengthened the position (added warnings about consolidation tests, MCP-layer coverage, and exact-value assertions). No challenges flipped a core recommendation. Position is solid.

**Exit: Cycle 1 — position firm with three new warnings.**
