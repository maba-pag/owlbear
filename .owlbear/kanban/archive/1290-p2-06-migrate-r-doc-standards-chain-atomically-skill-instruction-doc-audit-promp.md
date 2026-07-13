---
id: 1290
title: 'P2-06: Migrate r-doc-standards chain atomically (skill + instruction + doc-audit
  prompt)'
status: archived
priority: medium
created: 2026-05-02T16:01:17.114235+00:00
updated: 2026-05-03T19:43:45.866461+00:00
tags:
- phase-2
- scope:docs
- shared-layer
- docs
parent: 1280
depends_on:
- 1285
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1280 and `.owlbear/briefs/draft-neutral-shared/brief.md`

## Acceptance Criteria

- [ ] r-doc-standards/SKILL.md: OwlBear-specific scope enumeration (doc-type table, serve/ paths, audience table) extracted
- [ ] If insufficient generic substance remains, entire skill moved to .owlbear/skills/; if generic rules remain, skill stays in share/ with reduced content
- [ ] doc-standards.instructions.md: applyTo and description updated to match new skill location
- [ ] doc-audit.prompt.md moved from share/prompts/ to .owlbear/prompts/
- [ ] No dangling cross-references between the three chain members (skill ↔ instruction ↔ prompt)
- [ ] Migration is atomic — all three files updated in the same commit
- [ ] Tests from #1285 pass for r-doc-standards chain assertions

## Scope

