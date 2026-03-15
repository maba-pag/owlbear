---
id: 538
title: Evaluate declarative tool registration for toolsets
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:43.2377201+01:00
updated: 2026-03-15T09:23:36.9484266+01:00
started: 2026-03-07T00:36:38.943944+01:00
completed: 2026-03-15T09:23:33.1090807+01:00
tags:
    - audit
    - yagni
    - tools
class: standard
---

YAGNI-01 evaluation complete. Decision: DEFER. The _register_tools ceremony is harmless -- no bugs, consistent pattern, PydanticAI native API. Building a custom declarative layer (decorator or ClassVar) would add 30-80 LOC of framework code to save ~3 LOC per toolset, violating KISS/YAGNI. If PydanticAI adds class-level declarative registration, adopt it then. See docs/research/declarative-tool-registration.md.

## AC

- [x] Decision documented: DEFER

[[2026-03-15]] Sun 07:36
## Architecture Review
Verdict: APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Decision documented: DEFER | Research doc complete at docs/research/declarative-tool-registration.md. DEFER decision well-justified by KISS/YAGNI. | Accept as-is |

### Architecture Notes
Research confirms all 14 FunctionToolset subclasses follow identical _register_tools pattern (49 add_function calls). Pattern uses PydanticAI native API, causes zero bugs, is consistent and transparent. DEFER is the correct decision -- building a custom declarative layer would add 30-80 LOC of framework to save ~3 LOC per toolset, violating both KISS and YAGNI. No implementation follow-ups needed.

### Changes Made
- Moved to todo

### Dependencies
- None

[[2026-03-15]] Sun 07:40
## Test-Writer Notes
- Non-implementation task (tagged: audit, yagni, tools)
- AC is 'Decision documented: DEFER' -- research/evaluation only, no testable code produced
- No tests applicable. Passing through to builder.

[[2026-03-15]] Sun 07:48
## Builder Notes\n- Non-implementation task -- no code changes needed.\n- AC 'Decision documented: DEFER' already complete (docs/research/declarative-tool-registration.md exists).\n- Passing through to review.

[[2026-03-15]] Sun 08:18
## Review Evidence
Test/Lint/Coverage: N/A (non-implementation research task, no code produced)

### Pass 1 - CRITICAL
Security: No code changes. Test Integrity: N/A. Test Quality: N/A. Data Safety: N/A.

### Pass 2 - INFORMATIONAL
Research doc well-structured: 4 sources, 3 options evaluated, cost-benefit table, DEFER justified by KISS/YAGNI at .90 confidence.

### AC Compliance
Decision documented DEFER: docs/research/declarative-tool-registration.md Section 4 states Defer as YAGNI (.90 confidence) -> PASS

### Verdict: PASS
### Confidence: .95

[[2026-03-15]] Sun 08:51
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Research/evaluation task, decision=DEFER, no behavior or API change |
| 2 | Docstrings complete | No | N/A | No Python modules created or modified |
| 3 | sources/overview.md | No | N/A | External sources studied for evaluation only, nothing adopted (DEFER) |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/declarative-tool-registration.md exists, linked in task body |
| 6 | No impact | -- | -- | Items 1-4 N/A, item 5 pass. No docs changes needed. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/538-* files found)

[[2026-03-15]] Sun 08:52
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Research/eval task, decision=DEFER, no behavior/API change |
| 2 | Docstrings complete | No | N/A | No Python modules created or modified |
| 3 | sources/overview.md | No | N/A | Sources studied for eval only, nothing adopted |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/declarative-tool-registration.md exists |
| 6 | No impact | -- | -- | Items 1-4 N/A, item 5 pass |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-15]] Sun 09:23
## Audit (2026-03-15)
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Decision documented: DEFER | docs/research/declarative-tool-registration.md Section 4: Defer as YAGNI (.90 confidence) | PASS |

### Research Task Verification
- Research doc exists: docs/research/declarative-tool-registration.md (committed 42ff2c6)
- Follow-up tasks: Section 5 states No implementation tasks needed with clear KISS/YAGNI justification
- Doc quality: 4 sources, 3 options evaluated, cost-benefit matrix, explicit recommendation

### Test Results
- N/A (non-implementation research task, no code produced)
- Ruff: N/A

### Confidence: .97
### Action: archive
