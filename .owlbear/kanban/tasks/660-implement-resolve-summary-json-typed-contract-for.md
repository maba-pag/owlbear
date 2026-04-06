---
id: 660
title: Implement resolve-summary.json typed contract for scribe↔orchestrator boundary
status: review
priority: important
created: 2026-04-06T08:01:24.034837+02:00
updated: 2026-04-06T18:55:22.1296624+02:00
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

[[2026-04-06]] Mon 16:26
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: replace text-parsing NEEDS-INFO signal with file-based JSON contract. All 11 change points serve this single objective. |
| Interface clarity | PASS | AC specifies JSON schema (`{resolved, needs_info, pending}` arrays), file location, read/delete lifecycle, and graceful degradation for missing file. Research doc §4 provides exact per-item schema. |
| Dependency correctness | PASS | Depends on #657 (research) — verified `archived`. No missing dependencies. |
| Module layering | PASS | All changes are prompt-layer (agent/skill markdown). No Python code. Scribe writes → orchestrator reads: correct dependency direction. |
| TDD compliance | PASS | Non-impl task (markdown only). Requires `agent` pass-through tag — **add `agent` tag before test-writer processes**. |
| KISS/YAGNI | PASS | Minimal scope: 4 files, 11 change points, zero Python code. JSON structure is exactly what's needed. |
| Premise challenge | PASS | Current text-parsing approach requires a critical_rules carve-out exception — replacing it with file-based state is justified. |
| Pattern consistency | PASS | File-based inter-agent state has precedent (`curation-report.json`). readFile + delete-after-read is standard infrastructure pattern. |
| Security surface | PASS | No new system boundaries. File written/read within `.owlbear/decisions/` namespace (scribe's existing domain). Trusted internal JSON. |
| Single domain | PASS | All within pipeline/orchestration domain. All 4 files in `share/agents/` and `share/skills/`. |

### Failure Mode Map

Not applicable — no Python codepaths. All changes are prompt-level instructions for LLM agents. Key edge cases already covered by AC:
- Scribe fails to write file → AC4: missing file = empty dispatches (graceful degradation)
- Orchestrator fails to delete → AC3: stale-file mitigation (delete-after-read instruction)
- Scribe crashes mid-run → partial file is safe: each DR resolution is atomic; delete-after-read prevents stale data; next cycle processes remaining DRs

### Challenge Results
- Challenger: FALLBACK — no challenger agent available in current session
- Prior challenge from #657: `reconsider` → confidence revised .85→.80, rebutted. Transport-vs-semantics concern addressed (all options share the semantic property). Stale-file risk mitigated by delete-after-read.
- Architect assessment: research challenge was thorough; no new concerns found in AC review.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Scribe writes resolve-summary.json | Verifiable — check file write instruction in scribe output contract | None |
| Orchestrator reads via readFile | Verifiable — check Step 1 instructions | None |
| Orchestrator deletes after reading | Verifiable — check delete instruction in Step 1 | None |
| Missing file = empty dispatches | Verifiable — check graceful degradation language | None |
| Carve-out exception removed | Verifiable — check orchestrator.agent.md L44 | None |
| w-orchestration Step 1 updated | Verifiable — check file-read replaces text-parsing | None |
| w-decision-routing updated | Verifiable — check resolve output spec | None |
| scribe.agent.md updated | Verifiable — check output contract includes file write | None |
| NEEDS-INFO still works E2E | Verifiable — trace through updated instructions | None |
| No regression in DR processing | Verifiable — check all 5 response types still documented | None |

### Architecture Notes
- After refactor, orchestrator critical_rules "Never interpret pipeline-agent output" becomes absolute (no exception). File reading is infrastructure data access, not output interpretation.
- Scribe writes file synchronously before returning → no race condition with orchestrator read.
- Delete-after-read is essential: prevents stale data accumulation across cycles.

### Action Required
- **Add `agent` pass-through tag** before test-writer processes (non-impl task producing no testable Python code).

### Verdict: APPROVE
### Action Taken: Advance to todo. All 10 AC lines are verifiable, architecture is sound, dependency #657 archived. Pass-through tag `agent` needed.

[[2026-04-06]] Mon 17:15
## Test-Writer Notes
- Non-implementation task (tagged type:refactor, scope:pipeline) — no tests applicable.
- All 4 files affected are prompt-layer markdown: `share/agents/scribe.agent.md`, `share/agents/orchestrator.agent.md`, `share/skills/w-orchestration/SKILL.md`, `share/skills/w-decision-routing/SKILL.md`.
- Architecture review explicitly flagged: "Non-impl task (markdown only). Requires `agent` pass-through tag."
- AC keywords scanned: no `implement`, `function`, `class`, `src/`, `.py`, or Python import references found.
- Heuristic pass-through: config/docs only (`.agent.md` + `SKILL.md` changes).
- Passing through to builder.

[[2026-04-06]] Mon 18:55
## Builder Notes

**Non-implementation task — all changes are prompt-layer markdown (4 files, 11 change points).**

### Files Changed
- `share/agents/orchestrator.agent.md` — removed carve-out exception from critical_rules; replaced with reference to `resolve-summary.json` via `readFile`
- `share/agents/scribe.agent.md` — added `needs_info` array collection to needs-info signal flow (L71); added `resolve-summary.json` write instruction + JSON schema to resolve output contract (L100-106)
- `share/skills/w-orchestration/SKILL.md` — 7 change points: context budget (remove exception), state variable source, signal contracts, Step 1 file-read-and-delete, verification checklist updated, pitfall rewritten for file-based pattern
- `share/skills/w-decision-routing/SKILL.md` — added step 4 (record in resolve-summary.json) to needs-info flow; step 5 renumbered

### Test Results
Non-implementation task — no Python code, no tests applicable.

### Lint Status
No Python files changed — ruff N/A. Markdown files verified via read-back.

### AC Evidence
- [x] Scribe resolve mode writes `resolve-summary.json` with `{resolved, needs_info, pending}` arrays — added to output contract with JSON schema
- [x] Orchestrator reads `resolve-summary.json` via `readFile` after scribe returns — updated Step 1
- [x] Orchestrator deletes `resolve-summary.json` after reading — delete-after-read instruction in Step 1
- [x] Missing file treated as empty dispatches — graceful degradation note in Step 1
- [x] Carve-out exception removed from `orchestrator.agent.md` critical_rules — verified
- [x] `w-orchestration` Step 1 updated: file read replaces text parsing — verified
- [x] `w-decision-routing` resolve output contract updated — step 4 added to needs-info flow
- [x] `scribe.agent.md` output contract updated to include file write — verified
- [x] NEEDS-INFO dispatch still works E2E — same `needs_info_dispatches` injection in Step 2, source is now the JSON file
- [x] No regression in DR processing — all 5 response types still documented and handled
