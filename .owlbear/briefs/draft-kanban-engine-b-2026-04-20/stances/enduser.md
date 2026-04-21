# End User Stance — Brief B: Kanban Engine API

**Panelist:** End User (UX practitioner)
**Brief:** Kanban Engine API & MCP Implementation (Brief B)
**Consumers:** (1) Calling agents via MCP — cost = context budget + tool-call count + error-recovery friction. (2) Human operator via Cockpit — laptop user debugging stuck claims and reorganizing the board.
**Confidence:** 0.85 — high on Q1/Q2/Q9/C2/error model; moderate on Q5 wave_reason token economics (need real dispatch traces to validate).

---

## Open Question Positions

### Q1 — Optimistic Token: Optional (ETag-Style)

**Position: Token is optional on `edit_task` / `move_task`. If passed, engine enforces; if omitted, engine proceeds without conflict check.**

- **MCP agent pain if required:** Every edit demands a pre-fetch round trip to obtain the `updated` token. Agents work sequentially on claimed tasks — the orchestrator is single-threaded, conflicts are near-impossible on a single laptop. Requiring the token punishes the common case (no conflict) to protect against the rare case (concurrent edit).
- **Cockpit human pain if omitted:** The UI renders the task and naturally holds the token. The current 409-on-stale flow is correct for Cockpit — the human refreshes and retries. No new pain.
- **Asymmetry rationale:** This is standard ETag semantics (`If-Match` is optional in HTTP). Clients that want safety opt in. Clients that don't, skip the overhead. MCP callers that read-then-edit in the same cycle can pass the token cheaply; callers that blindly mutate (e.g., `end_work` after a claim) don't need it.
- **Conflict resolution:** When Cockpit and MCP both edit the same task, the Cockpit human's edit should win — they're the operator overriding the agent. Optional MCP token + required Cockpit token naturally produces this: the human gets the 409 and can retry with intent; the agent's unprotected write succeeds or is silently overwritten by the next human save.

### Q2 — Clarity Gate: Tighten via Structured Body Model

**Position: Tighten the clarity-gate predicate to require a Section with heading "AC" containing ≥1 list item. Preserve the 9-tag escape set. No raw-text migration needed.**

- **Why the Critic changed my mind:** D7 specifies `body: list[Section]`. If the engine's internal model is already structured, the gate checks `any(s.heading == "AC" for s in task.body)` — a structural query, not a raw regex. Existing tasks with `## AC` headings already parse correctly into Section objects. No markdown rewriting needed.
- **Escape tags survive:** Tasks tagged `research`, `docs`, `type:config`, `type:docs`, `test`, `type:test`, `agent`, `quality`, or `type:user-action` bypass the AC requirement. This matches current behavior.
- **Agent ecosystem need:** Agents need tasks with clear acceptance criteria to evaluate their own work. The loose predicate (any bullet point anywhere) produces false positives — a random note list passes the gate, the agent dispatches, finds no real AC, and wastes an entire cycle. Structural checking eliminates this class of waste.
- **Migration cost:** Zero for tasks that already have `## AC` headings. Tasks without them fail the gate and stay undispatched until a human (or planner agent) adds the heading. This is a quality investment, not busywork — those tasks weren't ready for dispatch anyway.

### Q5 — pick_waves Algorithm: Greedy, Deterministic, Self-Explaining

**Position: Greedy by priority (PRIORITY_RANK), deterministic tie-break on task ID (lower wins). Include `wave_reason: str` on DispatchEntry by default.**

- **Determinism over fairness.** The orchestrator needs the same board state to produce the same wave composition on repeated calls. Any randomization or "fairness" balancing makes planning non-reproducible. Lower ID tie-break is arbitrary but stable.
- **Self-explanation pays for itself.** When a wave assignment surprises the orchestrator (or the human inspecting dispatch), `wave_reason` answers "why this task, why this wave" without a follow-up `show_task` call. Cost: ~10-20 tokens per entry. Savings: avoiding an entire debugging cycle when dispatch seems wrong.
- **Trivial reasons omittable.** Engine may omit `wave_reason` when the assignment is obvious (standard priority ordering). This reduces noise without losing diagnostic value for edge cases (dep-gated promotion, escape-tag dispatch).

