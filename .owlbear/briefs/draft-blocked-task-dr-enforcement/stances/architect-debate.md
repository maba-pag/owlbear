# Architect — Critic Debate Log

## Round 1

### Architect Initial Position

**Q1:** Option (d) — `guidance: list[str] = []` on `KanbanTask`. Optional field, invisible to `extra="ignore"` consumers. Schema auto-propagates via `outputSchema` patch.

**Q2:** Pure-function `guidance.py` with flat `(predicate, template)` list. `collect_guidance(action, *, task, params)`.

**Q3:** Pre-read via `_show_validated()` in MCP tool layer. Sub-ms local FS read. Same pattern as Cockpit `move_task`.

**Q4:** Inject `block:user` in `_build_edit_kwargs()` on the block branch. Remove on unblock.

**Confidence:** 85%

### Critic R1 Challenges (5 challenges, 2 blind spots)

1. **CRITICAL — `block:user` in `_build_edit_kwargs` breaks tag-diff contract.** Full-replacement tag semantics via set-diff logic conflict with appending `block:user` inside the helper. A request sending `tags` + `block_reason` together can't round-trip the caller's explicit tag set.
2. **MODERATE — Schema blast radius understated.** Position claims "invisible" while also warning strict consumers will notice. Inconsistent framing.
3. **MODERATE — Salience not established.** Brief requires "first thing the agent sees." Position never explains how an optional field at the end of a Pydantic model achieves this.
4. **MODERATE — Non-atomic pre-read; forward-skip ordering not canonical.** `_status_rank` is private. `AppContext` doesn't expose it. No snapshot guard. `dispatch.py` uses a different `STATUS_RANK`.
5. **MODERATE — `block:user` not traced to normative policy surfaces.** `h-mcp-kanban` is tool guidance, not the authoritative rule layer (`r-pipeline-protocol`, `w-decision-routing`).

**Blind spots:** No ordering semantics for multi-message guidance. Empty-guidance noise on non-target tools.

**Critic recommendation:** Reject. Confidence: 0.44.

### Architect Response

- **Accepted R1.1:** Moved injection from `_build_edit_kwargs` to route handler, after kwargs are built.
- **Accepted R1.2:** Clarified: schema change is deliberate, not accidental. "Invisible" applies to Pydantic consumers; raw JSON consumers see it intentionally.
- **Accepted R1.3:** Declared `guidance` as FIRST field in `KanbanTask`. Pydantic v2 field-declaration order = serialization order. Added `"⚠️ ACTION REQUIRED: ..."` prefix for additional salience.
- **Partially accepted R1.4:** Acknowledged TOCTOU race (acceptable for advisory). Agreed `_status_rank` is private — will use public `engine.board_config().statuses` instead.
- **Partially accepted R1.5:** Noted skill file updates as required Brief deliverables.

---

## Round 2

### Architect Refined Position

- Q1: `guidance` as first field. Deliberate schema change. Salience via field order + action prefix.
- Q2: Explicit input contract: `collect_guidance(action, *, task, outcome, old_status, status_names)`.
- Q3: Public `board_config()` instead of private `_config`. `"archived"` excluded from skip detection.
- Q4: Route handler injection with tag-diff conflict resolution. MCP unblock clears `block:user`.

**Confidence:** 80%

### Critic R2 Challenges (6 challenges, 3 blind spots)

1. **CRITICAL — `block:user` doesn't prove human actor.** No auth, no identity, no provenance. Tag is transport-path marker, not actor assertion. Semantic mismatch with DR-suppression rule.
2. **CRITICAL — Tag staleness.** MCP block/unblock don't manage the tag. A Cockpit-origin tag survives agent re-block without unblock step.
3. **CRITICAL — Guidance helper lacks coherent input contract.** `KanbanTask` has no tool name, outcome, or prior-state metadata. Helper depends on undeclared per-call inputs.
4. **MODERATE — Forward-skip formula incomplete for "archived".** Archive not in config statuses — no defined `new_rank`.
5. **MODERATE — Private `_config` access is false binary.** Public `board_config()` already exists, used by Cockpit adapter.
6. **MODERATE — Salience asserted, not demonstrated.** JSON field order doesn't control MCP client rendering.

**Blind spots:** No verification design. Non-Cockpit human-origin blocks unconsidered. Client-layer rendering unaddressed.

**Critic recommendation:** Reject. Confidence: 0.34.

### Architect Response

- **Accepted R2.1 (partially):** Clarified tag is intentionally a transport-path heuristic, not an identity assertion. This is the user's locked design choice ("classification, not enforcement"). Note that skill file updates must reflect this policy.
- **Accepted R2.2:** Added MCP-side `block:user` cleanup: MCP `edit_task` block branch removes `block:user`; MCP `edit_task` unblock branch removes `block:user`. Closes the staleness gap for unblock-then-reblock sequences.
- **Rejected R2.3:** The input contract WAS explicitly defined in the position (`action`, `task`, `outcome`, `old_status`, `status_names`). The Critic missed it. The helper's inputs are tool-call-time parameters, not model fields. This is standard for a post-processing function.
- **Accepted R2.4:** Archive excluded from skip detection. Predicate returns early for `status == "archived"`.
- **Accepted R2.5:** Switched from `_config` to public `board_config()`.
- **Partially accepted R2.6:** Acknowledged limitation. JSON field order is best available mechanism. Document as known limitation.

---

## Round 3

### Architect Hardened Position

Full lifecycle for `block:user`: Cockpit block adds, Cockpit unblock removes, MCP unblock removes, MCP block removes (clears stale provenance). In-place reblocking via MCP now explicitly clears the tag.

**Confidence:** 88%

### Critic R3 Challenges (4 challenges, 3 blind spots)

1. **CRITICAL — `block:user` bypasses documented pipeline contract.** `r-pipeline-protocol` requires scribe-created artifacts for all blocks including user-action blocks. Tag-only provenance leaves no artifact for unblock/re-entry machinery.
2. **MODERATE — "Only humans use Cockpit" not grounded.** The route is a plain HTTP endpoint. Tests already drive it programmatically. No auth layer.
3. **MODERATE — In-place reblocking lifecycle gap.** Agent `edit_task(block=...)` on already-blocked task with `block:user` doesn't pass through unblock, so tag persists.
4. **MODERATE — Habituation from empty guidance.** `"guidance": []` on every `show_task`, `start_work`, `create_task` call. `end_work(outcome="success")` reminder fires on universal success path.

**Critic recommendation:** Reject. Confidence: 0.34.

### Architect Final Response

- **R3.1 — Policy scope.** The user's locked decision explicitly overrides the existing `r-pipeline-protocol` language for Cockpit-origin blocks. The Brief deliverables must include `r-pipeline-protocol` updates. This is a policy change, not an architecture flaw.
- **R3.2 — Transport-path proxy.** Accepted as known limitation. No auth exists. The heuristic is the user's design choice. Documenting it honestly is the architecture's job.
- **R3.3 — Accepted.** Genuine gap. MCP `edit_task` block branch must explicitly remove `block:user` (agent re-block clears Cockpit provenance). Added to the final stance.
- **R3.4 — Partially accepted.** LLMs don't habituate like humans (no attention fatigue on repeated tokens). But the concern about noise volume on `end_work(outcome="success")` is valid. The user chose this as a V1 use case; flagged as a monitoring point.

**Final confidence:** 88%
