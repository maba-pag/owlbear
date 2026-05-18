# Decisions — Cockpit Memory Tab

*Append-only. Records chosen and rejected options with rationale.*

## D1 — 2026-05-17 — Project Type

**Status quo:** No memory UI exists in the cockpit.
**Decision to make:** Is this net-new, existing-feature/refactor, or uncertain?

**Options considered:**

- A: net-new — standalone memory browser
- B: existing-feature/refactor — new tab in the cockpit using #1638 tab infrastructure

**Chosen:** B — existing-feature/refactor

**Rejected:**

- A because the cockpit already exists and tab infrastructure (#1638) explicitly names Memory as a planned follow-on. The route config pattern makes this additive, not greenfield.

## D2 — 2026-05-17 — Investment Tier

**Status quo:** No tier assigned.
**Decision to make:** What depth of ideation does this problem warrant?

**Options considered:**

- A: Tool — standard M2, selective panel
- B: Shared — full panel, research bridge required
- C: Production — full panel + Critic at every moment

**Chosen:** B — Shared (multi-consumer artifact: user + agents, internal tooling, durability matters)

**Rejected:**

- A because this is more than single-user tooling — the cockpit is a shared surface, and the memory UI must stay consistent with the MCP tool behavior
- C because it's internal-facing, not external

## D3 — 2026-05-17 — Mutation Scope

**Status quo:** Input document includes browse + filter + delete + approve + edit.
**Decision to make:** Which mutations belong in V1?

**Options considered:**

- A: Browse + delete only — defer approve and edit
- B: Browse + delete + approve — defer edit
- C: Full set — browse + filter + delete + approve + edit

**Chosen:** C — full mutation set in V1. The user wants a polished, complete feature.

**Rejected:**

- A, B because reducing the mutation surface makes the feature feel half-built. Approve and edit are core to meaningful memory management, not optional polish.

## D4 — 2026-05-17 — Detail Pattern

**Decision deferred to mediation.** Options: inline expand vs separate detail view. Content is capped at 1024 chars, so inline expand is viable. User prefers mediation to decide this.

## D5 — 2026-05-17 — Client-Side Filtering

**Status quo:** Input document proposes backend filter parameters.
**Decision to make:** Backend or client-side filtering?

**Chosen:** Client-side filtering (early challenge consensus). At ≤500 entries and ≤500KB, one `GET` endpoint returning all entries and filtering in React eliminates backend query complexity without reducing polish.

## D6 — 2026-05-17 — Delete Semantics

**Chosen:** State-dependent, matching engine behavior — pending = hard delete (remove file from disk), curated/approved = soft delete (state → deleted).
