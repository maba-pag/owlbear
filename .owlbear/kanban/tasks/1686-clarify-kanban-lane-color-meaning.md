---
id: 1686
title: Clarify kanban lane color meaning
status: research
priority: important
created: 2026-05-21T19:52:28.209451+02:00
updated: 2026-05-21T19:52:28.209451+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - kanban
  - visual-system
parent:
depends_on: []
ac:
  - Audit current lane accent colors and their source/mapping.
  - Classify whether colors carry real semantics or decorative ambiguity.
  - Adopt a consistent lane color system with documented product meaning.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
The colors above Kanban columns/lanes need explanation. Do those specific colors have meaning? If not, why are they varied but not a rainbow, increasing scale, or just Porsche red?

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current visual-system ambiguity.
- Value question: lane color should communicate workflow/status meaning, reinforce brand, or disappear; decorative arbitrary color weakens trust.
- Screenshot target: full Kanban header/lane row across all lanes.

## Acceptance Criteria
- Identify current lane color mapping and whether it has semantic meaning.
- Choose a consistent visual system: semantic, restrained brand, or no lane accent.
- Document the rationale and ensure color does not imply false status meaning.