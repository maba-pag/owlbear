---
id: 678
title: Update share/agents and share/skills READMEs to reflect current counts
status: archived
priority: medium
created: 2026-04-08T18:34:28.3160163+02:00
updated: 2026-04-09T00:23:06.8671575+02:00
started: 2026-04-09T00:23:06.8671575+02:00
completed: 2026-04-09T00:23:06.8671575+02:00
tags:
    - scope:docs
    - ' type:docs'
    - ' source:analysis'
class: standard
---

## Context

Analysis synthesis identified that both READMEs in `share/` are stale:

- `share/agents/README.md`: Lists 15 agents, actual count is 23. Missing: voice panel agents (6: critic-voice, architect-voice, data-voice, enduser-voice, security-voice, pragmatist-voice), ideator, scribe. Tier assignment for voice agents and ideator is undefined.
- `share/skills/README.md`: Lists 29 skills, actual count is 32. Missing skills need identification by scanning the `share/skills/` directory.

## Acceptance Criteria

- [ ] AC1: `share/agents/README.md` lists all 23 agents with correct tier assignments
- [ ] AC2: Voice panel agents assigned to a tier (likely T3 or a new "Voice" tier)
- [ ] AC3: Ideator assigned to a tier (likely T1)
- [ ] AC4: Deprecated dispatcher agent marked clearly
- [ ] AC5: `share/skills/README.md` lists all 32 skills with correct category counts
- [ ] AC6: Deprecated/archived skills marked clearly (h-kanban-md, w-dispatch-planning, w-project-scoping)

[[2026-04-08]] Wed 21:12
## Architecture Review

### Context Corrections
- README header says "15 agents" but tier table lists only 13. Actual `.agent.md` count: 23.
- Task context incorrectly lists scribe as missing — it's already at T3. Correctly missing from README: architect-voice, critic-voice, data-voice, enduser-voice, pragmatist-voice, security-voice, dispatcher, fix-attempt, ideator, quality-runner (10 agents).
- Skills: actual breakdown is h-: 14, w-: 15, r-: 3 = 32 (README says h-: 12, w-: 14, r-: 3 = 29).