### Q9 — Cockpit Sessions: Narrow + `last_end_outcome` Field

**Position: D10 is correct — engine drops closed-session history. Add `last_end_outcome: str | None` to the task model as a lightweight substitute.**

- **What the human loses with D10:** The ability to answer "what happened last time this task was worked on?" without reading the full body. The stuck-session display shows currently-claimed tasks, but the human debugging a pipeline stall needs recent history, not just the present.
- **Where the data lives today:** `activity.jsonl`, which D10 demotes to audit-only. After D10, this data is outside engine scope.
- **Proposed substitute:** `last_end_outcome` is set by `end_work` to the outcome value ("success", "reject", "release"). Cleared on any `move_task` or status change not via `end_work` (prevents stale values after manual admin moves). Persisted in frontmatter — cheap, no history log needed.
- **UX payoff:** Cockpit task-list view shows "last outcome: reject" in one glance. The human sees that the builder rejected this task without drilling into the body. Combined with stuck-session display (currently claimed + expired), this covers 90% of debugging scenarios without any session history log.

### Q3 — Section Model (drive-by)

Section should preserve heading level (`##` vs `###`). Pre-heading prose = Section with `heading: None`. Trailing content after last heading = final Section. This matches human mental model of markdown structure.

### Q4 — Exception Taxonomy (drive-by)

Covered below under Error Model.

### Q6 — agent_map Shape (drive-by)

`dict[str, str]` (status → one agent). Multi-agent statuses add complexity with no current consumer need. YAGNI.

### Q7 — claim_timeout Format (drive-by)

Support `s/m/h/d` suffixes with Pydantic validation at config-load time. Fail-fast, not delayed failure on first claim.

### Q8 — Body Wire Format (drive-by)

Brief A's `body: str` wire shape should stay as markdown string for MCP callers. The structured `list[Section]` model is internal to the engine. MCP callers receive rendered markdown; Cockpit receives rendered markdown for display. Section projection is an engine operation, not a wire-format concern.

---

## Additional Usability Positions

### Error Model: Structured ToolError (Code + Message)

**Position: Engine exception taxonomy maps to structured ToolError payloads with `code: str` and `message: str`. No remediation hints.**

- **Current state:** `ToolError(str(exc))` leaks file paths, config details, and Python exception class names. An LLM parsing "FileNotFoundError: /Users/markus/.owlbear/kanban/tasks/42-fix-sweep.md" must guess whether to retry, re-ID, or escalate.
- **Proposed:** Canonical error codes: `TASK_NOT_FOUND`, `INVALID_STATUS`, `ALREADY_CLAIMED`, `CLAIM_EXPIRED`, `CONCURRENCY_CONFLICT`, `INVALID_TRANSITION`, `DANGLING_REFERENCE`, `VALIDATION_ERROR`, `CORRUPTION_DETECTED`. Each code maps to a specific exception class in the engine taxonomy.
- **Why no hints:** Hints are paternalistic and frequently wrong. Code + message is enough for deterministic retry logic: agent maps `TASK_NOT_FOUND` → re-fetch task list; `CONCURRENCY_CONFLICT` → re-read and retry; `ALREADY_CLAIMED` → wait or skip. The agent's orchestration logic handles remediation, not the engine's error string.
- **Cockpit mapping:** Same codes map to HTTP status codes. `TASK_NOT_FOUND` → 404, `CONCURRENCY_CONFLICT` → 409, `VALIDATION_ERROR` → 422, `ALREADY_CLAIMED` → 409.

### Guidance Field: Actionable-Only Contract

**Position: `guidance: list[str]` emitted only when actionable. Empty array = silent success. No informational noise.**

- **Anti-pattern:** `guidance: ["3 tasks found"]` wastes tokens and teaches agents to ignore guidance. If guidance is always present, agents learn to skip it.
- **Correct pattern:** Guidance appears when the caller should change behavior: `"dep_status redirect on task 42 — follow archival_refs"`, `"section 'AC' found 3 times — occurrence count: 3"`, `"claim expires in 4 minutes"`.
- **Contract:** If `guidance` is non-empty, the caller SHOULD read it. If empty, no action needed. This makes guidance a reliable signal, not background noise.

### Multi-Wave: Return Multiple, Document as Advisory

