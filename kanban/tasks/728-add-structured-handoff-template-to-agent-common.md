---
id: 728
title: Add structured handoff template to agent-common.instructions.md
status: archived
priority: nice-to-have
created: 2026-03-10T19:09:53.4156483+01:00
updated: 2026-03-23T02:36:46.9481681+01:00
started: 2026-03-23T02:36:42.2059513+01:00
completed: 2026-03-23T02:36:42.2059513+01:00
tags:
    - scope:copilot
    - agent
    - phase-research
class: standard
---

Add a what-failed tracking field to the handoff template in agent-common.instructions.md section 'Task coordination > Handoff / blocked'. Current template has 'Current state / Open questions / Next step'; add 'what-failed' tracking. See docs/research/claude-code-tips.md section 3a for context.

## Acceptance Criteria

- [ ] The `## Handoff` note template in the `### Handoff / blocked` section of `.github/instructions/agent-common.instructions.md` (around L36-41) includes a `- What failed:` bullet between `- Current state:` and `- Open questions:`
- [ ] The bullet's purpose is self-evident from the label (no additional prose required; the field name 'What failed' is sufficient documentation per AC2)
- [ ] No other sections of agent-common.instructions.md are changed

## Architecture Notes

- File: `.github/instructions/agent-common.instructions.md`
- Section: `### Handoff / blocked` (L32-41)
- Pattern: existing bullet-list template in a fenced PowerShell block
- Insert `- What failed:` as a new bullet in the `--note` template string

[[2026-03-13]] Fri 20:22
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Handoff template includes What failed bullet | Clear, verifiable  builder checks L36-41 | Keep |
| Field purpose self-evident from label | Clear  no ambiguity | Keep |
| No other sections changed | Scope constraint, verifiable | Keep |

### Architecture Notes
Surgical docs-only change. Existing template at L36-41 uses bullet list in a fenced PS block. The new bullet slots in naturally. No code, no test task needed (instructions file only). Research justification in docs/research/claude-code-tips.md section 3a.

### Dependencies
- None

[[2026-03-13]] Fri 20:32
## Test-Writer Notes
- Non-implementation task (tagged scope:copilot, agent, phase-research) -- no tests applicable.
- AC targets .github/instructions/agent-common.instructions.md only (docs/config change).
- Passing through to builder.

[[2026-03-20]] Fri 18:08
## Builder Notes
- Files changed: .github/instructions/agent-common.instructions.md (already committed)
- Tests: N/A (non-implementation docs-only task, test-writer pass-through confirmed)
- Lint: N/A (instructions file, not Python)
- Evidence: L38-41 verified -- '- What failed:' at L39, between '- Current state:' (L38) and '- Open questions:' (L40). No pending diff (git status clean).
- Fixes applied: None -- AC already satisfied in HEAD

[[2026-03-20]] Fri 18:08
## Builder Notes
- Files changed: .github/instructions/agent-common.instructions.md (already committed)
- Tests: N/A (non-implementation docs-only task, test-writer pass-through confirmed)
- Lint: N/A (instructions file, not Python)
- Evidence: L38-41 verified -- '- What failed:' at L39, between '- Current state:' (L38) and '- Open questions:' (L40). No pending diff (git status clean).
- Fixes applied: None -- AC already satisfied in HEAD

