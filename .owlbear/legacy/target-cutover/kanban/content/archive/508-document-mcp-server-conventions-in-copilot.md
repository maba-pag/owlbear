---
id: 508
title: Document MCP server conventions in copilot-instructions.md
status: archived
priority: medium
created: 2026-03-31 23:41:06.504902+02:00
updated: 2026-04-01 17:50:31.189334+02:00
started: 2026-04-01 17:50:30.631594+02:00
completed: 2026-04-01 17:50:30.631594+02:00
tags:
- scope:mcp
- ' type:docs'
- ' phase-2'
depends_on:
- 506
- 507
class: standard
archival_reason: completed
archival_refs: []
---

## AC
- [ ] Add `## MCP Server Conventions` section to `.github/copilot-instructions.md` covering:
  - Error prefix: all tool execution errors start with `error: ` (empty-result messages like "No sources found." are informational, not errors)
  - Tool annotations: `readOnlyHint`, `idempotentHint`, `destructiveHint` on every tool (reference: mcp-kanban)
  - Return types: structured (`dict`/`list`) for queryable data (lists, metadata); `str` for content bodies, messages, and errors
  - Lifespan pattern: `AppContext` dataclass + `asynccontextmanager` lifespan
  - Module exports: `__all__` in every `server.py`
- [ ] Keep section under 30 lines
- [ ] Place section after the Tech stack table (near existing MCP server references)

## Context
See docs/research/mcp-server-error-return-standardization.md
Depends on #506 (error prefix + __all__) and #507 (structured returns) — write docs after implementation so conventions match reality.

## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A — T1 consistency refactor, no DR required (research doc classifies all changes as T1)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Add MCP Server Conventions section | Clear target file and heading level | None |
| Error prefix convention | Refined: clarified execution errors vs informational empty-results | Rewritten |
| Tool annotations | Clear, references mcp-kanban as pattern | None |
| Return types | Refined: queryable data vs content bodies distinction added | Rewritten |
| Lifespan pattern | Clear and specific | None |
| Module exports | Clear | None |
| 30-line limit | Measurable constraint | None |
| Placement after Tech stack | Added for builder clarity | New AC line |

