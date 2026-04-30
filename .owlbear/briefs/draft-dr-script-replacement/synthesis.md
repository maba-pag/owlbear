# Synthesis — DR/AR Script Replacement

**Mode:** converge | **Active stances:** architect, data, enduser | **Date:** 2026-04-30

---

## Summary

All three panelists endorse the core proposal: replace the scribe agent with a deterministic `decisions.py` module in the kanban engine, expose `create_dr` via MCP, and provide Cockpit-native resolve UI. Agreement is strong on module boundaries, the always-block semantic, simplified file format, fire-and-forget agent ergonomics, and the file-edit fallback. Tensions cluster around three areas: (1) how to guard the resolve sequence against concurrency and partial writes, (2) how strictly to validate the response field, and (3) Cockpit polling and stale-state behavior.

---

## Convergences

### C1 — Scribe replacement with deterministic engine code

All three stances agree the scribe agent adds no value and should be replaced by a `decisions.py` module in `serve/kanban/`. The architect specifies the module API surface and `engine_ops` protocol; the data panelist endorses deterministic code as the correct home for file I/O; the enduser stance treats it as settled and focuses on the UX surface.

### C2 — Always-block semantics for `create_dr`

Architect (explicit trade-off table) and enduser ("if the agent doesn't need an answer to proceed, it shouldn't create a DR") both endorse always-blocking the originating task on DR creation. Data does not contest this. No advisory/non-blocking path.

### C3 — No `query_drs` or `resolve_drs` MCP tools

All three align: agents fire-and-forget DRs (architect, enduser). Resolution is triggered by Cockpit (primary) or `pick_tasks` sweep (fallback). No extra MCP tools for orchestrator or agents (architect, enduser). Data agrees agents that read resolved files do so directly.

### C4 — Simplified file format with backward/forward compatibility

Architect and data both specify that the reader must accept and ignore unknown frontmatter keys (handles legacy fields like `urgency`, `impact_tier`). Data adds the dual-format requirement explicitly; architect notes passive migration. Enduser requires that users see rendered prose, not raw YAML — consistent with engine-managed frontmatter.

### C5 — Cockpit as primary resolve path, file-edit as fallback

All three agree. Architect defines separate `/api/decisions/` endpoints. Enduser specifies the interaction flow (status bar → popover → modal). Data does not contest the Cockpit-primary model and focuses on ensuring file-edit fallback produces valid data.

### C6 — Always-visible status bar indicator with count

Architect specifies a status bar indicator as must-have. Enduser elaborates: always visible (dormant state at zero), single attention color (no DR/AR hue split), count number always shown, screen-reader live region for count changes. Data does not contest.

### C7 — `pick_tasks` auto-resolve as side-effect (with reservations)

All three accept the locked outcome. Architect implements it via a fail-safe guard (`_try_resolve_pending_drs()` that swallows exceptions). Data accepts the mechanism but flags the contract change as high risk. Enduser treats it as backend-internal. The agreement is on the *what*; the tensions below are on the *how*.

### C8 — Atomic writes for resolved files

Data explicitly requires write-to-temp-then-rename for resolved files so direct-reading agents never see partial content. Architect implicitly supports this via the atomic rename reference. No contradiction from enduser.

---

## Disagreements

### T1 — Concurrency guard: `processing/` directory vs. documented contract change

| Aspect | architect | data | enduser |
|--------|-----------|------|---------|
| Position | Accept purity violation. Guard with try/except. No OCC — single-user system. | **CRITICAL.** Three-state rename (pending → processing → resolved) as single-writer lock. Prevents duplicate body appends. | Not addressed directly. |
| Risk framing | "Contained if guard truly swallows all exceptions." | "Atomic rename only guards the final step; body append + unblock are unguarded." | — |
| Implication | Simpler implementation, no new directory. | New `processing/` directory; Cockpit and agents must understand the state. | — |

**Tension level: HIGH.** The architect's position works if and only if concurrent resolve is impossible in practice (single-user, single pick_tasks caller). The data panelist's concern is structurally valid — the body append + unblock sequence is genuinely unguarded. The question is whether the theoretical race justifies the complexity of a third directory.

### T2 — Response field validation: closed enum vs. open freeform

| Aspect | architect | data | enduser |
|--------|-----------|------|---------|
| Position | Four explicit branches (approved, rejected, needs-info, completed); "free-text response field" listed as acceptable trade-off. Does not specify behavior for unknown values. | Closed enum is "non-negotiable." Unknown values → do not resolve, log warning, leave in pending. Also supports matching against DR `options:` list labels. | Textarea for user composition (UI concern). |
| Risk framing | "User could write nonsensical response (their problem)." | "Prevents the exact misclassification the scribe was designed to catch." | — |

