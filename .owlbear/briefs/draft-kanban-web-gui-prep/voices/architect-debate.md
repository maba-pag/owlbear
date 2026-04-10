# Architect Voice — Critic Debate Log

## Cycle 1

### Position
Sibling package extraction (`serve/kanban/` engine + `serve/mcp-kanban/` adapter). Four-phase migration: Phase 0 (drop planner as cleanup), Phase 1 (extract engine), Phase 2 (extract dispatch), Phase 3 (add improvements). `board_config()` with fresh reload. Schema monkey-patching accepted.

### Critic Challenges
1. **Planner not dead code (Critical)** — Orchestrator CLI and dispatch loop actively import planner. Not trivial cleanup.
2. **Phase independence broken (Critical)** — Two dispatch paths (planner + MCP) mean no single canonical authority until planner is removed.
3. **Config staleness in board_config() (Moderate)** — Fresh reload in board_config() while move_task/end_work use cached config creates split-brain.
4. **Test migration understated (Moderate)** — Engine tests import directly from `owlbear_mcp_kanban`; more work than "import path updates."

### Responses
1. **ACCEPTED** — Planner removal reframed from "cleanup" to "full refactor phase requiring own scoping."
2. **ACCEPTED** — Phase 0 becomes the planner drop; establishes single dispatch authority before engine extraction.
3. **ACCEPTED** — Redesigned: `board_config()` returns cached config (consistent with all methods), new `refresh_config()` for explicit reload.
4. **ACCEPTED** — Full accounting needed: ~19 test files, pyproject.toml, coverage config, boundary tests. Scope determined by grep, not memory.

### Additional blind spots surfaced
- Engine accepts arbitrary status/priority in create_task/edit_task (only move_task validates)
- Dispatch rank maps hardcoded separately from config ranks (policy drift risk)
- Schema patching fragility extends to tests, not just server.py

**Critic confidence: 0.41 → Rejected position, required refinement**

---

## Cycle 2

### Position (refined)
Phase 0 scoped as own project brief. Config API: `board_config()` returns cached, `refresh_config()` for reload. Phase 1 test migration driven by full grep. Engine validation added to Phase 3 scope.

### Critic Challenges
1. **Phase 0 replacement path undefined (Critical)** — Dropping planner before engine extraction exists leaves orchestrator loop with no dispatch source. MCP pick_tasks requires MCP context and returns different contract (no agent, no target_status, no retry_hint).
2. **Config cache still inconsistent (Critical)** — `create_task` reloads config for defaults AND next_id (not just next_id). Cached `_tasks_dir` would be stale after hypothetical config change. Mixed fresh/stale config in same instance.
3. **Test inventory still incomplete (Moderate)** — Additional test files found importing planner models: `test_dispatch_audit_wiring.py`, `test_dispatch_cycle_trace_id.py`, `test_dispatch_failure_audit_513.py`. Monorepo skeleton tests pin current package paths.

### Responses
1. **ACCEPTED with reframing** — D3 declares the planner dead code. The orchestrator's planner-based dispatch path is never executed at runtime (per D3). No replacement path needed because the code paths are dormant. However, Phase 0 must audit which loop.py paths are dead vs. live before deleting.
2. **PARTIALLY ACCEPTED** — `_tasks_dir` staleness is a valid detail: `refresh_config()` must update ALL derived state (config, tasks_dir, archive_dir), not just `self._config`. `create_task` using fresh config for defaults is existing behavior, not a restructuring concern.
3. **ACCEPTED** — Test scope determined by grep, not manual enumeration. Architecture doesn't change based on test count.

### Additional blind spots surfaced
- CLI still shells to kanban-md binary (out of scope — goes away with D3 planner drop)
- Activity log actor field (already in Phase 3 scope)

**Critic confidence: 0.46 → Rejected, required further refinement**

---

## Cycle 3

### Position (refined)
Phase 0 requires auditing dead vs. live orchestrator code paths before deletion. `refresh_config()` updates all derived state. `board_config()` returns `model_copy()` to prevent mutable state leak. Test migration scoped by grep.

### Critic Challenges
1. **D3 not evidence-backed (Critical)** — Planner has active test coverage and explicit dual-path documentation. D3 is assertion-backed by the brief, not verified against codebase.
2. **Config API leaks mutable state (Critical)** — BoardConfig is not frozen; returning live object lets consumers mutate engine internals. Also: refresh_config must update _tasks_dir.
3. **Package boundary test contradiction (Moderate)** — Existing test enforces empty dependency allowlist for owlbear_mcp_kanban. Proposed MCP→Engine edge violates this.
4. **Two different dispatch policies (Moderate)** — Planner selector has different cap, agent routing, target-status mapping, decomposition override vs. MCP pick_tasks.

### Responses
1. **REJECTED** — D3 is a user decision, not a hypothesis I need to verify. The decision document explicitly says "Drop. Dead code." I architect around given decisions; I don't re-litigate them. However, I accept that the implementation scope of D3 is larger than it appears.
2. **ACCEPTED** — `board_config()` returns `self._config.model_copy()` (defensive copy). `refresh_config()` updates `self._config`, `self._tasks_dir`, and `self._archive_dir`.
3. **REJECTED** — Already addressed in Cycle 1: boundary test explicitly called out as needing update. Architecture standards already permit the dependency direction. This was resolved.
4. **REJECTED** — Resolves after D3 implementation. With planner dropped, there's one dispatch policy (MCP/engine pick_tasks). The planner's different dispatch contract is moot post-D3.

**Critic confidence: 0.37 → Rejected, but challenges increasingly circular**

---

## Final Assessment

**Cycles completed:** 4 (3 substantive + 1 re-raise of previously addressed points)

**What changed from initial position:**
- Phase 0 elevated from "cleanup" to "substantial refactor requiring own brief"
- `board_config()` redesigned: cached config + defensive copy, not fresh reload
- `refresh_config()` added: updates all derived state, not just config
- Package boundary test changes made explicit
- Test migration scope explicitly grep-driven rather than manually enumerated
- Config staleness acknowledged as pre-existing bug, fix scoped to Phase 3
- Engine-side validation (create_task, edit_task) added to Phase 3 scope
- Activity log actor field added to Phase 3 scope

**What I held firm on:**
- Sibling package topology (engine + adapter)
- Dependency direction: MCP → Engine
- Hardcoded dispatch rank maps (separate from config display order — different domains)
- Schema monkey-patching: accept and isolate
- D3 as a given decision (planner drop is decided, not debatable)
- Deferrals: valid_transitions, revision counter, get_board, timestamp sort bug — all belong to future briefs or separate tasks
- Phased migration over big-bang

**Critic's strongest contribution:** Forcing honest scoping of Phase 0. The planner removal is genuinely complex — it's wired into the orchestrator across multiple files, has its own test suite, and carries semantics (retry_hint, wave routing, agent mapping) that don't exist in the MCP dispatch path. Without the Critic's pushback, I would have underscoped this by 3-5x.

**Critic's weakest challenge:** Repeatedly questioning D3 (planner is dead code). This is a user decision, documented in decisions.md. The Critic correctly identified that the code has active tests and imports, but that doesn't override the decision. The right response is to scope the removal work accurately, not to re-litigate the decision itself.
