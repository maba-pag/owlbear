---
id: 1028
title: 'P2-04: share-category READMEs sweep'
status: archived
priority: medium
created: 2026-04-19 23:52:56.675044+00:00
updated: 2026-04-20 04:52:11.053219+00:00
tags:
- phase-2
- docs-currency
- docs-sweep
- type:docs
parent: 1016
depends_on:
- 1024
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1016

## Acceptance Criteria

- [ ] `share/agents/README.md` accurately describes all 23 agents using a tier table with correct counts per tier and unambiguous names (fix current "curator" ambiguity → use test-curator, memory-curator)
- [ ] `share/skills/README.md` describes all 31 skills categorized by prefix (r- 4 rules, w- 13 workflows, h- 14 handbooks); note deprecated h-kanban-md separately
- [ ] `share/instructions/README.md` accurately describes all 6 instruction files; framing distinguishes the 4 stub-style files (which point to skills) from the 2 substantive instruction documents (agent-common, owlbear-system)
- [ ] `share/prompts/README.md` (new file) describes the prompts category per STR-9: purpose, naming convention, invocation pattern (user-invocable one-shot commands), and current count/grouping
- [ ] READMEs describe categories via convention tables and structural groupings per STR-10 — tier tables with grouped names are acceptable; raw file-by-file enumeration is not
- [ ] All conform to `r-doc-standards` STR-9 (purpose, inventory summary, loading notes) and STR-10 (convention tables over file lists)
- [ ] Doc-index regenerated after changes

## Files

- Modifies/creates: `share/agents/README.md`, `share/skills/README.md`, `share/instructions/README.md`, `share/prompts/README.md`

## Notes

These are category overview docs — they describe what's in each directory and how the categories relate, not the behavioral content of individual agents/skills. Pure documentation — no TDD pairing.

### Builder Guidance

