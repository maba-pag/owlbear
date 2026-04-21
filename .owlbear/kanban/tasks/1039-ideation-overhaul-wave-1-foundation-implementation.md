---
id: 1039
title: Ideation overhaul Wave 1 foundation implementation
status: review
priority: important
created: 2026-04-20T22:46:36.851409+00:00
updated: 2026-04-21T13:41:32.872692+00:00
tags:
- ideation-overhaul
- wave-1
- brief-driven
parent:
depends_on: []
blocked: false
block_reason:
claimed_by: jade-fern
claimed_at: 2026-04-21T13:41:32.872692+00:00
---
Implement Wave 1 of the ideation overhaul directly in owlbear-dev, using the canonical brief at .owlbear/briefs/draft-ideation-overhaul-2026-04-20/brief.md as source of truth.

Scope:
- split the ideation workflow surface toward discovery vs mediation
- resolve single-ideator assumptions in dev-branch agent contracts
- introduce the early challenge lane foundation
- keep changes coherent in the dev repo without depending on the consumer/main branch

Out of scope:
- full Wave 2 behavioral refinement
- pipeline delegation of this first implementation wave
- changes to the adjacent consumer repo

[[2026-04-20]]
Implemented the Wave 1 ideation foundation split in the dev repo. Added phase-specific workflow skills (`w-ideation-discovery`, `w-ideation-mediation`), converted `w-ideation` into a thin router, turned `ideator` into a compatibility router, added new user-facing agents (`ideation-discoverer`, `ideation-mediator`), added early challengers (`ideation-firstprinciples`, `ideation-simplifier`, `ideation-outsider`), updated `ideation-pragmatist` for converge/denoise modes, removed hardcoded model dependency from `ideation-critic`, refreshed the panel handbook, and updated the blackboard/agent docs for the new phase model. Verified edited files with `get_errors` and repo searches for stale ideation references in the active surfaces.
[[2026-04-20]]
Post-implementation audit note: the phase-split foundation remains sound, but Wave 1 acceptance was not actually complete at closure time because the brief's scenario-driven validation layer (golden scenarios / artifact evidence) had not yet been added. Treat this task as foundation complete, not full Wave-1 acceptance.
[[2026-04-20]]
Validation-artifact follow-up is now split into a new task so this foundation task stays scoped to the phase-surface implementation only.
[[2026-04-20]]
Starting the actual follow-up task creation now.
[[2026-04-20]]
No further status-only updates after this; file work follows the new task.