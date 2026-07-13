---
id: 125
title: 'Clean up askQuestions references: decouple confidence patterns from tool usage'
status: archived
priority: medium
created: 2026-03-29 06:34:47.219217+02:00
updated: 2026-03-29 09:49:39.074765+02:00
started: 2026-03-29 09:49:35.097168+02:00
completed: 2026-03-29 09:49:35.097168+02:00
tags:
- phase-1
- scope:docs
- scope:agents
- type:docs
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Research and scope the askQuestions cleanup: decouple valuable patterns (confidence scores, structured options, (bp:)/(rec:) conventions) from the askQuestions tool reference.

## Acceptance Criteria (research deliverables)

- [x] Research doc delivered at docs/research/askquestions-cleanup-scope.md with file inventory, replacement language matrix, and gap analysis
- [x] Follow-up implementation task #126 created at ideation: behavioral reference rewrites (7 files, ~12 edits)
- [x] Follow-up implementation task #127 created at ideation: new confidence scoring rules for copilot-instructions.md
- [x] Decomposition verified: #126 + #127 fully cover original implementation scope
- [x] YAML tool removal correctly scoped out (handled by #101)
- [x] Research docs (docs/research/*.md) correctly excluded from edit scope (historical records)

## Context

Project decision (2026-03-29): askQuestions is not used in OwlBear. The decision-requests skill is the established async deferral mechanism. See docs/research/vs-code-new-tools-evaluation.md section 4. Related: #101 (revert tool grants).

[[2026-03-29]] Sun 07:24
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Research doc delivered | Verified: docs/research/askquestions-cleanup-scope.md exists with file inventory, replacement matrix, gap analysis | Kept |
| #126 created for behavioral rewrites | Verified: 7 files, ~12 edits, detailed AC with per-file line counts | Kept |
| #127 created for confidence rules | Verified: AC covers new copilot-instructions.md section, references existing threshold table | Kept |
| Decomposition covers original scope | Verified: #126 + #127 map 1:1 to original AC items 1-8 | Kept |
| YAML removal scoped out | Verified: #101 at todo covers YAML tool grants in 3 agent files | Kept |
| Research docs excluded | Correct: 5 research docs are historical records | Kept |

### Architecture Notes
- Research doc file inventory verified by grep: 10 behavioral matches in agent/prompt/instruction files, 12 in SKILL files
- Decomposition is clean: #126 (behavioral text, scope:docs+agents) and #127 (new rules, scope:docs) are single-domain
- #101 overlap correctly identified and excluded from #126 scope
- No TDD required: all deliverables are research artifacts (doc + task creation), not code
- No module layering or security concerns: docs-only task

### Changes Made
- Rewrote task body: replaced implementation-focused AC with research-deliverable AC (all items pre-checked since research is complete)
- Original implementation AC now lives in #126 and #127

### Dependencies
- Verified: #101 (YAML tool removal) at todo, independent of this task
- Downstream: #126 and #127 at ideation, will go through full pipeline independently

[[2026-03-29]] Sun 08:10
## Test-Writer Notes
- Non-implementation task (tagged type:docs, scope:docs, scope:agents) — no tests applicable.
- All AC items are research deliverables (research doc + follow-up tasks), not executable code.
- Architecture review confirms: "No TDD required: all deliverables are research artifacts."
- Passing through to builder.

[[2026-03-29]] Sun 08:40
## Builder Notes
- Non-implementation task â€” no code changes needed.
- All AC items are research deliverables (doc + follow-up tasks), confirmed complete by architect and test-writer.
- Passing through to review.

[[2026-03-29]] Sun 08:51
## Review Evidence

### Task type: Non-implementation (type:docs, scope:docs, scope:agents)

No code changes - steps 3-6 (pytest, ruff, coverage, test integrity) do not apply.
Verification is direct inspection of research deliverables.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| Research doc exists with file inventory + matrix + gap analysis | File confirmed; sections 3.1 (10 files grep-verified), 3.3 (5-entry replacement matrix), 3.4 (confidence scoring gap) | PASS |
| #126 created at ideation (7 files ~12 edits) | Task #126 exists, advanced from ideation; AC matches doc section 3.1 file counts | PASS |
| #127 created at ideation (confidence scoring rules) | Task #127 exists, advanced from ideation; AC covers copilot-instructions.md Process Habits | PASS |
| Decomposition covers original scope | #126 behavioral refs + #127 copilot-instructions.md + #101 YAML = complete coverage | PASS |
| YAML removal scoped to #101 | Research doc sections 3.1/3.2 explicitly exclude kanban-planner/orchestrator/curator YAML | PASS |
| Research docs excluded from edit scope | Research doc section 3.2 Historical docs row + section 5 confirm exclusion | PASS |

### Minor Note

Research doc section 5 heading says 'Task commands executed below' but no commands follow - truncated stub. Does not affect AC compliance since tasks exist.

### Confidence: .94 - Verdict: PASS

[[2026-03-29]] Sun 09:09

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Research-only task; behavioral changes deferred to #126 and #127 |
| 2 | Docstrings | No | N/A | No Python modules changed (type:docs task) |
| 3 | sources/overview.md | No | N/A | Sources are internal OwlBear docs or already in sources/overview.md (VS Code tools, #95) |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | PASS | docs/research/askquestions-cleanup-scope.md exists; #126 and #127 created and active in pipeline |
| 6 | Scratch files | N/A | PASS | No docs/scratch/125-* files found |

### Files Updated

- None

### Scratch Files Cleaned

- None

[[2026-03-29]] Sun 09:49
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Research doc at docs/research/askquestions-cleanup-scope.md | File exists: 77 lines, sections 3.1 (file inventory), 3.3 (replacement matrix), 3.4 (gap analysis) | PASS |
| Follow-up #126 created at ideation | Task #126 exists, currently at docs status (advanced past ideation) | PASS |
| Follow-up #127 created at ideation | Task #127 exists, currently at docs status (advanced past ideation) | PASS |
| Decomposition: #126 + #127 cover original scope | #126 covers 7 files ~12 edits, #127 covers copilot-instructions.md confidence rules | PASS |
| YAML removal scoped out to #101 | Research doc section 3.2 explicitly excludes YAML (handled by #101) | PASS |
| Research docs excluded from edit scope | Research doc section 3.2 Historical docs row confirms exclusion | PASS |

### Test Results
- pytest: 709 passed, 97 failed (all pre-existing from other tasks: disable-model-invocation, rename-todo, setup-script, skill-sync-131, etc.)
- ruff: clean (tests/), pre-existing E902 on src/ (dangling symlink)

### Architect Quality
- AC specificity: All 6 items are concrete and verifiable (file exists, task exists, scope confirmed)
- Edge case coverage: #101 overlap explicitly called out
- Design direction: Architect correctly converted implementation AC to research-deliverable AC
- AC quality score: 4 (adequate, clear decomposition, minor: section 5 stub in research doc)

### Upstream Gap
- Research doc was never committed by researcher or writer. Committed as leftover: ef2defd.

### Confidence: .97
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| ef2defd | docs | docs/research/askquestions-cleanup-scope.md | #125 |
