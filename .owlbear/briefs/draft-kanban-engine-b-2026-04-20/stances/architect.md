# Architect Stance — Brief B (Kanban Engine API + MCP Adapter + Cockpit Surface)

**Panelist:** Architect
**Status:** HARDENED (post-Critic)
**Confidence:** 0.85

---

## Architectural Stance

Brief B's engine API must be a **thin, storage-agnostic contract layer** that fulfills every Brief A AC in a single round trip, exposes capability through type-level view facades (not runtime guards), and keeps projection logic co-located with the operations that need it. The engine is NOT a service — it's a library constructed by each consumer with a board root and accessed through typed views.

---

## Positions on Open Questions

### Q1: Optimistic-concurrency `updated` token — required or optional?

**Position: Optional-when-present at engine level; required by `CockpitEngineView`.**

The engine always returns `updated` in every mutation response. When a caller passes `updated`, the engine validates and raises `ConcurrencyError` on mismatch. When omitted, the engine proceeds without check. `CockpitEngineView.edit_task()` and `CockpitEngineView.move_task()` make `updated` a required parameter at the type level. `AgentEngineView` leaves it optional.

**Rationale:** The engine has one consistent behavior: validate when present, proceed when absent. Views set policy on whether the token is required. D13 establishes optimistic concurrency as the documented mutation guarantee. D11 explicitly defines claims as non-ownership tokens — claims do NOT serialize access. The only realistic conflict vector is concurrent mutation of unclaimed tasks, which is vanishingly rare in the single-user laptop deployment. Cockpit is stateful (load → edit → submit) and genuinely needs the token. MCP agents perform read→mutate in tight tool-call sequences where the race window is narrow.

**Trade accepted:** An MCP agent editing an unclaimed task concurrently with a Cockpit user wins silently. Acceptable for single-user deployment. The engine's behavior is consistent regardless — the split is view-level parameter policy, not engine-level semantics.

**end_work and OCC:** `end_work` is also a body-writing mutation (appends note, changes status, clears claim). Under D11's anonymous-claim model, there is no identity check — any caller can end_work on any claimed task. The zombie-writer path (crashed agent calls end_work after another agent re-claimed the task) is real. Brief B specifies: `end_work` optionally accepts `updated` at the engine level, same as edit_task/move_task. When present, the engine validates. The orchestrator is responsible for ensuring only one agent operates on a claimed task at a time (release before re-dispatch). This makes the concurrency model consistent across all mutations: validate when present, proceed when absent.

### Q2: Tighten clarity-gate predicate or keep loose?

**Position: Keep loose predicate. Document as-is.**

The current regex (`^\s*(-\s|\d+\.\s)` anywhere in body) plus the 9-tag escape set is sufficient. Tightening to require `## AC` heading would force migration of every existing task that uses informal bullet lists — high cost, no demonstrated false-positive problem.

**Rationale:** The gate's job is "has someone thought about this task enough to dispatch it?" not "does the task follow a specific markdown template." The 9-tag escape set already handles legitimate exceptions (research, docs, config tasks). If false positives become a real problem, tightening is a follow-up — but the landscape audit found no evidence of that.

**Trade accepted:** Loose matching may pass tasks that have incidental bullet points (e.g., a body with only `- TODO: flesh this out`). Risk is low: tasks reaching dispatch-active statuses have been through human or agent curation, so incidental-bullet false positives are uncommon. The cost of tightening (migrating all existing task bodies to use `## AC` heading convention) exceeds the cost of occasional false dispatch.

### Q3: Exact shape of `Section` model

**Position: `Section = {heading: str | None, level: int, content: str}`**

Extends D7 with `level: int`. Level 0 = preamble (content before any heading). Level 2 = `##`, level 3 = `###`, etc. This is a non-breaking extension of D7's `{heading, content}` — it adds precision without contradicting.

**Parsing rules:**
- Each markdown heading at any level produces a Section entry.
- A `## Main` section's content runs until the next same-or-higher-level heading (`##` or `#`).
- `### Sub` sections within that range also get their own entries.
- `show_task(section="Main")` matches level-2 headings and returns content including nested subsections.
- **Multiple matches:** When a heading appears more than once (e.g., two `## Audit` blocks), all matching sections are concatenated in document order. `guidance` reports occurrence count. This satisfies Brief A AC12.
- **Missing section:** When the heading isn't found, `body: null` and `missing_sections: ["<section>"]`. Satisfies AC11.
- Pre-heading prose → `Section(heading=None, level=0, content="...")`.
- Empty body → `body: []` (empty list).
- Body with only prose → `[Section(heading=None, level=0, content="...")]`.
- **Fence-aware parsing:** Content inside ``` fences is never treated as headings, even if it contains `## Heading` literals.

