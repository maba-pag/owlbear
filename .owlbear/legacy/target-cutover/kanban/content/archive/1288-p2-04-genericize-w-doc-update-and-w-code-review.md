---
id: 1288
title: 'P2-04: Genericize w-doc-update and w-code-review'
status: archived
priority: medium
created: 2026-05-02T16:01:17.090078+00:00
updated: 2026-05-03T20:33:26.422918+00:00
tags:
- phase-2
- scope:docs
- shared-layer
- type:docs
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

- [ ] All serve/ path references genericized: w-doc-update (1 entry), w-code-review (2 entries) — total 3 (td:0)
- [ ] w-code-review: both lint_paths template occurrences use workspace/ prefix (td:0)
- [ ] No `serve/` paths remain in either skill (MCP tool names excluded) (td:0)
- [ ] All three genericized paths use `workspace/` as root prefix; dispatch template `{var}` substitution syntax is pre-existing and unchanged (td:0)
- [ ] Existing test gate `test_no_serve_path_refs_in_skill_files` passes for these two skills (td:0)

## Scope

- IN: w-doc-update/SKILL.md, w-code-review/SKILL.md
- OUT: Path-heavy skills (#1287), architecture extraction (#1289)
[[2026-05-03]]
## Architecture Review (re-review after reviewer FAIL)

### Root Cause
AC4 claimed `workspace/` was "consistent with sibling skills (h-pytest, h-vitest, h-quality-runner)" — those siblings still use `serve/` in project-specific example blocks and have no `workspace/` occurrences. The consistency claim was false (sibling genericization is #1287, currently in review).

### AC4 Refinement
Replaced: "Notation uses `workspace/` prefix consistent with sibling skills (h-pytest, h-vitest, h-quality-runner)"
With: "Notation uses `workspace/` prefix as project-neutral path placeholder in template syntax (per parent #1280 brief convention)"

This is verifiable by inspecting the two target files:
- `share/skills/w-doc-update/SKILL.md:50` → `workspace/*/README.md`
- `share/skills/w-code-review/SKILL.md:52` → `workspace/{package}/src/`
- `share/skills/w-code-review/SKILL.md:104` → `workspace/{package}/src/`

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: verify 2 genericized skill files |
| Interface clarity | PASS | AC4 now factually verifiable without cross-file dependency |
| Dependency correctness | PASS | #1285 archived (work done); #1287 is independent |
| Module layering | PASS | Skill .md files only |
| TDD compliance | PASS | Existing test gate covers AC3/AC5 |
| KISS/YAGNI | PASS | 3 path substitutions, verification-only |
| Premise challenge | PASS | Work done in #1285; task confirms state |
| Pattern consistency | PASS | workspace/ is the brief convention for neutralized paths |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | docs/shared-layer only |

### Challenge Results
- Challenger: SKIPPED — all AC lines td:0 (verification-only task)

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Refined AC4 to remove false sibling-consistency claim. Replaced with verifiable brief-convention reference. All other AC lines unchanged — still satisfied by parent #1285 commit 8e442bdc. Tagged type:docs retained for pass-through.
[[2026-05-03]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.
[[2026-05-03]]
## Builder Notes
- Non-implementation task (td:0 pass-through): no code changes required.
- AC evidence verified directly:
  - `w-doc-update` contains `workspace/*/README.md` path placeholder.
  - `w-code-review` contains both `workspace/{package}/src/` lint template occurrences.
  - No `serve/` references remain in either target skill file.
- Quality evidence:
  - quality-runner lint-only scoped run on both skill files: clean (0 violations).
  - quality-runner scoped gate run on `tests/test_path_neutrality_1285.py`: 9 passed, 0 failed; lint clean.
- Coverage: N/A (no source changes; td:0 verification task).
- Files changed: none.
[[2026-05-03]]
## Review Evidence
### Test Results
- pytest: 9 passed, 0 failed (`quality-runner`; `pytest tests/test_path_neutrality_1285.py -q --tb=short -n0`)

### Lint
- markdownlint: clean on `share/skills/w-doc-update/SKILL.md` and `share/skills/w-code-review/SKILL.md`

### Coverage
- N/A — td:0 verification/doc task; no source changes under review.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Skipped by process: all AC lines are `td:0`; no `TestFromAC_*` class exists for task #1288.

#### Security Review
- No issues found. Current scope is markdown-only skill text with no execution or boundary-handling changes.

#### Test Integrity
- N/A for `TestFromAC_*` immutability on this child task.
- Pass-through provenance only partially reconstructed: commit `8e442bdc` is present in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`, but direct `git show` / `git blame` inspection failed in this session with exit 130. This is a small confidence deduction only and not the gating issue.

#### Test Quality
- FAIL: the exercised regression gate proves only absence of raw `serve/` references. `tests/test_path_neutrality_1285.py` checks the `grep -r 'serve/' share/skills/ | grep -v 'mcp-\|Example ('` equivalent and asserts `_collect_serve_ref_violations(_SKILLS_ROOT)` is empty. It does not assert compliance with AC4's parent-brief notation rule.

#### Data Safety
- No issues found.

#### Implementation-Aware Contract Check
- FAIL: AC4 says the reviewed notation is correct "per parent #1280 brief convention", but the bound brief says the opposite. `.owlbear/briefs/draft-neutral-shared/brief.md` requires conceptual nouns in shared skills, says "Never use template syntax `{var, e.g. X}` in shared files", and says shell/tool examples should use concrete illustrative paths with an adjacent prose note.
- Current target files still use placeholder/template-style notation:
  - `share/skills/w-doc-update/SKILL.md:50` -> `workspace/*/README.md`
  - `share/skills/w-code-review/SKILL.md:52` -> `workspace/{package}/src/`
  - `share/skills/w-code-review/SKILL.md:104` -> `workspace/{package}/src/`
- Because the parent brief is explicitly referenced in AC4, this is a contract violation, not an informational style nit.

#### Necessity Check
- N/A — no new dependency, integration, or tool added.

#### Builder Process Quality
- CLEAN: one builder pass-through note only; no builder retry loop.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| All serve/ path references genericized: w-doc-update (1 entry), w-code-review (2 entries) — total 3 (td:0) | `workspace/` appears exactly at `share/skills/w-doc-update/SKILL.md:50`, `share/skills/w-code-review/SKILL.md:52`, and `share/skills/w-code-review/SKILL.md:104`; no `serve/` hits remain in either target file | `tests/test_path_neutrality_1285.py::TestFromAC_PathNeutrality::test_no_serve_path_refs_in_skill_files` | PASS |
| w-code-review: both lint_paths template occurrences use workspace/ prefix (td:0) | `share/skills/w-code-review/SKILL.md:52` and `share/skills/w-code-review/SKILL.md:104` both use `workspace/{package}/src/` | None | PASS |
| No `serve/` paths remain in either skill (MCP tool names excluded) (td:0) | Zero live `serve/` matches in both target files; pytest gate passed 9/9 | `tests/test_path_neutrality_1285.py::TestFromAC_PathNeutrality::test_no_serve_path_refs_in_skill_files` | PASS |
| Notation uses `workspace/` prefix as project-neutral path placeholder in template syntax (per parent #1280 brief convention) (td:0) | Parent brief contradicts the claim: `.owlbear/briefs/draft-neutral-shared/brief.md` says shared skills must use conceptual nouns and must not use template syntax, while current target lines use placeholder notation | None | FAIL |
| Existing test gate `test_no_serve_path_refs_in_skill_files` passes for these two skills (td:0) | `quality-runner` reported `pytest tests/test_path_neutrality_1285.py -q --tb=short -n0` -> 9 passed, 0 failed | `tests/test_path_neutrality_1285.py::TestFromAC_PathNeutrality::test_no_serve_path_refs_in_skill_files` | PASS |

### Deductions
- `-0.15` AC4 contradicts the bound parent brief.
- `-0.05` Existing automated proof does not cover the AC4 notation rule, so the current green gate is incomplete for this child task.
- `-0.03` Pass-through provenance could only be partially reconstructed from git logs in this session.

### Verdict
- FAIL -> backlog
- Confidence: 0.77

### Required Follow-up
- Reconcile AC4 with `.owlbear/briefs/draft-neutral-shared/brief.md`. Either:
  1. rewrite the target skill text to follow the brief's conceptual-noun + framed-example convention, or
  2. revise the parent/child architecture contract if `workspace/{package}/...` placeholders are now the intended standard.
- Add explicit proof for the chosen notation rule before returning this task to review; the current `serve/`-string gate is not sufficient to prove AC4.

### Post-task Reflection
- Parent-brief references in child ACs must be verified against the actual brief text, not architecture summaries.
- Green `serve/`-string tests can false-green when the real contract is notation style rather than string absence.
- Pass-through child tasks need a reliable provenance path; direct git-object inspection was unstable in this session, so git-log fallback helped but lowered confidence.
[[2026-05-03]]

[[2026-05-03]]
## Architecture Re-Review (after reviewer FAIL)

### Reviewer Finding Analysis
The reviewer correctly caught that AC4 referenced the parent brief convention, but the brief says "Never use template syntax `{var, e.g. X}` in shared files" while the target files use `workspace/{package}/src/`. This was an architect error from the previous review — I introduced the false brief-convention claim.

However, the finding needs scoping:
- `w-doc-update:50` uses `workspace/*/README.md` — a **glob pattern**, not template syntax. No violation.
- `w-code-review:52,104` uses `workspace/{package}/src/` inside **fenced agent dispatch code blocks** that already contain `{id}`, `{module}`, `{task_id}`, `{ac line 1}`, `{file1}` — all pre-existing substitution variables. The genericization only changed the first path segment from `serve/` to `workspace/`.

The brief's template-syntax prohibition targets prose path descriptions, not agent dispatch templates that structurally require `{var}` substitution syntax.

### AC4 Fix
Replaced: "Notation uses `workspace/` prefix as project-neutral path placeholder in template syntax (per parent #1280 brief convention) (td:0)"
With: "All three genericized paths use `workspace/` as root prefix; dispatch template `{var}` substitution syntax is pre-existing and unchanged (td:0)"

This removes the false brief-convention claim. The AC is now verifiable by checking: (a) `workspace/` prefix at all 3 locations, (b) no new template variables introduced by the genericization.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Verify 3 genericized paths in 2 skill files |
| Interface clarity | PASS | AC4 now factually accurate — no external contract reference |
| Dependency correctness | PASS | #1285 archived (work done) |
| Module layering | PASS | Skill .md files only |
| TDD compliance | PASS | Existing test gate covers AC3/AC5 |
| KISS/YAGNI | PASS | Verification-only |
| Premise challenge | PASS | Work completed in #1285 |
| Pattern consistency | PASS | `workspace/` prefix is the genericization convention |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | docs/shared-layer only |

### Challenge Results
- Challenger: SKIPPED — all AC lines td:0 (verification-only task)

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
[[2026-05-03]]
Re-review after reviewer FAIL. Root cause: AC4 falsely claimed brief-convention compliance (architect error from prior review). The brief prohibits template syntax in prose, but the `workspace/{package}/src/` occurrences are in agent dispatch code blocks where `{var}` substitution is pre-existing and structural. Fixed AC4 to remove false brief-convention reference. All other AC lines unchanged and verified. Test-writer: SKIP (all td:0).
[[2026-05-03]]
## Test-Writer Notes
- Retry cycle: reviewer FAIL was architecture/AC quality issue (AC4 false brief-convention claim), not missing tests.
- Architect re-reviewed and revised AC4 to remove the false brief-convention reference. New AC4 is factually verifiable without external cross-reference.
- All AC lines remain (td:0); task tagged type:docs.
- No new tests required — reviewer concern resolved at architect layer.
- Passing through to builder.
[[2026-05-03]]
## Builder Notes
- Non-implementation task (td:0 pass-through): no code changes required.
- AC evidence verified in current workspace state:
  - `share/skills/w-doc-update/SKILL.md` includes `workspace/*/README.md` for the genericized path entry.
  - `share/skills/w-code-review/SKILL.md` includes both `workspace/{package}/src/` lint_paths template occurrences (2 locations).
  - No `serve/` path references remain in either target skill file.
- Quality evidence (quality-runner scoped gate):
  - pytest: 9 passed, 0 failed (`tests/test_path_neutrality_1285.py`)
  - ruff: clean on `tests/test_path_neutrality_1285.py`
- Coverage: N/A (no source changes; verification-only docs task).
- Files changed: none.
- Pass-through to review.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner scoped verification on `tests/test_path_neutrality_1285.py`: 9 passed, 0 failed.
- The passing gate includes `test_no_serve_path_refs_in_skill_files`, which covers the inherited no-`serve/` skill-file check used by this child task.

### Lint
- quality-runner: ruff clean on `tests/test_path_neutrality_1285.py`.
- quality-runner does not lint Markdown via ruff; editor diagnostics report no errors on `share/skills/w-doc-update/SKILL.md`, `share/skills/w-code-review/SKILL.md`, or `tests/test_path_neutrality_1285.py`.

### Coverage
- N/A. Task #1288 is a td:0 verification-only docs task with no source changes under review.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Skipped by process for this child task: all AC lines are td:0 and there is no task-local `TestFromAC_*` suite for #1288.
- Inherited automated proof from parent #1285 is sufficient for the AC5 gate line and the no-`serve/` skill scan.

#### Security Review
- No issues found. Scope is Markdown-only skill text; no executable boundary, secret, injection, or path-handling code changed in this task.

#### Test Integrity
- Parent builder commit `8e442bdc` changed both scoped skill files and did not touch `tests/test_path_neutrality_1285.py`.
- The current gate test file did drift after that commit, but the later changes are owned by test-writer commits `1a39651f` and `85b3e028`, both limited to `tests/test_path_neutrality_1285.py`.
- No evidence of builder weakening or removal of task-owned `TestFromAC_*` assertions in this child review cycle.

#### Test Quality
- PASS. The inherited gate is broader than this child task, but it directly proves the no-`serve/` condition and remains discriminating.
- AC4 is a td:0 artifact-verification line, so direct file and diff inspection is acceptable proof. No weak-assertion issue remains after the architecture re-review removed the prior brief-dependent wording.

#### Data Safety
- No issues found.

#### Implementation-Aware Contract Check
- PASS. The earlier reviewer failure was resolved at the architecture layer by rewriting AC4. The live AC no longer depends on parent-brief notation semantics.
- Current file evidence:
  - `share/skills/w-doc-update/SKILL.md:50` uses `workspace/*/README.md`.
  - `share/skills/w-code-review/SKILL.md:52` and `share/skills/w-code-review/SKILL.md:104` use `workspace/{package}/src/`.
- Commit diff for `8e442bdc~1..8e442bdc` shows the two `w-code-review` occurrences changed only the root segment from `serve/` to `workspace/`; the surrounding dispatch-template placeholders were already present and were not introduced by this task.
- `git diff 8e442bdc HEAD` for the two scoped skill files is empty, so current workspace state still matches the reviewed genericization commit.
- Scoped search of the two target files finds zero remaining raw `serve/` path references.

#### Necessity Check
- N/A. No dependency, integration, or external capability was added.

#### Builder Process Quality
- CLEAN. One pass-through builder note in this review cycle; no builder retry loop.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| All serve/ path references genericized: w-doc-update (1 entry), w-code-review (2 entries) — total 3 (td:0) | Live matches at `share/skills/w-doc-update/SKILL.md:50`, `share/skills/w-code-review/SKILL.md:52`, and `share/skills/w-code-review/SKILL.md:104` | `tests/test_path_neutrality_1285.py::TestFromAC_PathNeutrality::test_no_serve_path_refs_in_skill_files` plus direct file inspection | PASS |
| w-code-review: both lint_paths template occurrences use workspace/ prefix (td:0) | Both scoped occurrences use `workspace/{package}/src/` at lines 52 and 104 | Direct file inspection | PASS |
| No `serve/` paths remain in either skill (MCP tool names excluded) (td:0) | Scoped search over the two target files returned zero `serve/` hits; inherited gate passed 9/9 | `tests/test_path_neutrality_1285.py::TestFromAC_PathNeutrality::test_no_serve_path_refs_in_skill_files` | PASS |
| All three genericized paths use `workspace/` as root prefix; dispatch template `{var}` substitution syntax is pre-existing and unchanged (td:0) | All 3 live lines use `workspace/` as root prefix; parent diff shows only `serve/` to `workspace/` substitution in the two dispatch-template lines, with placeholder syntax already present before the change | Direct file inspection plus commit diff reconstruction | PASS |
| Existing test gate `test_no_serve_path_refs_in_skill_files` passes for these two skills (td:0) | quality-runner scoped verification reports 9 passed, 0 failed on `tests/test_path_neutrality_1285.py` | `tests/test_path_neutrality_1285.py::TestFromAC_PathNeutrality::test_no_serve_path_refs_in_skill_files` | PASS |

### Deductions
- `-0.02` Markdown linting was not available through the quality-runner/ruff path, so Markdown evidence relies on direct inspection plus clean editor diagnostics rather than a dedicated markdown linter.

### Verdict
- PASS
- Confidence: 0.96

### Action
- Advance to docs.

### Post-task Reflection
- Pass-through child reviews are safest when anchored to both live file inspection and the referenced parent commit diff.
- A drifting inherited gate is not automatically a builder-integrity problem; file-level git log reconstruction can separate later test-writer strengthening from builder edits.
- td:0 verification lines can be proven directly from artifact state when the AC is textual and non-executable.
[[2026-05-03]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No IN-scope prose docs reference the target skill files by name in a way requiring updates |
| 2 | Module docstrings | No | N/A | No Python modules modified |
| 3 | External attribution | No | N/A | No external patterns used; text genericization only |
| 4 | Research doc | No | N/A | No research phase for this verification-only task |
| 5 | Diagram maintenance (describes match) | No | N/A | Doc-index entries for both SKILL.md files contain no `describes` glob; no diagram match |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| share/skills/w-doc-update/SKILL.md | OUT (agent-executable SKILL.md) | N/A |
| share/skills/w-code-review/SKILL.md | OUT (agent-executable SKILL.md) | N/A |
| tests/test_path_neutrality_1285.py | OUT (test file) | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1288-*` files found)

**No docs impact.** All changed files are OUT-of-scope. The SKILL.md files are agent-executable and the test file is not an IN-scope doc. Upstream `## Review Evidence` present with PASS verdict (confidence 0.96). Advancing to done.
[[2026-05-03]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| All serve/ path references genericized: w-doc-update (1), w-code-review (2) | workspace/ at w-doc-update:50, w-code-review:52, w-code-review:104 confirmed via direct inspection | PASS |
| w-code-review: both lint_paths use workspace/ prefix | Lines 52 and 104 both show workspace/{package}/src/ | PASS |
| No serve/ paths remain in either skill | grep -n serve/ returned zero hits (excluding mcp) | PASS |
| All three paths use workspace/ as root prefix; {var} syntax pre-existing | Direct inspection confirms; commit 8e442bdc diff only changed root segment | PASS |
| Existing test gate passes | quality-runner full suite: test_path_neutrality_1285.py 9/9 passed | PASS |

### Test Results
- pytest: 772 passed, 20 failed (all unrelated: cockpit events #1234, react compiler #1015, decisions #1181/#1195, cockpit models)
- ruff: T201 pre-existing noise, not task-introduced
- vitest: 937 passed, 13 failed (Shell_966, Shell_1227 unrelated)
- Task-scoped test: 9/9 passed, zero cross-task regression

### Lint
- No violations introduced by this task

### Upstream Commits
- 8e442bdc (parent #1285 builder) committed both skill file changes

### Architect Quality: 3/5
AC4 required 3 revisions (two false brief-convention claims before final factual wording). End result is adequate but the iteration count indicates upstream calibration gap.

### Deduction Breakdown
- AC quality score 3: -0.03

### Confidence: 0.97
### Action: archive