- Parent #1016 brief is unavailable (archived). Scope is self-contained from AC — do not search for the brief.
- **Agents README:** Current tier table sums to 22 (not 23) and uses ambiguous "curator" label. Fix: verify each agent's tier from its `.agent.md` frontmatter `description` field; use full names (test-curator, memory-curator).
- **Instructions README:** Current framing ("stubs — safety nets") applies to 4 of 6 files. `agent-common.instructions.md` and `owlbear-system.instructions.md` are substantive documents, not stubs. Restructure README to distinguish both categories.
- **Prompts README:** Greenfield creation. Follow STR-9 structure. Prompts are user-invocable one-shot commands loaded via VS Code prompt files — different from agent/skill loading.
- **Skills README:** r- prefix count changed from 3 → 4 (r-doc-standards added). Update prefix counts and total.
[[2026-04-20]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Four related README files in one category-docs domain |
| Interface clarity | PASS | AC specifies exact files, structural standards (STR-9/10), and content expectations |
| Dependency correctness | PASS | Dep #1024 not in task store (likely archived/done); task is self-contained from AC |
| Module layering | N/A | Pure documentation, no code modules |
| TDD compliance | PASS | Non-implementation; tagged `type:docs` for pass-through |
| KISS/YAGNI | PASS | Minimal scope — 4 files, convention compliance |
| Premise challenge | PASS | READMEs are genuinely stale (agents: 22 vs 23 in tier table, instructions: 4 of 6 listed, skills: wrong r- count, prompts: missing entirely) |
| Pattern consistency | PASS | Follows r-doc-standards STR-9/STR-10 for share-category READMEs |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | docs-sweep domain only |

### Refinements Applied

1. **Agent count 24 → 23** — verified via file_search (23 .agent.md files)
2. **Skill count ~30 → 31** — 4 r-rules (was 3), 13 w-workflows, 14 h-handbooks
3. **STR-10 alignment** — rewrote AC to specify convention tables/structural groupings, not per-file enumeration
4. **Instructions framing** — AC now distinguishes 4 stubs from 2 substantive docs (agent-common, owlbear-system)
5. **Prompts README** — noted as greenfield creation with STR-9 guidance
6. **Added `type:docs` tag** — required pass-through tag for non-implementation pipeline handling
7. **Builder guidance section** — added specific notes on tier table arithmetic, curator ambiguity, instructions restructuring, and missing parent brief

### Challenge Results

- Challenger: **reconsider** (0.55)
- Key concerns: (C1) tier table arithmetic wrong, (C2) STR-10 tension with agent enumeration, (C3) AC4 named specific file, (C4) 2/6 instructions aren't stubs
- Architect response: **accepted and incorporated** — all 4 concerns addressed in AC refinements and builder guidance. C3 resolved by removing specific file name from AC4. C4 resolved by reframing AC3 to distinguish stubs from substantive docs.

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC (7 corrections), added type:docs tag, added builder guidance section, advanced to todo
[[2026-04-20]]
## Test-Writer Notes
- Non-implementation task (tagged type:docs) — no tests applicable.
- Passing through to builder.
[[2026-04-20]]
## Builder Notes

### Files Changed
- `share/agents/README.md` — fixed T3 tier: "curator" → "test-curator, memory-curator" (4 agents); added Count column to tier table; table now sums to 23 ✓
- `share/skills/README.md` — updated total 30 → 31; r- count 3 → 4 (r-doc-standards); deprecated note updated to name replacement skill
- `share/instructions/README.md` — restructured to distinguish 2 substantive docs (agent-common, owlbear-system) from 4 stubs; all 6 files now listed
- `share/prompts/README.md` — new file created; STR-9 structure (purpose, inventory summary, invocation notes); STR-10 convention table (not file list); 8 prompts in 4 groups

### Doc-Index
- `uv run doc-index` ran successfully (exit 0)

### AC Verification
- [x] agents/README.md: 23 agents, tier table with counts, "curator" ambiguity resolved
- [x] skills/README.md: 31 skills, r-4/w-13/h-14, h-kanban-md deprecated with replacement noted
- [x] instructions/README.md: all 6 files listed, stubs vs substantive framing correct
- [x] prompts/README.md: new file, STR-9/STR-10 compliant, invocation pattern described
- [x] Convention tables used throughout (no raw file-by-file enumeration)
- [x] Doc-index regenerated

### Test Results
Non-implementation task (type:docs) — no tests applicable.
[[2026-04-20]]
## Review Evidence

### Test Results
Non-implementation task (type:docs) — no tests applicable. Quality-Runner not invoked.

### Security
No security surface — pure documentation.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: agents/README.md — 23 agents, tier table with counts, unambiguous names | 2+7+4+10=23 confirmed via file_search (23 results); Count column present; "test-curator, memory-curator" used | COVERED |
| AC2: skills/README.md — 31 skills, r-4/w-13/h-14, deprecated note | 31 SKILL.md files confirmed via file_search; prefix breakdown verified: h-14, w-13, r-4; deprecated row names h-mcp-kanban as replacement (matches h-kanban-md frontmatter) | COVERED |
| AC3: instructions/README.md — 6 files, stubs vs substantive framing | 6 .instructions.md files confirmed; two-category framing present; **VIOLATION**: agents-and-skills.instructions.md row shows `applyTo: share/agents/**,share/skills/**` but actual file has `applyTo: ".owlbear/agents/**,.owlbear/skills/**,share/agents/**,share/skills/**"` — two glob patterns (.owlbear/agents/**, .owlbear/skills/**) omitted | **VIOLATION** |
| AC4: prompts/README.md — new file, STR-9, invocation pattern, count/grouping | File created; invocation pattern section present; naming convention table present; 8 prompts in 4 groups — confirmed via file_search (8 .prompt.md files) | COVERED |
| AC5: Convention tables, no raw file-by-file enumeration | All four READMEs use grouped convention tables | COVERED |
| AC6: r-doc-standards STR-9/STR-10 compliance | Purpose + inventory + guidance structure in all four; STR-10 convention tables throughout | COVERED |
| AC7: Doc-index regenerated | share/prompts/README.md (line 17232) and share/agents/README.md (line 17059) both present in .owlbear/doc-index.md | COVERED |

### Deductions

- **-0.12** AC3 VIOLATION: `share/instructions/README.md` table row for `agents-and-skills.instructions.md` shows truncated `applyTo`. README: `share/agents/**,share/skills/**`. Actual: `.owlbear/agents/**,.owlbear/skills/**,share/agents/**,share/skills/**`. The `.owlbear/` prefix patterns are the only ones that would fire for `.owlbear/`-local workspace copies — omitting them makes the README factually wrong for users relying on it to understand when the stub activates.

### Verdict

Confidence: .88 − .12 (AC3 violation) = **.78 → FAIL**

### Action Required

Builder fix in `share/instructions/README.md`: update the `agents-and-skills.instructions.md` row's `applyTo` column to show the full value:
`.owlbear/agents/**,.owlbear/skills/**,share/agents/**,share/skills/**`
[[2026-04-20]]
## Builder Notes (fix-pass)

### Fix Applied
- `share/instructions/README.md` — corrected `agents-and-skills.instructions.md` row's `applyTo` column from truncated `share/agents/**,share/skills/**` to full value `.owlbear/agents/**,.owlbear/skills/**,share/agents/**,share/skills/**` (matches actual frontmatter).

### Doc-Index
- `uv run doc-index` ran successfully (exit 0).

### AC Verification
- [x] AC3 violation resolved — all 6 instruction files now accurately described with correct applyTo patterns.
- All other AC items remain passing (unchanged files, no regressions).

### Test Results
Non-implementation task (type:docs) — no tests applicable.
[[2026-04-20]]
## Review Evidence

### Test Results
Non-implementation task (type:docs) — Quality-Runner not invoked. No tests applicable.

### Security
No security surface — pure documentation.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: agents/README.md — 23 agents, tier table with counts, unambiguous names | file_search: 23 `.agent.md` files confirmed; tier table sums 2+7+4+10=23; Count column present; T3 row uses "test-curator, memory-curator"; tier assignments spot-checked (builder="GREEN phase"→T2, memory-curator="Memory maintenance"→T3) | PASS |
| AC2: skills/README.md — 31 skills, r-4/w-13/h-14, deprecated note | file_search: 31 total, r-4/w-13/h-14 each confirmed via prefix-scoped searches; deprecated row text "h-kanban-md (DEPRECATED — use h-mcp-kanban instead)" matches actual frontmatter description exactly | PASS |
| AC3: instructions/README.md — 6 files, stubs vs substantive framing | file_search: 6 `.instructions.md` files confirmed; two-category framing present; `agents-and-skills.instructions.md` applyTo column now reads `.owlbear/agents/**,.owlbear/skills/**,share/agents/**,share/skills/**` — exact match with actual frontmatter (fix applied correctly) | PASS |
| AC4: prompts/README.md — new file, STR-9, invocation pattern, count/grouping | File created; invocation pattern section present; naming convention table present; 8 prompts in 4 groups (Orchestration:1, Audits:3, Frontend:3, Curation:1) matches file_search: 8 `.prompt.md` files | PASS |
| AC5: Convention tables, no raw file-by-file enumeration | All four READMEs use grouped convention tables throughout | PASS |
| AC6: r-doc-standards STR-9/STR-10 compliance | Purpose + inventory summary + guidance structure in all four; STR-10 convention tables throughout | PASS |
| AC7: Doc-index regenerated | `share/prompts/README.md` confirmed at line 17235 in `.owlbear/doc-index.md` | PASS |

### Pass 1 Checks
- 5.0 TestFromAC: N/A (no TestFromAC_* classes — type:docs task)
- 5.1 Security: no security surface — CLEAN
- 5.2 Test integrity: N/A
- 5.3 Test quality: N/A
- 5.4 Data safety: N/A
- 5.5 Implementation gaps: N/A
- 5.6 Necessity: N/A
- 5.7 Builder process: 1 build + 1 fix-pass; fix targeted exactly the AC3 violation; second review cycle (not loop-breaker threshold) — CLEAN

### Deductions
None. AC3 violation from first cycle verified as correctly resolved.

### Verdict
Confidence: .97 → PASS
[[2026-04-20]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pure documentation task — no behavior, API, or convention changes; copilot-instructions.md not affected |
| 2 | Module docstrings | No | N/A | No Python files created or modified |
| 3 | External attribution | No | N/A | No external patterns or sources used |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | No research doc produced for this task |

### Files Verified
- `share/agents/README.md` — 23 agents, tier table (2+7+4+10=23), Count column, "test-curator, memory-curator" ✓
- `share/skills/README.md` — 31 skills, r-4/w-13/h-14, deprecated note ✓
- `share/instructions/README.md` — 6 files, stubs-vs-substantive framing, `agents-and-skills.instructions.md` applyTo = `.owlbear/agents/**,.owlbear/skills/**,share/agents/**,share/skills/**` (verified against actual frontmatter) ✓
- `share/prompts/README.md` — new file, STR-9/STR-10 compliant, 8 prompts in 4 groups ✓

### Files Updated
None — deliverables verified as accurate; no secondary docs required updates.

### Scratch Files Cleaned
None — no `.owlbear/scratch/1028-*` files found.
[[2026-04-20]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: agents/README.md — 23 agents, tier table, unambiguous names | Spot-checked: 2+7+4+10=23 ✓; "test-curator, memory-curator" in T3 row | PASS |
| AC2: skills/README.md — 31 skills, r-4/w-13/h-14, deprecated note | Spot-checked: prefix table matches, deprecated row present | PASS |
| AC3: instructions/README.md — 6 files, stubs vs substantive framing | Spot-checked: two-category framing correct; applyTo for agents-and-skills matches actual frontmatter exactly (`.owlbear/agents/**,.owlbear/skills/**,share/agents/**,share/skills/**`) — AC3 fix confirmed | PASS |
| AC4: prompts/README.md — new file, STR-9, invocation, count/grouping | Spot-checked: file exists, STR-9 structure, 8 prompts in 4 groups, naming convention table | PASS |
| AC5: Convention tables, no raw file enumeration | Reviewer verified; spot-check confirms grouped tables in all 4 READMEs | PASS |
| AC6: r-doc-standards STR-9/STR-10 compliance | Reviewer verified; structure consistent across all deliverables | PASS |
| AC7: Doc-index regenerated | Reviewer verified presence in doc-index.md | PASS |

### Test Results
- pytest: 797 passed, 10 failed, 4 skipped, 33 errors — all failures pre-existing (test_pipeline_diagram_1033, mcp-knowledge output schema/search v2/phase-a config); 0 failures in task scope
- ruff: clean

### Architect Quality: 5/5
Specific, complete, mechanically verifiable AC. All 7 items named exact files, counts, and structural standards. Architect proactively corrected agent count (24→23), skill count (~30→31), added type:docs tag, and included builder guidance section addressing curator ambiguity, instructions framing, and missing parent brief. Challenger concerns (4) all incorporated.

### Deduction Breakdown
None. All AC lines verified with specific evidence. Lint clean. No task-scope test failures. Reviewer evidence detailed and present (two cycles, .97 confidence on 2nd pass). AC quality 5/5.

### Confidence: 1.00
### Action: archive