**Rationale:** Brief A's section projection operates on `## Heading` — level 2. Without `level` in the model, the engine can't distinguish `## AC` from `### AC` in a filter operation. Task bodies routinely mix `##` and `###`. Dropping level flattens semantic hierarchy and makes section projection ambiguous.

**Trade accepted:** Parser must be fence-aware, adding complexity. Worth it — code blocks with heading-like content are real in task bodies (especially builder/reviewer notes with markdown examples).

### Q4: Exception taxonomy

**Position: Shallow class hierarchy with `code` field for programmatic discrimination.**

```
KanbanError (base)
  ├── TaskNotFoundError          → MCP ToolError / Cockpit 404
  ├── ValidationError            → MCP ToolError / Cockpit 422
  │     └── TransitionError      → MCP ToolError / Cockpit 409
  ├── ConcurrencyError           → MCP ToolError / Cockpit 409
  ├── ClaimError                 → MCP ToolError / Cockpit 409
  └── CorruptionError            → MCP ToolError / Cockpit 500
```

Every exception carries:
- `code: str` — machine-readable discriminator (e.g., `"invalid_transition"`, `"stale_update"`, `"already_claimed"`, `"duplicate_id"`)
- `message: str` — human-readable, safe for wire (no file paths, no config internals)

**Rationale:** Class hierarchy allows adapters to catch at the granularity they need. Cockpit catches `ConcurrencyError` → 409; MCP catches `KanbanError` → ToolError. A flat enum forces switch-case mapping in every adapter. The hierarchy is shallow (max depth 2) — not over-engineered. The `code` field gives finer discrimination within a class (e.g., `ValidationError` with `code="body_and_append"` vs `code="invalid_priority"`) without needing a class per error.

`TransitionError` is a subclass of `ValidationError` because an invalid transition IS a validation failure — but adapters need to distinguish it (409 vs 422). This is the one exception to the flat-children rule, and it's justified.

**Trade accepted:** Six exception classes is more than today's two (ValueError, FileNotFoundError). The mapping table in Brief B makes migration mechanical.

### Q5: `pick_waves` algorithm

**Position: Greedy priority-first partitioning, fully deterministic, with updated gate set.**

Algorithm:
1. Compute dispatchable set using the **full Brief B gate set** (NOT the current 7 gates):
   - Terminal status exclusion (archived)
   - Blocked exclusion (blocked=True)
   - **dep_status gate:** exclude tasks with `dep_status="blocked"` (AC27); tasks with `dep_status="redirect"` are dispatchable but carry redirect guidance
   - Claimed exclusion (claimed_at present and not expired)
   - Tag filter (if provided)
   - TDD gate (in-progress only): `## Test-Writer Notes` or tag in escape set
   - Clarity gate (active statuses): loose regex
2. Sort by `(PRIORITY_RANK, STATUS_RANK, task_id)` ascending. Task ID as final tiebreaker guarantees determinism. Ranks derived from ordinal position in config `priorities`/`statuses` lists (see Q6).
3. For wave 0: greedily take tasks from sorted order, skipping any task that has a dependency edge (in either direction) with an already-selected task in this wave. Specifically, skip task X if: (a) X depends on any task already in the wave, OR (b) any task already in the wave depends on X. Fill up to `wave_size`.
4. Mark wave-0 tasks as "scheduled." For wave 1: repeat from remaining pool. Repeat for `max_waves`.
5. Return `list[Wave]`. Empty remaining pool = fewer waves returned.

**Rationale:** Greedy partitioning is simple, deterministic, and produces good-enough waves for a single-project laptop system. The critical change from current `pick_dispatchable` is the dep_status gate: tasks blocked by archived-wontfix/dropped dependencies are excluded per Brief A AC27, and redirect dependencies produce guidance per AC28. The deterministic tiebreaker (task_id) means identical state always produces identical waves, which is critical for testing and debugging.

**Trade accepted:** Greedy can produce suboptimal wave packing (a high-priority task may push a lower-priority independent task to wave 2 unnecessarily). Acceptable — optimality is not the goal; correctness (no intra-wave dep violations) and predictability are.

