# Architect–Critic Debate Log

## Cycle 1

**Position:** New `serve/kanban-engine/` package, `KanbanEngine` class, sync API, seam-by-seam migration (orchestrator first), no file locking, golden-path testing.

**Critic challenges (5 + 3 blind spots):**

1. **(Critical) Rewrite case under-defended.** Cross-platform could be solved by cross-compiling Go binary. GUI ambition is orthogonal. Prior research rejected direct parsing.
   - **Response: Acknowledged but bounded.** The brief's outcomes present the rewrite as the chosen direction. The duplication risk is acceptable because: (a) format is simple/stable, (b) OwlBear controls the schema, (c) 700+ existing files are a living spec. My role is to architect the HOW, not re-litigate WHETHER.

2. **(Critical) Config staleness.** "Load config on init" caches next_id — stale under long-lived MCP server. kanban-md is one-shot and re-reads every invocation.
   - **Response: ACCEPTED.** Refined: immutable config (statuses, priorities) loaded once; mutable state (next_id) read fresh from disk on each create, written back atomically.

3. **(Moderate) Engine boundary misses gate duplication.** Gates, dispatch routing, compound workflows (start_work/end_work) stay above engine — manual sync problem not solved.
   - **Response: Partially accepted.** start_work/end_work moved into engine (board lifecycle operations). Gates/dispatch routing stay above (orchestration policy).

4. **(Moderate) Migration order doesn't de-risk writes.** Orchestrator-first only exercises read paths.
   - **Response: ACCEPTED.** Reversed order: MCP server first (exercises all code paths including hardest writes).

5. **(Moderate) Testing oracle disappears with binary.** "Copy subset" doesn't support 700+ compatibility claim. No external parity harness defined.
   - **Response: ACCEPTED.** Added: golden snapshot capture before binary deletion; round-trip parsing of all 700+ files; three-level test strategy.

**Blind spots:**
- Board path inconsistency (MCP vs orchestrator defaults) → orthogonal to engine design.
- Setup.ps1 in seed/docs/tests → added to migration cleanup.
- Package-count test and Ruff config → acknowledged as one-time cost.

---

## Cycle 2

**Position (refined):** Config immutable/mutable split, MCP server first migration, start_work/end_work in engine, golden snapshots + round-trip tests.

**Critic challenges (4 + 2 blind spots):**

1. **(Moderate) activity.jsonl schema wrong.** Position says "details" but live data uses "detail" singular.
   - **Response: ACCEPTED.** Engine derives log schema from live data, not invented.

2. **(Moderate) MCP parity scope beyond board ops.** Tool exclusion, output schemas, structuredContent not covered by engine parity oracle.
   - **Response: ACCEPTED but bounded.** MCP server is rewired not rewritten — protocol behavior preserved in MCP layer. Engine oracle covers board operations only.

3. **(Moderate) config.yml round-trip not committed.** Only next_id mutated but full config preservation not stated.
   - **Response: ACCEPTED.** Explicit: config.yml round-trip is lossless. Parse full YAML, modify next_id, write back preserving all fields.

4. **(Moderate) "Shared models" collapses lossy projection into lossless persistence.** Current KanbanTask model drops fields; persistence must keep them all.
   - **Response: ACCEPTED.** Two model layers: persistence (lossless, all fields) and API (rich, consumers project at boundary).

**Blind spots:**
- README.md, sharing-guide.md binary references → added to cleanup.
- Orchestrator CLI status command → covered by engine.list_tasks(), no new method.

---

## Cycle 3

**Position (hardened):** Precise 9-method surface, two model layers, injectable non-deterministic params, lossless round-trip for tasks AND config, activity schema derived from live data.

**Critic challenges (4 + 2 blind spots):**

1. **(Moderate) Engine boundary inconsistent.** Position says "all 8 operations" but adds start_work/end_work, removes pick_tasks → actually 9 methods. Context says 8 primitives.
   - **Response: REJECTED.** 8 primitives are the kanban-md CLI surface. Engine surface is 9 because compound board logic (start_work/end_work) moves from MCP server to engine — structural improvement within KISS scope.

2. **(Moderate) Test suite overstates survivorship.** Binary discovery tests, subprocess call-count tests lose their subject after binary deletion.
   - **Response: ACCEPTED.** Three-category taxonomy: tests that survive (behavioral, rewritten), tests that die (subprocess mechanics), tests that are new (engine-level).

**Blind spots:**
- MCP server startup simplified (no binary discovery, KANBAN_BIN removed).
- Broader binary fixture usage (integration tests, mock_acp_agent) in cleanup scope.

---

## Cycle 4

**Position (final refinement):** Test migration taxonomy (survive/die/new), MCP startup simplified.

**Critic challenges (1 critical + blind spots):**

1. **(Critical per Critic, moderate per my assessment) Test survivorship incomplete.** Dispatch integration and e2e tests assert on-disk behavior, not just binary mechanics — these must survive. Planner models depend on specific field shapes (claimed_by, class, body, file).
   - **Response: Partially accepted.** Expanded survivorship taxonomy to include on-disk mutation tests and planner/board-reader tests as SURVIVE categories. These are rewired (binary fixtures → engine fixtures) but behavioral assertions preserved.

**Blind spots:**
- Config statuses are objects not strings → implementation detail handled by lossless round-trip commitment.
- Extra frontmatter fields in live tasks → already covered by persistence model (all fields preserved).

---

## Cycle 5

**Critic challenges (1 + blind spots):**

1. **(Critical per Critic) Test taxonomy still incomplete.** Dispatch integration tests assert post-dispatch body mutation and resulting board state — not just binary trivia.
   - **Response: Accepted.** Final taxonomy has 5 categories (board behavior, on-disk mutation, MCP protocol, planner/board-reader, subprocess mechanics) with clear survive/die classification.

**Blind spots:**
- Config statuses as objects (already addressed in cycle 4).
- Live task field richness (already addressed by persistence model).

---

## Final Assessment

**Cycles completed:** 5

**What changed through debate:**
- Config handling: init-once → immutable/mutable split with fresh disk reads for next_id.
- Migration order: orchestrator-first → MCP-server-first (exercises hardest code paths).
- Engine boundary: added start_work/end_work as compound board operations; removed pick_tasks (dispatch policy).
- Model layering: single model → persistence (lossless) + API (rich, consumer-projected).
- Testing: vague "golden path" → three-level strategy (unit, round-trip, golden parity) + five-category test migration taxonomy.
- activity.jsonl: pre-defined schema → derived from live data.
- config.yml: implicit preservation → explicit lossless round-trip commitment.
- Cleanup scope: expanded from binary+setup.ps1 to include seed, docs, smoke scripts, handbook, repo plumbing.

**What held:**
- Engine placement in `serve/kanban-engine/` (challenged as costly, defended as lowest coupling).
- Synchronous API (never challenged — FastMCP supports sync tools).
- No file locking / match existing concurrency (never substantively challenged).
- start_work/end_work in engine (challenged as scope expansion, defended as structural improvement).
- Package cost as one-time acceptable overhead (challenged twice, held both times).

**Final confidence:** 0.82
