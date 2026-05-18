# Decisions — Cockpit Ideas Notebook

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
