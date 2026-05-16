# Decisions — Cockpit Visual Redesign

## D1 — 2026-05-16 — Project Type

- **Chosen:** existing-feature/refactor
- **Rationale:** All JSX structure exists. The work is installing PDS foundation, migrating components to PDS React wrappers, replacing custom tokens with PDS variables, and adding CSS. No new features.
- **Rejected:** net-new — the cockpit ships and works; this is a visual quality pass, not a rebuild.

## D2 — 2026-05-16 — Investment Tier

- **Chosen:** Shared
- **Rationale:** The cockpit is a multi-consumer artifact — used directly, surfaces pipeline data, and sets the visual baseline all future features inherit. Full panel and research bridge are warranted.
- **Rejected:** Tool (too shallow — this isn't a single-user utility), Production (no external users yet).

## D3 — 2026-05-16 — Relationship to draft-board-visual-design

- **Chosen:** Supersede — this discovery produces the definitive brief; the old one is retired.
- **Rationale:** The old brief is responsible for the current 10/100 state. Its execution was ineffective — PDS foundation was never installed, component migration barely happened, layout was left in inline styles. The comprehensive audit revealed the problem is deeper than the old brief's "apply PDS tokens" framing. Starting clean from the audit findings.
- **Rejected:** Additive/complementary — the old brief's scope definition was the root of the failure, not just gaps in execution. Building on it would inherit the same framing problems.

## D4 — 2026-05-16 — Follow PDS recommendations strictly, including Tailwind

- **Chosen:** Follow PDS v4 documentation recommendations as closely as possible. Install full PDS stylesheet, use PDS Tailwind integration, adopt PDS component library comprehensively. Do not second-guess or simplify away what PDS recommends.
- **Rationale:** The previous brief failed *because* agents questioned design system recommendations and took "simpler" shortcuts. The result was a hand-rolled token system that shadowed PDS, producing 10/100. The early challengers (simplifier, first-principles) repeated this exact pattern — arguing from abstract simplicity to skip PDS-recommended tools. This is sunk-cost reasoning: the agents built the broken custom system and now argue to preserve the approach by questioning the replacement. The correct response is to go back, acknowledge the wrong turn, and follow the map (PDS docs) this time.
- **Rejected:** "Tailwind is unearned / not needed" (first-principles stance) — PDS provides the Tailwind integration for a reason; questioning it is the same pattern that produced the failure.
- **Rejected:** "Scope to Tier 1 only, evaluate Tailwind later" (simplifier stance) — incremental half-adoption is how we got the current state. Install the full recommended stack from the start.

## D5 — 2026-05-16 — Early challenger stances: acknowledged but overridden

- **Acknowledged:** Both challengers correctly identified that tokens.css is the root cause and that the 73 findings are mostly one defect expressed everywhere.
- **Acknowledged:** Both challengers correctly flagged the execution risk (builder agents writing CSS blind) and the need for human visual review between batches.
- **Overridden:** Their recommendation to skip/defer Tailwind and scope down to "just the foundation." The user's direct experience is that this reductive pattern *is the failure mode*. PDS recommends a stack; we adopt the stack.
- **Retained for Phase 2:** Smaller batches with human checkpoints. Re-audit after foundation lands. Builder visual feedback as a process constraint.
