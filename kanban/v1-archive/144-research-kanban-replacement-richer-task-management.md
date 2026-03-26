---
id: 144
title: 'Research: Kanban replacement — richer task management'
status: archived
priority: someday
created: 2026-02-27T14:59:15.1180834+01:00
updated: 2026-03-22T00:11:46.9179219+01:00
started: 2026-03-01T20:08:53.0346447+01:00
completed: 2026-03-22T00:11:42.6829546+01:00
tags:
    - research
    - tooling
    - phase-14
class: standard
---

## Goal

Decide whether OwlBear should keep kanban-md, augment it, or replace it with a richer task-management tool.

## Scope

- Research only. Do not prototype or modify OwlBear source code as part of this task.
- Reuse existing OwlBear research where available instead of duplicating it.

## OwlBear Integration Seams

Any replacement or augmentation recommendation must account for these existing touchpoints:
- src/owlbear/tools/kanban.py
- src/owlbear/core/board_context.py
- src/owlbear/core/context_hook.py
- src/owlbear/core/retrospective_hook.py
- src/owlbear/projects/workspace.py
- kanban/config.yml and kanban/tasks/*.md

## Acceptance Criteria

- [ ] Create docs/research/kanban-replacement-options.md with sections for context/question, sources studied, comparison matrix, recommendation, and follow-up tasks.
- [ ] Compare the current kanban-md baseline against the task's named candidate directions: Mission Control, GitHub Issues/Projects, and at least one additional offline, file-based, CLI-capable alternative or an augment-kanban-md-without-replacement option.
- [ ] Score each option against these criteria: offline operation, file-based agent operability, CLI ergonomics, dependency/priority/assignment support, richer UI surface, migration cost across the OwlBear integration seams above, and security/privacy implications.
- [ ] Reuse docs/research/mission-control.md as Mission Control input and explicitly state whether richer board visibility is better delivered by augmenting kanban-md rather than replacing it.
- [ ] End with exactly one recommendation: keep kanban-md, augment around kanban-md, or replace it with a named alternative. If no clear winner exists, create a decision request in docs/decisions/pending/ instead of implementation follow-up tasks.
- [ ] If the recommendation implies engineering work, execute kanban-md create commands for every follow-up task at ideation status and link each new task back to the research doc. If the recommendation is to keep or defer, the doc must explicitly state why no follow-up tasks are required.

[[2026-03-21]] Sat 13:48
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Evaluate whether kanban-md should be replaced with something richer | Valid research direction, but not a verifiable deliverable | Rewrote as a research doc plus recommendation contract |
| Requirements: file-based, CLI-friendly, supports dependencies, priorities, agents/assignment, ideally web/TUI view | Good evaluation criteria, but buried in prose and incomplete without migration-cost analysis | Converted into explicit scored comparison criteria |
| References: Mission Control, GitHub Issues/Projects, linear-style CLIs | Useful starting candidates, but missing the current baseline and an augment-without-replacement option | Expanded the comparison set and required reuse of existing Mission Control research |
| Only replace if something is materially better | Sound guardrail, but materially better was undefined | Rewrote as a single required keep, augment, replace, or decision-request outcome |

### Architecture Notes
OwlBear's current task-board workflow is wired into multiple integration seams: src/owlbear/tools/kanban.py, src/owlbear/core/board_context.py, src/owlbear/core/context_hook.py, src/owlbear/core/retrospective_hook.py, src/owlbear/projects/workspace.py, and the kanban/ board files. That makes this a cross-cutting architecture decision, not a cosmetic tooling swap.

Existing research already covers one candidate in docs/research/mission-control.md, and docs/research/textual-tui-dashboard.md shows that richer board visibility may be better delivered by layering UI on top of the existing file-based board instead of replacing kanban-md. The refined AC therefore requires comparison against the current baseline, migration cost across real OwlBear touchpoints, and an explicit augment-versus-replace conclusion.

Research-only task. No code, no tests, no new security surface. TDD N/A.

### Changes Made
- Replaced the vague body with a verifiable research contract
- Approved and moved task to todo

### Dependencies
- Verified: no blocking task dependencies
- Reuse as inputs: docs/research/mission-control.md, docs/research/textual-tui-dashboard.md
- TDD predecessor not required because this task produces research, not implementation

[[2026-03-21]] Sat 14:27
## Test-Writer Notes
Non-implementation task (tagged: research) — no tests applicable. Passing through to builder.

[[2026-03-21]] Sat 15:00
## Builder Notes
- Files changed: docs/research/kanban-replacement-options.md (created, 247 lines)
- Follow-up task created: #905 (bearclaw board Rich table view, ideation)
- Research: assessed kanban-md vs Mission Control vs GitHub Issues/Projects vs Taskwarrior vs augment-kanban-md
- Recommendation: keep + augment (confidence .90)
- Reused: docs/research/mission-control.md, docs/research/textual-tui-dashboard.md
- Commit: ef5ae42

[[2026-03-21]] Sat 18:31
## Review Evidence
### Review: #144 — Research: Kanban replacement — richer task management

### Test Results
- pytest: 23 failed, 2 warnings in 4.54s (uv run pytest tests/test_cli_board.py -q --tb=short).
- Failure signature: AttributeError: module 'bearclaw.commands' has no attribute 'board' across TestFromAC_* board tests.
- Scope note: failures are tied to open implementation split (#909/#910) and are not introduced by task #144 (commit ef5ae42 is doc-only).

### Lint Results
- ruff: 451 errors, 363 fixable (uv run ruff check src/ tests/).
- Scope note: errors are repository baseline across many existing test files and unrelated to task #144 deliverable.

### Coverage
- Not applicable: builder commit ef5ae42 changed only docs/research/kanban-replacement-options.md.

### Pass 1 — CRITICAL
#### Security Review
- Hardcoded secret scan on docs/research/kanban-replacement-options.md: no credential pattern matches.
- No injection/path traversal/deserialization/input-validation/data-leak surface added; deliverable is markdown research content only.
- No dependency additions in ef5ae42.

#### Test Integrity (TestFromAC comparison)
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| N/A for #144 deliverable | No test files changed in ef5ae42 | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | No tests were added or modified by #144; artifact is research markdown. |
| Negative/error paths | ADEQUATE | Not applicable to this research-only deliverable. |
| Mutation reasoning | ADEQUATE | No implementation logic changed in ef5ae42 to mutate. |
| Test independence | ADEQUATE | No new tests introduced by #144. |
| Descriptive names | ADEQUATE | No new tests introduced by #144. |

#### Data Safety
- No data safety issues found; no runtime/data-path code changed.

### Pass 2 — INFORMATIONAL
- Repository currently contains unrelated red board tests and broad lint debt; these are tracked by separate implementation tasks and do not violate #144 AC.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Create docs/research/kanban-replacement-options.md with required sections | File exists; sections present at lines 6, 27, 51, 212, 234 in docs/research/kanban-replacement-options.md | Artifact inspection | PASS |
| Compare baseline vs Mission Control, GitHub Issues/Projects, and additional offline or augment option | Candidate matrix includes kanban-md, Mission Control, GitHub Issues + Projects, Taskwarrior, Augment kanban-md (lines 45-49) | Artifact inspection | PASS |
| Score each option on required criteria including migration cost and security/privacy | Scoring table contains all required criteria rows (lines 58-64) | Artifact inspection | PASS |
| Reuse mission-control research and state augment-vs-replace visibility conclusion | Mission Control source cited (lines 31, 89); explicit conclusion at line 209 favors augmenting kanban-md | Artifact inspection | PASS |
| End with exactly one recommendation (keep, augment, or replace) | Single recommendation heading and statement: Keep kanban-md with targeted augmentation (line 214) | Artifact inspection | PASS |
| If engineering work implied, create ideation follow-up task(s) linked back to research doc | Follow-up create command uses --status ideation (line 239); follow-up task exists as #905 and links back to docs/research/kanban-replacement-options.md in body line 17; create event recorded in kanban/activity.jsonl line 2696 | Artifact inspection | PASS |

### Verdict: PASS
Confidence: .91

### Action Taken
- kanban\kanban-md.exe edit 144 --status docs --release

[[2026-03-21]] Sat 23:40
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Research-only task; recommendation is keep kanban-md (already documented in tech stack table). No behavior or convention change. |
| 2 | Docstrings | No | N/A | Builder commit ef5ae42 touched only docs/research/kanban-replacement-options.md. No .py files modified. |
| 3 | docs/sources/overview.md | No | N/A | No external code patterns adopted; research doc cites sources as comparative references, not code borrowed into OwlBear. |
| 4 | README.md | No | N/A | No CLI commands added or modified by this task. |
| 5 | Research doc linked | Yes | Pass | docs/research/kanban-replacement-options.md exists (247 lines, sections 1-7 verified). Follow-up task #905 created at ideation (now backlog), body links to research doc sections 5 and 6. |
| 6 | No docs impact (default) | N/A | N/A | Items 1-4 do not apply; item 5 passes. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/144-* files found)

[[2026-03-22]] Sun 00:11
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Create docs/research/kanban-replacement-options.md with required sections | File exists (247 lines), 7 sections: Context/Question, Sources Studied, Candidates, Comparison Matrix, Richer Board Visibility, Recommendation, Follow-up Tasks | PASS |
| Compare baseline vs Mission Control, GitHub Issues/Projects, and additional alternative or augment option | Matrix includes kanban-md (baseline), Mission Control, GitHub Issues+Projects, Taskwarrior (additional CLI alternative), Augment kanban-md | PASS |
| Score each option on required criteria incl. migration cost and security/privacy | All 7 criteria scored in comparison matrix (offline, file-based operability, CLI ergonomics, dependency/priority/assignment, richer UI, migration cost, security/privacy) | PASS |
| Reuse mission-control research and state augment-vs-replace visibility conclusion | Mission Control cited in Sources table; explicit conclusion in section 5: richer board visibility is better delivered by augmenting kanban-md | PASS |
| End with exactly one recommendation (keep, augment, or replace) | Single recommendation in section 6: Keep kanban-md with targeted augmentation (.90 confidence) | PASS |
| If engineering work implied, create ideation follow-up task(s) linked to research doc | Follow-up task #905 created at ideation, body references docs/research/kanban-replacement-options.md sections 5 and 6; later split by architect into #909/#910 | PASS |

### Research Task Verification
- Research doc: docs/research/kanban-replacement-options.md exists (247 lines, complete)
- Follow-up task #905 created on board (now blocked parent, split -> #909, #910)
- Follow-up tasks link back to research doc: confirmed in #905 body

### Test Results
- pytest: 3746 passed, 102 failed, 20 skipped (full suite, 144s). All 102 failures are pre-existing (numpy compat, bearclaw module changes, bootstrap unpacking) -- none related to #144 doc-only commit ef5ae42.
- ruff: 451 errors (pre-existing baseline). None introduced by #144.

### Commit Verification
- Commit ef5ae42: docs: kanban replacement options research (#144, builder) -- properly scoped, doc-only.

### Confidence: .97
### Action: archive

[[2026-03-22]] Sun 00:11
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Create docs/research/kanban-replacement-options.md with required sections | File exists (247 lines), 7 sections: Context/Question, Sources Studied, Candidates, Comparison Matrix, Richer Board Visibility, Recommendation, Follow-up Tasks | PASS |
| Compare baseline vs Mission Control, GitHub Issues/Projects, and additional alternative or augment option | Matrix includes kanban-md (baseline), Mission Control, GitHub Issues+Projects, Taskwarrior (additional CLI alternative), Augment kanban-md | PASS |
| Score each option on required criteria incl. migration cost and security/privacy | All 7 criteria scored in comparison matrix (offline, file-based operability, CLI ergonomics, dependency/priority/assignment, richer UI, migration cost, security/privacy) | PASS |
| Reuse mission-control research and state augment-vs-replace visibility conclusion | Mission Control cited in Sources table; explicit conclusion in section 5: richer board visibility is better delivered by augmenting kanban-md | PASS |
| End with exactly one recommendation (keep, augment, or replace) | Single recommendation in section 6: Keep kanban-md with targeted augmentation (.90 confidence) | PASS |
| If engineering work implied, create ideation follow-up task(s) linked to research doc | Follow-up task #905 created at ideation, body references docs/research/kanban-replacement-options.md sections 5 and 6; later split by architect into #909/#910 | PASS |

### Research Task Verification
- Research doc: docs/research/kanban-replacement-options.md exists (247 lines, complete)
- Follow-up task #905 created on board (now blocked parent, split -> #909, #910)
- Follow-up tasks link back to research doc: confirmed in #905 body

### Test Results
- pytest: 3746 passed, 102 failed, 20 skipped (full suite, 144s). All 102 failures are pre-existing (numpy compat, bearclaw module changes, bootstrap unpacking) -- none related to #144 doc-only commit ef5ae42.
- ruff: 451 errors (pre-existing baseline). None introduced by #144.

### Commit Verification
- Commit ef5ae42: docs: kanban replacement options research (#144, builder) -- properly scoped, doc-only.

### Confidence: .97
### Action: archive

[[2026-03-22]] Sun 00:11
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Create docs/research/kanban-replacement-options.md with required sections | File exists (247 lines), 7 sections: Context/Question, Sources Studied, Candidates, Comparison Matrix, Richer Board Visibility, Recommendation, Follow-up Tasks | PASS |
| Compare baseline vs Mission Control, GitHub Issues/Projects, and additional alternative or augment option | Matrix includes kanban-md (baseline), Mission Control, GitHub Issues+Projects, Taskwarrior (additional CLI alternative), Augment kanban-md | PASS |
| Score each option on required criteria incl. migration cost and security/privacy | All 7 criteria scored in comparison matrix (offline, file-based operability, CLI ergonomics, dependency/priority/assignment, richer UI, migration cost, security/privacy) | PASS |
| Reuse mission-control research and state augment-vs-replace visibility conclusion | Mission Control cited in Sources table; explicit conclusion in section 5: richer board visibility is better delivered by augmenting kanban-md | PASS |
| End with exactly one recommendation (keep, augment, or replace) | Single recommendation in section 6: Keep kanban-md with targeted augmentation (.90 confidence) | PASS |
| If engineering work implied, create ideation follow-up task(s) linked to research doc | Follow-up task #905 created at ideation, body references docs/research/kanban-replacement-options.md sections 5 and 6; later split by architect into #909/#910 | PASS |

### Research Task Verification
- Research doc: docs/research/kanban-replacement-options.md exists (247 lines, complete)
- Follow-up task #905 created on board (now blocked parent, split -> #909, #910)
- Follow-up tasks link back to research doc: confirmed in #905 body

### Test Results
- pytest: 3746 passed, 102 failed, 20 skipped (full suite, 144s). All 102 failures are pre-existing (numpy compat, bearclaw module changes, bootstrap unpacking) -- none related to #144 doc-only commit ef5ae42.
- ruff: 451 errors (pre-existing baseline). None introduced by #144.

### Commit Verification
- Commit ef5ae42: docs: kanban replacement options research (#144, builder) -- properly scoped, doc-only.

### Confidence: .97
### Action: archive
