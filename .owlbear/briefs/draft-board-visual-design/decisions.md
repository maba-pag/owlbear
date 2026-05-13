# Decisions — Board Visual Design

## D1 — 2026-05-13 — Project Type

**Status quo:** Brief describes adding CSS to existing components.
**Decision to make:** Is this net-new, existing-feature/refactor, or uncertain?

**Options considered:**

- A: Net-new (new visual system)
- B: Existing-feature/refactor (dress up existing structure)

**Chosen:** B — existing-feature/refactor

**Rejected:**

- A because the brief explicitly states "not a redesign, just dressing up the existing structure" and "no structural changes to JSX."

**Source inputs:**

- Input brief: "No structural changes to JSX — styling the existing elements"

## D2 — 2026-05-13 — Investment Tier

**Status quo:** Single-user internal cockpit, but visual baseline is consumed by all future cockpit features.
**Decision to make:** How much rigor for this brief?

**Options considered:**

- A: Tool — single user, standard depth
- B: Shared — multi-consumer artifact, full panel + research bridge

**Chosen:** B — Shared

**Rejected:**

- A because multiple future briefs (#7 Board Grouping, #8 Search, #5 Decisions Tab, etc.) will build on this visual baseline. Getting it right requires proper research into PDS patterns.

## D3 — 2026-05-13 — DnD Scope

**Status quo:** Native HTML DnD exists on task cards for status moves.
**Decision to make:** Remove, deactivate, or keep DnD?

**Chosen:** Keep for now. Don't remove, possibly deactivate if trivial. Style minimally if it stays active.

**Rationale:** DnD is useful for other things eventually, just not ideal for intentional task status changes. Removing is a functional change out of scope. If deactivation is simple, do it; otherwise style it passably and move on.

**Source inputs:**

- User: "i think dnd has its place, but it NOT moving tasks between status... if its already there i say we dont remove it, maybe we can deactivate it"

## D4 — 2026-05-13 — Dark Theme Shipping

**Status quo:** Original plan ships both light and dark themes. Challengers suggest dark QA doubles effort.
**Decision to make:** Ship both now or architect-now-ship-later?

**Options considered:**

- A: Ship both themes in this brief (styled, tested, toggle working)
- B: Architect for dark (extend tokens), ship light only, dark activation as fast follow-up

**Chosen:** A — Ship both themes now.

**Rejected:**

- B because user wants dark theme, the architecture cost is near-zero, and testing is manageable for 6 components.

## D5 — 2026-05-13 — JSX Change Boundary

**Status quo:** Original brief said "no structural changes to JSX." Challengers flag this is unrealistic for proper CSS implementation.
**Decision to make:** What's the real boundary for JSX changes?

**Chosen:** No new features or behavioral changes, EXCEPT the card signal model (D10) which replaces priority display with operational-state display. JSX changes in service of visual quality are acceptable. This includes: className additions, inline style removal, wrapper elements for padding/radius, layout property changes, and the card signal data wiring.

**Rationale:** PDS spacing, radius, and composition conventions may require minor structural adjustments. Blocking those creates worse CSS hacks. The card signal model is included because styling cards with the wrong (priority) border and then immediately changing it is throwaway work — one coherent pass is better.

**Amendment (Critic validation):** D10 requires adding `dep_status` to frontend Task type, connecting DR data to card rendering, and replacing priority rendering logic. This is bounded behavioral work included by explicit scope expansion.

**Source inputs:**

- User: "what if we notice that certain margins, corner radiuses, distances are recommended or required resulting in necessary changes?"
- Simplifier: "you *must* touch JSX to add className and remove inline styles"
- First-principles: "Card.tsx has 16 lines of inline styles with conditional logic"

## D6 — 2026-05-13 — Theme Toggle Mechanism

**Status quo:** Zero dark theme infrastructure exists in the frontend.
**Decision to make:** How should theme switching work?

**Options considered:**

- A: Auto only (`prefers-color-scheme`) — zero UI needed, follows OS
- B: Manual toggle only (`data-theme` + localStorage) — explicit control, ignores OS
- C: Both — auto default + manual override

**Chosen:** C — Both (auto default + manual override)

**Rationale:** Near-zero extra cost over manual-only, respects user intent in both directions. Auto-only blocks users who want dark-in-daylight; manual-only ignores system preference.

## D7 — 2026-05-13 — Card Height Constraint

**Status quo:** Cards use `minHeight: 48px, maxHeight: 56px` for tight density.
**Decision to make:** Keep fixed or release to grow with content?

**Options considered:**

- A: Keep fixed height (uniform grid, titles may truncate)
- B: Release constraint (cards grow with content)
- C: Hybrid (fixed default + expand on hover/focus)

**Chosen:** B — Release constraint (cards grow with content)

**Rationale:** Long titles shouldn't truncate. Cards show title + border only — no tags or labels — so growth is bounded by title length. Density remains naturally tight for most tasks.

**Amendment (Critic validation):** Original rationale referenced tags (no longer on cards). Updated to reflect actual card content model.

## D8 — 2026-05-13 — Column Scroll Behavior

**Status quo:** Column has conditional `overflowY`. No fixed header.
**Decision to make:** Fixed header with scrolling body, or full-column scroll?

**Chosen:** Fixed header + scrolling body

**Rationale:** Column identity and count should always be visible for board scanning. CSS cost is minimal (flex-column with overflow on the body).

## D9 — 2026-05-13 — Empty State Design

**Status quo:** Empty columns show nothing or plain text.
**Decision to make:** What visual treatment for empty columns?

**Options considered:**

- A: Minimal text ('No tasks')
- B: Dashed border invitation
- C: PDS illustrated placeholder (icon + message)

**Chosen:** C — PDS illustrated placeholder

**Rationale:** User prefers the more designed feel. Icon + message communicates state clearly and maintains visual quality bar.

## D10 — 2026-05-13 — Card Left-Border Signal Model

**Status quo:** Card left border encodes priority (critical=red, needed=orange, important=blue, nice-to-have=blue, someday=grey). Blocked/claimed use emoji badges (⛔, ▶).
**Decision to make:** What does the left border encode?

**Chosen:** Left border encodes operational state, NOT priority. Priority is dropped from card display entirely.

**Signal model (exhaustive, mutually exclusive, with override precedence):**

| State | Color | Condition |
|-------|-------|-----------|
| Ready | White/Black (theme-aware) | Default — no other condition active |
| Deps unmet | Grey | Dependencies not met |
| Blocked | Red | `blocked === true` and no DR/AR |
| DR/AR exists | Orange | Decision request pending (overrides blocked) |
| Claimed | Purple (fallback blue) | Agent actively working |

**Rejected:**

- Priority-based border (current impl) because user doesn't find priority valuable at board-scan level
- Background tints because user wants border-only signaling
- Emoji badges because user prefers color-symbolic over text/symbol indicators
- Text labels (WCAG) because single-user tool, color suffices

**Source inputs:**

- User: "only left border for signals. red = blocked, orange = AR/DR exists, white/black = ready for dispatch, grey = dependencies unmet, purple = claimed. no background tint, no border tint."
- User: "i prefer color symbolic over symbols on the tasks"
- User: "drop priority from being exposed, user doesnt care"

## D11 — 2026-05-13 — Empty State Illustration Approach

**Status quo:** D9 chose illustrated placeholders.
**Decision to make:** What kind of illustrations, and how are they produced?

**Chosen:** Fun, status-appropriate illustrations (not onboarding messages). Deliverable: a file with prompts for an image-generating LLM (e.g., Nano Banana) specifying dimensions, file type, and creative direction per status. User runs the prompts and supplies the resulting images.

**Rationale:** Illustrations should be whimsical and status-relevant. Using image-gen prompts as the deliverable separates creative direction (brief scope) from image production (user scope).

## D12 — 2026-05-13 — Theme Toggle Placement

**Chosen:** Status bar, right side.

**Rationale:** Conventional, discoverable location (GitHub, VS Code use footer/status area for theme toggles).

## D13 — 2026-05-13 — Column Minimum Width

**Chosen:** 200px floor (replaces current 80px in `minmax()`).

**Rationale:** Readable card titles; board uses horizontal scroll when columns exceed available space.

## D14 — 2026-05-13 — Signal Precedence

**Chosen:** Orange (DR/AR) > Red (blocked) > Purple (claimed) > Grey (deps unmet) > White/Black (ready)

**Rationale:** "Needs human decision" trumps all. Blocked prevents work. Claimed beats deps-unmet because a task CAN be picked/claimed even if deps are unmet, but not if blocked. Ready is the default.

**Note:** Selected and drag-target are UI states that layer on top via different CSS channels (outline, box-shadow) — they don't replace the left border signal.

## D15 — 2026-05-13 — Responsive Overflow

**Chosen:** Sidecar collapsible (default open) + horizontal scroll on board container.

**Rationale:** 7 columns × 200px + gaps exceeds available space at most viewport widths. Collapsible sidecar gives the board more room when needed. Horizontal scroll handles the remaining overflow.
