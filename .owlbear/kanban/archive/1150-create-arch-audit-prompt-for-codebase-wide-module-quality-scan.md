---
id: 1150
title: Create arch-audit prompt for codebase-wide module quality scan
status: archived
priority: medium
created: 2026-04-27T21:51:43.242550+00:00
updated: 2026-04-28T00:03:44.714715+00:00
tags:
- quality
- arch
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Create a `.prompt.md` file that performs a codebase-wide module quality audit on `serve/` packages using the vocabulary from `r-architecture-standards` § Module Quality Vocabulary.

## Approach

- Scan each `serve/` package as the audit unit
- Apply the full Module Quality Vocabulary: Depth, Leverage, Locality, Seam, Adapter, Deletion Test, Dependency Classification
- Present findings with concrete evidence (what callers change if the package were removed)
- Optionally create kanban tasks for improvements found

## Acceptance Criteria

- [ ] File created at `share/prompts/arch-audit.prompt.md` with YAML frontmatter (`description:` field)
- [ ] Prompt instructs the executing agent to load `r-architecture-standards` § Module Quality Vocabulary before scanning
- [ ] Each `serve/` package is evaluated against all 5 vocabulary dimensions: Depth, Leverage, Locality, Seam/Adapter status, and Dependency Classification type
- [ ] Deletion Test applied to each package with explicit evidence: what complexity reappears in callers if the package is removed
- [ ] Output format is a structured table per package with columns: Package, Depth (deep/shallow), Leverage (caller count), Locality (self-contained/leaky), Seam status (real/hypothetical/none), Deletion Test result (earning-keep/pass-through/candidate-for-removal), Evidence, Recommendation

## Context

This prompt catches historical module debt across the codebase. It complements `w-arch-review` criterion #6, which applies the Deletion Test per-task only when new abstractions are introduced.

## Source

Inspired by mattpocock/skills `improve-codebase-architecture` + DEEPENING.md

