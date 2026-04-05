---
id: 573
title: Clarify README prerequisites and corporate environment constraints
status: archived
priority: someday
created: 2026-03-04T07:39:15.2924485+01:00
updated: 2026-03-21T16:09:31.7518177+01:00
started: 2026-03-07T04:53:04.5373163+01:00
completed: 2026-03-21T16:08:52.6887386+01:00
tags:
    - audit
    - docs
class: standard
---

DOC-F-05: The README already contains a Prerequisites section, so the remaining audit gap is to document the supported environment constraints precisely and without adding unsupported compatibility claims. Sources: docs/documentation-audit.md and docs/research/browser-automation.md.

## AC

- [ ] README's `Prerequisites` section explicitly states `Python >= 3.12` and `uv` as the supported local-development toolchain.
- [ ] README's `Prerequisites` section explicitly states platform support: Windows is the primary development OS; Linux and macOS are expected to work but remain untested.
- [ ] README adds a brief environment-constraints note, backed by docs/research/browser-automation.md, that browser automation is designed for corporate Windows laptops by attaching to an existing Edge session over CDP instead of requiring admin rights, browser extensions, or a separate unmanaged browser install.
- [ ] README does not add broader hardware or cross-platform support claims that are not already supported elsewhere in the repository.

## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| README has a Prerequisites/Requirements section | Already satisfied by README.md; the original task wording is stale relative to the current repository state. | Rewrote the task around the remaining documentation gap. |
| Mentions Python 3.12+ | Already satisfied by README.md. | Kept as an explicit contract requirement. |
| Mentions uv package manager | Already satisfied by README.md. | Kept as an explicit contract requirement. |
| Notes corporate laptop constraints if relevant | Conditional wording is vague. The repository only gives concrete evidence for browser-automation constraints on corporate Windows laptops in docs/research/browser-automation.md. | Rewrote as a narrow, repo-backed environment-constraints requirement. |

### Architecture Notes
- README.md already contains the prerequisites section introduced in commit 504c0b01 on 2026-03-15, so this task entered architect review partially complete.
- The remaining actionable delta from docs/documentation-audit.md is to document environment constraints truthfully, without inventing broader hardware or compatibility guarantees.
- Single domain: documentation only. No module-layering, dependency-injection, or interface-design concerns.
- TDD gate: not applicable because this task changes README content only.
- Failure mode map: N/A (documentation-only).

### Changes Made
- Claimed #573 as architect.
- Renamed the task to match the remaining scope.
- Replaced the stale AC with precise, verifiable README requirements.
- Approved the task for todo after refinement.

### Dependencies
- Added/Removed/Verified: none.
- Verified no preceding RED task is required because the task is documentation-only.

[[2026-03-21]] Sat 06:55
## Test-Writer Notes
Non-implementation task (tagged: docs). Architecture review explicitly states TDD gate is not applicable — this task modifies README.md content only. No testable code is produced. Passing through to builder.

[[2026-03-21]] Sat 12:34
## Builder Notes
- Files changed: README.md (+5 lines)
- No code changes — documentation-only task (TDD gate: N/A per architect review)
- AC1: Python >= 3.12 and uv already present in Prerequisites — verified
- AC2: Windows primary, Linux/macOS expected but untested — already present
- AC3: Added blockquote note about CDP attach, no-admin, no-extensions, no separate browser install, with link to docs/research/browser-automation.md
- AC4: No broader platform claims introduced
- Lint: ruff N/A (markdown only); pre-existing MD013 on line 72 (Slack section, untouched)
- Commit: a228249

[[2026-03-21]] Sat 14:10
## Review Evidence
## Review: #573 - Clarify README prerequisites and corporate environment constraints

### Test Results
- pytest (independent): subprocess-captured run against tests/test_project_workspace.py with readme filter
- Result: 1 passed, 32 deselected, 2 warnings, EXIT_CODE=0
- Tooling note: direct pytest CLI attempts hit KeyboardInterrupt during plugin or atexit handling; subprocess capture produced stable output.