### Q6: `agent_map` config shape and rank derivation

**Position: `agent_map: dict[str, str]` — status maps to exactly one agent name. Rank is derived from config list order, not stored in `agent_map`.**

Example in config.yml:
```yaml
statuses: [backlog, todo, in-progress, review, docs, done]  # ordinal = STATUS_RANK
priorities: [critical, important, needed, low]               # ordinal = PRIORITY_RANK
agent_map:
  backlog: researcher
  todo: test-writer
  in-progress: builder
  review: reviewer
  docs: doc-writer
  done: auditor
```

`STATUS_RANK` = index of status in the `statuses` list. `PRIORITY_RANK` = index of priority in the `priorities` list. The hardcoded `PRIORITY_RANK`/`STATUS_RANK` constants in current `dispatch.py` are replaced by config-derived ordinals. This resolves the context.md B1 requirement for "status → agent name + rank" without polluting `agent_map` with rank numbers — rank is implicit in the already-ordered config lists.

**Default when `agent_map` absent:** Engine uses a hardcoded fallback mapping matching current `dispatch.py` behavior. When `agent_map` is present, it must cover all statuses listed in `statuses` config. Missing mapping for any active status → `ValidationError` at engine construction (fail-fast). This ensures every `DispatchEntry` always has a non-null `agent` — no null-agent tasks leak into waves.

**Rationale:** The pipeline has one agent per status by design. Multi-agent statuses don't match the system model — orchestrator-level routing doesn't belong in board config. Deriving rank from config list order eliminates a separate rank field while making the ordering explicit and user-editable.

**Trade accepted:** If the pipeline evolves to have multi-agent statuses, this needs a schema migration. Acceptable — YAGNI applies.

### Q7: `claim_timeout` format

**Position: Support `s`/`m`/`h`/`d` suffixes. Validate at config load time.**

Pydantic validator on `BoardConfig.claim_timeout` parses the suffix and converts to seconds internally. Invalid format → `ValidationError` at engine construction, not at first claim attempt.

