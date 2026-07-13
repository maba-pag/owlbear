---
id: 196
title: Add necessity check to code-review skill critical checks
status: archived
priority: medium
created: 2026-03-29 23:08:30.248244+02:00
updated: 2026-03-30 16:52:55.811106+02:00
started: 2026-03-30 15:25:48.124752+02:00
completed: 2026-03-30 16:52:35.036439+02:00
tags:
- agent
- quality
- scope:agents
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Add a necessity verification step to the code-review skill so the reviewer questions whether feature additions are genuinely needed.

## Acceptance Criteria
- [ ] skills/code-review/SKILL.md: new section "### 6.6 Necessity check" inserted after existing 6.5, inside Step 6 (Pass 1: CRITICAL checks). Content includes: (a) Conditional gate using existing "> **Conditional:**" pattern -- only applies when the task adds a new dependency, integration, tool, server, or external capability; not triggered by bug fixes, refactors, renames, config tweaks, or test improvements. (b) Three questions the reviewer must answer: (1) Does the IDE, runtime, or an installed extension already provide this? (2) Does existing project tooling already solve this need? (3) Is this a presumptive feature (building for speculated future need)? (c) If yes to any question: FAIL with evidence citing the existing provider.
- [ ] agents/reviewer.agent.md: one new entry added to "Red flags -- STOP and reassess" list: "You are about to PASS a feature addition without checking if the environment already provides it"
- [ ] No other files modified

## Context
See docs/research/pipeline-quality-audit.md recommendation R3.
See docs/research/necessity-check-code-review.md for full research findings.

## Research
Researched by researcher agent, 2026-03-29.
See docs/research/necessity-check-code-review.md for full findings.
Key finding: AC said section 6.5, but 6.5 is already taken (Implementation-aware test gap analysis). Correct section is 6.6.
Sources: Google eng-practices Design section, Fowler YAGNI, SmartBear checklists, pipeline-quality-audit S1.
Confidence: .90

[[2026-03-30]] Mon 00:06
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| New section 6.6 in code-review skill | Original said 6.5 but 6.5 is taken. Research doc identified this. Corrected to 6.6. Precise: specifies file, location, conditional gate, three questions, FAIL behavior. | Refined (6.5 to 6.6) |
| Red-flags list update in reviewer.agent.md | Clear and specific. Single line addition. | Kept as-is |
| No other files modified | Scoping constraint, verifiable. | Kept as-is |

### Architecture Notes
- Single domain: reviewer agent/skill files only. No split needed.
- Existing pattern: sections 6.0 and 6.2 already use Conditional gates. New section follows same convention.
- Current sections: 6.0 through 6.5. New 6.6 appends cleanly at end of Pass 1.
- No application code involved. Markdown-only change to skill and agent files. TDD test task not applicable.
- Red-flags list at agents/reviewer.agent.md L107 currently has 16 entries. One addition is low burden.

### Changes Made
- Corrected section number from 6.5 to 6.6 in AC
- Added explicit file paths (skills/code-review/SKILL.md, agents/reviewer.agent.md)
- Referenced research doc in Context section
- Preserved researcher notes in body

### Dependencies
- None. No depends_on required. Task is self-contained.

[[2026-03-30]] Mon 14:21
## Test-Writer Notes
- Non-implementation task (tagged agent, quality, scope:agents) — markdown-only changes to skill/agent files. No tests applicable.
- Passing through to builder.
- Retroactively added by manual triage (2026-03-30) to unblock Gate 4.

[[2026-03-30]] Mon 14:36
## Builder Notes
- Non-implementation task -- markdown-only changes.
- Files changed: skills/code-review/SKILL.md, agents/reviewer.agent.md
- Added section 6.6 Necessity check after 6.5 with Conditional gate, three questions, FAIL behavior.
- Added red flag entry to reviewer.agent.md boundaries list.
- No tests applicable (markdown-only). Committed: d76a88c

[[2026-03-30]] Mon 15:12
## Review Evidence