### Architecture Notes
- Research doc (owning task #496) establishes conventions based on mcp-kanban reference implementation
- copilot-instructions.md is the correct placement (loaded for all agents, MCP conventions affect all tool interactions)
- Added depends_on [506, 507] so docs are written after implementation completes
- Created #512 (backlog) for mcp-project ToolAnnotations gap not covered by #506

### Changes Made
- Added depends_on: 506, 507
- Refined AC: error prefix distinction (execution errors vs informational), return types (queryable data vs content bodies)
- Added placement AC line (after Tech stack table)
- Created follow-up #512: Add ToolAnnotations to mcp-project server tools

### Dependencies
- Added: #506 (error prefix + __all__), #507 (structured returns)
- Created: #512 (mcp-project annotations gap)

### Challenge Results
- Challenger: reconsider (confidence 0.55)
- Key challenges: (1) ordering risk, (2) return type AC too vague, (3) mcp-project ToolAnnotations gap, (4) instruction file placement
- Architect response: accepted (1) via depends_on, accepted (2) via AC refinement, accepted (3) via follow-up #512, rebutted (4) per research doc rationale

[[2026-04-01]] Wed 06:48
## Test-Writer Notes
- Non-implementation task (tagged type:docs) — no tests applicable.
- Passing through to builder.

[[2026-04-01]] Wed 14:21
## Builder Notes
- Files changed: .github/copilot-instructions.md
- Added ## MCP Server Conventions section after Tech stack table (9 lines, under 30-line limit)
- Section covers all 5 AC items: error prefix, tool annotations, return types, lifespan pattern, module exports
- No tests (type:docs non-implementation task)
- Committed: docs: add MCP server conventions (#508, builder)

[[2026-04-01]] Wed 15:46
## Review Evidence
PASS (confidence 0.97) -- all 8 AC lines verified against git diff (commit 4aa8761). Section present at line 67, 10 lines added (under 30-line limit), placed directly after Tech stack table. All 5 conventions covered: error prefix, tool annotations, return types, lifespan pattern, module exports. Builder process: CLEAN (1 notes section, no retries). No tests applicable (type:docs). No security issues.

[[2026-04-01]] Wed 15:54
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | PASS | ## MCP Server Conventions section present at line 67, 10 lines (under 30-line limit), placed directly after Tech stack table. All 5 conventions covered: error prefix, tool annotations, return types, lifespan pattern, module exports. |
| 2 | Docstrings | No | N/A | No Python modules created or modified (builder changed only .github/copilot-instructions.md) |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used -- conventions derived from existing mcp-kanban reference implementation already in project |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc linked | Yes | PASS | docs/research/mcp-server-error-return-standardization.md exists and is linked in task body Context section |

### Files Updated
- None (copilot-instructions.md updated by builder, committed in commit 4aa8761)

### Scratch Files Cleaned
- docs/scratch/508-reviewer.tmp

[[2026-04-01]] Wed 15:54
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | PASS | MCP Server Conventions section at line 67, 10 lines (under 30), after Tech stack table. All 5 conventions: error prefix, tool annotations, return types, lifespan pattern, module exports. |
| 2 | Docstrings | No | N/A | No Python modules changed. |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used. |
| 4 | README.md | No | N/A | No CLI changes. |
| 5 | Research doc | Yes | PASS | docs/research/mcp-server-error-return-standardization.md exists and linked in task body. |

### Files Updated
- None (copilot-instructions.md committed by builder, commit 4aa8761)

### Scratch Files Cleaned
- docs/scratch/508-reviewer.tmp

## Docs Gate

[[2026-04-01]] Wed 15:55
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | PASS | MCP Server Conventions section present at line 67, 10 lines (under 30-line limit), placed after Tech stack table. All 5 conventions covered: error prefix, tool annotations, return types, lifespan pattern, module exports. |
| 2 | Docstrings | No | N/A | No Python modules created or modified (builder changed only .github/copilot-instructions.md). |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used â€” conventions derived from mcp-kanban reference implementation already in project. |
| 4 | README.md | No | N/A | No CLI commands added or changed. |
| 5 | Research doc | Yes | PASS | docs/research/mcp-server-error-return-standardization.md exists and is linked in task body Context section. |

### Files Updated
- None (copilot-instructions.md updated by builder, committed in commit 4aa8761)

### Scratch Files Cleaned
- docs/scratch/508-reviewer.tmp

[[2026-04-01]] Wed 17:50
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| MCP Server Conventions section added | Section at L67 of .github/copilot-instructions.md, heading `## MCP Server Conventions` | PASS |
| Error prefix convention | Bullet 1: `error: ` prefix for execution errors, informational distinction | PASS |
| Tool annotations convention | Bullet 2: readOnlyHint, idempotentHint, destructiveHint, references mcp-kanban | PASS |
| Return types convention | Bullet 3: dict/list[dict] for queryable, str for content/messages/errors | PASS |
| Lifespan pattern | Bullet 4: AppContext dataclass + asynccontextmanager | PASS |
| Module exports | Bullet 5: __all__ in every server.py | PASS |
| Under 30 lines | 10 lines total (1 heading + 1 intro + 5 bullets + whitespace) | PASS |
| Placed after Tech stack table | Section appears directly after Tech stack table ending at L65 | PASS |

### Test Results
- pytest: 2171 passed, 222 failed, 1 error (all failures pre-existing, unrelated to this docs-only task)
- ruff: 2 pre-existing PT018 violations in test_necessity_check_196.py (unrelated)

### Commit Verification
- Commit 4aa8761: `docs: add MCP server conventions section (#508, builder)` -- 1 file, 10 lines added, clean scope

### AC Quality Score: 5/5
AC was specific (5 named conventions, measurable line limit, explicit placement). Architect added useful refinements (depends_on for ordering, error prefix distinction, return type categories). No gaps found.

### Reviewer Evidence
PASS at 0.97 -- detailed verification present in task body.

### Deduction breakdown: none -- all AC verified with evidence, no task-scope failures, AC quality 5/5, reviewer evidence present
### Confidence: 1.00
### Action: archive
