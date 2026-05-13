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

**Chosen:** No new features or behavioral changes. JSX changes in service of visual quality are acceptable. This includes: className additions, inline style removal, wrapper elements for padding/radius, layout property changes.

**Rationale:** PDS spacing, radius, and composition conventions may require minor structural adjustments. Blocking those creates worse CSS hacks. The constraint is behavioral, not structural.

**Source inputs:**

- User: "what if we notice that certain margins, corner radiuses, distances are recommended or required resulting in necessary changes?"
- Simplifier: "you *must* touch JSX to add className and remove inline styles"
- First-principles: "Card.tsx has 16 lines of inline styles with conditional logic"
