---
id: 1291
title: 'P2-07: Move agent-audit and arch-audit prompts to .owlbear/prompts/'
status: archived
priority: medium
created: 2026-05-02T16:01:17.128331+00:00
updated: 2026-05-03T19:13:35.519854+00:00
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

- [ ] agent-audit.prompt.md moved from share/prompts/ to .owlbear/prompts/
- [ ] arch-audit.prompt.md moved from share/prompts/ to .owlbear/prompts/
- [ ] No dangling references to old locations in any instruction or skill file
- [ ] Tests from #1285 pass for prompt-location assertions

## Scope

- IN: share/prompts/agent-audit.prompt.md, share/prompts/arch-audit.prompt.md → .owlbear/prompts/
- OUT: doc-audit.prompt.md (handled by #1290 as part of atomic chain)
[[2026-05-03]]
## Research

Trivial file-move task — implementation already complete.

### Verification Evidence
- `agent-audit.prompt.md` exists at `.owlbear/prompts/`, absent from `share/prompts/` ✓
- `arch-audit.prompt.md` exists at `.owlbear/prompts/`, absent from `share/prompts/` ✓
- Zero dangling refs in `share/instructions/`, `share/skills/`, `share/agents/` ✓
- `test_audit_prompts_relocated_to_owlbear_prompts` passes ✓
- Remaining old-path mentions are in `.owlbear/briefs/` and `.owlbear/sources/` (historical docs, not active references)

### Recommendation
Builder should do a verification-only pass: confirm tests, commit message if uncommitted, close ACs. No code changes needed. Confidence: 0.95.

No follow-up tasks needed — all ACs satisfied by prior work.
[[2026-05-03]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Moves two related audit prompts — same operation, same domain |
| Interface clarity | PASS | AC specifies exact source/dest paths |
| Dependency correctness | PASS | #1285 archived (done) — test suite exists |
| Module layering | N/A | File moves only, no code imports |
| TDD compliance | PASS | `test_audit_prompts_relocated_to_owlbear_prompts` exists in test_path_neutrality_1285.py |
| KISS/YAGNI | PASS | Minimal mechanical move, already completed |
| Premise challenge | PASS | Valid per parent brief — audit prompts are dev-only, belong in .owlbear/ |
| Pattern consistency | PASS | Follows same relocation pattern as sibling tasks (#1290) |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | docs/prompts domain only |

### Codebase Verification
- `agent-audit.prompt.md` present at `.owlbear/prompts/`, absent from `share/prompts/` ✓
- `arch-audit.prompt.md` present at `.owlbear/prompts/`, absent from `share/prompts/` ✓
- Zero dangling references in `share/instructions/`, `share/skills/`, `share/agents/` ✓
- Test file: tests/test_path_neutrality_1285.py line 214 — asserts both existence and absence

### Challenge Results
- Challenger: SKIPPED — all AC lines td:0
- Architect response: N/A

### Test Depth
- AC1: agent-audit moved (td:0) — verified by existing test
- AC2: arch-audit moved (td:0) — verified by existing test
- AC3: No dangling refs (td:0) — mechanical verification
- AC4: Tests pass (td:0) — references existing test, no new test needed
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Added `docs` pass-through tag; advanced to todo. Builder does verification-only pass (confirm tests green, commit if uncommitted, close ACs).
[[2026-05-03]]
## Test-Writer Notes
- Non-implementation task (tagged `docs`) — no tests applicable.
- All AC lines are (td:0); existing coverage in `tests/test_path_neutrality_1285.py` covers AC4 (prompt-location assertions).
- Passing through to builder.
[[2026-05-03]]
## Builder Notes
- Implementation: no files changed (verification-only pass-through)
- Tests: 1 passed (`tests/test_path_neutrality_1285.py::test_audit_prompts_relocated_to_owlbear_prompts`)
- Coverage: N/A (test-only integration assertion; no application module instrumentation)
- ruff: clean
- Evidence summary: required prompt-location assertion is green and task body confirms both prompt moves plus no active dangling references in instructions/skills/agents.
- Fixes applied: none
[[2026-05-03]]
## Review Evidence

### Source Control Scope
- Reconstructed this as a verification-only pass-through task. Builder notes report no task-local file changes, so review evidence is based on current tracked repo state plus the proving test.
- Git-tracked deliverables confirmed: `.owlbear/prompts/agent-audit.prompt.md`, `.owlbear/prompts/arch-audit.prompt.md`, and `tests/test_path_neutrality_1285.py`.
- Prior `## Review Evidence` sections in this task: 0.

### Test Results
- Quality-runner: 1 passed, 0 failed, 0 skipped.
- Scoped selector: `tests/test_path_neutrality_1285.py::TestFromAC_PathNeutrality::test_audit_prompts_relocated_to_owlbear_prompts`.

### Lint
- Quality-runner: clean on `tests/test_path_neutrality_1285.py`.

### Coverage
- N/A. This task is a prompt-relocation verification pass and does not change an application module.

### Pass 1 - Critical
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `agent-audit.prompt.md` moved from `share/prompts/` to `.owlbear/prompts/` | `test_audit_prompts_relocated_to_owlbear_prompts` | Yes. The test asserts the file exists under `.owlbear/prompts/` and does not exist under `share/prompts/`. Workspace file search also returned only the `.owlbear/prompts/` copy. | COVERED |
| `arch-audit.prompt.md` moved from `share/prompts/` to `.owlbear/prompts/` | `test_audit_prompts_relocated_to_owlbear_prompts` | Yes. The test asserts the file exists under `.owlbear/prompts/` and does not exist under `share/prompts/`. Workspace file search also returned only the `.owlbear/prompts/` copy. | COVERED |
| No dangling references to old locations in any instruction or skill file | N/A | Yes. Exact-path grep for `share/prompts/agent-audit.prompt.md` and `share/prompts/arch-audit.prompt.md` returned no matches under `share/instructions/`, `share/skills/`, `share/agents/`, `.owlbear/instructions/`, `.owlbear/skills/`, and `.owlbear/agents/`. | COVERED |
| Tests from #1285 pass for prompt-location assertions | `test_audit_prompts_relocated_to_owlbear_prompts` | Yes. Quality-runner reported 1 passed and 0 failed for the scoped relocation selector. | COVERED |

#### Security Review
- No issues. This task verifies prompt file placement only and does not introduce runtime input handling, secrets, or new dependencies.

#### Test Integrity
- No task-local builder edits were reported or required. The current proving test is tracked in git and uses discriminating assertions on both positive and negative path existence checks. No weakened or removed assertions were found in this task.

#### Test Quality
- STRONG. The relocation test would fail if either prompt were missing from `.owlbear/prompts/` or still present in `share/prompts/`.

#### Data Safety
- No issues. No data mutation or shared-state code path changed in this task.

#### Implementation-Aware Test Gap Analysis
- No significant gap within AC scope. The task is fully proven by current file presence, old-path absence, and the passing relocation assertion.

#### Necessity Check
- Not applicable. No dependency or tool addition.

#### Builder Process Quality
- CLEAN. One `## Builder Notes` section and no prior `## Review Evidence` sections.

### Informational
- Search hits for the old prompt paths still exist in `.owlbear/briefs/` and `.owlbear/sources/`. Those are historical documents, not instruction or skill files, so they do not violate this task's AC.

### Deductions
- Minor confidence deduction because there is no task-local builder commit hash. Changed-surface ownership was reconstructed from task notes, tracked-file checks, and live repo state.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `agent-audit.prompt.md` moved from `share/prompts/` to `.owlbear/prompts/` | `.owlbear/prompts/agent-audit.prompt.md` exists in tracked repo state, and the scoped relocation selector passed. | `test_audit_prompts_relocated_to_owlbear_prompts` | PASS |
| `arch-audit.prompt.md` moved from `share/prompts/` to `.owlbear/prompts/` | `.owlbear/prompts/arch-audit.prompt.md` exists in tracked repo state, and the scoped relocation selector passed. | `test_audit_prompts_relocated_to_owlbear_prompts` | PASS |
| No dangling references to old locations in any instruction or skill file | Exact-path grep returned no matches in the instruction, skill, and agent file surfaces listed above. | N/A | PASS |
| Tests from #1285 pass for prompt-location assertions | Quality-runner reported 1 passed, 0 failed for `test_audit_prompts_relocated_to_owlbear_prompts`. | `test_audit_prompts_relocated_to_owlbear_prompts` | PASS |

### Verdict
- PASS. Confidence: 0.96.

### Action
- Advance to docs.
[[2026-05-03]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No IN-scope README, setup guide, research doc, or sources file references `share/prompts/agent-audit.prompt.md` or `share/prompts/arch-audit.prompt.md`. Grep across `*.md` IN-scope set: 0 matches for old paths. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | No external patterns used. |
| 4 | Research doc | No | N/A | No research doc produced for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/project-overview.excalidraw` has `describes: share/**, .owlbear/**` — matches both old (`share/prompts/`) and new (`.owlbear/prompts/`) paths. Footer updated: `Last verified: 2026-05-03 (6af3f3db)`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request. |
| 7 | Deletion detection | Yes | N/A | Old paths `share/prompts/agent-audit.prompt.md` and `share/prompts/arch-audit.prompt.md` deleted. Grep across all IN-scope docs (READMEs, setup guides, share/README.md, `.owlbear/research/*.md`, `.owlbear/sources/*.md`): 0 matches for old paths. No orphaned IN-scope docs detected. References in `.owlbear/research/gate4-tw-missing-tag-exemptions.md` are to an even older `.github/prompts/` location (pre-existing historical reference, not introduced by this task). |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.owlbear/prompts/agent-audit.prompt.md` | OUT (prompt file) | N/A |
| `.owlbear/prompts/arch-audit.prompt.md` | OUT (prompt file) | N/A |
| `share/prompts/agent-audit.prompt.md` (deleted) | OUT (prompt file) | N/A |
| `share/prompts/arch-audit.prompt.md` (deleted) | OUT (prompt file) | N/A |
| `tests/test_path_neutrality_1285.py` | OUT (test file) | N/A |
| `share/diagrams/project-overview.excalidraw` | IN (diagram) | Footer updated |

### Files Updated
- `share/diagrams/project-overview.excalidraw` — footer bumped to `2026-05-03 (6af3f3db)`. Commit: 16919813.

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1291-*` files found)
[[2026-05-03]]
## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| agent-audit.prompt.md moved to .owlbear/prompts/ | file_search: exists at `.owlbear/prompts/`, absent from `share/prompts/` | PASS |\n| arch-audit.prompt.md moved to .owlbear/prompts/ | file_search: exists at `.owlbear/prompts/`, absent from `share/prompts/` | PASS |\n| No dangling references in instruction/skill files | grep `share/prompts/agent-audit\|arch-audit` across `share/**`: 0 matches | PASS |\n| Tests from #1285 pass for prompt-location assertions | `test_audit_prompts_relocated_to_owlbear_prompts`: 1 passed | PASS |\n\n### Test Results\n- pytest (full): 3841 passed, 128 failed, 4 skipped — all failures pre-existing, unrelated to prompt relocation (engine, config, decisions, Shell domains)\n- vitest (full): 937 passed, 13 failed — Shell EventSourceProvider test setup issue, unrelated\n- ruff: 1 T201 (print statement) — not in task scope\n\n### Upstream Commits\n- Deliverables committed in `8e442bdc` (task #1285 builder) — this task was a verification-only pass-through dependent on #1285\n\n### Architect Quality: 5/5\nAC lines specify exact source/dest paths, a dangling-reference gate, and a test-pass assertion. Clear, unambiguous, verifiable.\n\n### Deduction Breakdown\n- None. All 4 AC lines verified with specific evidence. Reviewer evidence detailed (0.96, PASS). No in-scope lint or test failures.\n\n### Confidence: 1.00\n### Action: archive