### Binding Tier Assignments (architect decisions)
These tier assignments are binding — the builder must use them:
- **ideator** → T1 — Orchestrator (user-invocable top-level agent managing ideation workflow)
- **dispatcher** → T2 — Pipeline (DEPRECATED — mark clearly with deprecation note referencing #619/#621)
- **Voice agents** (architect-voice, critic-voice, data-voice, enduser-voice, pragmatist-voice, security-voice) → T4 — Tools (voice-panel subagents invoked by ideator)
- **fix-attempt** → T4 — Tools (builder repair subagent)
- **quality-runner** → T4 — Tools (mechanical utility subagent)

### Additional Requirement (binding)
**AC7 (appended): `share/skills/h-agent-structure/SKILL.md` tier table must be updated to match the README tier assignments.** This file is the canonical tier reference (both READMEs say "See h-agent-structure for tier definitions"). Updating READMEs without updating the source of truth would create a structural contradiction.

### Deprecated items presentation
- Deprecated agents: keep in tier table, append "(DEPRECATED)" annotation
- Deprecated/archived skills: keep in category counts, append "(DEPRECATED)" or "(ARCHIVED)" annotation

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: update taxonomy documentation across 3 files |
| Interface clarity | PASS | Inputs/outputs are markdown files with well-defined structure |
| Dependency correctness | PASS | No dependencies |
| Module layering | N/A | Documentation only |
| TDD compliance | PASS | type:docs — pass-through tag present |
| KISS/YAGNI | PASS | Minimal scope, no over-engineering |
| Premise challenge | PASS | READMEs and tier table are genuinely stale — verified by directory scan |
| Pattern consistency | PASS | Follows existing README table format |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | docs domain only |

### Challenge Results
- Challenger: block (confidence 0.40)
- Architect response: partially accepted — h-agent-structure sync added as AC7, tier assignments resolved as binding decisions, deprecated presentation specified. Hardcoded counts rebutted (point-in-time verification, builder will scan directories).

### Verdict: APPROVE
### Action Taken: Advanced to todo with binding tier assignments and appended AC7 for h-agent-structure sync.

[[2026-04-08]] Wed 21:46
## Test-Writer Notes
- Non-implementation task (tagged type:docs) — no tests applicable.
- AC1–AC7 all reference markdown files only: `share/agents/README.md`, `share/skills/README.md`, `share/skills/h-agent-structure/SKILL.md`.
- Step 2a scan: zero Python implementation intent — no keywords (`implement`, `function`, `class`, `src/`, `.py`, `import`, `endpoint`) present in AC.
- Passing through to builder.

[[2026-04-08]] Wed 22:21
## Builder Notes

### Files Changed
- `share/agents/README.md` — count 15→23, tier table expanded
- `share/skills/README.md` — count 29→32, prefix counts corrected (w-:14→15, h-:12→14), deprecated skills noted
- `share/skills/h-agent-structure/SKILL.md` — tier table expanded to match README

### Changes Applied
- AC1/AC2/AC3/AC4: agents README now lists all 23 agents. ideator→T1, dispatcher→T2 (DEPRECATED — #619/#621), voice agents (architect-voice, critic-voice, data-voice, enduser-voice, pragmatist-voice, security-voice)→T4, fix-attempt→T4, quality-runner→T4
- AC5: skills README updated to 32 total, h-:14, w-:15, r-:3
- AC6: deprecated/archived skills annotated inline (h-kanban-md DEPRECATED, w-dispatch-planning ARCHIVED, w-project-scoping DEPRECATED)
- AC7: h-agent-structure SKILL.md tier table synced — ideator added to T1, dispatcher (DEPRECATED) added to T2, fix-attempt/quality-runner/voice agents added to T4

### Verification
- Directory scan confirmed 23 .agent.md files and 32 skill directories (h-:14, w-:15, r-:3)
- All binding tier assignments from architect review applied verbatim
- No tests applicable (type:docs pass-through)

[[2026-04-08]] Wed 23:07
## Review Evidence

### Files Changed
- `share/agents/README.md` — count 15→23, tier table expanded
- `share/skills/README.md` — count 29→32, category counts corrected, deprecated/archived skills annotated
- `share/skills/h-agent-structure/SKILL.md` — tier table expanded to include all binding assignments

### Tests
type:docs pass-through — no tests applicable. Test-writer confirmed in prior stage.

### Lint
Not applicable — markdown files only.

### Coverage
Not applicable.

### AC Compliance

| AC | Evidence | Status |
|----|----------|--------|
| AC1: README lists all 23 agents with correct tier assignments | Directory: 23 `.agent.md` files. Tier table: T1(2)+T2(8)+T3(3)+T4(10) = 23. All file-based agents present. | PASS |
| AC2: Voice agents assigned to a tier | README T4: architect-voice, critic-voice, data-voice, enduser-voice, pragmatist-voice, security-voice — all 6 present. Tier = T4 per architect binding. | PASS |
| AC3: Ideator assigned to T1 | README T1: `orchestrator, ideator` — matches architect binding decision | PASS |
| AC4: Deprecated dispatcher marked clearly | README T2: `dispatcher (DEPRECATED — see #619/#621)` | PASS |
| AC5: Skills README lists 32 skills with correct counts | Directory scan: h-:14, w-:15, r-:3 = 32. README: h-:14, w-:15, r-:3 = 32. | PASS |
| AC6: Deprecated/archived skills marked | `h-kanban-md (DEPRECATED), w-dispatch-planning (ARCHIVED), w-project-scoping (DEPRECATED)` present in README. | PASS |
| AC7: h-agent-structure SKILL.md tier table synced | All binding assignments applied. **Observation (documentation detail only):** SKILL.md has `dispatcher (DEPRECATED)` without `— see #619/#621`; README has full reference. Architect's binding required this reference. No structural inconsistency created. **Pre-existing:** SKILL.md T4 retains `Explore` (VS Code built-in agent) not in README (README is file inventory; SKILL.md is tier taxonomy). Pre-dates this task; outside scope of binding decisions. | PARTIAL — minor detail only |

### Deductions
- AC7 SKILL.md missing `— see #619/#621` in dispatcher annotation vs README: -0.02 (documentation detail, not structural failure)
- Explore discrepancy: pre-existing, outside binding scope: -0.00

### Verdict
**PASS — confidence 0.96 (≥ 0.90 threshold)**

All AC lines verified by direct file evidence. Directory scan confirms 23 agents and 32 skills matching README counts. All architect binding tier assignments applied verbatim. Two minor observations noted, neither rising to FAIL level.

[[2026-04-08]] Wed 23:13
## Docs Gate

### Checklist

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | copilot-instructions.md contains no agent tier table or counts — only "agent workflows" reference (line 5). No update needed. |
| 2 | Module docstrings | No | N/A | Zero Python files modified. Confirmed by builder notes and file list. |
| 3 | External attribution | No | N/A | Pure internal taxonomy update — no external patterns, repos, or articles used. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | No research doc produced for this task. Source was prior analysis synthesis. |
| 6 | No docs impact | No | N/A | Docs impact exists — items above evaluated. |
| 7 | Upstream Review Evidence | Yes | PASS | `## Review Evidence` section present with full AC compliance table, confidence 0.96. |

### File Updated (doc-writer)

- `share/skills/h-agent-structure/SKILL.md` — fixed `dispatcher (DEPRECATED)` to `dispatcher (DEPRECATED — see #619/#621)` to match architect's binding annotation and align with README. This was the AC7 PARTIAL issue noted by reviewer (-0.02). Commit: `f6c234a`.

### Observed Files (builder, verified accurate)

- `share/agents/README.md` — 23 agents, tier table correct, all binding assignments applied, dispatcher annotation complete with `— see #619/#621`.
- `share/skills/README.md` — 32 skills, prefix counts correct (h-:14, w-:15, r-:3), deprecated/archived annotations present.

### Scratch Files

No `.owlbear/scratch/678-*` files found.

### Verdict

DONE — checklist passed. One doc-writer fix applied (SKILL.md dispatcher annotation). All AC lines verified by direct file inspection.

[[2026-04-09]] Thu 00:23
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: agents README lists all 23 agents with correct tiers | `share/agents/README.md` count=23, T1(2)+T2(8)+T3(3)+T4(10)=23. `file_search` returned 23 `.agent.md` files. | PASS |
| AC2: Voice agents assigned to a tier | README T4 row: architect-voice, critic-voice, data-voice, enduser-voice, pragmatist-voice, security-voice — all 6 present | PASS |
| AC3: Ideator assigned to T1 | README T1: `orchestrator, ideator` | PASS |
| AC4: Deprecated dispatcher marked clearly | README T2: `dispatcher (DEPRECATED — see #619/#621)` | PASS |
| AC5: Skills README lists 32 with correct counts | `share/skills/README.md` h-:14, w-:15, r-:3 = 32. Directory listing confirmed 14+15+3 = 32. | PASS |
| AC6: Deprecated/archived skills marked | `h-kanban-md (DEPRECATED), w-dispatch-planning (ARCHIVED), w-project-scoping (DEPRECATED)` present | PASS |
| AC7: h-agent-structure SKILL.md tier table synced | All tiers match README. `dispatcher (DEPRECATED — see #619/#621)` present. Committed by doc-writer in `f6c234a`. | PASS |

### Test Results
- pytest: 3671 passed, 388 failed, 18 skipped (none in task scope — docs-only, no Python changes)
- ruff: 5 violations (all in serve/mcp-kanban/, none in deliverables — pre-existing)

### Architect Quality: 4/5
AC was specific with 7 verifiable lines. Tier assignments were explicit binding decisions. Minor gap: original AC didn't include h-agent-structure sync — architect caught and appended AC7. Good upstream work.

### Deduction Breakdown
- 7 AC lines, all with specific evidence: -0.00
- Builder failed to commit README deliverables: -0.02 (content correct, commit gap only)
- Test failures outside task scope: -0.00
- Lint violations outside task scope: -0.00
- AC quality 4/5: -0.00
- Reviewer evidence section: present, detailed, PASS at 0.96 — trusted: -0.00

### Confidence: 0.98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| f6c234a | docs | share/skills/h-agent-structure/SKILL.md | #678 |
| 3c72ccc | docs | share/agents/README.md, share/skills/README.md | #678 |
