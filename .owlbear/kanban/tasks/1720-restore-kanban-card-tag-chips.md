---
id: 1720
title: Restore kanban card tag chips
status: done
priority: important
created: 2026-05-23T01:27:54+02:00
updated: 2026-05-23T01:39:10+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - kanban
  - cards
  - tags
parent:
depends_on: []
ac:
  - Restore tag bubbles on Kanban task cards where they add scanning value.
  - Show actual tags instead of a generic `+N tags` overflow line when practical.
  - Allow cards to grow for real tag content rather than hiding useful metadata.
  - Validate with desktop screenshot evidence and focused quality checks.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Kanban task tags were one of the few places where bubbles made sense, but they were removed. Most cards now end with `+1 tags` or `+2 tags`; that space could show the actual tags instead. Tags are usually short and few enough to fit, and enlarging the card is acceptable if the content is useful.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current UI regression, not theoretical.
- Product value: tags support fast scanning, filtering, and topic recognition; unlike status chips, they are not already encoded by the column layout.
- Impact: hurts Cockpit now because generic overflow text hides the exact metadata that helps users decide which task to open.
- Screenshot target: real Kanban cards at desktop width, especially cards with 4+ tags.

## Acceptance Criteria
- Kanban cards render normal tags as compact chip/bubble metadata again.
- Cards show all non-redundant visible tags instead of a `+N tags` overflow summary.
- The `active-decision` duplicate remains hidden when the card already shows the Decision signal.
- Tags wrap without clipping; card height may grow for useful metadata.

## Completion Evidence
- Implementation: Kanban card tags now render as compact secondary PDS `PTag` chips again. The previous `+N tags` overflow summary was removed; all non-redundant tags render and wrap naturally inside the card.
- Product classification: confirmed current UI regression, not theoretical. The previous quiet text treatment hid useful metadata behind generic counts, while the restored chips make topic/scope scanning faster without reintroducing the redundant status chip.
- Real-data browser proof: `.owlbear/scratch/1716-wide-cockpit/kanban-tags-1720.png` at 2560x1440 shows restored tag chips on the board.
- Metrics from the real board: 44 cards present, 44 cards with visible tags, max 7 tags on a card, 0 `card-tag-overflow` elements. Sample card heights stayed compact at 124px for most tagged cards, with taller cards only when tag/content density warranted it.

## Verification
- `npx vitest run src/__tests__/Card.visual-treatment.test.tsx src/__tests__/CardVariants.test.ts --reporter=json --outputFile=/Users/markus/Projects/owlbear-dev/.owlbear/scratch/1720-vitest-card-tags.json` -> 49 tests passed.
- `npx eslint src/components/Card.tsx src/__tests__/Card.visual-treatment.test.tsx src/__tests__/CardVariants.test.ts` -> passed.
- `npm run build` -> passed; existing Vite chunk-size warning only.