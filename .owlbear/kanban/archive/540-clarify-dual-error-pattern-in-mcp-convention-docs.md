---
id: 540
title: Clarify dual error pattern in MCP convention docs
status: archived
priority: medium
created: 2026-04-02 05:59:38.529706+02:00
updated: 2026-04-02 15:58:27.217841+02:00
started: 2026-04-02 15:58:26.818576+02:00
completed: 2026-04-02 15:58:26.818576+02:00
tags:
- scope:mcp
- type:docs
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

## AC
- [ ] Add a note to `.github/copilot-instructions.md` â†’ MCP Server Conventions â†’ **Error prefix** bullet clarifying when to use each error mechanism:
  - `ToolError` (exception, `isError=true`): use when the return type is a pure model (`dict`, `list[dict]`) and an error string cannot be embedded in the typed return
  - `error: ` string prefix (`isError=false`): use for `str`-return and union-return tools (`dict | str`)
  - Both are MCP-spec-valid (spec distinguishes protocol errors from tool execution errors)
- [ ] Keep addition â‰¤ 5 lines â€” a sub-bullet list under the existing Error prefix bullet
- [ ] Do not change any existing bullets or add new top-level bullets

## Context
See docs/research/mcp-server-error-return-standardization.md S3a
mcp-kanban uses ToolError for show_task/move_task/pick_task (pure dict returns) and error: strings for others (str returns).
mcp-knowledge and mcp-project use error: strings for all tools (union return types allow embedding error strings).

[[2026-04-02]] Thu 07:50
## Architecture Review
**Verdict:** REFINE (AC rewritten)
**DR Verification:** N/A — T1 research classification, no DR required

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Add note explaining ToolError vs error: | Original framed as state description of kanban-only pattern | Rewritten as decision framework (when to use which) |
| ToolError for typed returns sets isError=true | Accurate for mcp-kanban but not universal | Scoped: use when return type is pure model and error string cannot be embedded |
| error: prefix sets isError=false (informational) | "informational" label misleading | Removed label, clarified as approach for str-return and union-return tools |
| MCP spec S6 reference | Spec uses section headings, not numbered sections | Changed to prose description |
| Keep under 5 lines | Good constraint, verifiable | Kept; added: sub-bullet list under existing Error prefix bullet |

### Architecture Notes
Docs-only task. The existing Error prefix bullet in MCP Server Conventions (.github/copilot-instructions.md L72) describes only the error: string convention. mcp-kanban also uses ToolError for pure-typed returns (show_task, move_task, pick_task at server.py L235/287/374). The note fills a real documentation gap.

Key refinement: the original AC described the kanban-only pattern as if universal. mcp-knowledge and mcp-project use union return types (dict | str) so they embed errors as strings. The refined AC frames the note as a decision framework — when to use ToolError vs error: string — so it remains accurate regardless of how sibling task #539 resolves knowledge server null safety.

No dependency on #539 needed: #539 adds null checks returning error: strings (union return types unchanged), so the convention described here holds before and after.

### Changes Made
- Rewrote task body with refined AC via temp-file pattern
- Scoped ToolError guidance to "pure model returns where error string cannot be embedded"
- Added instruction to keep changes as sub-bullets under existing bullet (no new top-level bullets)

### Dependencies
- Verified: no depends_on listed, correct for standalone docs task
- Related: #539 (null safety in mcp-knowledge) at todo — no ordering dependency needed

### Challenge Results
- Challenger: reconsider (confidence 0.55 in original)
- Key challenges: (C1) AC enshrines kanban-only pattern as universal convention; (C2) "informational" label misleading; (C3) MCP spec S6 reference unverifiable
- Architect response: C1 accepted — rewrote AC as decision framework; C2 accepted — removed "informational"; C3 accepted — replaced with prose. Prescriptive-vs-descriptive blind spot also addressed.
- Confidence in original after challenge: revised verdict still APPROVE (after AC refinement)

[[2026-04-02]] Thu 10:38
## Test-Writer Notes
- Non-implementation task (tagged type:docs) - no tests applicable.
- Passing through to builder.

[[2026-04-02]] Thu 11:47
## Builder Notes\n- Files changed: .github/copilot-instructions.md\n- Change: added 3 sub-bullets under Error prefix bullet in MCP Server Conventions\n- ToolError (isError=true) for pure model returns; error: string (isError=false) for str/union returns; both MCP-spec-valid\n- Lines added: 3 (within 5-line AC constraint)\n- No existing bullets modified, no new top-level bullets added\n- Lint: N/A (docs-only change)\n- Commit: 585c49a

