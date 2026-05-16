# Data Quality Stance — Cockpit Visual Redesign

## Core Position

The cockpit is a **read-write mutation surface**, not a read-only dashboard. The redesign is primarily presentation, but presentation decisions have data-integrity consequences because formatted display values sit adjacent to mutation controls that consume canonical values. The hard rule: **canonical values passed to mutation APIs must never be derived from formatted display text.** Formatting operates on a copy; the mutation path reads from the underlying data object.

## Data Shape Awareness

The board operates on **three distinct data streams**, not two:

1. **Board task list** — compact summaries fetched on mount and refetched when SSE signals invalidation (mtime-based). Carries: id, title, status, priority, blocked, tags[], updated, claimed_at, dep_status.
2. **Selected task detail** — full payload fetched on selection, refetched on nonce change. Adds: description, body, dependencies, parent, session history, block_reason, archival fields.
3. **Pending decision requests** — separate endpoint, polled/cached independently. Joined client-side to compute availability signal.

These three streams have **independent freshness**. The sidecar detail can lag behind the board list. The DR set can update independently of both. The formatting layer must not assume synchrony across streams.

## Canonical vs. Display Value Partition

Every field that participates in a mutation API call is **canonical** — the raw API value must be preserved untouched for write operations. Formatting applies only to display copies.

Critical canonical fields:
- `updated` — optimistic concurrency token. The raw ISO string from the last API/refetch response goes into move/edit/release calls verbatim. Formatting this for display is fine; using the formatted value for mutation is a data-corruption vector.
- `claimed_at` — `claimed` is derived from it server-side. Display as relative time; mutations don't send it directly but the raw value informs UI state.
- `priority`, `status`, `blocked`, `tags[]`, `parent`, `depends_on`, `body`, `block_reason`, `archival_reason`, `archival_refs` — all appear in edit/move APIs. Display transforms on these must never feed back into mutation payloads.

**Rule for the sidecar edit surface:** When a field transitions from read to edit state, the edit control must populate from the canonical data object, not from the rendered display text.

## Availability Signal: Cross-Stream Derived Domain Logic

The card-face availability signal is **domain logic at the display boundary**, not formatting. `computeSignal` implements a precedence chain by joining task fields with pending-DR IDs from a separate data stream:

1. Decision pending (DR blocks task) — highest precedence
2. Blocked (explicit flag)
3. Claimed (derived from claimed_at)
4. Dependencies unmet (dep_status === "blocked"; note: "redirect" and null currently fall through to ready — this may be deliberate UX collapse)
5. Ready (default)

This is the most integrity-sensitive display element. The redesign must:
- Preserve this precedence chain exactly
- Make each signal state visually distinct and unambiguous (icon + color + label)
- Handle the cross-stream join explicitly — if DR data is stale or unavailable, the signal computation must degrade to "unknown" rather than falsely showing "ready"
- Add an **unknown/indeterminate state** to the signal type for when critical inputs are missing or malformed

## Card Face Information Density

