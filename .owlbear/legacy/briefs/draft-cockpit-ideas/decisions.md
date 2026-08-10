# Decisions — Cockpit Ideas Notebook

## D9 — 2026-05-18 — External-Edit Conflict Interaction

**Status quo:** D6 defines external-edit awareness but the "file changed externally" notice had no actionable interaction — Save still meant blind overwrite.
**Decision to make:** What happens when dirty + external change detected?

**Options considered:**

- A: Two-button interaction (Overwrite / Discard & Reload) — forces explicit choice
- B: Notice only, Save still works normally — awareness without agency
- C: Drop conflict notice entirely — simpler v1

**Chosen:** A — when dirty content + external change detected, show a notice with Overwrite and Discard & Reload buttons. Regular Save is disabled while the notice is showing, forcing an explicit choice. This completes the trust contract for explicit save (Critic Pass 2 finding #2, validated).

**Rejected:**

- B because naming a conflict without actionable options is worse than no notice at all.
- C because the feature's value is cockpit co-location alongside VS Code; ignoring the dual-surface reality undermines the value proposition.

## D6 — 2026-05-18 — External-Edit Awareness

**Status quo:** No mechanism to detect changes made to `.owlbear/ideas.md` outside the cockpit.
**Decision to make:** Include external-edit detection in v1 or defer?

**Options considered:**

- A: Re-fetch on tab focus (`visibilitychange` + re-fetch; dirty-state notice for conflicts)
- B: Defer to later — ship simple, see if stale-content friction materializes
- C: Manual refresh button

**Chosen:** A — re-fetch on tab focus AND route activation. Dual-surface use (cockpit + VS Code) is the expected pattern per D5. Shipping without detection creates predictable stale-content frustration on a feature whose value is co-location.

Triggers: (1) `visibilitychange` for alt-tab/minimize scenarios; (2) route activation (component remount) for intra-cockpit navigation (Ideas → Kanban → Ideas). Both are needed because `visibilitychange` alone misses intra-cockpit route changes (Critic finding #5, validated).

**Rejected:**

- B because the user knows dual-surface use is the norm; deferring would require a near-certain follow-up.
- C because it doesn't solve the problem — user must remember to click.

**Source inputs:**

- UX review: "dual-surface use is the expected pattern, not an edge case"
- Architecture review: silent on this topic (complementary coverage gap)

## D7 — 2026-05-18 — Preview Toggle

**Status quo:** Simplifier (Phase 1) proposed cutting preview entirely. Dependencies already bundled.
**Decision to make:** Include markdown preview toggle in v1 or ship textarea-only?

**Options considered:**

- A: Include preview toggle — complete feature, marginal code, supports re-reading
- B: Textarea-only — simplest v1, toggle trivially addable later

**Chosen:** A — include preview toggle in v1. Dependencies are already bundled, pattern exists in TaskFieldsEditor, and it supports the re-reading use case without requiring a context switch to VS Code.

**Rejected:**

- B because the incremental cost is low and the feature would feel incomplete without it.

## D8 — 2026-05-18 — Housekeeping Bundling

**Status quo:** Two minor items flagged by architecture review.
**Decision to make:** Bundle into ideas feature or separate tasks?

**Chosen:** Include `atomic_write` docstring update in the ideas feature scope. Update to remove kanban-specific framing since the function is now consumed cross-package.

**Removed from scope (Critic finding #3, validated):** CockpitProvider eager polling on non-board routes is an app-topology issue owned by #1638 (tab system), not page-local housekeeping. The ideas page depends on #1638 solving this.

**Rejected:**

- Separate task for docstring — too small to warrant its own task; naturally touched during implementation.

## D1 — 2026-05-17 — Project Type

**Status quo:** No prior classification.
**Decision to make:** Classify the work to scope the research approach.

**Options considered:**

- A: net-new — greenfield feature with no existing code
- B: existing-feature/refactor — extends or modifies existing cockpit code

**Chosen:** B (existing-feature/refactor) — the tab system infrastructure (#1638) is already designed and decomposed. This feature plugs into that system as a new route entry + page component + backend API pair. The markdown edit/preview pattern already exists in TaskFieldsEditor.

**Rejected:**

- A because the tab system and editor patterns already exist; this is additive, not greenfield.

## D2 — 2026-05-17 — Investment Tier

**Status quo:** No tier assigned.
**Decision to make:** Calibrate discovery depth.

**Options considered:**

- Scratch: minimal discovery, thin brief
- Tool: standard M2, selective panel, full brief
- Shared: full panel, research bridge required
- Production: full panel + Critic at every boundary

**Chosen:** Tool — internal utility for a single user, small scope, well-defined. Standard outcome definition + selective early challenge.

**Rejected:**

- Scratch because the feature touches both backend and frontend with reuse decisions worth recording.
- Shared/Production because single-user, no external consumers, no durability concerns beyond normal git tracking.

## D3 — 2026-05-17 — Save Behavior

**Status quo:** Brief proposed save button for v1, auto-save as v2 extension.
**Decision to make:** Save interaction model.

**Options considered:**

- A: Explicit save button only
- B: Auto-save on blur/idle
- C: Both (auto-save + manual fallback)

**Chosen:** A (explicit save button) — simple, predictable, matches the existing task editing UX. Reuse dirty-state patterns from TaskFieldsEditor.

**Rejected:**

- B/C because they add complexity without clear value for a single-user scratchpad. Can be added later if the friction of clicking Save proves annoying.

**Source inputs:**

- User: "save-button only... i would like to re-use what we have"

## D4 — 2026-05-17 — Agent Integration

**Status quo:** Brief mentioned agents picking up ideas from the file.
**Decision to make:** Whether to build any agent-facing integration.

**Chosen:** No agent integration — the file is plain markdown at `.owlbear/ideas.md`, git-tracked, visible to agents via filesystem. Users reference sections by heading when starting ideation manually.

**Rejected:**

- Any "send to ideation" button or structured format because it's overkill. "Ideate on the section ## xxx in the notepad file" works.

**Source inputs:**

- User: "there is no need for direct agent interaction... everything else is overkill"

## D5 — 2026-05-17 — Early Challenge Response

**Status quo:** Both challengers (simplifier, first-principles) questioned whether the cockpit is the right surface. VS Code is always open and is a better markdown editor. A zero-code trial (file + keybinding) was proposed.
**Decision to make:** Proceed with cockpit tab or trial-first?

**Options considered:**

- A: Two-week trial with `.owlbear/ideas.md` + VS Code keybinding, revisit after
- B: Build the cockpit tab anyway — preference for complete workspace experience
- C: Drop the feature

**Chosen:** B — the user acknowledges the challengers' points but wants the cockpit version as a workspace completeness preference. The feature is small, low-risk, and the tab system makes it trivial.

**Rejected:**

- A because the user has already decided they want the cockpit experience; a trial delays a small feature without changing the preference.
- C because the feature has legitimate (if preference-based) value.

**Note:** This is explicitly a preference feature, not a gap fix. The challengers' observation that VS Code is the superior editor is acknowledged and accepted — the value is cockpit co-location, not editing quality.
