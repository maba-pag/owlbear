---
id: 729
title: Add command decomposition guideline to Terminal discipline
status: archived
priority: nice-to-have
created: 2026-03-10T19:09:59.1137219+01:00
updated: 2026-03-21T03:46:30.3155837+01:00
started: 2026-03-21T03:46:26.2963396+01:00
completed: 2026-03-21T03:46:26.2963396+01:00
tags:
    - scope:copilot
    - docs
    - phase-research
class: standard
---

Add a command decomposition bullet to agent-common.instructions.md section 'Terminal discipline'. AC: (1) New bullet point in Terminal discipline using bold-header format matching existing bullets (e.g. '**Command decomposition.**'); (2) Body text advises breaking complex multi-step operations into separate simple terminal calls rather than long chained pipelines; (3) Rationale mentions independent reviewability and reduced approval friction; (4) Does NOT contradict the 'Chain with ;' bullet -- clarify that ;-chaining applies to closely related commands in one logical operation, while decomposition separates distinct logical steps.

[[2026-03-13]] Fri 20:23
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| (1) Bold-header bullet in Terminal discipline | Clear, matches existing format | Keep |
| (2) Advises decomposition of complex multi-step ops | Precise - builder knows what content to write | Keep |
| (3) Rationale: reviewability + approval friction | Clear motivation for the guideline | Keep |
| (4) No contradiction with 'Chain with ;' | Addresses the tension explicitly | Keep (added by architect) |

### Architecture Notes
Existing Terminal discipline section (agent-common.instructions.md L130-142) has 4 bullets in bold-header format. New bullet slots in naturally. The 'Chain with ;' bullet (L139) is syntax guidance (PS 5.1 compat); decomposition is scope guidance (when to use separate tool calls). AC (4) ensures builder addresses this distinction.

Docs-only task -- no test task needed, no .py changes, no failure modes.

### Changes Made
- Refined AC body: added format requirement (bold-header), distinction from ;-chaining, approval friction rationale

### Dependencies
- None

[[2026-03-13]] Fri 20:44
## Test-Writer Notes
Non-implementation task (docs-only, tagged docs). No .py source changes, no testable code. Passing through to builder.

-t

[[2026-03-20]] Fri 19:10
## Builder Notes
- Files changed: .github/instructions/agent-common.instructions.md
- Change: Added **Command decomposition.** bullet to Terminal discipline section
- Commit: bc2b5c7 (already committed)
- AC (1) Bold-header bullet: PASS
- AC (2) Advises decomposition of complex ops into separate calls: PASS
- AC (3) Rationale: independently reviewable + reduces approval friction: PASS
- AC (4) Clarifies ;-chaining vs decomposition distinction: PASS
- Docs-only task, no .py changes, no tests needed (test-writer pass-through confirmed)

[[2026-03-21]] Sat 02:41
## Review Evidence
## Review: #729 - Add command decomposition guideline to Terminal discipline

### Test Results
- Command: `uv run pytest tests/test_agent_definitions.py -q --tb=short`
- Result: 84 passed, 2 warnings (optional dependency skip warnings from `tests/conftest.py`).
- Scope note: Task is docs-only; there are no task-specific Python behavior changes to test.

### Lint Results
- Task-scoped command: `uv run ruff check .github/instructions/agent-common.instructions.md`
- Result: All checks passed.
- Repo-wide context command: `uv run ruff check src/ tests/`
- Result: 477 errors in unrelated files; outside #729 scope.

### Coverage
- Not applicable: #729 changes only `.github/instructions/agent-common.instructions.md` (no Python modules changed).

### Pass 1 - CRITICAL
#### Security Review
- No security issues found. Change is documentation text only.

#### Test Integrity (TestFromAC comparison)
- N/A. No test files were modified for #729.

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | N/A | Docs-only task; no test changes. |
| Negative/error paths | N/A | Docs-only task; no test changes. |
| Mutation reasoning | N/A | Docs-only task; no test changes. |
| Test independence | N/A | Docs-only task; no test changes. |
| Descriptive names | N/A | Docs-only task; no test changes. |

#### Data Safety
- No data safety issues found. No runtime/data-path code changes.

### Pass 2 - INFORMATIONAL
- Commit `bc2b5c7` includes additional instructions content in the same file; no conflicts with #729 acceptance criteria were found.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| (1) Add new bullet in Terminal discipline using bold-header format | `.github/instructions/agent-common.instructions.md:175` contains `- **Command decomposition.** ...` | N/A (docs-only) | PASS |
| (2) Advise breaking complex multi-step operations into separate terminal calls | `.github/instructions/agent-common.instructions.md:175` includes `Break complex multi-step operations into separate terminal calls rather than long chained pipelines.` | N/A (docs-only) | PASS |
| (3) Include rationale about independent reviewability and reduced approval friction | `.github/instructions/agent-common.instructions.md:175` includes `Each call is independently reviewable and reduces approval friction.` | N/A (docs-only) | PASS |
| (4) Do not contradict `Chain with ;`; clarify decomposition vs chaining scope | `.github/instructions/agent-common.instructions.md:174` preserves `Chain with ';'`; line 175 clarifies `;`-chaining for closely related commands while separating distinct logical steps | N/A (docs-only) | PASS |

### Verdict: PASS
Confidence: .95

[[2026-03-21]] Sat 03:05
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | No Terminal discipline section there |
| 2 | Docstrings | No | N/A | Docs-only task, no .py changes |
| 3 | sources/overview.md | No | N/A | ykdojo attribution already at L1153 from #596 |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | docs/research/claude-code-tips.md exists, linked from #596 |

### Files Updated
- None

### Scratch Files Cleaned
- None found

[[2026-03-21]] Sat 03:05
## Docs Gate

[[2026-03-21]] Sat 03:46
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| (1) Bold-header bullet | L175: `- **Command decomposition.**` matches existing format | PASS |
| (2) Advise decomposition | L175: `Break complex multi-step operations into separate terminal calls` | PASS |
| (3) Rationale | L175: `Each call is independently reviewable and reduces approval friction` | PASS |
| (4) No contradiction with Chain-with-; | L174 preserved; L175 clarifies ;-chaining vs decomposition scope | PASS |

### Test Results
- pytest: 3691 passed, 90 failed (all pre-existing: numpy compat, bootstrap unpacking, CLI refactors), 20 skipped
- ruff: N/A (docs-only, no .py changes)
- Collection errors: test_security_audit_log.py, test_web_extract.py (missing modules, pre-existing)

### Commit Verified
- bc2b5c7: `docs: add command decomposition guideline` -- file committed, no uncommitted changes

### Confidence: .97
### Action: archive