[[2026-04-27]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One deliverable: a single `.prompt.md` file |
| Interface clarity | PASS (after refinement) | AC now specifies exact filename, vocabulary dimensions, output columns, evidence requirement |
| Dependency correctness | PASS | No deps; referenced `r-architecture-standards` § Module Quality Vocabulary exists at SKILL.md L29 |
| Module layering | N/A | Prompt file, no code |
| TDD compliance | N/A | Non-impl task, tagged `quality` (pass-through) |
| KISS/YAGNI | PASS | Minimal scope — one prompt file with defined output |
| Premise challenge | PASS | No existing arch/module audit prompt; complements per-task criterion #6 in w-arch-review |
| Pattern consistency | PASS | Follows `*-audit.prompt.md` naming convention (agent-audit, doc-audit, frontend-audit) |
| Security surface | PASS | Read-only audit, no new system boundaries |
| Single domain | PASS | Agent ecosystem / prompts domain |

### Challenge Results
- Challenger: reconsider (0.58)
- Findings: vocabulary completeness gap, audit-unit ambiguity, output contract missing evidence column, complementarity AC not verifiable
- Architect response: accepted all four concerns → REFINE. Rewrote AC to enumerate all 5 vocabulary dimensions, specify `serve/` packages as audit unit, add evidence column to output table, moved complementarity note to Context section (non-AC).

### Verdict: REFINE → APPROVE
### Action Taken: Rewrote task body with tightened AC (5 lines, all mechanically verifiable), then advanced to todo.
[[2026-04-27]]
## Test-Writer Notes
- Non-implementation task (tagged `quality`, `arch`) — no tests applicable.
- AC delivers only `share/prompts/arch-audit.prompt.md` (a `.prompt.md` file). No Python interfaces, modules, or endpoints introduced.
- Architecture Review in task body confirms: "TDD compliance | N/A | Non-impl task, tagged `quality` (pass-through)".
- Passing through to builder.
[[2026-04-27]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Test-Writer indicated explicit non-impl pass-through for tags `quality`, `arch`.
- Implementation: none
- Tests: N/A
- Coverage: N/A
- ruff: N/A
- Passing through to review.
[[2026-04-27]]
## Review Evidence
### Test Results
- quality-runner: Tests N/A. This is a prompt-file task with no executable test surface.
- quality-runner conclusion: no pytest/ruff/coverage evidence applies here; validation is structural/manual.

### Lint
- N/A. `share/prompts/` contains Markdown/YAML only; no Python files were in scope for ruff.

### Coverage
- N/A. No Python implementation was delivered for this task.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- No `TestFromAC_*` classes exist for this non-implementation prompt task. Skipped.

#### Security Review
- No new code surface was delivered. No security finding identified, but this does not offset the missing artifact.

#### Test Integrity
- No `TestFromAC_*` classes in scope. Skipped.

#### Test Quality
- N/A for this prompt-only task. Executable test quality is not the gating issue.

#### Data Safety
- No new runtime/data-handling path was delivered.

#### Implementation-Aware Gaps
- The required artifact is missing. Task AC at `.owlbear/kanban/tasks/1150-create-arch-audit-prompt-for-codebase-wide-module-quality-scan.md:32-38` requires a new prompt file.
- `file_search("share/prompts/arch-audit.prompt.md")` returned no files.
- Directory listing of `share/prompts/` contains peer prompts (`agent-audit.prompt.md`, `doc-audit.prompt.md`, `frontend-audit.prompt.md`, etc.) but not `arch-audit.prompt.md`.
- Because the file does not exist, AC 2-5 cannot be satisfied or verified.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The authoritative vocabulary the prompt was supposed to reference exists in `share/skills/r-architecture-standards/SKILL.md:29-54` (`Module Quality Vocabulary`, `Deletion Test`, `Dependency Classification`). The task failed before reaching content conformance against that authority.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| File created at `share/prompts/arch-audit.prompt.md` with YAML frontmatter (`description:` field) | Required by task file `.owlbear/kanban/tasks/1150-create-arch-audit-prompt-for-codebase-wide-module-quality-scan.md:34`. `file_search("share/prompts/arch-audit.prompt.md")` returned no files. | N/A | FAIL |
| Prompt instructs the executing agent to load `r-architecture-standards` § Module Quality Vocabulary before scanning | Required by task file `...:35`. Cannot verify because the prompt file does not exist. | N/A | FAIL |
| Each `serve/` package is evaluated against all 5 vocabulary dimensions: Depth, Leverage, Locality, Seam/Adapter status, and Dependency Classification type | Required by task file `...:36`. Cannot verify because the prompt file does not exist. | N/A | FAIL |
| Deletion Test applied to each package with explicit evidence: what complexity reappears in callers if the package is removed | Required by task file `...:37`. Cannot verify because the prompt file does not exist. | N/A | FAIL |
| Output format is a structured table per package with columns: Package, Depth (deep/shallow), Leverage (caller count), Locality (self-contained/leaky), Seam status (real/hypothetical/none), Deletion Test result (earning-keep/pass-through/candidate-for-removal), Evidence, Recommendation | Required by task file `...:38`. Cannot verify because the prompt file does not exist. | N/A | FAIL |

### Deductions
- 0.50: AC1 failed outright; the required deliverable is absent.
- 0.38: AC2-AC5 are unverified and unsatisfied because the artifact does not exist.

### Verdict
- FAIL. Confidence that the task satisfies its acceptance criteria: 0.12.

### Action
- Route to `in-progress`.
- Builder must create the required prompt artifact and then the review can verify structure/content against the task AC and `r-architecture-standards`. 
[[2026-04-27]]
## Builder Notes
- Implementation: created share/prompts/arch-audit.prompt.md with required YAML frontmatter `description`.
- AC alignment: prompt explicitly requires loading `r-architecture-standards` Module Quality Vocabulary, Deletion Test, and Dependency Classification before scanning.
- Audit scope contract: evaluates each top-level `serve/` package against Depth, Leverage, Locality, Seam/Adapter status, and Dependency Classification.
- Deletion Test contract: requires explicit per-package evidence describing what complexity reappears in callers if the package is removed.
- Output contract: includes exact required table columns: Package, Depth (deep/shallow), Leverage (caller count), Locality (self-contained/leaky), Seam status (real/hypothetical/none), Deletion Test result (earning-keep/pass-through/candidate-for-removal), Evidence, Recommendation.
- Tests: N/A (non-implementation prompt artifact only; no TestFromAC file exists for this task).
- Coverage: N/A.
- ruff: N/A.

Post-task reflection:
- Problem faced: prior pass-through closed without delivering the required artifact.
- Workaround applied: anchored implementation directly to AC and the authoritative vocabulary section.
- Pattern discovered: non-implementation tasks still need explicit artifact delivery checks before pass-through.
- Quality gap: lack of task-scoped executable checks for prompt-only artifacts increases risk of false-green handoffs.
[[2026-04-27]]
## Review Evidence
### Test Results
- quality-runner: Tests N/A. No task-scoped pytest surface exists for this prompt-only artifact review.
- Workspace search: no matches for `1150` or `arch-audit.prompt.md` under `tests/**`; no task-owned tests exist.

### Lint
- quality-runner: N/A. No Python lint surface was in scope for this task.

### Coverage
- quality-runner: N/A. No executable module surface was delivered for this task.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- No `TestFromAC_*` classes or task-owned tests exist for task 1150. Skipped.

#### Security Review
- No code-execution, secret-handling, or dependency-risk surface was introduced in `share/prompts/arch-audit.prompt.md`. No security finding.

#### Test Integrity
- No task-owned tests in scope. Skipped.

#### Test Quality
- N/A. This is a prompt-only artifact.

#### Data Safety
- No runtime data path or persisted data flow was added. No gating data-safety finding.

#### Implementation-Aware Gaps
- AC3 at `.owlbear/kanban/tasks/1150-create-arch-audit-prompt-for-codebase-wide-module-quality-scan.md:36` requires each package to be evaluated against all 5 vocabulary dimensions, including dependency classification type.
- The prompt does enumerate dependency classification in Step 3 at `share/prompts/arch-audit.prompt.md:31-38`.
- But Step 4 then requires one table row per package with exactly these columns at `share/prompts/arch-audit.prompt.md:48-52`, and that schema omits dependency classification.
- Because extra columns are forbidden and no existing column is instructed to carry dependency classification, an executing agent cannot produce a structured visible dependency-classification result while staying inside the output contract.
- This leaves AC3 unsatisfied and makes the AC5 table contract incomplete for the required audit dimensions.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- The prompt correctly loads the authoritative vocabulary before scanning at `share/prompts/arch-audit.prompt.md:10-17`, matching `share/skills/r-architecture-standards/SKILL.md:29-54`.
- The Deletion Test requirement is correctly represented at `share/prompts/arch-audit.prompt.md:40-46`, matching `share/skills/r-architecture-standards/SKILL.md:41-47`.
- Operational wording is slightly mixed: `share/prompts/arch-audit.prompt.md:7` calls this a read-only audit, while Step 5 later allows optional kanban task creation. This is not the gating issue because the task approach explicitly allows optional follow-up tasks.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| File created at `share/prompts/arch-audit.prompt.md` with YAML frontmatter (`description:` field) | File exists and has YAML frontmatter with `description` at `share/prompts/arch-audit.prompt.md:1-3`. | N/A | PASS |
| Prompt instructs the executing agent to load `r-architecture-standards` § Module Quality Vocabulary before scanning | Step 1 requires loading `share/skills/r-architecture-standards/SKILL.md`, `## Module Quality Vocabulary`, `### Deletion Test`, and `### Dependency Classification` at `share/prompts/arch-audit.prompt.md:10-17`. | N/A | PASS |
| Each `serve/` package is evaluated against all 5 vocabulary dimensions: Depth, Leverage, Locality, Seam/Adapter status, and Dependency Classification type | Step 3 enumerates all 5 dimensions at `share/prompts/arch-audit.prompt.md:31-38`, but Step 4 omits dependency classification from the fixed output schema at `share/prompts/arch-audit.prompt.md:48-52`. | N/A | FAIL |
| Deletion Test applied to each package with explicit evidence: what complexity reappears in callers if the package is removed | Step 3 requires removing the package, stating what complexity reappears in callers, and supplying concrete evidence at `share/prompts/arch-audit.prompt.md:40-46`. | N/A | PASS |
| Output format is a structured table per package with columns: Package, Depth (deep/shallow), Leverage (caller count), Locality (self-contained/leaky), Seam status (real/hypothetical/none), Deletion Test result (earning-keep/pass-through/candidate-for-removal), Evidence, Recommendation | The table exists at `share/prompts/arch-audit.prompt.md:50-52`, but it is incomplete against the task contract because dependency classification is required for every package and no table column captures it. | N/A | FAIL |

### Deductions
- 0.16: AC3 is not fully satisfied because dependency classification is required but not surfaced in the output contract.
- 0.10: AC5 is incomplete relative to the required audit dimensions; the exact-column table omits dependency classification.
- 0.02: No executable guardrail exists to catch this prompt-contract mismatch.

### Verdict
- FAIL. Confidence that task 1150 satisfies its acceptance criteria: 0.72.

### Action
- Route to `in-progress`.
- Builder must reconcile Step 3 and Step 4 without changing the task contract: keep the required table columns, but explicitly instruct where dependency classification is reported (for example within the `Evidence` column) so the audit output visibly covers all 5 required dimensions.

Post-task reflection:
- Problem faced: prompt-only tasks can look complete once the file exists, but contract gaps still hide in the output schema.
- Workaround applied: adversarial code-reader review caught the Step 3 versus Step 4 mismatch that a simple artifact-exists check would miss.
- Pattern discovered: when AC requires a dimension that is absent from a fixed-column output table, review the reporting path, not just the presence of the instruction.
- Quality gap: non-implementation prompt tasks still lack executable safeguards, so line-level contract review is the only effective gate.
[[2026-04-27]]
## Builder Notes
- Implementation: updated [share/prompts/arch-audit.prompt.md](share/prompts/arch-audit.prompt.md) to resolve the Step 3 vs Step 4 contract gap without changing required table columns.
- Fix applied: added an explicit rule that the `Evidence` column must include the dependency classification label (`in-process`, `local-substitutable`, `remote-but-owned`, or `true-external`) plus caller/dependency proof.
- AC alignment: keeps exact required columns while making dependency classification visibly reportable for every package.
- Tests: N/A for task-scoped executable tests (no `tests/test_*1150*.py` files).
- Coverage: N/A (no tests executed).
- ruff: clean (`ruff` exit 0; markdown path has no Python lint surface).

Post-task reflection:
- Problem faced: output schema required exact columns but did not define where dependency classification should appear.
- Workaround applied: embedded dependency classification reporting requirement into `Evidence` column, preserving fixed schema.
- Pattern discovered: for prompt-only tasks, dimension completeness must be validated against output schema, not just instruction prose.
- Quality gap: non-implementation prompt tasks still rely on manual contract checks rather than executable guards.
[[2026-04-27]]
## Review Evidence
### Test Results
- quality-runner: Tests N/A. No task-owned pytest surface exists for this prompt-only artifact review.
- Evidence: `tests/**/*1150*` returned no files, and a content search for `arch-audit.prompt.md|1150` under `tests/**` returned no matches.
- code-reader: no FAIL-level findings.

### Lint
- quality-runner: N/A. The delivered artifact is Markdown/YAML only at `share/prompts/arch-audit.prompt.md`.

### Coverage
- quality-runner: N/A. No executable module surface was added for this task.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- No `TestFromAC_*` classes or task-owned tests exist for task 1150. Skipped.

#### Security Review
- No issues found. The changed artifact is a Markdown prompt only; it introduces no executable code path, secret-handling surface, or new dependency boundary.

#### Test Integrity
- No task-owned tests were added or modified. Skipped.

#### Test Quality
- N/A for executable tests. This review used manual contract verification because the deliverable is a prompt artifact, not code.

#### Data Safety
- No issues found. The prompt frames the audit as read-only at `share/prompts/arch-audit.prompt.md:7` and reiterates that default at `share/prompts/arch-audit.prompt.md:71`. Optional follow-up task creation is explicit and bounded in Step 5.

#### Implementation-Aware Gaps
- No FAIL-level gaps remain.
- The prior failure on dependency-classification reporting is resolved: Step 3 requires the classification itself at `share/prompts/arch-audit.prompt.md:38`, and Step 4 now explicitly binds that classification into the `Evidence` column at `share/prompts/arch-audit.prompt.md:55` while preserving the fixed schema at `share/prompts/arch-audit.prompt.md:52`.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- The prompt correctly loads the authoritative vocabulary before scanning at `share/prompts/arch-audit.prompt.md:9-17`, aligned with `share/skills/r-architecture-standards/SKILL.md:29-54`.
- The Deletion Test requirement is correctly represented at `share/prompts/arch-audit.prompt.md:40-46`, matching `share/skills/r-architecture-standards/SKILL.md:41-45`.
- Residual clarity gap only: `share/prompts/arch-audit.prompt.md:37` requires seam status with adapter context, but unlike dependency classification, adapter context is not explicitly assigned to a specific table cell. This is informational, not blocking, because AC5's fixed schema does not provide an adapter column and the prompt still requires the context to be included.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| File created at `share/prompts/arch-audit.prompt.md` with YAML frontmatter (`description:` field) | File exists with YAML frontmatter at `share/prompts/arch-audit.prompt.md:1-3`, including `description` at line 2. | N/A | PASS |
| Prompt instructs the executing agent to load `r-architecture-standards` § Module Quality Vocabulary before scanning | Step 1 at `share/prompts/arch-audit.prompt.md:9-17` requires loading `share/skills/r-architecture-standards/SKILL.md`, `## Module Quality Vocabulary`, `### Deletion Test`, and `### Dependency Classification` before continuing. | N/A | PASS |
| Each `serve/` package is evaluated against all 5 vocabulary dimensions: Depth, Leverage, Locality, Seam/Adapter status, and Dependency Classification type | Step 3 enumerates all 5 dimensions at `share/prompts/arch-audit.prompt.md:30-38`; Step 4 binds dependency classification into every row's `Evidence` cell at `share/prompts/arch-audit.prompt.md:55`. | N/A | PASS |
| Deletion Test applied to each package with explicit evidence: what complexity reappears in callers if the package is removed | Step 3 requires removing the package, stating what complexity reappears in callers, and citing concrete evidence at `share/prompts/arch-audit.prompt.md:40-46`. | N/A | PASS |
| Output format is a structured table per package with columns: Package, Depth (deep/shallow), Leverage (caller count), Locality (self-contained/leaky), Seam status (real/hypothetical/none), Deletion Test result (earning-keep/pass-through/candidate-for-removal), Evidence, Recommendation | Step 4 defines the exact required fixed schema at `share/prompts/arch-audit.prompt.md:50-52`. The dependency-classification reporting requirement at line 55 supplements the `Evidence` cell without altering the mandated columns. | N/A | PASS |

### Deductions
- 0.03: No executable task-owned guardrail exists; verification is necessarily structural/manual.
- 0.02: Adapter context is required conceptually but not explicitly pinned to a named output cell the way dependency classification is.

### Verdict
- PASS. Confidence that task 1150 satisfies its acceptance criteria: 0.95.

### Action
- Advance to `docs`.

Post-task reflection:
- Problem faced: prompt-only tasks rely on manual contract review because no task-scoped executable checks exist.
- Pattern discovered: a fixed-column table can still satisfy an extra required audit dimension when the prompt explicitly binds that dimension into the `Evidence` cell.
- Quality gap: seam/adapter context is still looser in the output contract than dependency classification, though not enough to fail this task.
[[2026-04-27]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed file `share/prompts/arch-audit.prompt.md` is OUT-scope (agent-executable). No IN-scope README or guide references this prompt by name. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | Yes | Updated | Task body `## Source` cites `mattpocock/skills improve-codebase-architecture`. No prior entry in `.owlbear/sources/overview.md`. Added row under new `## Arch-Audit Prompt (Task #1150)` section. |
| 4 | Research doc | No | N/A | No research doc produced or linked from task body. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/project-overview.excalidraw` describes `share/**`; changed file matches. Footer updated from `2026-04-28 (c06b12e2)` → `2026-04-28 (a8986003)`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `share/prompts/arch-audit.prompt.md` | OUT (agent-executable `.prompt.md`) | N/A — no direct edits; diagram footer triggered by `share/**` describes match |

### Files Updated
- `.owlbear/sources/overview.md` — added attribution row for mattpocock/skills improve-codebase-architecture
- `share/diagrams/project-overview.excalidraw` — footer updated to `2026-04-28 (a8986003)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found for task 1150
[[2026-04-28]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| File created at `share/prompts/arch-audit.prompt.md` with YAML frontmatter (`description:` field) | File exists with `description:` at lines 1-3 | PASS |
| Prompt instructs executing agent to load `r-architecture-standards` § Module Quality Vocabulary before scanning | Step 1 at lines 9-17 loads SKILL.md + subsections | PASS |
| Each `serve/` package evaluated against all 5 vocabulary dimensions | Step 3 (L30-38) enumerates all 5; Step 4 (L55) binds dep classification into Evidence column | PASS |
| Deletion Test applied with explicit evidence | Step 3 (L40-46) requires removal assumption + caller complexity evidence | PASS |
| Output format is structured table with required columns | Step 4 (L50-52) exact columns; L55 supplements Evidence cell with dep classification | PASS |

### Test Results
- pytest: 2739 passed, 117 failed, 4 skipped — all failures pre-existing (react compiler, mode6, corruption, atomicity); none task-scoped
- ruff: 8 violations all in unrelated packages (knowledge, mcp-knowledge, mcp-memory, orchestrator); none in task scope

### Architect Quality: 4/5
AC rewritten after challenger REFINE with 5 mechanically verifiable lines. Minor ambiguity in dependency-classification reporting path (AC3 vs AC5 interaction) caused one builder iteration, but AC was adequate post-refinement.

### Deduction Breakdown
- AC lines without evidence: 0 (-.00)
- Lint violations in scope: 0 (-.00)
- AC quality ≤ 3: No (-.00)
- Missing reviewer evidence: No (-.00)
- Task-scoped test failures: 0 (-.00)
- Conservative: no executable guardrail for prompt-contract drift (-.02)

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| decb611e | feat | share/prompts/arch-audit.prompt.md | #1150 |
| a14038d2 | fix | share/prompts/arch-audit.prompt.md | #1150 |
| b9644c17 | docs | .owlbear/sources/overview.md, share/diagrams/project-overview.excalidraw | #1150 |
| 123df7a7 | chore | .owlbear/kanban/tasks/1150-*.md | #1150 |