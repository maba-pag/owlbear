# Simplifier Stance — Cockpit Visual Redesign

## Core Diagnosis

The previous brief failed and produced a 10/100. The proposed response is a *larger, more comprehensive* brief covering 73+ findings across 4 tiers. This is scope inflation disguised as thoroughness. A bigger plan does not fix the execution problem — it makes it worse.

## Cut 1: The Brief Should Be Tier 1 Only

**Tier 1 (PDS foundation) is the only structural prerequisite.** It unblocks everything else. Tiers 2–4 are independent, parallelizable follow-ups that don't need architectural decisions — they're mechanical migration.

Deliver Tier 1 as a single brief:
- Install PDS stylesheet imports (variables, font-face, normalize)
- Delete `tokens.css`
- Confirm both themes render

This is 3–5 tasks. It can be verified visually in one session. It transforms the baseline from "nothing works" to "PDS is live, components inherit real tokens."

## Cut 2: Component Migration Is Not a Brief — It's a Checklist

Replacing `<button>` with `<PButton>` nine times is not architecture. It's grep-and-replace with type checking. Same for the five raw options, seven lists, five headings. These don't need panel deliberation, domain panelists, or decision gates. They need a task tagged `chore` with a file list.

**Defer Tier 2 entirely.** After Tier 1 lands, file individual tasks per component type (buttons, modals, lists). Each is ~30 minutes of work. No brief needed.

## Cut 3: Layout Redesign Should Be Its Own Brief (If Warranted)

Board grid, sidecar sections, card metadata, filter panel — these are UX decisions that affect interaction patterns. They *might* warrant a brief, but only after Tier 1 lands and you can see what PDS defaults already fix for free. Half the "layout problems" may vanish when real tokens, spacing, and typography are active.

**Defer Tier 3.** Evaluate after Tier 1.

## Cut 4: Tier 4 Is Pure Polish — Never Brief-Worthy

Timestamp formatting, dark mode borders, ESLint bans, screenshot tests. These are backlog tasks, not brief material. File them individually.

## Why the Old Brief Failed (and This One Would Too)

The old brief failed because:
1. It tried to do foundation + migration + layout in one execution pass
2. Without the foundation installed, every other change was building on sand
3. Execution couldn't tell "done" from "partially done" because the scope was too broad to verify

This proposal repeats the same pattern but bigger. 73 findings ≠ 73 things that belong in one delivery unit.

## Recommended Decomposition

| Delivery unit | Scope | Brief? | Tasks |
|---|---|---|---|
| **P1 — Foundation** | Install PDS stylesheet, delete tokens.css, confirm themes | Yes (this brief) | 3–5 |
| **P2 — Component swap** | Mechanical PDS React wrapper replacements | No — task batch | ~8 |
| **P3 — Layout** | Board scroll, sidecar padding, card metadata | Maybe — evaluate post-P1 | TBD |
| **P4 — Polish** | Dark mode, timestamps, a11y, lint rules | No — backlog tasks | ~10 |

## The 80/20

P1 alone takes the score from 10/100 to ~40/100 (real tokens, real fonts, real spacing on every existing PDS component). P1 + P2 gets to ~65/100. P3 is where UX judgment matters. P4 is gravy.

Trying to plan all four in one brief is how you get another 10/100.

## Confidence

**0.85** — High confidence that the 4-tier-in-one-brief pattern will repeat the old brief's failure mode. The foundation must land alone and be verified before anything else is planned on top of it.
