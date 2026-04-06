---
id: 660
title: Implement resolve-summary.json typed contract for scribe↔orchestrator boundary
status: backlog
priority: important
created: 2026-04-06T08:01:24.034837+02:00
updated: 2026-04-06T15:05:43.9971431+02:00
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

[[2026-04-06]] Mon 15:05
## Research
- Research doc: .owlbear/research/scribe-orchestrator-typed-contract.md (validation pass — doc from #657, same day, fully pipeline-approved and archived)
- Sources: 7 studied (all internal codebase), 4 high-relevance — unchanged from #657
- Recommendation: Option A — resolve-summary.json file (confidence: .80, unchanged)
- Follow-up tasks created: none (this task IS the implementation follow-up from #657)
- Decision requests: none (T1 — refactor within approved scope)

## Validation Pass Results
Codebase state matches all research doc assumptions:
- Carve-out exception confirmed at orchestrator.agent.md L44
- NEEDS-INFO text parsing confirmed in w-orchestration Step 1 (L38)
- 3-line text output contract confirmed in scribe.agent.md L100-106
- NEEDS-INFO signal confirmed in w-decision-routing resolve mode
- No additional files outside the 4 identified reference the text-parsing pattern

## Change Impact Map (11 change points, 4 files)
1. `share/agents/orchestrator.agent.md` L44 — remove carve-out exception, reference resolve-summary.json
2. `share/agents/scribe.agent.md` L71 — add file write to needs-info signal flow
3. `share/agents/scribe.agent.md` L100-106 — add resolve-summary.json write to resolve output contract
4. `share/skills/w-orchestration/SKILL.md` L16 — context budget: remove exception note
5. `share/skills/w-orchestration/SKILL.md` L17 — state: needs_info_dispatches sourced from file, not text
6. `share/skills/w-orchestration/SKILL.md` L26 — signal contracts: remove exception note
7. `share/skills/w-orchestration/SKILL.md` L36-38 — Step 1: replace text parsing with readFile + delete
8. `share/skills/w-orchestration/SKILL.md` L62 — Step 2: needs_info_dispatches unchanged (same injection logic)
9. `share/skills/w-orchestration/SKILL.md` L201 — verification checklist: update source reference
10. `share/skills/w-orchestration/SKILL.md` L207 — pitfall: rewrite for file-based pattern
11. `share/skills/w-decision-routing/SKILL.md` resolve §4 — add file write step to needs-info flow

## Challenge Results
- Challenger: SKIP — validation pass of existing challenged recommendation (challenged in #657: reconsider, confidence revised .85→.80, rebutted)
- Confidence in original: .80
- Key challenges: already addressed in #657 (transport-vs-semantics, stale-file risk, Option D dismissal)
- Researcher response: no new concerns found; all #657 guidance for #660 AC is present