### Lint Results
- ruff command: uv run ruff check src/ tests/
- Result: exit code 1 due pre-existing unrelated lint debt (example files: [tests/test_slack_sender_validation.py](tests/test_slack_sender_validation.py#L19), [tests/test_soft_fail_exit.py](tests/test_soft_fail_exit.py#L50), [tests/test_terminal_tools.py](tests/test_terminal_tools.py#L382)).
- Scope check: commit a228249 changed only README.md (+5 lines).

### Coverage
- Not applicable (documentation-only task; no Python source changes).

### Pass 1 - CRITICAL

#### Security Review
- No hardcoded secrets introduced.
- No injection, path traversal, deserialization, or command-execution surface changed (markdown-only edit).
- No dependency changes.

#### Test Integrity (TestFromAC comparison)
- Not applicable: no test files changed and no TestFromAC classes were modified by this task.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | N/A | Documentation-only task; no executable behavior added |
| Negative or error paths | N/A | Documentation-only task; no runtime path changed |
| Mutation reasoning | N/A | No implementation logic changed |
| Test independence | N/A | No new tests in task scope |
| Descriptive names | N/A | No new tests in task scope |

#### Data Safety
- No data safety risks introduced (no persistence, concurrency, or input-processing code changes).

### Pass 2 - INFORMATIONAL
- rg was unavailable in this shell; used PowerShell Select-String fallback for line-number evidence.
- Repo-wide ruff failures appear unrelated to this docs-only task and predate this change.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Prerequisites explicitly state Python >= 3.12 and uv | [README.md](README.md#L14), [README.md](README.md#L15) | N/A (documentation acceptance criterion) | PASS |
| Prerequisites explicitly state Windows primary; Linux or macOS expected but untested | [README.md](README.md#L16) | N/A (documentation acceptance criterion) | PASS |
| README adds environment-constraints note backed by browser automation research doc (CDP attach, no admin rights, no extensions, no separate unmanaged install) | [README.md](README.md#L18), [README.md](README.md#L19), [README.md](README.md#L20), [README.md](README.md#L21), [docs/research/browser-automation.md](docs/research/browser-automation.md#L18), [docs/research/browser-automation.md](docs/research/browser-automation.md#L19), [docs/research/browser-automation.md](docs/research/browser-automation.md#L20), [docs/research/browser-automation.md](docs/research/browser-automation.md#L22) | N/A (documentation acceptance criterion) | PASS |
| No broader unsupported hardware or cross-platform claims added | git show --stat --oneline a228249 shows one changed file (README.md, +5 lines); git show a228249 -- README.md shows only constrained browser note addition and no broader support claims | N/A (negative diff validation) | PASS |

### Verdict: PASS (confidence .93)

### Action Taken
- Pending status move: review to docs

[[2026-03-21]] Sat 14:10
## Review Evidence
## Review: #573 - Clarify README prerequisites and corporate environment constraints

### Test Results
- pytest (independent): subprocess-captured run against tests/test_project_workspace.py with readme filter
- Result: 1 passed, 32 deselected, 2 warnings, EXIT_CODE=0
- Tooling note: direct pytest CLI attempts hit KeyboardInterrupt during plugin or atexit handling; subprocess capture produced stable output.

### Lint Results
- ruff command: uv run ruff check src/ tests/
- Result: exit code 1 due pre-existing unrelated lint debt (example files: [tests/test_slack_sender_validation.py](tests/test_slack_sender_validation.py#L19), [tests/test_soft_fail_exit.py](tests/test_soft_fail_exit.py#L50), [tests/test_terminal_tools.py](tests/test_terminal_tools.py#L382)).
- Scope check: commit a228249 changed only README.md (+5 lines).

### Coverage
- Not applicable (documentation-only task; no Python source changes).

### Pass 1 - CRITICAL

#### Security Review
- No hardcoded secrets introduced.
- No injection, path traversal, deserialization, or command-execution surface changed (markdown-only edit).
- No dependency changes.

#### Test Integrity (TestFromAC comparison)
- Not applicable: no test files changed and no TestFromAC classes were modified by this task.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | N/A | Documentation-only task; no executable behavior added |
| Negative or error paths | N/A | Documentation-only task; no runtime path changed |
| Mutation reasoning | N/A | No implementation logic changed |
| Test independence | N/A | No new tests in task scope |
| Descriptive names | N/A | No new tests in task scope |

#### Data Safety
- No data safety risks introduced (no persistence, concurrency, or input-processing code changes).

### Pass 2 - INFORMATIONAL
- rg was unavailable in this shell; used PowerShell Select-String fallback for line-number evidence.
- Repo-wide ruff failures appear unrelated to this docs-only task and predate this change.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Prerequisites explicitly state Python >= 3.12 and uv | [README.md](README.md#L14), [README.md](README.md#L15) | N/A (documentation acceptance criterion) | PASS |
| Prerequisites explicitly state Windows primary; Linux or macOS expected but untested | [README.md](README.md#L16) | N/A (documentation acceptance criterion) | PASS |
| README adds environment-constraints note backed by browser automation research doc (CDP attach, no admin rights, no extensions, no separate unmanaged install) | [README.md](README.md#L18), [README.md](README.md#L19), [README.md](README.md#L20), [README.md](README.md#L21), [docs/research/browser-automation.md](docs/research/browser-automation.md#L18), [docs/research/browser-automation.md](docs/research/browser-automation.md#L19), [docs/research/browser-automation.md](docs/research/browser-automation.md#L20), [docs/research/browser-automation.md](docs/research/browser-automation.md#L22) | N/A (documentation acceptance criterion) | PASS |
| No broader unsupported hardware or cross-platform claims added | git show --stat --oneline a228249 shows one changed file (README.md, +5 lines); git show a228249 -- README.md shows only constrained browser note addition and no broader support claims | N/A (negative diff validation) | PASS |

### Verdict: PASS (confidence .93)

### Action Taken
- Pending status move: review to docs

[[2026-03-21]] Sat 14:50
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Documentation-only task; no behavior/API/convention change. Tech stack Browser row already correct (CDP localhost only). |
| 2 | Docstrings complete | No | N/A | Builder confirmed commit a228249 changed only README.md (+5 lines). No Python source changes. |
| 3 | sources/overview.md | No | N/A | Relied on existing docs/research/browser-automation.md; CDP/browser attribution already present in sources/overview.md. No new external sources. |
| 4 | README.md | Yes | Pass | Lines 14-21 verified: Python >=3.12 and uv (AC1), Windows primary/Linux+macOS untested (AC2), CDP attach blockquote with no-admin/no-extensions/no-separate-install + research link (AC3), no broader claims (AC4). |
| 5 | Research doc linked | Yes | Pass | docs/research/browser-automation.md exists and linked from README. No follow-up tasks required. |
| 6 | No impact default | N/A | N/A | Items 1-5 evaluated with evidence above. |

### Files Updated
- None (README.md already updated by builder in commit a228249)

### Scratch Files Cleaned
- None (no docs/scratch/573-* files found)

[[2026-03-21]] Sat 16:08
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Python >= 3.12 and uv in Prerequisites | README.md L14-15 | PASS |
| Windows primary; Linux/macOS untested | README.md L16 | PASS |
| CDP environment-constraints note backed by research doc | README.md L18-21, links docs/research/browser-automation.md | PASS |
| No broader unsupported claims | Commit a228249: +5 lines, narrowly scoped | PASS |

### Test Results
- pytest: 3723 passed, 97 failed (all pre-existing: numpy version, bootstrap signature, unrelated tasks), 20 skipped. No regressions from #573.
- ruff: All checks passed on README.md

### Confidence: .97
### Action: archive

[[2026-03-21]] Sat 16:09
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 98c9ff6 | chore | kanban/tasks/573-* | #573 |
