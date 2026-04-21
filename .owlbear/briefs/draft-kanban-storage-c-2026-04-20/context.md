# Brief C — Kanban Storage Layer — Context

**Status:** M1 (Understanding) — locked
**Tier:** Studio (declared in kickoff)
**Aperture:** Wide (no backwards compat; quality > everything)
**Predecessor:** Brief B (`draft-kanban-engine-b-2026-04-20`) — engine API contract, frozen.
**Consumer:** the Brief B engine. Storage is opaque under the engine; storage's only client is the engine implementation.

---

## §1 — Problem Statement (M1, locked)

The kanban storage layer must underwrite the Brief B engine API as an opaque, atomicity-correct, low-concurrency persistence primitive. Brief B raised the integrity bar — D41 atomicity, D11 (drop `claimed_by`), D14 (UTC + offset), D19 (duplicate-ID corruption), D27 (`CorruptionError` semantics). Current storage (filesystem-as-DB, YAML frontmatter + free-form Markdown body) has produced zero data corruption in three months but was not designed against D41 and leaves contract enforcement to downstream regex.

Storage's consumers are mediated and reliable: the engine is the only steady-state writer; MCP and Cockpit the only readers; the user does not hand-edit files (agents go through MCP). The decision space splits into two logically separable axes:

### Axis A — Task shape (backend-agnostic, logically prior)

Is the task body free-form Markdown prose, or a strictly-validated structured object (named sections enforced at write time)? Today's body is free-form, and the predicate DSL (D64) checks it via regex over rendered Markdown — fragile by construction. If sections were first-class structured data (JSON object keys, parsed Markdown sections validated at write time, or relational rows), the predicate DSL becomes an object-presence check, contract violations are caught at write time not predicate-eval time, and pipeline reliability climbs. **This may matter more than corruption surfacing** because it directly governs whether agent handoffs can be trusted. The shape question is settled before the backend question because both candidate backends can implement either shape.

### Axis B — Persistence backend

Filesystem (Markdown / JSON files) vs SQLite. Four real differentiators, each carrying real weight; the panel argues them on technical merit, no pre-decided burden of proof:

1. **Atomicity & corruption.** SQLite gives transactional D41 for free; filesystem requires explicit rename/lock/fsync primitives. Both can satisfy the contract; one is structurally easier.
2. **Git diff-reviewability of task-mutating PRs.** Markdown / JSON files produce per-task diffs that human PR reviewers can read directly (e.g. when a brief approval generates 30 tasks on a feature branch). SQLite produces an opaque blob diff — history exists but isn't human-readable in PR view. Real, named asymmetry; matters because the board *is* git-tracked and PRs *are* reviewed (see §4).
3. **Cross-branch mergeability.** If parallel branches ever create tasks (hasn't happened, plausibly will), filesystem supports clean git merges via rename / ID-rewrite / per-file diff. SQLite is unmergeable as a binary blob — parallel branches would have to serialise board work. SQLite forecloses the option.
4. **Structure-enforcement ergonomics.** If Axis A picks structured shape, JSON files and pure-relational SQLite both implement it cleanly; mixed (JSON-in-SQLite TEXT columns) is worst-of-both-worlds and is not a serious option.

Observation (not a verdict): three of the four differentiators (2, 3, 4 in the JSON-files reading) lean filesystem-side; SQLite's structural advantage is concentrated in #1. The panel decides whether SQLite's atomicity-correctness advantage outweighs the other three.

Brief C must produce a single normative storage contract that:

- (a) supports D41 atomicity end-to-end,
- (b) defines the on-disk shape **and the canonical task-shape schema** that backs every projection field in `paper-integration.md` §2 *and* every section-name referenced by predicates,
- (c) settles D40 body-round-trip semantics in light of structured-section enforcement,
- (d) specifies migration for D11 + D14 *and* for any structural reshaping introduced by (b),
- (e) names the predicate DSL extensions beyond D64 in the new structural model,
- (f) decides corruption modes beyond D19 surfaced at read time and how the storage layer signals them to the engine.

The contract must be specific enough that engine-implementation tasks can be derived directly from it, the same way `paper-integration.md` is the source for engine-implementation decomposition.

## §2 — Frozen contract (cannot be touched by Brief C)

- Brief B engine method signatures (paper §1).
- Role-view exposure matrix (paper §5).
- Error taxonomy + canonical error-code list (D27 + D57).
- Projection schemas: `TaskSummary`, `TaskFull`, `DispatchEntry`, `Wave` (paper §2).
- `BoardConfig` parameter shape (D62/D63/D64/D65). **Note:** the predicate DSL *key set* is explicitly extensible per Brief B §6 + D64 — Brief C may add new keys (regex matchers, frontmatter requirements, etc.) as discrete decisions; this is not a frozen surface.
- `pick_tasks` 4-step pipeline (paper §1.3).
- Adapter responsibilities (brief §4).

If Brief C surfaces a need to change any of the above → file a Decision-Request task against Brief B; do not silently change the contract.

## §3 — Forbidden in Brief C

- No `agent_name` parameter anywhere (D33 + D43).
- No `claimed_by` on disk (D11).
- No diagnostic log written by storage (D43).
- No partial-application paths — storage must support engine D41 atomicity end-to-end.

## §4 — M1 Findings (background for panel)

- **Concurrency reality.** Three races in three months, all from intentional dual-orchestrator testing. Single laptop. Defensive machinery is correctness-under-accidental-race only, not throughput.
- **Scale.** ~1000 tasks lifetime, ~150 active on board, 200–500 archive. Trivial for either physical model.
- **Hand-edit reality.** Agents do not hand-edit task body files outside the engine. MCP has all the tools they need.
- **Cockpit availability.** Shipping today; no organisational forcing-function value left in keeping a "human can `cat` a task" fallback.
- **Other databases in the project.** `memory.db` (SQLite, will follow kanban's choice). `knowledge` (SQLite + vector + graph, stays as DB regardless).
- **Historical data failures.** Zero with Markdown. The only ever issue was a CRLF/LF mismatch in a defunct Windows EXE viewer — view-only, not data.
- **Git-tracked assumption (explicit).** The board (`.owlbear/kanban/`) is git-tracked; task-creation and task-mutation changes routinely appear in feature-branch PRs and are human-reviewed before merge. This is the operating assumption that makes Axis B differentiator #2 (diff-reviewability) and #3 (mergeability) carry real weight.
- **Migration scope (locked in M3).** Archive is **not** migrated. D11/D14/any-Axis-A reshape touches **only the ~150 active task files**. Archive files retain their Go-era shape; the read path tolerates them via Pydantic `extra="allow"`. Migration cost is therefore minimal; it is not a valid argument for or against any backend or shape choice.

---

## §5 — Outcomes (M2, locked)

Brief C's consumers are the **planner subagent** at M6 (decomposition into atomic tasks), the **builder agents** executing those tasks (need a normative contract to code against), and the **user** (must verify what's being built). The five outcomes below are framed against those three consumers.

1. **Planner can decompose Brief C without inventing contract decisions.** Every storage primitive, every frontmatter rule (or schema field), every predicate-DSL extension has a locked decision in `decisions.md`. Zero `decision-request` tasks back to ideation during M6 decomposition.

2. **D41 atomicity is structurally guaranteed for steady-state writes; migration is transactional-batch with safe re-run.** Every engine call (one logical mutation per Brief B D41) maps to one atomic storage primitive (transaction or atomic-rename + fsync) — partial-state engine writes are physically impossible. Migration is multi-artifact by nature and is specified as a transactional batch with idempotent re-run on partial failure (no physical-impossibility claim there). A reviewer asking "what happens if this fails midway?" finds a one-line answer in the Brief for both cases.

3. **Predicate evaluation is an object check, not a regex hunt.** After Brief C, the D64 predicate DSL keys (`required_sections`, `require_list_in_section`, `test_section_or_non_impl_tag`) read from a structured task object. No regex against rendered Markdown in the engine. *(Conditional on Axis A landing structured — if the panel argues for free-form prose, this outcome reshapes.)*

4. **Migration is one command, idempotent, and verifiable.** D11/D14 cleanup, plus any structural reshape introduced by Axis A, runs on existing tasks once; running twice is a no-op; partial-migration recovery is safe. The user can verify what changed and re-run if needed. The verification mechanism is Axis-B-dependent (per-task git diff for filesystem; before/after report for SQLite) and is locked at M4.

5. **Corruption is loud and early.** Whatever corruption modes Brief C surfaces (D19 + extensions) are detected at read time with `CorruptionError(code, user_message)` naming the file/row and what's wrong. No silent fallthrough into a degraded engine state.

6. **Body round-trip is predictable.** Whatever D40 lands on (byte-exact, normalised, or structured-fields-with-prose-blocks), agents can save a body and read it back without unexpected normalisation surprises; the round-trip rule is documented in the Brief and a user spot-check confirms it. *(Conditional on Axis A: if the body lands strictly structured, this outcome is satisfied as a consequence of structure-enforcement and may be folded into outcome 3 at M4.)*

No performance outcome — current scale (~1000 tasks lifetime, ~150 active) is trivial for either backend; adding a perf number would be designing for hypothetical workload increase against the user's stated YAGNI.