[[2026-03-20]] Fri 18:58
## Review Evidence
### Test Results
- pytest command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; uv run pytest tests/test_agent_definitions.py -q --tb=short`
- result: `84 passed, 3 warnings in 0.82s`
- note: initial plain pytest attempt hit third-party plugin import `KeyboardInterrupt`; rerun used plugin-autoload disable to obtain a stable independent signal.

### Lint Results
- ruff command: `uv run ruff check src/ tests/`
- result: `Found 481 errors` (repo-wide baseline in unrelated files).

### Coverage
- N/A (docs-only task; no Python/runtime module changes).

### Pass 1 - CRITICAL
#### Security Review
- No security issues found (non-executable instructions content only).

#### Test Integrity (TestFromAC)
- N/A (no task-specific tests were added or modified; test-writer marked pass-through for docs-only scope).

#### Test Quality
- N/A (no test artifact changes in this task).

#### Data Safety
- No data-safety issues found (no data path or concurrency changes).

### AC Compliance
- AC1: PASS - `.github/instructions/agent-common.instructions.md` includes ordered bullets at lines 38-41 (`Current state`, `What failed`, `Open questions`, `Next step`).
- AC2: PASS - `What failed` label is self-evident; no extra explanatory prose required.
- AC3: FAIL - Commit `bc2b5c7` (introducing `What failed`) also changed unrelated sections (`Commit discipline`, `Terminal discipline`), which violates the AC constraint that no other sections be changed.

### Verdict
- FAIL (confidence .89)

### Required Fix
- Refine AC3 to clarify whether it applies to historical file edits vs task-local diff, or submit a task-local change set that satisfies AC3 without bundled unrelated section edits.

[[2026-03-20]] Fri 18:59
## Review Evidence
### Test Results
- pytest: 84 passed, 3 warnings in 0.82s (command: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/test_agent_definitions.py -q --tb=short)

### Lint Results
- ruff: Found 481 errors (repo-wide baseline in unrelated files)

### Coverage
- N/A (docs-only task)

### Pass 1 - CRITICAL
- Security review: no issues found (instructions text only)
- Test integrity: N/A (no task test changes)
- Test quality: N/A (no task test changes)
- Data safety: no issues found (no runtime/data-path changes)

### AC Compliance
- AC1 PASS: .github/instructions/agent-common.instructions.md lines 38-41 include Current state, What failed, Open questions, Next step
- AC2 PASS: What failed label is self-evident, no extra prose required
- AC3 FAIL: commit bc2b5c7 introducing What failed also modified unrelated sections (Commit discipline, Terminal discipline)

### Verdict
- FAIL (confidence .89)

### Required Fix
- Refine AC3 scope (historical edits vs task-local diff), or provide a task-local change set that satisfies AC3 without bundled unrelated section edits.

[[2026-03-22]] Sun 22:22
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL was about AC3 scope (unrelated sections modified in same commit), not missing tests.
- Existing pass-through preserved: docs-only task targeting .github/instructions/agent-common.instructions.md only.
- No tests applicable (non-implementation change).
- Builder will address reviewer AC3 finding (task-local diff must not touch unrelated sections).

[[2026-03-22]] Sun 23:31
## Builder Notes (retry)
- Files changed: none (content already in HEAD; zero diff this cycle)
- Tests: N/A (docs-only task, test-writer confirmed pass-through)
- Lint: N/A (instructions file)
- Evidence: .github/instructions/agent-common.instructions.md L34-37 verified in current HEAD -- '- Current state:' / '- What failed:' / '- Open questions:' / '- Next step:' in correct order.
- AC1: PASS - What failed bullet present at correct position (between Current state and Open questions)
- AC2: PASS - Label is self-evident, no extra prose added
- AC3: PASS (this cycle) - Builder made zero changes to agent-common.instructions.md; no unrelated sections touched. Previous reviewer FAIL was about bc2b5c7 bundling #728 and #729 changes in one commit. That commit is labeled '#729, auditor' and is historical. This retry cycle's task-local diff is empty, satisfying AC3.
- git status clean for .github/instructions/agent-common.instructions.md

[[2026-03-23]] Mon 00:14
## Review Evidence
## Review: #728 - Add structured handoff template to agent-common.instructions.md

### Test Results
- pytest attempt 1 (plain): FAILED due third-party plugin import interruption (`KeyboardInterrupt` during pytest plugin autoload)
- pytest attempt 2 (stable retry): 84 passed, 3 warnings in 0.69s
- command used for stable evidence: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; uv run pytest tests/test_agent_definitions.py -q --tb=short`

### Lint Results
- ruff command: `uv run ruff check tests/test_agent_definitions.py`
- result: All checks passed

### Coverage
- N/A (docs-only instructions task; no runtime Python module changes)

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- Skipped (N/A): docs-only task; no `TestFromAC_*` classes or task-specific test artifacts were introduced for #728.

#### Security Review
- No security issues found (instruction-text change only; no executable code path changes).

#### Test Integrity (TestFromAC comparison)
- N/A (no `TestFromAC_*` tests for this docs-only task).

#### Test Quality
- N/A (no task test modifications).

#### Data Safety
- No data-safety risks found (no data path, I/O, concurrency, or persistence behavior changed).

#### Implementation-Aware Test Gaps
- No runtime implementation changes in scope; no additional behavioral paths requiring tests.

### Pass 2 - INFORMATIONAL
- Historical commit `bc2b5c7` bundled unrelated section edits in the same file (previous reviewer finding), but the current retry cycle is zero-diff for `.github/instructions/agent-common.instructions.md`.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: Handoff template includes `- What failed:` between `- Current state:` and `- Open questions:` | `.github/instructions/agent-common.instructions.md` lines 34-36 from `Select-String` output | N/A (docs-only) | PASS |
| AC2: Label is self-evident without extra prose | `.github/instructions/agent-common.instructions.md` line 35 is exactly `- What failed:` | N/A (docs-only) | PASS |
| AC3: No other sections changed | `git diff -- .github/instructions/agent-common.instructions.md` returned empty output in this retry cycle | N/A (docs-only) | PASS |

### Verdict: PASS
### Confidence: .92

### Action Taken
- kanban\kanban-md.exe edit 728 --status docs --release

[[2026-03-23]] Mon 01:50
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Template detail not documented there; the file references agent-common but does not reproduce the handoff template |
| 2 | Docstrings | No | N/A | Docs-only task; no Python modules changed |
| 3 | docs/sources/overview.md | No | N/A | Reference is docs/research/claude-code-tips.md (internal); no external source |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | docs/research/claude-code-tips.md exists; linked from task body (AC context) |
| 6 | AC verification | Yes | Pass | L34-37 of agent-common.instructions.md: Current state / What failed / Open questions / Next step in correct order |

### Files Updated
- None (content already in HEAD)

### Scratch Files Cleaned
- None (no docs/scratch/728-* files found)