**Tension level: HIGH.** This is the most consequential design fork. The architect's four-branch state machine has an implicit "anything else" gap. Data explicitly closes it: unknown values are treated as unresolved. The cost of the closed enum is that a user typo (e.g., "approvd") silently does nothing; the cost of the open approach is that a typo auto-resolves incorrectly. Data also proposes matching against per-DR `options:` labels, which neither other panelist addresses.

### T3 — `pick_tasks` contract change documentation

| Aspect | architect | data | enduser |
|--------|-----------|------|---------|
| Position | Adds a test that pick_tasks succeeds even with corrupted decisions_dir; treats as implementation detail. | Requires explicit MCP tool description update ("read + resolve side-effect") and documentation of the contract change. | Not addressed. |

**Tension level: MODERATE.** Both agree on the behavior but disagree on whether it needs formal contract documentation or just a test.

### T4 — Cockpit polling interval

| Aspect | architect | data | enduser |
|--------|-----------|------|---------|
| Position | Not specified. | Not addressed. | 5–10 seconds, not the 60s scan default. Pipeline-blocking items demand responsive awareness. |

**Tension level: LOW.** No opposition — the architect and data stances simply don't address it. The enduser's position is unopposed and well-reasoned.

### T5 — Stale-state protection in resolve modal

| Aspect | architect | data | enduser |
|--------|-----------|------|---------|
| Position | Not addressed. | Not addressed. | Modal MUST preserve user input if backend resolves mid-composition. Show non-dismissive banner. |

**Tension level: LOW.** Unopposed. Implementation cost is the only question.

### T6 — `create_dr` MCP tool response shape

| Aspect | architect | data | enduser |
|--------|-----------|------|---------|
| Position | Not specified beyond "MCP layer validates presence and types." | Not specified. | Must confirm blocking: `{created: true, path: "...", task_blocked: true}`. |

**Tension level: LOW.** Unopposed by other stances.

---

## Open Questions

### Q1 — Closed-enum response validation (T2)

Does the brief adopt the data panelist's strict closed-enum approach (unknown values → unresolved, log warning) or the architect's implicit open approach (user responsibility)? This also decides whether per-DR `options:` label matching is in scope.

### Q2 — `processing/` directory or accept the concurrency gap (T1)

Does the brief add a three-state resolve flow (pending → processing → resolved) to guard the full sequence, or accept the theoretical race condition as single-user-acceptable and document the `pick_tasks` contract change?

### Q3 — Polling interval for status bar indicator (T4)

Should the brief lock a specific short-poll interval (5–10s as enduser recommends) or leave it as an implementation detail?

### Q4 — Stale-state protection scope (T5)

Is the draft-preservation behavior in the resolve modal a P3 must-have or a follow-up polish item?

### Q5 — `create_dr` response contract (T6)

Should the brief lock the MCP response shape (including `task_blocked` confirmation) or leave it to implementation?

---

## Recommendation

| Question | Recommended resolution | Grounding | Confidence |
|----------|----------------------|-----------|------------|
| Q1 — Closed enum | **Adopt closed enum.** Unknown values → unresolved, log, leave in pending. Drop `options:` label matching (adds complexity for marginal value). | Data panelist's argument is structurally sound: the open approach reintroduces the misclassification risk the scribe was designed to prevent. Architect's four-branch table is compatible — it just needs an explicit "else" clause. | 0.82 |
| Q2 — `processing/` dir | **Skip `processing/` directory. Document the contract change.** Add the test architect proposes (pick_tasks succeeds with corrupted dir). Update MCP tool description per data's recommendation. | The theoretical race requires two concurrent callers resolving the same DR — not realistic in a single-user, single-orchestrator system. The `processing/` directory adds a third state that Cockpit, agents, and the engine must all understand, for a race that won't occur. Documentation + test is sufficient. | 0.72 |
| Q3 — Polling interval | **Lock 10s in the brief.** | Unopposed, well-reasoned by enduser. Pipeline-blocking items at 60s polling is a real UX failure. 10s balances responsiveness with load. | 0.85 |
| Q4 — Stale-state protection | **P3 must-have, but minimal implementation.** Show a banner on stale detection; don't build a full conflict-resolution flow. | Enduser's draft-loss scenario is real (Cockpit resolve + pick_tasks sweep can race). A banner is cheap; full preservation is polish. | 0.75 |
| Q5 — Response shape | **Lock the response shape.** Include `created`, `path`, and `task_blocked` fields. | Enduser's rationale is correct: agents need confirmation that blocking was applied to proceed with certainty. Costs nothing to specify now. | 0.80 |

**Overall synthesis confidence: 0.78**

The three stances are well-aligned on the overall direction. The highest-stakes disagreement (T2, response validation) has a clear resolution supported by two of three stances. The second-highest (T1, concurrency guard) is a genuine architectural judgment call where simplicity and realism favor the lighter approach.