**Position: Return up to `max_waves` waves. Waves 2+ are advisory — stale after any board mutation.**

- **Value:** The orchestrator gets a planning horizon: "after this wave, here's what could come next." This aids dispatch sequencing and resource estimation.
- **Staleness risk:** Wave 2 depends on wave 1 completing. By dispatch time, wave 1 outcomes may have changed the board (new blocks, resolved deps, status transitions). Wave 2 as dispatched could be wrong.
- **Mitigation:** Document that waves 2+ become stale after ANY board mutation. The orchestrator's natural loop (dispatch wave → await results → re-call `pick_waves`) handles this. No explicit staleness signal needed — the re-call replaces stale waves with fresh ones.

### Stuck Sessions Without Closed History: Viable with `last_end_outcome`

**Position: Stuck-session display is useful without closed-session history, but only IF `last_end_outcome` exists on the task model.**

- Without `last_end_outcome`: the human sees "task X is stuck (claimed 3h ago)" but cannot see what happened previously without drilling into the body. Debugging friction is high.
- With `last_end_outcome`: the human sees "task X is stuck (claimed 3h ago, last outcome: reject)". Immediate context — the builder rejected it, someone re-dispatched it, now it's stuck again. One-glance diagnosis.
- Full closed-session history remains Brief C's concern. `last_end_outcome` bridges the gap cheaply.

---

## C2 — Role View Ergonomics

**Position: Role views (`AgentEngineView`, `CockpitEngineView`) are the correct pattern. They must carry forwarded method docstrings.**

- **Discoverability wins:** A Cockpit developer adding a mutation route types `cockpit_view.` and sees only valid methods via IDE autocomplete. Calling `claim_task` from Cockpit is a type error, not a runtime surprise discovered in production.
- **Comparison with raw engine + docstring:** The docstring contract ("Cockpit may only call these 8 methods") is invisible to the type checker, invisible to autocomplete, invisible to new developers who don't read the README. The deny-list in `adapter.py` today is a runtime guard that boundary tests must cover — one missed test and the boundary leaks.
- **Docstring forwarding requirement:** If `CockpitEngineView.edit_task()` silently delegates to `engine.edit_task()`, a developer hovering the method in their IDE sees no documentation. The view class must carry the method signature and docstring — either via explicit forwarding or a `__doc__` delegation pattern. Without this, the developer is forced to trace through to engine.py, which defeats the discoverability benefit.

---

## Warnings

1. **`last_end_outcome` is a model addition.** It adds a field to every task and requires `end_work` to write it, plus `move_task` to clear it. This is small but crosses the "no-implementation" boundary if not carefully scoped as a model-only spec.
2. **Tightened clarity gate will block existing tasks.** Even without raw-text migration, tasks lacking `## AC` headings will stop dispatching. The human must be warned at deploy time, and `list_tasks(blocked=True)` should surface gate-blocked tasks distinctly from dep-blocked tasks.
3. **`wave_reason` adds token weight to every dispatch.** If wave sizes grow or dispatch frequency increases, the cumulative token cost needs monitoring. Consider a `verbose: bool` parameter on `pick_waves` if this becomes a problem.
4. **Optional optimistic token means MCP callers can unknowingly overwrite Cockpit edits.** The asymmetry is intentional (operator override wins), but agents that read-then-edit across multiple tool calls should be encouraged to pass the token via guidance.

---

## Key Trade-offs

| Decision | Gains | Costs |
|----------|-------|-------|
| Q1: Optional token | Zero MCP overhead for common case; natural operator-override semantics | Silent overwrites possible when MCP omits token during Cockpit concurrent use |
| Q2: Tighten via structured model | Eliminates false-positive dispatches; zero raw-text migration | Tasks without `## AC` stop dispatching until fixed; escape-tag set must be maintained |
| Q5: wave_reason | Self-explaining dispatch; fewer debugging follow-ups | 10-20 tokens per DispatchEntry; noise risk for trivial assignments |
| Q9: last_end_outcome | One-glance Cockpit debugging without session logs | New field in every task; cleared-on-move semantics add complexity |
| Error codes | Deterministic agent retry; no leaked internals | Codes must be maintained as taxonomy evolves; Brief A revision required |