**Rationale:** The current delayed failure (only surfaces on first claim) is a latent bug found in the landscape audit (Red Flag #4). Config-load validation is fail-fast. Adding `s` and `d` is nearly free and useful — `s` for testing, `d` for long-running manual tasks.

**Trade accepted:** Existing configs with valid `h`/`m` suffixes keep working. New suffixes are additive. No migration cost.

### Q8: Wire format for body between engine and MCP/Cockpit

**Position: `body: str` on the wire for ALL consumers. Engine-internal `list[Section]` does not leak to any wire format.**

Both MCP and Cockpit receive `body` as rendered markdown string. Section projection (`show_task(section=...)`) returns the filtered markdown string — the matching section content rendered as markdown, not as JSON structure. No consumer needs `list[Section]` on the wire.

The engine's internal `list[Section]` exists for:
1. Section projection (filter and render matching sections)
2. Body modification operations (append to section, replace section)
3. Validation (no-op detection, section existence checks)

**Rationale:** MCP callers are LLM agents — they consume markdown natively. Cockpit currently renders body as markdown in the task detail view. No consumer has demonstrated a need for structured body on the wire. If Cockpit later needs structured sections for a rich editor, that's a separate Cockpit endpoint added at that time — not pre-built now (YAGNI). This avoids the trap of using views to carry different representation dialects for the same concept, which would exceed their intended role as capability filters.

**Brief A impact:** None. Brief A already defines the return shapes that carry these fields: `ListTasksResponse.guidance`, `ShowTaskResponse.missing_sections`, `ShowTaskResponse.guidance`, `PickTasksResponse.guidance`, `TaskSummary.dep_status`. The engine's job is to populate these fields per Brief A's projection schemas. No Brief A wire revision needed.

**Trade accepted:** If Cockpit later wants structured body for a rich markdown editor, it requires a new endpoint/projection. Acceptable — YAGNI.

### Q9: Cockpit `/api/sessions` response

**Position: Narrow to running + stuck only. Drop closed-session listing.**

Response: `list[ActiveSession]` where:
```
ActiveSession {
  task_id:    int
  task_title: str
  status:     str
  claimed_at: str       # ISO 8601
  is_stuck:   bool      # claimed_at + timeout < now
}
```

No `agent` field. Per D11, `claimed_by` is dropped — claims are anonymous boolean-with-timestamp. The admin panel shows "task X is stuck, claimed at time Y" and the admin can release it. Agent identity is irrelevant for the release action.

**Rationale:** Per D10, `activity.jsonl` is demoted from engine semantics. Closed-session history derived from task state alone would require iterating all archived tasks for `claimed_at` residue — expensive and semantically wrong (archived tasks had their claims cleared). The only meaningful session data derivable from current task state is "what's claimed right now and is it stuck?" That's exactly what the Cockpit admin panel needs.

**Trade accepted:** Loss of both historical session data and agent identity on sessions. User accepted historical loss in D10. Agent identity loss follows from D11. If either matters later, it's Brief C's concern (a proper audit/identity store).

---

## Additional Architectural Concerns

### AC-1: View delegation pattern — no shared base, no protocol overhead

Both `AgentEngineView` and `CockpitEngineView` hold a `_engine: KanbanEngine` reference. Shared read methods are one-line delegations on each view. No common abstract base class, no Protocol.

**Why:** With ~6 shared reads, the duplication is 6 one-liners per view. An ABC or Protocol adds an import, a registration, and a maintenance burden for zero runtime benefit. The views are constructed by the adapter layer — there's no polymorphic dispatch over "some view" at any call site. Each adapter knows exactly which view type it has.

### AC-2: `pick_waves` projection coupling is appropriate

`pick_waves` returns `list[Wave]` containing `DispatchEntry` projections (id, status, priority, title, tags, agent). This couples dispatch logic with a dispatch-specific projection. That's **correct coupling** — the alternative (returning IDs only) forces callers into N+1 `show_task` calls. `DispatchEntry` is purpose-built and narrow. If dispatch needs evolve, the projection changes in one place (engine), and both MCP and orchestrator consumers get the updated shape.

### AC-3: Engine signals capability via construction, not introspection

The engine doesn't know who's calling. MCP constructs `engine.agent_view()`; Cockpit constructs `engine.cockpit_view()`. The view's type signature IS the capability contract. No runtime `engine.capabilities()` method, no feature flags, no "am I MCP or Cockpit?" check. This is the cleanest separation — capability is a compile-time (type-check-time) concern, not a runtime concern.

### AC-4: `agent_map` stays in config.yml, not a separate file

`agent_map` is 6-8 lines of `status: agent` pairs. It belongs in `config.yml` alongside `statuses`, `priorities`, and `defaults` — same category of board-level configuration. A separate file adds file-loading complexity, sync risk, and cognitive overhead for zero benefit at this scale.

### AC-5: Body parsing belongs in engine, not storage

Storage returns raw body as `str`. The engine's `body_parser` module converts to `list[Section]`. This keeps storage truly agnostic (it stores/retrieves strings) and puts domain knowledge (section semantics, fence-aware heading splitting) in the engine where it belongs. Storage never needs to understand markdown.

### AC-6: `claimed_by` removal is a behavioral change — document migration

D11 drops `claimed_by`. Current code allows same-agent re-claim (idempotent). Without `claimed_by`, ALL claims on active-claimed tasks are rejected until timeout expires. This means the orchestrator MUST explicitly release before re-dispatching after an agent crash. This is stated in D11 but needs prominent callout in Brief B as a behavioral migration: existing orchestrator code that relies on "re-claim by same name succeeds" will break.

### AC-7: `dep_status` computation is engine-side, per-task, on-demand

`dep_status` is computed when projecting `TaskSummary` or `DispatchEntry`, not stored. The engine iterates `depends_on`, checks each dep's archival state and reason, applies the D-priority rule (any `blocked` → `blocked`; any `redirect` → `redirect`; else `ok`; no deps → `null`). This means `list_tasks` does N dependency lookups per task — but with the engine's task cache, those are memory lookups, not file reads. No N+1 storage cost.

### AC-8: Transition validation in engine, not adapter

`move_task` validates that the requested status transition is legal (per `valid_transitions` from config). Currently landscape shows Cockpit does this check [mutation.py]; MCP does not. Brief B specifies: engine owns transition validation. Adapters may do pre-checks for UX (Cockpit showing only valid targets in dropdown), but the engine is the enforcement point. This prevents MCP from bypassing transition rules.

### AC-9: `sweep()` call responsibility and concurrent safety

Per D18, all consumers must call `sweep()` on init. `sweep()` is a mutation (clears expired claims, moves orphaned archives). The dangerous race: consumer A reads an expired claim on task X, consumer B re-claims task X (placing a fresh claim), consumer A's stale sweep clears the fresh claim thinking it was the expired one.

Brief B specifies: `sweep()` must be safe against concurrent claim mutations. Specifically, a sweep must not clear a claim whose `claimed_at` value differs from the expired value it observed. This is a compare-and-clear semantic — the implementation strategy (atomic check, optimistic compare, file lock) is Brief C's freedom. Brief B's contract is: sweep never destroys a claim that was placed after the sweep read.

### AC-10: Error message safety

Per landscape Red Flag #7, current `ToolError(str(exc))` leaks file paths and config internals. Brief B's exception taxonomy (Q4) specifies that `message` on every `KanbanError` is wire-safe — no file paths, no internal state. The MCP adapter maps `KanbanError.message` directly to `ToolError` message. The Cockpit adapter maps to HTTP error response body. No additional sanitization needed in adapters.

### AC-11: AC30 timestamp prefix — behavioral change from `[[YYYY-MM-DD]]` to full ISO

Per D20, `append_body(timestamp=True)` must prepend full ISO 8601 with offset (e.g., `2026-04-20T14:30:00+00:00`). Current behavior prepends `[[YYYY-MM-DD]]` (date only). This is a deliberate behavioral change. Existing task bodies retain their historical `[[YYYY-MM-DD]]` prefixes — no retroactive rewrite. New appends get full ISO. Brief B documents this as a known format inconsistency in existing task bodies that Brief C's migration may optionally normalize.

---

## Key Trade-offs Summary

| Decision | Accepted Trade | Mitigation |
|----------|---------------|------------|
| Q1: Optional OCC for MCP | Silent MCP-wins-over-Cockpit on unclaimed edits | Single-user laptop; engine behavior is consistent |
| Q1: end_work OCC optional | Zombie-writer path if orchestrator misbehaves | Orchestrator owns agent lifecycle |
| Q2: Loose clarity gate | May pass under-specified tasks | Cost of tightening exceeds cost of false dispatch |
| Q3: Level in Section model | Parser complexity (fence-aware) | Well-defined parsing rules; tested edge cases |
| Q4: Class hierarchy | 6 exception classes vs today's 2 | Mapping table makes migration mechanical |
| Q5: Greedy waves | Suboptimal packing | Correctness > optimality for <50 tasks |
| Q6: Single-agent map, fail-fast | Incomplete agent_map blocks startup | Fail-fast is correct — silent null-agent worse |
| Q8: String body only on wire | Cockpit loses structured body option | YAGNI; add endpoint when needed |
| Q9: Running+stuck only, no agent | Loss of session history + agent identity | D10 + D11 already accepted this |
| AC-6: `claimed_by` removal | Breaks same-agent re-claim | Orchestrator must release first |
| AC-9: Compare-and-clear sweep | More complex sweep implementation | Brief C's freedom; correctness requirement |
| AC-11: AC30 format change | Inconsistent timestamps in existing bodies | No retroactive rewrite; Brief C may normalize |

---

## Warnings

1. **Body parser is the highest-risk new component.** Fence-aware markdown section splitting has edge cases (nested fences, indented fences, HTML comments containing headings). Brief B must specify exhaustive parsing rules or accept that the parser will have a "best effort" contract with documented limitations.

2. **`dep_status` computation on `list_tasks` is O(N×D) where D is average dep count.** For the current task volume (<200 active), this is fine. If task volume grows significantly, `dep_status` may need caching or storage-level indexing (Brief C concern).

3. **`agent_map` introduction requires config migration.** Every existing `config.yml` lacks `agent_map`. Engine must have a default (either hardcoded fallback or "unmapped status → null agent"). Brief B should specify the default behavior when `agent_map` is absent or incomplete.

4. **Cockpit mutation rewire (D21) will temporarily break Cockpit tests.** Current tests assert against direct engine calls. After rewire to `CockpitEngineView`, test setup changes. This is implementation-phase concern but Brief B should note it.

---

**Confidence: 0.87** — Two Critic cycles completed. Wave algorithm corrected for bidirectional dep check. end_work concurrency gap closed with consistent OCC model. Sweep race addressed with compare-and-clear contract. Null-agent eliminated via fail-fast config validation. Remaining uncertainty: body parser fence-awareness depth (Q3) and dep_status computation scaling beyond ~200 tasks.
