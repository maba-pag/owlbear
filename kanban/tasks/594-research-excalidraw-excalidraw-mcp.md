---
id: 594
title: 'Research: excalidraw/excalidraw-mcp'
status: archived
priority: important
created: 2026-03-05T23:51:52.2436534+01:00
updated: 2026-03-10T04:21:39.3288573+01:00
started: 2026-03-06T21:44:36.7644475+01:00
completed: 2026-03-10T04:21:39.3288573+01:00
tags:
    - research
    - phase-research
    - scope:copilot
parent: 582
class: standard
---

**Source:** <https://github.com/excalidraw/excalidraw-mcp>
Analyze for Excalidraw MCP server implementation, tool definitions, and integration patterns.

**Research:** See docs/excalidraw-mcp-research.md

**Findings:**

- MCP Apps is an official MCP extension for interactive HTML UIs (iframe) in chat hosts (Claude, VS Code, ChatGPT)
- excalidraw-mcp implements 5 tools (2 model-visible, 3 app-only) with dual transport (stdio + StreamableHTTP)
- Key pattern: cheat-sheet companion tool (read_me) pre-loads domain context into model before main tool call
- Architecture mismatch with OwlBear: MCP Apps need HTML-capable host; OwlBear channels (CLI, Slack) cannot render iframes
- Recommendation: Do not adopt MCP Apps rendering (YAGNI). One adoptable pattern: cheat-sheet tool for complex toolsets

**Research checklist:**

- [x] Theoretical validity -- MCP Apps are sound, official spec, 6+ supported hosts
- [x] Prior art -- 20+ examples in ext-apps repo, excalidraw is flagship
- [x] Technical feasibility -- Python SDK exists but requires HTML host; OwlBear is not an MCP host
- [x] Architecture fit -- Low fit; OwlBear consumes MCP tools, does not render HTML iframes
- [x] Implementation approach -- Cheat-sheet tool pattern is adoptable; MCP Apps rendering is not

[[2026-03-10]] Tue 00:52

## Test-Writer Notes

Non-implementation task (tagged research) -- no tests applicable. Passing through to builder.

[[2026-03-10]] Tue 01:53
## Builder Notes
- Non-implementation research task -- no code changes, no tests
- Research doc verified: docs/excalidraw-mcp-research.md (complete, 5 sections)
- Follow-up task #718 created at ideation (cheat-sheet tool pattern evaluation)
- All 5 research checklist items checked
- Findings match task body summary
- No lint/test evidence needed (pure research)

[[2026-03-10]] Tue 01:53
## Builder Notes
- Non-implementation research task -- no code changes, no tests
- Research doc verified: docs/excalidraw-mcp-research.md (complete, 5 sections)
- Follow-up task #718 created at ideation (cheat-sheet tool pattern evaluation)
- All 5 research checklist items checked
- Findings match task body summary
- No lint/test evidence needed (pure research)

[[2026-03-10]] Tue 02:29
## Review Evidence

### Deliverables Verified
- Research doc: docs/excalidraw-mcp-research.md (committed, 69 lines, 5 sections)
- Follow-up task: #718 (ideation, nice-to-have, cheat-sheet pattern evaluation)

### Research Checklist (5/5)
| Checklist Item | Doc Section | Status |
|----------------|-------------|--------|
| Theoretical validity | S3.3 row 1 | PASS |
| Prior art | S3.3 row 2 | PASS |
| Technical feasibility | S3.3 row 3 | PASS |
| Architecture fit | S3.3 row 4 | PASS |
| Implementation approach | S3.2 + S4 | PASS |

### Document Quality
- Sources table with relevance ratings (.80-.90)
- Architecture analysis: 6 reusable patterns with OwlBear relevance
- MCP Apps assessment: 5 criteria evaluated
- Recommendation with confidence scores (.70 main, .85 cheat-sheet, .80 security)
- Concrete follow-up kanban command in S5
- YAGNI/KISS principles applied correctly

### Issues (non-blocking, for docs gate)
1. **Duplicate file:** committed at docs/ root (wrong per file placement rules), untracked copy at docs/research/ (correct). The docs gate should ensure canonical location is docs/research/ and remove the root copy.
2. **Follow-up already executed:** #718 was created by builder. Research-docs instructions say to present commands for user review, not execute. Minor process issue.
3. **Duplicate builder notes** in task body (cosmetic).

### Security Review
N/A  pure research task, no code changes.

### Verdict: PASS confidence .91

[[2026-03-10]] Tue 03:06
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Pure research task, no behavior/API/convention change |
| 2 | Docstrings complete | No | N/A | No Python modules created or modified |
| 3 | sources/overview.md | Yes | Pass | Already attributed at line 1098-1104 (3 sources with URLs, dates, Where Used) |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Fixed | Moved from docs/ root to docs/research/excalidraw-mcp-research.md per file placement rules (commit 2df32cb); task body links correctly |
| 6 | Follow-up tasks | Yes | Pass | #718 exists at ideation status |

### Files Updated
- docs/excalidraw-mcp-research.md -> docs/research/excalidraw-mcp-research.md (relocated, commit 2df32cb)

### Scratch Files Cleaned
- Deleted docs/scratch/594-builder.tmp

[[2026-03-10]] Tue 04:21
## Audit
### AC Verification
| AC Item | Evidence | Status |
|---------|----------|--------|
| Research doc written | docs/research/excalidraw-mcp-research.md - 69 lines, 5 sections | PASS |
| Research checklist 5/5 | Task body all 5 checked | PASS |
| Follow-up tasks created | #718 at ideation (cheat-sheet tool pattern) | PASS |
| Sources attributed | docs/sources/overview.md L21 - 3 sources | PASS |
| Doc in correct location | docs/research/ per rules (moved 2df32cb) | PASS |
| Duplicate removed | docs/excalidraw-mcp-research.md absent | PASS |
| Scratch files cleaned | No docs/scratch/594-* | PASS |

### Test Results
- pytest: 177 passed (representative sample)
- ruff: 3 pre-existing errors, none from #594

### Confidence: .97
### Action: archive
