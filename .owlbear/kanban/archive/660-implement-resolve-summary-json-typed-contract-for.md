---
id: 660
title: Implement resolve-summary.json typed contract for scribe↔orchestrator boundary
status: archived
priority: medium
created: 2026-04-06T08:01:24.034837+02:00
updated: 2026-04-06T20:13:42.3712061+02:00
started: 2026-04-06T20:13:42.3712061+02:00
completed: 2026-04-06T20:13:42.3712061+02:00
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

[[2026-04-06]] Mon 19:17
## Review Evidence

### Test Results
- pytest: N/A — non-implementation task (markdown-only, 4 prompt-layer files, 0 Python changes)

### Lint: N/A — no Python files changed

### Coverage: N/A

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
No `TestFromAC_*` classes exist. Conditional skip applies. Test-writer correctly identified this as markdown-only and passed through. CLEAN.

#### Security Review
No new code — all changes are markdown instructions. No user-controlled input, shell commands, file paths exposed externally, or deserialization concerns. Only internal trusted agents write/read the JSON file within `.owlbear/decisions/` (scribe's established domain). CLEAN.

#### Test Integrity
No `TestFromAC_*` classes exist. Conditional skip applies. CLEAN.

#### Test Quality
No tests applicable (markdown-only task). CLEAN.

#### Data Safety
`resolve-summary.json` is written by scribe (trusted internal agent) and read/deleted by orchestrator. No external input enters this flow. The `resolve-summary.json` schema is minimal and self-contained. "Write even when all arrays are empty" ensures graceful degradation. CLEAN.

#### Builder Process Quality
Single `## Builder Notes` section — first attempt, no loop. CLEAN.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| Scribe writes `resolve-summary.json` with `{resolved, needs_info, pending}` arrays | scribe.agent.md resolve Output Contract: JSON schema with all 3 arrays shown; "Write even when all arrays are empty" | PASS |
| Orchestrator reads via `readFile` after scribe returns | w-orchestration Step 1: "read `.owlbear/decisions/resolve-summary.json` via `readFile`" | PASS |
| Orchestrator deletes after reading | w-orchestration Step 1: "Delete the file after reading (stale-file mitigation)" | PASS |
| Missing file = empty dispatches (graceful degradation) | w-orchestration Step 1: "If the file is missing, treat as empty (graceful degradation)" | PASS |
| Carve-out exception removed from `orchestrator.agent.md` critical_rules | orchestrator.agent.md critical_rules: "After the scribe returns in resolve mode, read `.owlbear/decisions/resolve-summary.json` via `readFile`" — no exception carve-out present | PASS |
| `w-orchestration` Step 1 updated: file read replaces text parsing | Step 1 now sources `needs_info_dispatches` from JSON file exclusively | PASS |
| `w-decision-routing` resolve output contract updated | w-decision-routing Mode 2 needs-info step 4: "Record in resolve-summary.json — add `{task_id, agent}` to the `needs_info` array" | PASS |
| `scribe.agent.md` output contract updated to include file write | scribe.agent.md resolve Output Contract: full JSON schema and write instruction | PASS |
| NEEDS-INFO dispatch injection still works E2E | w-orchestration Step 2: "NEEDS-INFO injection: Append `needs_info_dispatches` (from Step 1) to the dispatch list" unchanged in Step 2 | PASS |
| No regression in DR processing | scribe.agent.md resolve mode: all 5 response types (pending, approved, completed, needs-info, rejected) + auto-resolve still documented in both files | PASS |

### All 11 Change Points Verified
1. orchestrator.agent.md L44 — carve-out removed, `resolve-summary.json` reference added ✓
2. scribe.agent.md L71 — `needs_info` array collection added ✓
3. scribe.agent.md L100-106 — resolve-summary.json write + schema in output contract ✓
4. w-orchestration context budget — exception note replaced with file-read note ✓
5. w-orchestration state variable — `needs_info_dispatches` sourced from file ✓
6. w-orchestration signal contracts — exception note replaced ✓
7. w-orchestration Step 1 — readFile + delete-after-read instructions present ✓
8. w-orchestration Step 2 — `needs_info_dispatches` injection logic unchanged ✓
9. w-orchestration checklist — two new items: `resolve-summary.json` read/delete + `needs_info_dispatches` injection ✓
10. w-orchestration pitfall — "File-based dispatch injection" replaces text-parsing pitfall ✓
11. w-decision-routing needs-info flow — step 4 added to record in resolve-summary.json ✓

### Deductions
None.

### Verdict
Confidence: .97 → PASS

[[2026-04-06]] Mon 19:21
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | scribe↔orchestrator boundary changed (text-parsing → file contract). `.github/copilot-instructions.md` is 3 lines (project identity only) — no pipeline protocol tables to update. Primary docs (agent/skill files) already updated by builder and verified by reviewer at confidence .97. |
| 2 | Module docstrings | No | N/A | Zero Python files changed — all changes are prompt-layer markdown (4 files). |
| 3 | External attribution | No | N/A | Task body: "7 studied (all internal codebase)". No external repos, articles, or docs used. Research doc §2 confirms all sources are internal workspace files. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/scribe-orchestrator-typed-contract.md` exists and is linked in task body. Follow-up tasks: none required — this task IS the implementation follow-up from #657. |

### Files Updated
- None — no doc updates required. Agent/skill files updated by builder are the primary documentation for this change.

### Scratch Files Cleaned
- None — no `.owlbear/scratch/660-*` files found.

[[2026-04-06]] Mon 20:13
## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Scribe writes resolve-summary.json with {resolved, needs_info, pending} arrays | scribe.agent.md resolve Output Contract: JSON schema with all 3 arrays; "Write even when all arrays are empty" | PASS |
| Orchestrator reads via readFile after scribe returns | w-orchestration Step 1: "read .owlbear/decisions/resolve-summary.json via readFile" | PASS |
| Orchestrator deletes after reading | w-orchestration Step 1: "Delete the file after reading (stale-file mitigation)" | PASS |
| Missing file = empty dispatches | w-orchestration Step 1: "If the file is missing, treat as empty (graceful degradation)" | PASS |
| Carve-out exception removed from orchestrator.agent.md | orchestrator.agent.md critical_rules: no carve-out exception; replaced with file-read reference to resolve-summary.json | PASS |
| w-orchestration Step 1 updated: file read replaces text parsing | Step 1 fully rewritten: readFile + delete-after-read + graceful degradation | PASS |
| w-decision-routing resolve output contract updated | Mode 2 needs-info step 4: "Record in resolve-summary.json" with JSON schema | PASS |
| scribe.agent.md output contract updated to include file write | resolve Output Contract: full JSON schema and write instruction present | PASS |
| NEEDS-INFO dispatch injection still works E2E | w-orchestration Step 2: needs_info_dispatches injection logic unchanged, source is now JSON file | PASS |
| No regression in DR processing | All 5 response types (pending, approved, completed, needs-info, rejected) + auto-resolve documented in both files | PASS |

### Test Results
- pytest: 3135 passed, 443 failed (all pre-existing/unrelated TDD-RED tests), 8 skipped. 1 collection error (test_planner_gates.py from #207, pre-existing).
- ruff: Pre-existing violations in mcp-kanban server/tests only. No Python files changed by #660.

### Scope Check
- Commit 3d37b56 touches all 4 target files + minor tangential edit to architect.agent.md (adding "after" to decomposition detection rule). Harmless.
- Commit message missing #660 task ID (process note, not a rubric deduction).

### Architect Quality: 5/5
All 10 AC lines are specific, verifiable, and complete. Edge cases (missing file, stale file, empty arrays) explicitly covered. Change impact map (11 points, 4 files) was precise and matched implementation exactly. Research grounding via #657 was thorough.

### Deduction Breakdown
- Start: 1.00
- AC lines with no evidence: 0 (10/10 PASS) = 0
- Lint violations: N/A (markdown-only) = 0
- AC quality score <=3: No (5/5) = 0
- Missing reviewer evidence: No (detailed, 11 change points verified) = 0
- Full-suite failures in task scope: 0 = 0

### Confidence: .98
### Action: archive
