# Decisions — Decision Request Data Model

## D0 — 2026-05-24 — Project Type

**Status quo:** No formal project type classification.
**Decision to make:** Classify the project type for discovery depth calibration.

**Options considered:**

- A: net-new — build a completely new request system
- B: existing-feature/refactor — extend the existing DR/AR system with structured data
- C: uncertain

**Chosen:** B — existing-feature/refactor

**Rejected:**

- A: The system already exists (pending DR files, engine parsing, MCP `create_dr`, Cockpit decisions route). This work extends it, not replaces it from scratch.
- C: The input material clearly identifies existing code to build on.

**Source inputs:**

- Input: references existing `create_dr` MCP tool, current pending decision files, Cockpit Decisions route work

## D1 — 2026-05-24 — Investment Tier

**Status quo:** No tier assigned.
**Decision to make:** Calibrate discovery depth.

**Options considered:**

- A: Scratch — lightweight, skip panel
- B: Tool — standard M2, selective panel
- C: Shared — full panel, research bridge required
- D: Production — full panel + Critic at every moment

**Chosen:** C — Shared

**Rejected:**

- A/B: Multiple internal consumers (agents, Cockpit, downstream agents) depend on this model. Getting it wrong creates cross-layer rework.
- D: Not external-facing; durability matters but not at production-critical level.

## D2 — 2026-05-24 — Backward Compatibility

**Status quo:** DR format has changed multiple times recently.
**Decision to make:** Whether to require migration of existing DR files.

**Chosen:** No backward compatibility required. Clean break.

**Rejected:**

- Migration in place: format is unstable, old files are few and short-lived.
- Read-only compat: unnecessary complexity when no external readers exist.

**Source inputs:**

- User: "no backward compat is required. old DR do not have to be migrated"

## D3 — 2026-05-24 — Early Challenge Lane Outcomes

**Status quo:** Input doc proposed 5 kinds, 6 response modes, per-option confidence, supersession chains, blocking flag, 6+ engine operations.
**Decision to make:** Which proposed features survive challenge.

**Kept (user-confirmed):**

- 2 kinds: `decision` + `action` (approval/clarification/confirmation are decisions with specific options)
- Per-option `confidence: float` — user uses relative spread for decision speed
- `recommended` flag per option
- `rationale` per option
- Single unified data model for both kinds across full lifecycle
- Request ID generated as UUID4 (reuse memory engine pattern)

**Cut (challenger-validated, user-approved):**

- `response_mode` enum — redundant with data shape (options present → cards; no options → free text; action → done/blocked)
- `supersedes_request_id` / `parent_request_id` — zero observed chains, trivial to add later
- Separate `blocking` flag on request — creating a DR/AR blocks the task via existing `blocked` attribute; resolving unblocks it
- DR/AR tag on tasks — Cockpit already detects pending requests visually regardless of tags
- `cancel` / `supersede` as first-class engine operations — these are resolve-variants

**Semantic clarification (user):**

- Creating a request blocks the task (sets `blocked=True`); tags are unnecessary since Cockpit detects pending requests independently
- Resolving writes the resolution to the task body, then unblocks
- No implicit blocking from request existence alone — the `blocked` attribute on the task is the single source of truth

**Source inputs:**

- Simplifier stance: collapse kind 5→2, drop response_mode, engine 6→3
- First-principles stance: design from observed patterns, separate three independent fixes
- User: "I need the confidence value per option... the higher the difference the faster I decide"
- User: "only block when creating a dr/ar, and unblock when its solved after writing the resolution to the task body"
- User: "I wouldn't see a good reason to not have one data model for the lifecycle"

## D4 — 2026-05-24 — Action Resolution States

**Status quo:** No structured resolution states for actions.
**Decision to make:** What terminal states should action requests have?

**Options considered:**

- A: `done` + `rejected` — minimal pair, nuance via free_text
- B: `done` + `failed` + `rejected` — distinguishes try-and-fail from refusal
- C: `done-success` + `done-problems` + `rejected` — most expressive

**Chosen:** A — `done` + `rejected`

**Rejected:**

- B/C: Free text covers "completed-with-issues" nuance. More states increase agent interpretation complexity for minimal single-user value.

**Source inputs:**

- User: "done + rejected"
- Data stance: minimal terminal pair
- Enduser stance: "completed-with-issues" covered by free_text on done

## D5 — 2026-05-24 — needs-info Modeling

**Status quo:** Synthesis recommended needs-info as notes[] list (request stays pending, task stays blocked).
**Decision to make:** How should "I need more info" work?

**Options considered:**

- A: Notes list — request stays pending, task stays blocked
- B: needs-info as resolution status — task unblocks, agent sees it
- C: Notes list + separate cancel button

