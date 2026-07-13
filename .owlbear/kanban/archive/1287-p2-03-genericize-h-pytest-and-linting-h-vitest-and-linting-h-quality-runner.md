---
id: 1287
title: 'P2-03: Genericize h-pytest-and-linting, h-vitest-and-linting, h-quality-runner'
status: archived
priority: medium
created: 2026-05-02T16:01:17.076781+00:00
updated: 2026-05-03T19:44:57.497166+00:00
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

- [ ] h-pytest-and-linting: ~7 serve/ path references replaced with concrete illustrative paths + prose note pattern
- [ ] h-vitest-and-linting: ~6 serve/cockpit/web/ references replaced with "your frontend package root" + framed example
- [ ] h-quality-runner: path examples genericized; routing prose added directing agents to read project copilot-instructions.md
- [ ] All replacements use the Brief's notation convention (prose-first with framed examples, never template syntax)
- [ ] Tests from #1285 pass for these three skills

## Scope

- IN: h-pytest-and-linting/SKILL.md, h-vitest-and-linting/SKILL.md, h-quality-runner/SKILL.md
- OUT: Skills covered by #1286, workflow skills (#1288)
[[2026-05-03]]
## Research

**Key finding:** Commit 8e442bdc (#1285 builder) already did a mechanical serve/ → workspace/ replacement across all 3 skills. All #1285 tests pass. However, the implementation violates the Brief's notation convention (AC4): no conceptual nouns ("your frontend package root"), no framed examples (> Example (OwlBear-dev): ...), no prose notes on shell commands (# adjust paths). `workspace/` is also semantically wrong — doesn't exist in any project.

**Recommendation:** Option B — refine to match Brief convention. ~30 lines across 3 files, no test changes needed. Confidence .80.

**Trade-off matrix:** See .owlbear/research/1287-genericize-skills.md

**No follow-up tasks needed** — this task itself IS the implementation task once it reaches the builder. The AC gap (notation convention) should be noted as architect guidance when this advances.
[[2026-05-03]]

## Architecture Review

**Verdict:** APPROVE → todo
**Test-writer: SKIP** (all AC lines td:0 — existing test floor from #1285, no new tests)

### AC Assessment

| AC | Assessment | Test Depth | Action |
|----|-----------|-----------|--------|
| AC1: h-pytest-and-linting paths genericized | Verifiable — end-state described, Brief notation convention defines format | td:0 | None |
| AC2: h-vitest-and-linting paths genericized | Verifiable — conceptual noun + framed example pattern clear | td:0 | None |
| AC3: h-quality-runner genericized + routing prose | Already satisfied by #1285 commit; verify preservation | td:0 | None |
| AC4: Brief notation convention compliance | Verifiable by inspection against Brief §Notation Convention | td:0 | None |
| AC5: Tests from #1285 pass | Regression gate via `test_path_neutrality_1285.py` | td:0 | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Three related skill files, one notation convention |
| Interface clarity | PASS | Brief §Notation Convention defines exact format |
| Dependency correctness | PASS | #1285 archived (done); mechanical replacement in place |
| Module layering | N/A | Doc-only changes |
| TDD compliance | PASS | Existing test gate from #1285 |
| KISS/YAGNI | PASS | ~30 lines of prose refinement across 3 files |
| Premise challenge | PASS | `workspace/` is semantically wrong — agents on consumer projects will fail |
| Pattern consistency | PASS | Matches Brief D5/D8 decisions |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | All in share/skills/ docs domain |

### Builder Guidance

Current state: `workspace/` placeholder paths exist (from #1285 mechanical replacement). Replace with Brief notation:
1. Inline conceptual nouns ("your source packages", "your frontend package root")
2. Framed examples where concrete paths aid comprehension: `> Example (OwlBear-dev): serve/cockpit/web/`
3. Shell command prose notes: `# adjust paths for your project layout`

The `Example (` prefix is explicitly excluded from the `\bserve/` test regex — framed examples containing real `serve/` paths will pass tests.

Challenge: SKIPPED (all td:0)
[[2026-05-03]]
Architecture review complete. All criteria pass. AC verifiable against Brief §Notation Convention. Existing test floor from #1285 serves as regression gate. All td:0 — test-writer SKIP. Tagged `docs` for pass-through. Builder guidance appended re: workspace/ → Brief notation pattern.
[[2026-05-03]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Existing regression gate: `tests/test_path_neutrality_1285.py` covers the path-neutrality contract for all three target skills.
- Passing through to builder.
[[2026-05-03]]
## Builder Notes
- Implementation: Updated path notation and examples in `share/skills/h-pytest-and-linting/SKILL.md`, `share/skills/h-vitest-and-linting/SKILL.md`, and `share/skills/h-quality-runner/SKILL.md`.
- Fixes applied:
  - Replaced placeholder `workspace/` roots with prose-first conceptual guidance (for example, "your source packages" and "your frontend package root").
  - Added framed examples in the required notation style (`Example (OwlBear-dev): ...`) where concrete context is helpful.
  - Kept `h-quality-runner` routing authority guidance to `copilot-instructions.md` intact while genericizing path examples.
- Tests: 9 passed (`tests/test_path_neutrality_1285.py` via quality-runner).
- Coverage: Not applicable for this doc-only gate run (quality-runner reported no instrumented module data).
- ruff: clean (quality-runner scoped lint run).
- Commit: `d47024b9` (`docs: genericize skill path notation (#1287, builder)`).
- Evidence summary: Baseline regression gate was green pre-edit, and remained green post-edit after notation-convention refactor; no test files modified.

### Reflection
- Problem faced: Prior mechanical replacement used a non-portable `workspace/` placeholder that did not match real consumer layouts.
- Workaround applied: Switched to prose-first path guidance plus framed examples to keep commands portable without losing clarity.
- Pattern discovered: `Example (OwlBear-dev): ...` framing preserves concrete onboarding value while remaining path-neutral for shared-layer docs.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner scoped pass on `tests/test_path_neutrality_1285.py`: 9 passed, 0 failed, 0 skipped.
- Commands executed by quality-runner:
  - `uv run pytest tests/test_path_neutrality_1285.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short`
  - `uv run ruff check tests/test_path_neutrality_1285.py`

### Lint
- ruff: clean for `tests/test_path_neutrality_1285.py`.

### Coverage
- Not a gating metric for this td:0 doc-only review. Quality-runner reported no instrumented production modules.

### Changed Files
- `share/skills/h-pytest-and-linting/SKILL.md`
- `share/skills/h-vitest-and-linting/SKILL.md`
- `share/skills/h-quality-runner/SKILL.md`
- Verified from builder commit `d47024b9` via `git diff --name-only d47024b9~1 d47024b9`.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- Skipped. Architecture Review marked all AC lines `td:0`; no `TestFromAC_*` classes exist for this task. Existing regression gate from #1285 was still executed for AC5.

#### Security Review
- No issues. Markdown-only skill edits; no runtime boundary or dependency changes.

#### Test Integrity
- PASS. Builder commit touched only the three skill files above; no test files were modified.

#### Data Safety
- No issues. Documentation-only change.

#### Implementation Compliance
- FAIL. The live skill text still contains placeholder paths in executable shell/tool-invocation examples instead of the brief-required concrete illustrative paths plus adjacent prose notes.
- Brief notation requirement: `.owlbear/briefs/draft-neutral-shared/brief.md:29-44` requires conceptual nouns in prose, framed examples where helpful, and for shell/tool invocations concrete illustrative paths with an adjacent prose note; it also forbids placeholder syntax in executable commands.
- `share/skills/h-pytest-and-linting/SKILL.md:27,63,66,69,107,123` still use `path/to/source-packages/` in shell commands.
- `share/skills/h-vitest-and-linting/SKILL.md:17,51,57,73,79` still use `path/to/frontend-package-root` in shell commands.
- `share/skills/h-quality-runner/SKILL.md:20,28` still model tool-invocation examples with placeholder roots rather than the same prose-first pattern.
- These are executable/example invocation lines, so the remaining placeholders are an implementation miss, not just a stylistic preference.

#### Necessity Check
- N/A. No new dependencies or integrations.

#### Builder Process Quality
- CLEAN. One builder cycle. No prior `## Review Evidence` section exists in `.owlbear/kanban/tasks/1287-p2-03-genericize-h-pytest-and-linting-h-vitest-and-linting-h-quality-runner.md`, so this is the first review-cycle failure.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| h-pytest-and-linting: ~7 serve/ path references replaced with concrete illustrative paths + prose note pattern | `share/skills/h-pytest-and-linting/SKILL.md:27,63,66,69,107,123` still use placeholder command paths without the required adjacent prose note. Brief rule at `.owlbear/briefs/draft-neutral-shared/brief.md:38-44`. | Inspection | FAIL |
| h-vitest-and-linting: ~6 serve/cockpit/web/ references replaced with "your frontend package root" + framed example | Prose and framed example exist at `share/skills/h-vitest-and-linting/SKILL.md:9-10`, but executable command examples at `:17,51,57,73,79` still use `path/to/frontend-package-root` placeholders instead of brief-compliant concrete illustrative paths. | Inspection | FAIL |
| h-quality-runner: path examples genericized; routing prose added directing agents to read project copilot-instructions.md | Generic routing prose is present at `share/skills/h-quality-runner/SKILL.md:39-42` and points agents to `.github/copilot-instructions.md`. | Inspection | PASS |
| All replacements use the Brief's notation convention (prose-first with framed examples, never template syntax) | Remaining placeholder executable examples in the three edited skills conflict with `.owlbear/briefs/draft-neutral-shared/brief.md:29-44`. | Inspection | FAIL |
| Tests from #1285 pass for these three skills | quality-runner report: 9 passed, 0 failed, 0 skipped on `tests/test_path_neutrality_1285.py`; ruff clean. | `tests/test_path_neutrality_1285.py` | PASS |

### Deductions
- -0.07: h-pytest-and-linting still uses placeholder command paths on multiple executable lines.
- -0.05: h-vitest-and-linting still uses placeholder command paths on multiple executable lines.
- -0.05: AC4 remains unmet because executable examples are not yet in the brief's notation pattern.

### Verdict
- FAIL -> in-progress
- Confidence: 0.83

### Required Follow-up
- Replace placeholder executable paths in `share/skills/h-pytest-and-linting/SKILL.md` shell blocks with concrete illustrative paths plus adjacent `# adjust paths for your project layout` notes, following the brief notation convention.
- Replace placeholder executable paths in `share/skills/h-vitest-and-linting/SKILL.md` shell blocks the same way.
- Align the tool-invocation examples in `share/skills/h-quality-runner/SKILL.md` with the same prose-first/framed-example convention; the routing prose at line 42 is already satisfied.
- Re-run `tests/test_path_neutrality_1285.py` after the doc fixes.
[[2026-05-03]]
## Builder Notes
- Implementation: Updated only `share/skills/h-pytest-and-linting/SKILL.md`, `share/skills/h-vitest-and-linting/SKILL.md`, and `share/skills/h-quality-runner/SKILL.md`.
- Fixes applied:
  - Replaced remaining placeholder executable paths (`path/to/...`) with concrete illustrative paths (`src/`, `frontend/`) in command/tool-invocation examples.
  - Added adjacent prose notes on executable examples (`# adjust paths for your project layout`) to match Brief notation convention.
  - Preserved the project-routing guidance to `.github/copilot-instructions.md` in `h-quality-runner`.
- Tests: 9 passed, 0 failed, 0 skipped (`tests/test_path_neutrality_1285.py`) via quality-runner scoped run.
- Coverage: N/A for this structural test gate (quality-runner reported no instrumented module data).
- ruff: clean (scoped lint on `tests/test_path_neutrality_1285.py`).
- Commit: `00a2296c` (`docs: finalize path-neutral command examples (#1287, builder)`).
- Evidence summary: Reviewer-flagged placeholder command paths were removed in all three target skills; regression gate remained green after edits.

### Reflection
- Problem faced: Prior edit pass left placeholder path syntax in executable examples, violating the brief notation contract.
- Workaround applied: Converted those examples to concrete illustrative commands and attached explicit adjustment notes for portability.
- Pattern discovered: Prose-first framing plus concrete command examples avoids ambiguous placeholders while keeping shared skills reusable across projects.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner scoped pass on tests/test_path_neutrality_1285.py: 9 passed, 0 failed, 0 skipped.
- This task is td:0 and doc-only, so code-reader was skipped. I still ran the scoped regression gate because AC5 explicitly requires the existing path-neutrality suite to pass.

### Lint
- ruff clean for tests/test_path_neutrality_1285.py.

### Coverage
- Not a gating metric for this doc-only review. No production modules were instrumented.

### Changed Files
- share/skills/h-pytest-and-linting/SKILL.md
- share/skills/h-vitest-and-linting/SKILL.md
- share/skills/h-quality-runner/SKILL.md
- Verified from both builder commits d47024b9 and 00a2296c. No test files changed.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- Skipped per td:0. No task-local TestFromAC classes exist for task 1287.
- Existing regression evidence was still checked for AC5 using tests/test_path_neutrality_1285.py.

#### Security Review
- No issues. Markdown-only edits; no runtime, dependency, or system-boundary changes.

#### Test Integrity
- PASS. Both builder commits touched only the three skill files above.

#### Test Quality
- ADEQUATE for task scope. The reused path-neutrality suite proves the relevant serve-path exclusions and routing-reference contract, while AC1 through AC4 are inspection-based documentation requirements.

#### Data Safety
- No issues. Documentation-only change.

#### Implementation Compliance
- PASS. The prior placeholder command paths in the targeted replacement surface are gone.
- h-pytest-and-linting now uses prose-first guidance at share/skills/h-pytest-and-linting/SKILL.md:23-24 and concrete illustrative command examples with adjustment notes at lines 27, 63, 66, 69, and 107.
- h-vitest-and-linting now uses your frontend package root guidance at share/skills/h-vitest-and-linting/SKILL.md:9, framed OwlBear-dev examples at lines 10 and 114, and concrete command examples with adjustment notes at lines 17, 51, 57, 73, and 79.
- h-quality-runner preserves routing authority to .github/copilot-instructions.md at share/skills/h-quality-runner/SKILL.md:44 and uses concrete prompt-path examples plus adjustment notes at lines 20-21 and 29-30, with framed frontend-root examples at lines 42 and 64.
- Informational only: share/skills/h-pytest-and-linting/SKILL.md:99 still contains a placeholder path inside a known-bad coverage-flag example. That line is not an executable command and is outside the serve-path replacement surface defined by this task, so it is not counted against AC4.

#### Necessity Check
- N/A. No new dependencies, integrations, or external capabilities.

#### Builder Process Quality
- CLEAN. One prior review section exists in the task file; this retry directly fixes the previously documented placeholder-command issue without changing scope.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| h-pytest-and-linting: about 7 serve path references replaced with concrete illustrative paths plus prose note pattern | share/skills/h-pytest-and-linting/SKILL.md:23-27, 63-69, 107 | Inspection plus tests/test_path_neutrality_1285.py:77 | PASS |
| h-vitest-and-linting: about 6 serve/cockpit/web references replaced with your frontend package root plus framed example | share/skills/h-vitest-and-linting/SKILL.md:9-10, 17, 51, 57, 73, 79, 113-114 | Inspection plus tests/test_path_neutrality_1285.py:77 | PASS |
| h-quality-runner: path examples genericized and routing prose added directing agents to read project copilot-instructions.md | share/skills/h-quality-runner/SKILL.md:20-21, 29-30, 42, 44, 64 | tests/test_path_neutrality_1285.py:109 | PASS |
| All replacements use the Brief notation convention | .owlbear/briefs/draft-neutral-shared/brief.md:29-44 cross-checked against the current replacement lines above; remaining non-executable negative example at h-pytest line 99 is out of scope for this AC | Inspection | PASS |
| Tests from 1285 pass for these three skills | quality-runner report: 9 passed, 0 failed, 0 skipped; ruff clean. Test definitions at tests/test_path_neutrality_1285.py:72, 77, 109 | tests/test_path_neutrality_1285.py | PASS |

### Deductions
- -0.03: h-pytest-and-linting still carries one non-executable placeholder path in a negative example, which adds minor wording ambiguity even though it is outside the task-owned replacement surface.
- -0.02: td:0 review relies primarily on document inspection rather than task-local executable proofs for AC1 through AC4.

### Verdict
- PASS. Advance to docs.
- Confidence: 0.95

### Reflection
- Problem faced: the second-cycle review boundary hinged on whether a leftover placeholder inside a negative example counted as an executable-command violation.
- Workaround applied: separated executable replacement lines from non-executable warning examples and anchored the verdict to the exact brief wording plus task scope.
- Pattern discovered: for shared-doc genericization tasks, the real gate is the replacement surface named in the AC, not every illustrative string in the file.
- Quality gap: td:0 doc tasks still benefit from one explicit regression run when an AC names an existing suite, even if the default td:0 workflow would otherwise be lint-only.
[[2026-05-03]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed files are all `share/skills/*/SKILL.md` (OUT-of-scope agent-executable). No IN-scope descriptive docs reference these skill files by name. |
| 2 | Module docstrings | No | N/A | No Python modules modified. |
| 3 | External attribution | No | N/A | No external patterns used; pure internal notation-convention refactor. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1287-genericize-skills.md` exists and is linked from task body under ## Research. |
| 5 | Diagram maintenance (describes match) | Yes | N/A (already current) | `share/diagrams/project-overview.excalidraw` describes `share/**` which matches the three changed skill files. Footer already updated to `2026-05-03 (599768ca)` by #1290 doc-writer (commit `363bb595`). No further update needed. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| share/skills/h-pytest-and-linting/SKILL.md | OUT | No action (agent-executable SKILL.md) |
| share/skills/h-vitest-and-linting/SKILL.md | OUT | No action (agent-executable SKILL.md) |
| share/skills/h-quality-runner/SKILL.md | OUT | No action (agent-executable SKILL.md) |

### Files Updated
- None (diagram footer was already current from #1290 doc-writer)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found (`.owlbear/scratch/1287-*` — no matches)
[[2026-05-03]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| h-pytest-and-linting: ~7 serve/ paths replaced | SKILL.md:23-27 prose-first + framed example + adjustment notes; no serve/ in commands | PASS |
| h-vitest-and-linting: ~6 paths replaced with "your frontend package root" | SKILL.md:9-10 + cd frontend/ with adjustment notes at :17,:51,:57,:73,:79 | PASS |
| h-quality-runner: genericized + routing prose | SKILL.md:20-21, 29-30 concrete examples + routing to copilot-instructions.md at :44 | PASS |
| Brief notation convention (prose-first, framed examples, no template syntax) | Spot-checked all 3 files: > Example (OwlBear-dev): framing, # adjust paths notes, no {{}} or path/to/ placeholders in commands | PASS |
| Tests from #1285 pass | tests/test_path_neutrality_1285.py: 9 passed, 0 failed | PASS |

### Test Results
- pytest full suite: 3841 passed, 128 failed (all in serve/kanban/ and serve/mcp-knowledge/ pre-existing), 4 skipped. 0 failures in task scope.
- vitest full suite: 937 passed, 13 failed (Shell_1227/Shell_966 traffic-light tests pre-existing). 0 in task scope.
- ruff: 1 pre-existing T201 in copilot_auth.py. Not in task scope.
- Task regression gate: tests/test_path_neutrality_1285.py 9/9 green.

### Commit Integrity
- d47024b9 docs: genericize skill path notation (#1287, builder)
- 00a2296c docs: finalize path-neutral command examples (#1287, builder)
- Both commits touch only the 3 target skill files. No test files modified.

### Architect Quality: 4/5
AC lines are specific and verifiable. Minor approximation in AC1/AC2 (uses ~7 and ~6 counts rather than exact), but transformation is clearly defined and the notation convention reference anchors the format requirement.

### Deduction Breakdown
- AC lines without evidence: 0 (all PASS)
- Lint in scope: 0
- AC quality <=3: no (score 4)
- Missing reviewer evidence: no (detailed, 2-cycle review with line-level inspection)
- Full-suite failures in scope: 0

### Confidence: 0.98
### Action: archive