---
id: 554
title: Replace brittle prompt substring assertions with semantic checks
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:56.8370984+01:00
updated: 2026-03-15T05:40:41.2150888+01:00
started: 2026-03-07T01:05:38.6153764+01:00
completed: 2026-03-15T05:40:36.8143486+01:00
tags:
    - audit
    - test
class: standard
---

M1: Tests assert exact substrings in agent system prompts. Any prompt rewording breaks them. Better: test for tool names in tool list, or use regex for semantic intent. See docs/test-quality-audit.md.

Research complete -- see docs/research/brittle-prompt-assertions.md. Findings: 30+ prompt assertions across 8 test files; only 2 files need changes (test_kanban_pipeline.py, test_source_evaluator.py). Follow-up: 2 implementation tasks.

## AC

- [x] Research doc at docs/research/brittle-prompt-assertions.md
- [x] Audited 30+ prompt assertions across 8 test files
- [x] Identified 2 files needing changes (test_kanban_pipeline.py, test_source_evaluator.py)
- [x] Follow-up implementation tasks created

[[2026-03-14]] Sat 21:06
## Architecture Review
Verdict: APPROVED

### AC Assessment
- AC1 (Research doc): Verified
- AC2 (Audited 30+ assertions): Verified
- AC3 (2 files identified): Verified
- AC4 (Follow-up tasks created): Fixed - created #810 and #811

### Architecture Notes
- defn.tools metadata checks over substring checks (follows test_agent_definitions.py pattern)
- AgentDefinition.tools list[str] confirmed in agent_def.py
- SAMPLE_PROJECT_CONTEXT is dict - follow-ups use bracket access
- Tests pass 6/6 but brittleness risk remains

### Changes Made
- Created #810: test_kanban_pipeline.py refactoring (backlog)
- Created #811: test_source_evaluator.py refactoring (backlog)

[[2026-03-15]] Sun 04:01
## Test-Writer Notes
- Non-implementation task (tagged audit/test) — research/audit with all AC delivered.
- No testable code produced. Follow-ups #810 and #811 will have their own test phases.
- Passing through to builder.

[[2026-03-15]] Sun 04:26
## Builder Notes
- Non-implementation task -- no code changes needed.
- All AC items verified complete (research doc, audit, follow-ups #810 #811).
- Passing through to review.

[[2026-03-15]] Sun 04:37
## Docs Gate
Checklist:

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Pass | Errors row already present at L55 with OwlBearError root exception, MI pattern, module path |
| 2 | Docstrings complete | Yes | Pass | core/exceptions.py: module + class docstring. BlockedCommandError, BlockedURLError, AskUserTimeoutError all have docstrings |
| 3 | sources/overview.md | Yes | Pass | Section 'Exception Hierarchy Research (Task #539)' present with 4 sources (httpx, requests, click, django) |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/exception-hierarchy.md exists, linked from exceptions.py docstring and copilot-instructions.md |
| 6 | No impact | N/A | N/A | Items 1-3,5 apply |

Files Updated: None (all docs already current)
Scratch Files Cleaned: None found (docs/scratch/539-* empty)

-t

[[2026-03-15]] Sun 05:06
## Docs Gate (Writer, 2026-03-15)
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Pure research/audit task -- no behavior, API, or convention change |
| 2 | Docstrings complete | No | N/A | No Python modules created or modified |
| 3 | sources/overview.md | Yes | Pass | 3 entries already present (PydanticAI, CheckList, Eugene Yan) at L366-368 |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/brittle-prompt-assertions.md exists; follow-ups #810 #811 created |
| 6 | No impact | N/A | N/A | Items 3 and 5 apply and pass |

### Files Updated
- None

### Scratch Files Cleaned
- None found

[[2026-03-15]] Sun 05:40
## Audit (2026-03-15)
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Research doc | docs/research/brittle-prompt-assertions.md committed (42ff2c6), 6 sections | PASS |
| 30+ assertions across 8 files | Section 3.1 inventory table: 8 files, 30+ assertions | PASS |
| 2 files needing changes | Section 3.1: kanban_pipeline (HIGH), source_evaluator (MEDIUM) | PASS |
| Follow-up tasks created | #810 (review), #811 (in-progress), both ref research doc | PASS |

### Research Task Checklist
- Doc exists + substantive: PASS
- Follow-ups on board: #810, #811 PASS
- Follow-ups link research doc: PASS
- Sources attributed (L366-368): PASS

### Test Results
- pytest (task scope): 139 passed
- pytest (broader core): 218 passed
- ruff: 2 pre-existing screenshot.py errors (unrelated)

### Confidence: .97
### Action: archive
