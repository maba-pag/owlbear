# End User — Critic Debate Log

## Round 1

### Position Stated

**Q1 (optimistic token):** Optional for MCP, required for Cockpit. MCP callers work sequentially on claimed tasks — conflicts are near-impossible on a single laptop. Requiring a pre-fetch round trip per edit is a punitive tax on agent call count. Cockpit humans naturally have the token from the rendered task view.

**Q2 (clarity gate):** Keep loose predicate today. Document `## AC` heading as convention. Tighten after migration tooling exists. Migration cost (rewriting 50+ existing tasks) is a full-stop blocker.

**Q5 (pick_waves):** Greedy by priority, deterministic tie-break (lower task ID). Add `wave_reason: str` to DispatchEntry so agents understand their assignment without follow-up queries.

**Q9 (sessions narrowing):** D10 is correct for engine scope. Add `last_work_outcome: str | None` to the task model (set by `end_work`). Gives Cockpit humans one-glance diagnosis without full body read or activity log dependency.

**C2 (role views):** Role views win on discoverability over raw engine + docstring. Must carry forwarded method docstrings — a developer hovering `cockpit_view.edit_task()` should see the full contract.

**Error model:** Structured ToolError: code + message + remediation hint. Agents can map codes to deterministic retry strategies.

**Guidance:** Only emit when actionable. Empty array = silent success.

**Multi-wave:** Return multiple waves. Document waves 2+ as advisory/preview. Re-call after each wave completes.

**Stuck sessions:** Useful without closed history IF `last_work_outcome` exists on the task model.

### Critic Challenges

1. **Q1 asymmetry risk.** "Optional for MCP" means any MCP server restart + orchestrator cache gives silent overwrites. Cockpit and MCP run concurrently by definition. The "single laptop" defense assumes no race conditions between two simultaneous consumers of the same task.

2. **Q2 false positives.** The loose predicate (any bullet anywhere in body) matches random notes, not real AC. You're trading one-time human migration pain for ongoing automated waste — every false-positive dispatch costs an entire agent cycle.

3. **`wave_reason` token tax.** 8 tasks per wave × 10-20 tokens per reason = 80-160 tokens added to every dispatch response. This is observability for a debugging case that happens rarely. Observability should be opt-in, not default.

4. **`last_work_outcome` is model bloat.** The body already contains timestamped notes from `end_work`. Section projection via `show_task(section="work-log")` gives the same information without adding a new field to every task.

5. **Structured ToolError hint.** "Hint" is paternalistic and will be wrong half the time. Code + message is sufficient. Agents determine remediation from context, not from engine-authored advice.

### Responses

1. **Partially accepted.** Refined: MCP passes a token → enforce it. MCP omits token → proceed without. This is standard ETag semantics — well-understood, not confusing. Clients that care about conflicts opt in; clients that don't, don't. The human operator's edit should win in a conflict (they're overriding the agent), and Cockpit always sends the token.

2. **Rejected.** Who rewrites 50 tasks? The human, manually. When? Before anything dispatches. That's a deployment blocker with no tooling path. False positives are recoverable — agent reports "no AC found, releasing" — but a migration blocker is not. Position held.

3. **Partially accepted.** Make `wave_reason` present by default but allow engine to omit for trivial reasons ("standard priority ordering"). Reduces noise without losing debugging value when waves are surprising.

4. **Rejected.** Section projection requires the human to know what section name to search AND to drill into `show_task`. `last_work_outcome` on TaskSummary is visible in the task list — one-glance diagnosis without navigation. Fundamentally different UX pattern: scan vs search.

5. **Partially accepted.** Drop "hint". Keep code + message. Agents map codes to retry strategies deterministically. No hand-holding strings that may be wrong.

---

## Round 2

### Refined Position

- Q1: ETag-style optional enforcement. Pass token → enforce. Omit → proceed.
- Q2: Keep loose predicate, document convention, tighten later.
- Q5: `wave_reason` present by default, omittable for trivial reasons.
- Q9: `last_work_outcome` on task model, set by `end_work`.
- Error model: code + message (no hint).

### Critic Challenges

1. **Q1 dual-semantic method.** "If passed, enforce; if omitted, proceed" means the same method has two concurrency behaviors depending on parameter presence. This is confusing. Prefer one semantic: always enforce (both consumers must pass tokens) or never enforce at engine level.

2. **Q2 structured body changes the calculation.** D7 specifies `body: list[Section]`. If body is already parsed into sections at read time, the clarity gate can structurally check for a Section with heading "AC" — no raw `## AC` text matching needed. No markdown migration required. Just a parser-level gate on the structured model.

3. **`last_work_outcome` staleness.** If set by `end_work`, what happens after a Cockpit `move_task` that isn't `end_work`? The field says "success" but the human admin just moved the task back to todo. The field is now misleading.

### Responses

1. **Rejected.** This IS how ETags work in HTTP. `If-Match` is optional. The HTTP spec is not "confusing" — it's the most widely deployed concurrency protocol on the planet. Clients that want conflict detection send the header; clients that don't, don't. Same principle here. Position held with confidence.

2. **Accepted.** Excellent challenge — this changes Q2 entirely. If D7's `list[Section]` model is the engine's internal representation, the clarity gate checks `any(s.heading == "AC" for s in body)`. No raw markdown parsing, no migration of text. Existing tasks with `## AC` already parse correctly. Tasks without the heading fail the structural check. The tightened gate is free — no migration cost because the structured model absorbs the parsing. Position refined: **tighten the clarity gate using the structured body model. Require a Section with heading "AC" containing ≥1 list item. No raw-text migration needed.**

3. **Accepted.** `last_work_outcome` must be cleared on any `move_task` call (or any status change not via `end_work`). Rename to `last_end_outcome` to make the semantic scope explicit: this records the last `end_work` call's outcome, and any non-`end_work` mutation clears it.

---

## Round 3

### Refined Position

- Q1: ETag-style optional. Position firm.
- Q2: Tighten gate via structured body model (Section heading check). No migration cost.
- Q5: `wave_reason` present by default.
- Q9: `last_end_outcome` on task model, cleared on non-`end_work` mutations.
- Error model: code + message.

### Critic Challenges

1. **Multi-wave advisory.** You say "re-call after each wave completes." How does the orchestrator know a wave completed? Is there a staleness signal, or does the orchestrator just re-call `pick_waves` after dispatching? If the latter, document it explicitly — don't assume orchestrator behavior.

2. **Q2 tightened gate + escape tags.** The 9-tag escape set exempts tasks from the clarity gate. With a tightened structural check, do those tags still apply? If a `research` task doesn't have `## AC`, it should still dispatch. Your revised position needs to account for the escape tags surviving the tightening.

### Responses

1. **Accepted for documentation.** The orchestrator already re-calls `pick_waves` after dispatching a wave (that's the dispatch loop). Document: waves 2+ become stale after ANY board mutation. No explicit staleness signal needed — the orchestrator's natural loop handles this. Position held with documentation note.

2. **Good catch.** Yes, escape tags survive. The tightened gate is: `has_ac_section(body) OR has_escape_tag(tags)`. The 9-tag set (research, docs, type:config, type:docs, test, type:test, agent, quality, type:user-action) exempts tasks from the AC requirement. This is the current behavior, just on the structural model instead of raw regex. Position refined to explicitly preserve escape tags.

### Critic Assessment

Position is solid on all points. No further material challenges.
