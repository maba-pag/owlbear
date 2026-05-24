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