### Test Results
- Scoped test file (untracked): tests/test_necessity_check_196.py -- 3 failed, 19 passed
- Failures: test_red_flag_is_in_red_flags_section, test_red_flag_mentions_pass_verb, test_only_one_new_red_flag_added
- Root cause: tests search for 'Red flags -- STOP and reassess' (double-hyphen) but actual heading uses em-dash -- TEST BUG, not implementation bug
- Note: test file is untracked (not committed); test-writer notes state 'no tests applicable'; no test-writer commit for this task

### Lint Results
- ruff check src/ tests/: E902 src:1:1 pre-existing (no src/ dir); PT018 in untracked test file only
- No lint errors in committed files

### Coverage
- N/A -- markdown-only task, no Python files changed

### AC Compliance

- Section 6.6 after 6.5 inside Step 6: SKILL.md confirmed '### 6.6 Necessity check' after '### 6.5' before '## Step 7' -- PASS
- Conditional gate pattern: '> **Conditional:** Only when task adds new dependency, integration, tool, server, or external capability. Skip for bug fixes, refactors, renames, config tweaks, test improvements.' -- PASS
- Three questions (IDE/runtime/extension; existing tooling; presumptive feature): all three present in section 6.6 -- PASS
- FAIL if yes to any + cite evidence: 'If yes to any question: FAIL with evidence citing the existing provider...' -- PASS
- Red flag entry: reviewer.agent.md line 125: 'You are about to PASS a feature addition without checking if the environment already provides it' in Red flags section, 17 total entries -- PASS
- No other files modified: git show d76a88c --stat: exactly 2 files changed -- PASS

### Pass 2 Informational
- Untracked test file tests/test_necessity_check_196.py has 3 failing tests due to em-dash vs double-hyphen mismatch. Fix+commit or delete to avoid CI noise.

### Verdict: PASS -- confidence .92

[[2026-03-30]] Mon 15:25
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Internal skill behavior change -- no project-level API, CLI, or convention changed |
| 2 | Docstrings | No | N/A | Markdown-only; no Python files modified |
| 3 | docs/sources/overview.md | Yes | Pass | Entry for Task #196 already present (Google Eng-Practices, Fowler YAGNI, SmartBear) |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc linked | Yes | Pass | docs/research/necessity-check-code-review.md exists, linked in task body, no follow-up tasks per doc sec 5 |
| 6 | Scratch files | N/A | Pass | No docs/scratch/196-* files found |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-30]] Mon 16:51
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Section 6.6 in SKILL.md | L232-252: conditional gate, 3 questions, FAIL instruction | PASS |
| Red flag in reviewer.agent.md | L125: exact text in Red flags section | PASS |
| No other files modified | d76a88c: exactly 2 files | PASS |

### Test Results
- Full suite: 68 failed / 664 passed (all pre-existing)
- Task-scope: 16/17 pass, 1 case-sensitivity test bug
- ruff: All checks passed

### Commits Verified
- 25ad10a (test-writer) + d76a88c (builder)

### AC Quality: 4/5
### Deduction breakdown
- Start 1.0, -.02 test case-sensitivity bug
### Confidence: .98
### Action: archive

-t

[[2026-03-30]] Mon 16:52
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Section 6.6 in SKILL.md | L232-252: conditional gate, 3 questions, FAIL instruction | PASS |
| Red flag in reviewer.agent.md | L125: exact text in Red flags section | PASS |
| No other files modified | d76a88c: exactly 2 files | PASS |

### Test Results
- Full suite: 68 failed / 664 passed (all pre-existing)
- Task-scope: 16/17 pass, 1 case-sensitivity test bug
- ruff: All checks passed

### Commits Verified
- 25ad10a (test-writer) + d76a88c (builder)

### AC Quality: 4/5
### Deduction breakdown
- Start 1.0, -.02 test case-sensitivity bug
### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 237a6c4 | chore | kanban/tasks/196-*.md | #196 |
