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

## D7 — 2026-05-18 — Engine Extraction Sequencing

**Status quo:** Memory engine lives inside `serve/mcp-memory/`. Cockpit cannot import MCP packages.
**Decision to make:** Extract to shared package or reimplement in cockpit?

**Options considered:**

- A: Extract `serve/memory/` as shared package (like kanban pattern)
- B: Direct-read with contract tests (cockpit reimplements logic)

**Chosen:** A — extract first. Matches kanban pattern, eliminates drift permanently, proven approach.

**Rejected:**

- B because logic drift between two state machines is a category of bug testing cannot fully prevent; ongoing maintenance cost.

## D8 — 2026-05-18 — Tab Infrastructure Dependency

**Status quo:** #1638 (nav-rail, route config, React Router) still in research.
**Decision to make:** How to handle the frontend dependency?

**Options considered:**

- A: Block all work on #1638
- B: Build with temporary Shell modification
- C: Split scope — backend now, frontend after #1638

**Chosen:** C — split scope. Backend (engine extraction + API routes) proceeds independently; frontend blocks on #1638 for the component mounting contract.

**Rejected:**

- A because backend has zero dependency on the frontend tab system
- B because temporary wiring is real rework and creates merge conflicts

## D9 — 2026-05-18 — SSE for Memory Events

**Status quo:** SSE exists for kanban; memory changes infrequently.
**Decision to make:** Include SSE in V1 or defer?

**Chosen:** No SSE in V1. Refetch-after-action + refetch-on-tab-focus. Add SSE as a follow-on.

**Rejected:**

- SSE in V1 because memory changes are rare and user-initiated; the effort adds scope without matching value.

## D10 — 2026-05-18 — Deleted Entries Default Visibility

**Chosen:** Exclude deleted from default view. State filter defaults to pending + curated + approved. Deleted available via opt-in filter toggle.

## D11 — 2026-05-18 — Git Commit Lifecycle

**Status quo:** MCP tools auto-commit; cockpit kanban mutations do not.
**Decision to make:** Should cockpit memory mutations auto-commit?

**Chosen:** No auto-commit (match cockpit kanban pattern). Cockpit writes files; git managed externally.

**Rejected:**

- Auto-commit because it's inconsistent with cockpit kanban behavior and creates noisy commit history.

## D12 — 2026-05-18 — Validation Leniency

**Status quo:** Existing entries may have minor cross-field invariant violations.
**Decision to make:** Strict reader requiring migration, or lenient read?

**Chosen:** Lenient on read, strict on write. Existing entries display as-is; mutations enforce full validation. Self-heals on edit.

**Rejected:**

- Migration because touching 103 files adds complexity and risk for cosmetic fixes.

## D13 — 2026-05-18 — Deferred Items

**Chosen:** Defer both to post-V1:
- Approval provenance (`approved_by` field) — schema change, future enhancement
- Remote image blocking in rendered markdown — defence-in-depth for local tool, lower severity