[[2026-04-02]] Thu 12:11
## Review Evidence

**Task:** #540 - Clarify dual error pattern in MCP convention docs
**Type:** docs-only, no tests applicable

### Changed Files
- `.github/copilot-instructions.md` -- 3 lines inserted (commit 585c49a)

### Test Results
N/A -- docs-only task (type:docs tag; no code changed). Test-writer confirmed no tests applicable.

### Lint Results
N/A -- markdown-only change.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| Add sub-bullets for ToolError (isError=true) pure model returns | Line 72: ToolError exception (isError=true): use when return type is pure model (dict, list[dict]) and error string cannot be embedded | PASS |
| Add sub-bullet for error: string (isError=false) str/union returns | Line 73: error: string prefix (isError=false): use for str-return and union-return tools (dict or str) | PASS |
| Add sub-bullet: both MCP-spec-valid | Line 74: Both approaches are MCP-spec-valid; the spec distinguishes protocol errors from tool execution errors | PASS |
| Keep addition at most 5 lines | 3 lines added (under limit) | PASS |
| Sub-bullets under existing Error prefix bullet only | All 3 lines are indented sub-bullets; no top-level bullets added | PASS |
| No existing bullets modified | git diff shows 3 insertions, 0 deletions | PASS |

### Content Accuracy Check
- ToolError guidance matches mcp-kanban actual usage (show_task/move_task/pick_task use ToolError per architect notes)
- error: string guidance matches mcp-knowledge and mcp-project (union return types embed errors as strings)
- MCP-spec statement is technically correct

### Verdict: PASS
Confidence: .97 -- all 3 AC items satisfied; no existing text modified; line count within constraint; content accurate.

[[2026-04-02]] Thu 14:41
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | PASS | 3 sub-bullets present at L72-74: ToolError (isError=true), error: string (isError=false), both MCP-spec-valid. No existing bullets modified. |
| 2 | Docstrings | No | N/A | type:docs task -- no Python modules modified |
| 3 | docs/sources/overview.md | No | N/A | Internal MCP server analysis, no external patterns adopted |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No new research doc produced by this task; referenced pre-existing doc at docs/research/mcp-server-error-return-standardization.md confirmed present |

### Files Updated
- None (builder committed change in 585c49a; docs gate review only)

### Scratch Files Cleaned
- None (no docs/scratch/540-* files found)

[[2026-04-02]] Thu 15:57
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Add sub-bullets clarifying ToolError vs error: string | L73-75 of .github/copilot-instructions.md: 3 sub-bullets under Error prefix bullet with correct content | PASS |
| Keep addition at most 5 lines | 3 lines added (under limit) | PASS |
| Do not change existing bullets or add new top-level bullets | git diff in 585c49a shows 3 insertions, 0 deletions; structure intact | PASS |

### Test Results
- pytest: 2806 passed, 317 failed (all pre-existing from other tasks), 8 skipped, 1 error. Zero failures in task scope.
- ruff: N/A (docs-only markdown change)

### Reviewer Evidence
Present and detailed. Confidence .97, all AC items PASS with line-level references. Content accuracy verified against actual MCP server usage.

### AC Quality Score: 5
AC was specific, verifiable, and led to clean implementation. Architect refined original AC to frame as decision framework rather than kanban-only description.

### Deduction breakdown: none (all AC verified with evidence, no lint issues, AC quality 5, reviewer evidence complete, no task-scope failures)
### Confidence: 1.0
### Action: archive

-t

[[2026-04-02]] Thu 15:58
## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| Add sub-bullets clarifying ToolError vs error: string | L73-75 of .github/copilot-instructions.md: 3 sub-bullets present with correct content | PASS |\n| Keep addition at most 5 lines | 3 lines added (under limit) | PASS |\n| Do not change existing bullets or add new top-level bullets | git diff in 585c49a: 3 insertions, 0 deletions; structure intact | PASS |\n\n### Test Results\n- pytest: 2806 passed, 317 failed (all pre-existing from other tasks), 0 in task scope\n- ruff: N/A (docs-only markdown change)\n\n### Reviewer Evidence\nPresent and detailed. Confidence .97, all AC items PASS with line-level references.\n\n### AC Quality Score: 5\nAC specific, verifiable, led to clean implementation.\n\n### Deduction breakdown: none\n### Confidence: 1.0\n### Action: archive
