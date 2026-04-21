---
id: 1041
title: Ideation overhaul validation artifacts
status: review
priority: needed
created: 2026-04-20T23:33:20.352087+00:00
updated: 2026-04-20T23:33:20.352087+00:00
tags:
- ideation
- wave-1
- brief-driven
- validation
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Add the remaining repo-side Wave 1 validation artifacts for the ideation overhaul in owlbear-dev.

Scope:
- add at least three named golden-scenario classes under the canonical ideation-overhaul brief
- carry the decision entry template into the workflow surface and blackboard docs
- extend static validation so the new artifacts are required by the repo contract
- keep completion language honest: this is repo-side validation scaffolding, not live runtime validation on the main-consuming surface

Out of scope:
- live scenario execution on the main-consuming runtime
- merge/sync to main

[[2026-04-21]]
Implemented the missing repo-side validation layer. Added golden scenario fixtures under `.owlbear/briefs/draft-ideation-overhaul-2026-04-20/golden-scenarios/` for `01-net-new-work`, `02-existing-feature-refactor`, and `03-overscoped-request`, including working artifacts and qualitative review notes. Carried the decision entry template into `.owlbear/briefs/README.md`, `share/skills/w-ideation-discovery/SKILL.md`, and `share/skills/w-ideation-mediation/SKILL.md`. Extended `tests/test_ideation_overhaul_static.py` to require the template anchors and the golden-scenario fixture set. Verified with `uv run pytest -q tests/test_ideation_overhaul_static.py` -> `16 passed`.

Residual risk:
- live validation on the main-consuming runtime is still pending before full brief acceptance.