**Chosen:** B — `needs-info` as a resolution status that unblocks the task

**Rationale:** If task stays blocked (A), no agent picks it up to see the note — workflow dead end. With B, the agent picks up the unblocked task, reads the needs-info resolution + free_text, then either creates a fresh DR with better context or proceeds differently. Clean cycle: create → block → resolve (approved/rejected/needs-info) → unblock → agent acts.

**Implications:**

- Decision resolution statuses: `approved`, `rejected`, `needs-info`
- Action resolution statuses: `done`, `rejected`, `needs-info`
- All resolutions unblock the task (conditional on no sibling pending requests)
- Eliminates the `notes[]` list concept entirely — free_text on resolution carries the message
- `approved` requires `selected_option_id`; `rejected` and `needs-info` do not

**Source inputs:**

- User: identified workflow dead-end with notes approach
- User: "what if that info leads the agent to think this DR is obsolete?"

## D6 — 2026-05-24 — Quick-Confirm Mode

**Status quo:** Not designed yet.
**Decision to make:** Should Cockpit pre-select the recommended option when confidence spread is large?

**Chosen:** Deferred — not in scope for this work.

**Rationale:** Pre-selection could signal "already decided." Confidence is visually clear enough that saving 0.5 seconds of selection doesn't justify the implementation and tuning cost. Model supports it naturally if added later.

**Source inputs:**

- User: "pre-selection could signal 'this has already been decided'"

## D7 — 2026-05-24 — Panel Synthesis Convergences (adopted)

The following positions from synthesis.md are adopted as design constraints:

- UUID4 filenames (`{request_id}.md`)
- Single engine writer — no layer writes DR files except engine
- Pydantic `extra="forbid"` with kind-discriminated cross-field validation
- Decisions require ≥2 options; actions have 0 options
- Confidence 0.0–1.0 per option, independent (not sum-to-1)
- At most one `recommended=True` per request
- `free_text` always available on resolution (optional, never hidden)
- ID-tagged summary written to task body (`<!-- dr:{request_id} -->` for idempotency)
- `create_request` → `task.blocked=True`; `resolve_request` → conditional unblock (sibling check)
- Malformed files surfaced as error objects, never silently dropped
- Slug-format option IDs: `^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$` (max 63 chars)
- Resolved files immutable (audit trail)
- Sweep kept as crash-recovery/power-user fallback only
- No MCP resolve tool (human-only for now; gate conditions documented)
- Max 10 options per request
- Option label max 120 chars, rationale max 500 chars
- Resolution atomicity: rename-as-check + marker idempotency

## D8 — 2026-05-24 — Resolution Model Simplification (supersedes D4, D5)

**Status quo:** D4 defined action states (done/rejected), D5 defined needs-info as a resolution status. Both assumed an `approved/rejected/needs-info/done` status enum.
**Decision to make:** Is a status enum needed at all?

**User insight:** "Why is approved and rejected even the options if the intent is to have the user choose between options with optional free text?"

**Options considered:**

- A: Keep status enum (approved/rejected/needs-info for decisions; done/rejected/needs-info for actions)
- B: Two lifecycle states (resolved + returned/needs-info)
- C: Binary lifecycle (pending → resolved), answer is just a payload

**Chosen:** C — resolution is just a payload, no status enum

**Resolution payload (both kinds):**
```yaml
resolution:
  selected_option_id: "hybrid"  # nullable — null if custom answer or action
  free_text: "context here"     # nullable — custom answer, notes, or action outcome
  resolved_by: "user"
  resolved_at: "2026-05-24T15:30:00+02:00"
```

**Semantics derived from content, not status:**
- Decision + option_id present = structured answer from menu
- Decision + option_id absent + free_text = custom answer ("none of these, here's what I want")
- Action + free_text = outcome report, refusal explanation, or info request
- Any + minimal/empty content = implicit dismissal
- "Needs-info" = resolve with free_text explaining gap → task unblocks → agent reads → creates new DR

**Rationale:**
- Agent can't edit existing DRs, so "returned for rework" has no consumer — agent creates new DR
- "Dismissed" is just resolved with negative free_text
- Status enum was borrowed from PR-review mental model; this is a choice form
- Simpler model = fewer agent interpretation rules, simpler Cockpit UI (one submit button)
- Lifecycle is filesystem: file in pending/ = not answered, file in resolved/ = answered

**Rejected:**
- A: Status enum adds artificial categories to what is fundamentally "pick or type → submit"
- B: "returned" has no consumer since agents can't edit existing DRs

**Source inputs:**
- User: "why is approved and rejected even the options?"
- User: "needs info doesn't need returned, that is resolved too"
- User: "dismissed is also just resolved with a negative message in free text"
- User: "an agent cannot edit an existing DR, it would just create a new one"
