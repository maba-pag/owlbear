# Simplifier Stance — Pipeline Review Rethink (Pass 2)

## Cuts

### Cut 1: Tagging is infrastructure, not a role behavior
Tagging requires schema + tooling + GC mechanism. Bundling it into role redesign couples delivery risk. Remove all tagging from role definitions. Roles define cognitive work, not metadata emissions. Tagging bolts on later (or lives as CI lint instead).

### Cut 2: "Tagging compliance" is make-work for reviewer
If tagging exists, compliance is `grep` — that's CI, not a reviewer cognitive task. Cut from reviewer role entirely.

### Cut 3: Re-running tests — already dead, bury it
User confirmed little value. Remove completely from reviewer. Reviewer reads test results; does not execute.

## Role Table After Cuts

| Agent | Single cognitive job |
|-------|---------------------|
| Planner | Intent clarity + AC scaffold |
| Architect | AC rewrite + feasibility gate |
| Test-writer | Tests from final AC |
| Builder | Implementation (self-checks via feedback loop) |
| Reviewer | AC completion audit: what's missing or incomplete? |
| Auditor | Cross-cutting: regression, broken deps, logic flaws, intent drift |

This is the user's hypothesis minus tagging. The "redesign" is mostly subtraction (removing redundant checks) and sharpening (making non-overlap explicit).

## Decomposition: 2 Phases

**Phase 1 — Role boundaries (no new mechanisms)**
- Rewrite skill files for all 6 agents with sharpened definitions
- Remove: reviewer test re-execution, duplicated checks
- Define handoff contracts between each pair
- Order: upstream first (planner→architect→test-writer), then downstream (builder→reviewer→auditor)
- Ship as one atomic commit
- Validate by replaying 2-3 recent tasks as dry-run

**Phase 2 — Metadata system (conditional)**
- Only if Phase 1 empirically shows pipeline still loses track of temporary code/tests
- May be unnecessary — sharper roles might solve it

## Risk

Real risk is NOT coordination failure — it's **insufficient pressure-testing**. Skill file words are cheap; they collapse into overlap when agents interpret with LLM fuzziness. Antidote: dry-run replay, not more design time.

## Confidence: 0.85