- IN: r-doc-standards/SKILL.md, doc-standards.instructions.md, doc-audit.prompt.md — all three atomically
- OUT: Other prompts (#1291), architecture extraction (#1289)
[[2026-05-03]]
## Research
- Research doc: .owlbear/research/1290-doc-standards-chain-migration.md
- Sources: 5 studied (skill file, instruction stub, prompt, tests, brief), all high-relevance
- Recommendation: Keep skill in share/ with reduced generic content (XREF + AUD principles + DIM framework); extract doc-type table, PLC-3/4, AUD-1 table to `.owlbear/instructions/doc-types.instructions.md`; update doc-audit prompt to load both (confidence: 0.82)
- Follow-up tasks: none needed — this task IS the implementation target, advancing to backlog for architect
- Decision requests: none (T1 — autonomous file reorganization)

## Key Findings
- doc-audit.prompt.md ALREADY moved to .owlbear/prompts/ — AC4 pre-satisfied
- All 3 audit prompts already relocated — AC6 pre-satisfied
- Chain cross-references already intact — AC5 pre-satisfied, tests pass
- Remaining work: AC1 (extract OwlBear-specific content), AC2 (decision: keep in share/), AC3 (update applyTo/description)
- Test constraint forces skill to stay at share/skills/ (tests assert file path existence)
- ~80 lines of generic content remains (sufficient substance)

## Challenge Results
- Challenge: FALLBACK — trivial T1 file reorganization, no arch/security implications
- Confidence: 0.82
[[2026-05-03]]

## Architecture Review

### Refined Acceptance Criteria (supersedes original)

- [ ] Create `.owlbear/instructions/doc-types.instructions.md` containing extracted OwlBear-specific content: § 1 (STR-1–STR-13 doc types), PLC-3 table, PLC-4, and AUD-1 audience table. Use `applyTo: "README.md,README-consumer.md,SECURITY.md,serve/*/README.md,share/README.md,setup/*.md"` (td:0)
- [ ] Reduce `share/skills/r-doc-standards/SKILL.md` to generic framework: citation format table, § 3 XREF-1–5, AUD-2–4 (genericized — replace "OwlBear" with project-neutral phrasing), § 5 DIM-1–8, and the companion wiring reference line containing `share/instructions/doc-standards.instructions.md` (td:0)
- [ ] Update `share/instructions/doc-standards.instructions.md` description to: "Documentation quality rules — cross-references, audience fitness, audit dimensions" (reflecting reduced generic scope); applyTo unchanged (td:0)
- [ ] Update `.owlbear/prompts/doc-audit.prompt.md` to load BOTH the shared skill `r-doc-standards` AND `.owlbear/instructions/doc-types.instructions.md` for project-specific doc-type definitions (td:0)
- [ ] No dangling cross-references: skill still contains `share/instructions/doc-standards.instructions.md`; instruction stub still contains `.owlbear/prompts/doc-audit.prompt.md`; all existing #1285 tests pass (td:0)
- [ ] Single atomic commit (td:0)

### Builder Guidance

- AC4 from original ("doc-audit.prompt.md moved from share/prompts/ to .owlbear/prompts/") is PRE-SATISFIED — prompt already at correct location.
- The skill MUST remain at `share/skills/r-doc-standards/SKILL.md` — tests assert this path.
- DIM section references to STR-* rule IDs should use generic phrasing like "project-defined doc-type rules" since those rules move to the local instruction.
- See `.owlbear/research/1290-doc-standards-chain-migration.md` for content classification table.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One chain, atomic migration |
| Interface clarity | PASS | Extraction destination + retained content now explicit |
| Dependency correctness | PASS | #1285 tests exist at tests/test_path_neutrality_1285.py |
| Module layering | PASS | No code imports; doc chain only |
| TDD compliance | PASS | Tests pre-exist from #1285; regression gate in AC |
| KISS/YAGNI | PASS | Minimal extraction to local instruction; no new abstractions |
| Premise challenge | PASS | Shared-layer neutrality is the project goal; this task serves it |
| Pattern consistency | PASS | `.owlbear/instructions/` follows existing `.owlbear/prompts/` pattern |
| Security surface | PASS | No system boundaries; doc files only |
| Single domain | PASS | Documentation domain only |

### Challenge Results
- Challenger: SKIPPED — all AC lines td:0 (mechanical file reorganization)

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
[[2026-05-03]]
Architecture review complete. Refined AC to specify extraction destination (`.owlbear/instructions/doc-types.instructions.md`), precise retained content, and doc-audit prompt update. All td:0 — mechanical file reorganization verified by existing #1285 tests. Added `docs` pass-through tag. Test-writer: SKIP.
[[2026-05-03]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.
[[2026-05-03]]
## Builder Notes
- Implementation:
  - `.owlbear/instructions/doc-types.instructions.md` (new): extracted OwlBear-specific `STR-*`, `PLC-3`/`PLC-4`, and `AUD-1` definitions.
  - `share/skills/r-doc-standards/SKILL.md`: reduced to shared/generic documentation quality framework (`XREF-*`, `AUD-2..4`, `DIM-*`, shared placement rules).
  - `share/instructions/doc-standards.instructions.md`: description updated to reduced generic scope; now also instructs loading `.owlbear/instructions/doc-types.instructions.md`.
  - `.owlbear/prompts/doc-audit.prompt.md`: updated to require loading both standards and to map rule-family authority between shared skill and local instruction.
- Tests:
  - quality-runner baseline (pre-edit): `tests/test_path_neutrality_1285.py` -> 9 passed, 0 failed.
  - quality-runner verification (post-edit): `tests/test_path_neutrality_1285.py`, `tests/test_cross_references_1283.py` -> 19 passed, 0 failed.
- Coverage: N/A for scoped documentation tests (no importable module coverage data emitted by quality-runner).
- Ruff: clean in scoped verification.
- Atomic commit: `1fca9847` with exactly the 4 task files staged.
- Evidence summary: cross-reference chain remains intact (`r-doc-standards` -> `doc-standards.instructions.md` -> `.owlbear/prompts/doc-audit.prompt.md`), and relocation assertions remain green.

## Post-task Reflection
- `apply_patch` could not safely handle the full-file skill rewrite; switched to delete+recreate flow and verified on-disk state before proceeding.
- Explicitly documenting rule-source ownership in the prompt prevented stale references after extracting project-specific sections.
- Scoped dual-test verification (`1285` neutrality + `1283` cross-reference) gave fast, sufficient regression confidence for this docs-chain task.
[[2026-05-03]]
## Review Evidence
### Test Results
- Quality-runner scoped regression on [tests/test_path_neutrality_1285.py](tests/test_path_neutrality_1285.py): 9 passed, 0 failed, 0 skipped.

### Lint
- Quality-runner scoped ruff on [tests/test_path_neutrality_1285.py](tests/test_path_neutrality_1285.py): clean.

### Coverage
- N/A for this docs-chain task. The scoped regression is a repository integration test file, not module coverage data.

### Pass 1 — Critical
#### Test-Writer AC Coverage
- Not applicable. All refined AC lines are td:0 and the task has no TestFromAC classes.

#### Security Review
- No issues found. The change surface is markdown-only documentation/prompt content with no executable boundary, secret handling, or input-processing path.

#### Test Integrity
- Not applicable. No TestFromAC immutability surface in this task.

#### Test Quality
- The scoped regression strongly proves chain existence and relocation, but it does not assert the prompt's internal rule-source mapping. That gap allowed a false green on the main defect below.

#### Data Safety
- No issues found.

#### Necessity Check
- Not applicable. No dependency or integration added.

#### Builder Process Quality
- CLEAN. One builder cycle, one recorded commit, no retry loop.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| Create local doc-types instruction with extracted OwlBear-specific STR, PLC-3/4, and AUD-1 content | [.owlbear/instructions/doc-types.instructions.md](.owlbear/instructions/doc-types.instructions.md#L2), [.owlbear/instructions/doc-types.instructions.md](.owlbear/instructions/doc-types.instructions.md#L3), [.owlbear/instructions/doc-types.instructions.md](.owlbear/instructions/doc-types.instructions.md#L22), [.owlbear/instructions/doc-types.instructions.md](.owlbear/instructions/doc-types.instructions.md#L58), [.owlbear/instructions/doc-types.instructions.md](.owlbear/instructions/doc-types.instructions.md#L69), [.owlbear/instructions/doc-types.instructions.md](.owlbear/instructions/doc-types.instructions.md#L73) | PASS |
| Reduce shared r-doc-standards skill to generic framework and keep companion wiring | [share/skills/r-doc-standards/SKILL.md](share/skills/r-doc-standards/SKILL.md#L9), [share/skills/r-doc-standards/SKILL.md](share/skills/r-doc-standards/SKILL.md#L11), [share/skills/r-doc-standards/SKILL.md](share/skills/r-doc-standards/SKILL.md#L37), [share/skills/r-doc-standards/SKILL.md](share/skills/r-doc-standards/SKILL.md#L59) | PASS |
| Update shared instruction stub description; keep applyTo unchanged | [share/instructions/doc-standards.instructions.md](share/instructions/doc-standards.instructions.md#L2), [share/instructions/doc-standards.instructions.md](share/instructions/doc-standards.instructions.md#L3), [share/instructions/doc-standards.instructions.md](share/instructions/doc-standards.instructions.md#L7), [share/instructions/doc-standards.instructions.md](share/instructions/doc-standards.instructions.md#L8) | PASS |
| Update doc-audit prompt to load both standards and use the local instruction for project-specific rule families | [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md#L15), [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md#L64), [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md#L65), [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md#L67) show the intended dual-source model, but stale single-source wording remains at [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md#L17), [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md#L175), [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md#L206), and [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md#L249), which still hardcode r-doc-standards as the sole rule source. That contradicts the extraction and would misattribute STR/PLC/AUD-1 findings. | FAIL |
| No dangling chain references and #1285 chain assertions remain green | [share/skills/r-doc-standards/SKILL.md](share/skills/r-doc-standards/SKILL.md#L11), [share/instructions/doc-standards.instructions.md](share/instructions/doc-standards.instructions.md#L7), [share/instructions/doc-standards.instructions.md](share/instructions/doc-standards.instructions.md#L8), [tests/test_path_neutrality_1285.py](tests/test_path_neutrality_1285.py#L11), [tests/test_path_neutrality_1285.py](tests/test_path_neutrality_1285.py#L144), [tests/test_path_neutrality_1285.py](tests/test_path_neutrality_1285.py#L155), [tests/test_path_neutrality_1285.py](tests/test_path_neutrality_1285.py#L171), [tests/test_path_neutrality_1285.py](tests/test_path_neutrality_1285.py#L181), [tests/test_path_neutrality_1285.py](tests/test_path_neutrality_1285.py#L214), plus quality-runner result: 9 passed, 0 failed | PASS |
| Single atomic commit | Builder commit 1fca9847; git show lists exactly these task files and no extra paths: .owlbear/instructions/doc-types.instructions.md, .owlbear/prompts/doc-audit.prompt.md, share/instructions/doc-standards.instructions.md, share/skills/r-doc-standards/SKILL.md | PASS |

### Deductions
- 0.14: AC for doc-audit prompt is incomplete because four live prompt lines still treat r-doc-standards as the only authoritative source.
- 0.05: Process text in the prompt still says to load only r-doc-standards during Phase 1, which conflicts with the new two-source model.
- 0.04: The scoped regression does not cover prompt authority-mapping/template text, so the defect escaped green tests.

### Verdict
- FAIL. Confidence: 0.77.
- Routing: in-progress. This is primarily an implementation miss in [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md), with a related proof gap.

### Required Follow-up
- Update [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md) so all behavioral-contract, process, and finding-card/template text refers to the loaded standards or to the correct authority file for each rule family; remove the stale r-doc-standards-only wording at lines 17, 175, 206, and 249.
- Add a narrow regression that asserts the prompt's rule-source mapping/template text, not just chain existence and prompt location.

### Post-task Reflection
- Docs-chain tasks can false-green when the regression suite checks only chain links and target paths; prompt/template internals may still point at the old authority source.
- After extracting rule families into a local instruction, the highest-value grep is for stale single-source phrases such as Rule: r-doc-standards or Load r-doc-standards.
- Contradictory prompt wording is a real implementation defect on docs tasks when the AC moves rule ownership across artifacts.
[[2026-05-03]]
## Builder Notes
- Implementation: updated `.owlbear/prompts/doc-audit.prompt.md` only.
- Fixes applied:
  - Replaced stale single-source wording with dual-source wording in Behavioral contract (rule-ID citation source now "loaded standards").
  - Updated Phase 1 Step 2 to load both `r-doc-standards` and `.owlbear/instructions/doc-types.instructions.md`.
  - Updated finding-card template `Rule:` field to use `{standards-source}` placeholder.
  - Updated task-emission template `Rule:` field to use `{standards-source}` placeholder.
- Tests: quality-runner scoped run on `tests/test_path_neutrality_1285.py` -> 9 passed, 0 failed.
- Lint: quality-runner scoped lint on `.owlbear/prompts/doc-audit.prompt.md` + `tests/test_path_neutrality_1285.py` -> clean.
- Coverage: N/A for this docs-only scoped gate.
- Evidence summary: reviewer-flagged stale single-source references removed; dual-source authority mapping is now consistent in process and templates.
- Commit: `fb1e79b2` (`docs: fix doc-audit dual-source rule mapping (#1290, builder)`).

## Post-task Reflection
- Template-level wording can silently retain old authority assumptions after rule extraction; targeted placeholder normalization prevented recurrence.
- Scoped quality-runner verification stayed fast and sufficient for docs-chain regressions while avoiding unrelated suite noise.
- Keeping the diff to a single prompt file reduced retry risk and preserved atomic task intent.
[[2026-05-03]]
## Review Evidence
### Changed File Surface
- Current retry commit `fb1e79b2` changes [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md) only.
- The task-wide chain still consists of [.owlbear/instructions/doc-types.instructions.md](.owlbear/instructions/doc-types.instructions.md), [share/skills/r-doc-standards/SKILL.md](share/skills/r-doc-standards/SKILL.md), [share/instructions/doc-standards.instructions.md](share/instructions/doc-standards.instructions.md), and [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md).

### Test Results
- Quality-Runner scoped gate on [tests/test_path_neutrality_1285.py](tests/test_path_neutrality_1285.py): 9 passed, 0 failed, 0 skipped.

### Lint
- Quality-Runner scoped ruff on [tests/test_path_neutrality_1285.py](tests/test_path_neutrality_1285.py): clean.

### Coverage
- N/A for this td:0 docs-chain task.

### Pass 1 — Critical
#### Test-Writer AC Coverage
- Not applicable. All refined AC lines are td:0 and there are no `TestFromAC_*` classes in scope.

#### Security Review
- No issues found. The change surface is markdown/prompt content only, with no executable boundary, input-processing path, or secret-handling path.

#### Test Integrity
- Not applicable. No `TestFromAC_*` immutability surface in this task.

#### Test Quality
- [tests/test_path_neutrality_1285.py](tests/test_path_neutrality_1285.py#L144) through [tests/test_path_neutrality_1285.py](tests/test_path_neutrality_1285.py#L214) still prove chain integrity and relocation, not prompt-internal authority wording. For this td:0 task that is acceptable because the content AC is satisfied by direct file inspection; residual risk noted below.

#### Data Safety
- No issues found.

#### Necessity Check
- Not applicable. No dependency, tool, or integration added.

#### Builder Process Quality
- CLEAN. One initial builder pass and one focused retry correcting the reviewer-flagged prompt wording. No repeated same-approach loop.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| Create local doc-types instruction with extracted OwlBear-specific STR, PLC-3/4, and AUD-1 content | [.owlbear/instructions/doc-types.instructions.md](.owlbear/instructions/doc-types.instructions.md#L6), [.owlbear/instructions/doc-types.instructions.md](.owlbear/instructions/doc-types.instructions.md#L22), [.owlbear/instructions/doc-types.instructions.md](.owlbear/instructions/doc-types.instructions.md#L58), [.owlbear/instructions/doc-types.instructions.md](.owlbear/instructions/doc-types.instructions.md#L69), [.owlbear/instructions/doc-types.instructions.md](.owlbear/instructions/doc-types.instructions.md#L73) | PASS |
| Reduce shared `r-doc-standards` skill to the generic framework and keep companion wiring | [share/skills/r-doc-standards/SKILL.md](share/skills/r-doc-standards/SKILL.md#L11), [share/skills/r-doc-standards/SKILL.md](share/skills/r-doc-standards/SKILL.md#L37), [share/skills/r-doc-standards/SKILL.md](share/skills/r-doc-standards/SKILL.md#L49), [share/skills/r-doc-standards/SKILL.md](share/skills/r-doc-standards/SKILL.md#L59), [share/skills/r-doc-standards/SKILL.md](share/skills/r-doc-standards/SKILL.md#L73) | PASS |
| Update shared instruction stub description and keep `applyTo` unchanged | [share/instructions/doc-standards.instructions.md](share/instructions/doc-standards.instructions.md#L2), [share/instructions/doc-standards.instructions.md](share/instructions/doc-standards.instructions.md#L3), [share/instructions/doc-standards.instructions.md](share/instructions/doc-standards.instructions.md#L6), [share/instructions/doc-standards.instructions.md](share/instructions/doc-standards.instructions.md#L7), [share/instructions/doc-standards.instructions.md](share/instructions/doc-standards.instructions.md#L8) | PASS |
| Update doc-audit prompt to load both standards and use correct authority/template wording for rule families | [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md#L15), [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md#L62), [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md#L64), [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md#L65), [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md#L175), [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md#L206), [.owlbear/prompts/doc-audit.prompt.md](.owlbear/prompts/doc-audit.prompt.md#L249); negative grep on `.owlbear/prompts/doc-audit.prompt.md` found no remaining stale single-source patterns (`Rule: r-doc-standards` / lone `Load r-doc-standards.`) | PASS |
| No dangling cross-references and existing #1285 chain assertions remain green | [share/skills/r-doc-standards/SKILL.md](share/skills/r-doc-standards/SKILL.md#L11), [share/instructions/doc-standards.instructions.md](share/instructions/doc-standards.instructions.md#L7), [share/instructions/doc-standards.instructions.md](share/instructions/doc-standards.instructions.md#L8), [tests/test_path_neutrality_1285.py](tests/test_path_neutrality_1285.py#L144), [tests/test_path_neutrality_1285.py](tests/test_path_neutrality_1285.py#L155), [tests/test_path_neutrality_1285.py](tests/test_path_neutrality_1285.py#L171), [tests/test_path_neutrality_1285.py](tests/test_path_neutrality_1285.py#L181), [tests/test_path_neutrality_1285.py](tests/test_path_neutrality_1285.py#L214), plus Quality-Runner result: 9 passed, 0 failed | PASS |
| Single atomic commit | Original migration remains recorded as builder commit `1fca9847`; current retry commit `fb1e79b2` is a prompt-only correction after review. No evidence shows the chain migration itself was split across the original delivery. | PASS |

### Deductions
- 0.03: The task-owned regression still does not pin the prompt's internal authority-mapping text, so closure of that detail rests on direct file inspection rather than executable proof.
- 0.03: Atomicity re-verification is slightly lower confidence because git diff-style path listing was unreliable in this shell session; commit identity, unchanged chain members, and the prior verified review state still line up with the current deliverable.

### Verdict
- PASS. Confidence: 0.94.
- Action: advance to docs.

### Post-task Reflection
- Docs-only tasks can legitimately PASS on td:0 when the content AC is proven by direct inspection and the required regression suite stays green; missing extra tests is a confidence deduction, not an automatic fail.
- The most important retry check here was negative: confirm the previously stale single-source phrases are actually gone, not just that new dual-source text was added elsewhere.
- Atomicity checks are easier to defend when the builder records the original migration commit and the retry commit separately, as happened here.
[[2026-05-03]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | All changed files are agent-executable (OUT-scope); no IN-scope prose docs reference skill/instruction/prompt chain files |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | Reorganization of internal docs; no external patterns or sources used |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1290-doc-standards-chain-migration.md` exists and is linked from task body |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/project-overview.excalidraw` describes `share/**` and `.owlbear/**`; footer updated to `Last verified: 2026-05-03 (599768ca)` and committed at `363bb595` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted; all changed files were created or modified |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.owlbear/instructions/doc-types.instructions.md` | OUT | N/A (agent-executable instructions file) |
| `share/skills/r-doc-standards/SKILL.md` | OUT | N/A (agent-executable SKILL.md) |
| `share/instructions/doc-standards.instructions.md` | OUT | N/A (agent-executable instructions stub) |
| `.owlbear/prompts/doc-audit.prompt.md` | OUT | N/A (agent-executable prompt file) |
| `share/diagrams/project-overview.excalidraw` | IN | Updated (diagram footer — describes `share/**`, `.owlbear/**`) |

### Files Updated
- `share/diagrams/project-overview.excalidraw` — footer updated to `Last verified: 2026-05-03 (599768ca)`, commit `363bb595`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1290-*` files existed)
[[2026-05-03]]
## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| Create .owlbear/instructions/doc-types.instructions.md with STR, PLC-3/4, AUD-1 | File exists: frontmatter applyTo matches, STR-1 through STR-13, PLC-3/4, AUD-1 present | PASS |\n| Reduce r-doc-standards to generic framework with companion wiring | Skill L9-11: generic description + companion wiring line; L37+: XREF rules; L59+: DIM rules; no STR/PLC/AUD-1 definitions remain | PASS |\n| Update doc-standards.instructions.md description, applyTo unchanged | Description: \"Documentation quality rules...\" (generic); applyTo unchanged; also loads local doc-types instruction | PASS |\n| Update doc-audit prompt for dual-source loading and correct authority mapping | L15: loads both; L62-65: authority split; L175: Phase 1 Step 2 loads both; L206/L249: {standards-source} placeholders; negative grep confirms no stale single-source phrases | PASS |\n| No dangling cross-references; #1285 tests pass | Chain wiring intact (skill->instruction->prompt); quality-runner 9/9 passed on test_path_neutrality_1285.py | PASS |\n| Single atomic commit | 1fca9847: exactly 4 task files; fb1e79b2: prompt-only retry fix; 363bb595: docs gate diagram footer | PASS |\n\n### Test Results\n- pytest (full): hangs at test_cockpit_events_1234.py (known SSE deadlock, pre-existing, unrelated)\n- pytest (scoped): 19 passed, 0 failed\n- ruff: 1 T201 in serve/knowledge copilot_auth.py (unrelated background debt)\n- vitest (scoped): 65 passed\n\n### Architect Quality: 4/5\nSpecific td:0 AC with explicit paths and content targets. Builder guidance helpful (pre-satisfied ACs noted, test constraint). Minor gap: refined AC did not flag stale-wording patterns in prompt, leaving the reviewer to catch it.\n\n### Deduction Breakdown\n- Full suite incomplete due to known background SSE hang: -.01\n- Regression test does not pin prompt internal authority text: -.02\n\n### Confidence: 0.97\n### Action: archive