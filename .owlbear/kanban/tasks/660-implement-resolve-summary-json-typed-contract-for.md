---
id: 660
title: Implement resolve-summary.json typed contract for scribe↔orchestrator boundary
status: research
priority: important
created: 2026-04-06T08:01:24.034837+02:00
updated: 2026-04-06T08:01:24.034837+02:00
tags:
    - scope:pipeline
    - ' type:refactor'
depends_on:
    - 657
class: standard
---

## Summary

Replace the text-based NEEDS-INFO signal with a JSON file contract. The scribe writes `.owlbear/decisions/resolve-summary.json` after processing DRs; the orchestrator reads it instead of parsing Channel A text.

See `.owlbear/research/scribe-orchestrator-typed-contract.md` §4 for design.

## Acceptance Criteria

- [ ] Scribe resolve mode writes `.owlbear/decisions/resolve-summary.json` with `{resolved, needs_info, pending}` arrays after processing all DRs
- [ ] Orchestrator Step 1 reads `resolve-summary.json` via `readFile` after scribe returns
- [ ] Orchestrator deletes `resolve-summary.json` after reading (stale-file mitigation)
- [ ] Missing file treated as empty dispatches (graceful degradation)
- [ ] Carve-out exception removed from `orchestrator.agent.md` critical_rules
- [ ] `w-orchestration` Step 1 updated: file read replaces text parsing
- [ ] `w-decision-routing` resolve output contract updated
- [ ] `scribe.agent.md` resolve output contract updated to include file write
- [ ] NEEDS-INFO dispatch injection still works end-to-end
- [ ] No regression in DR processing (approved, rejected, completed, needs-info, auto-approved)

## Files Affected

- `share/agents/scribe.agent.md` — resolve output contract + file write
- `share/agents/orchestrator.agent.md` — remove carve-out exception
- `share/skills/w-orchestration/SKILL.md` — Step 1 rewrite
- `share/skills/w-decision-routing/SKILL.md` — resolve output spec