Card face MUST show:
- Title
- Task ID (#NNNN)
- Priority badge (visual severity — dynamic values from config, not hardcoded P1-P4)
- Composite availability signal (single icon/badge, highest-precedence state wins)
- 2-3 tag chips max with overflow indicator
- Update recency (relative time — "2h ago", "May 14") — needed for board triage

Card face must NOT show:
- Full ISO timestamps
- Session data
- Description/body
- Dependency graph
- Claimed-by identity

## Enum Vocabularies Are Config-Driven

Task statuses and priorities are **not hardcoded enums**. The board API delivers `statuses[]` and `priorities[]` as configuration alongside task data. The formatting layer must:
- Accept any string value for status and priority, not switch on a fixed set
- Map known values to visual treatments (color, icon) via a lookup table
- Render unknown values as raw text with a neutral visual treatment (no warning needed — new statuses are expected, not malformed data)
- Treat `archived` as a special status (move target, not a standard column)

Session states (`running`, `released`, `expired`, `completed`, `stuck`, `rejected`, `blocked`) are a **separate vocabulary** from task states. Formatting utilities for session states belong in the Activity tab, not in task-level formatting.

## Tag Semantics: Not Purely Cosmetic

Tags arrive as `string[]` from the API (not comma-separated — the user's audit description reflects the old rendering, not the data contract). Most tags are passive metadata, but:
- `block:user` is system-coupled — server-side block/unblock operations add/remove it
- Tags with known prefixes (`scope:`, `type:`, `blocked-by-*`) carry semantic weight

The redesign should render tags as PDS Tag chips. Semantic tag categories (scope, type, block) could get distinct chip variants for scannability, but this is a **presentation choice**, not a data-integrity concern — as long as the tag array passed to mutation APIs is the original string array, not a reconstructed one from chip labels.

## Display Boundary Validation: Honest Scope

The current frontend does unchecked TypeScript casts on API responses. Fields like `task.tags.slice()` and boolean checks in card rendering dereference raw properties before any formatting function runs. **This redesign should not introduce full runtime schema validation** — that's a separate engineering concern. But:

**What the redesign SHOULD do:**
- Formatting utility functions must be null-safe: null/undefined input → sentinel display value ("—"), never throw
- Unknown enum values → display raw text, neutral styling (for config-driven enums) or with warning badge (for fixed vocabularies like signal states)
- Malformed timestamps → display raw string, not crash
- For critical availability signals: if `blocked`, `priority`, or `status` is missing/malformed, the signal must resolve to an explicit **"unknown" state** — visually distinct from "ready" — so humans don't misread task availability. This requires adding an unknown branch to the signal type system.

**What the redesign should NOT do:**
- Add Zod/io-ts runtime validation at the API boundary (out of scope)
- Add defensive checks around every property access in existing components (out of scope — that's tech debt, not visual redesign)
- Try to solve the stale-write problem in the interaction layer (the `updated` token staleness in drag/context-menu state is a pre-existing mutation-safety concern, not caused by this redesign)

## Stale-Write Risk: Acknowledged, Out of Scope

The Critic correctly identified that `updated` tokens can go stale in the interaction layer — drag state, context-menu moves, and archival flows snapshot `updated` into local state and may reuse it after SSE-triggered refetch has delivered a newer value. This is a **pre-existing mutation-safety concern**. The formatting layer cannot fix it and should not try. The redesign's responsibility is narrower: **don't make it worse.** Specifically:
- Never format the `updated` value in a way that loses the original
- Never use formatted timestamps as mutation inputs
- If the redesign refactors data flow through components, preserve the existing `updated`-passthrough pattern

## Formatting Utilities: Recommended Shape

Pure functions in a `utils/format.ts` module:
- `formatRelativeTime(iso: string | null): string` — relative for <24h, date for older, "—" for null/malformed
- `formatDuration(seconds: number | null): string` — "1h 23m", "< 1m", "—" for null
- `formatSignal(signal: Signal): { label: string, icon: string, severity: string }` — maps computed signal to display including the new "unknown" state
- `formatPriority(p: string | null, knownPriorities: string[]): { label: string, severity: string }` — dynamic lookup, fallback to raw display
- `formatSessionState(state: string): { label: string, severity: string }` — session-specific, separate from task formatting

These are display-boundary transforms. They do not change the API contract. `computeSignal` is the exception — it IS domain logic, already exists, and should be extended (unknown state) rather than reimplemented.

## Key Trade-offs

| Decision | Trade-off |
|----------|-----------|
| Relative timestamps on cards | Loses precision for forensic comparison — acceptable for triage, sidecar shows full timestamp |
| No runtime schema validation | Malformed API responses can still crash components — but adding validation is scope creep for a visual redesign |
| Unknown signal state | Adds visual noise for edge cases — but prevents false "ready" signal on malformed tasks |
| Config-driven enum formatting | No visual treatment for truly unexpected values — but this matches the dynamic nature of the board config |
| Not fixing stale-write risk | Pre-existing bug persists — but it's not caused by or worsened by the visual redesign |

## Warnings

1. **Formatter functions must never be in the mutation path.** If a future refactor routes edit/move payloads through any transform that touches display formatting, the `updated` concurrency token will corrupt. This is the single highest-integrity risk.
2. **The three-stream freshness model means card signal can be stale relative to DR state.** If a DR is resolved but the DR poll hasn't fired yet, the card will still show "decision pending." This is acceptable (conservative error — shows more blocked, not less) but should be documented.
3. **System-coupled tags (`block:user`) must not be stripped or reformatted in a way that prevents round-tripping through the edit API.** Tag chips are display; the underlying array is canonical.
4. **`computeSignal` extension (unknown state) must be covered by tests** that exercise the missing-field paths. The current test suite only covers well-formed inputs.

## Confidence

**0.80** — The core partition (canonical vs. display) and the signal integrity requirements are well-grounded. The honest scoping of what this redesign should and should not fix addresses the Critic's overclaim concern. Remaining uncertainty is in edge cases around the three-stream freshness model and whether the "unknown" signal state will surface in practice.
