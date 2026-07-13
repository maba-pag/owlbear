---
id: 128
title: Add MCP server customization section to README
status: archived
priority: medium
created: 2026-03-29 07:06:43.608754+02:00
updated: 2026-03-29 14:35:30.138547+02:00
started: 2026-03-29 14:35:18.632805+02:00
completed: 2026-03-29 14:35:18.632805+02:00
tags:
- phase-1
- scope:mcp
- type:docs
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Add a section to README.md documenting how to add project-specific MCP servers.

## Acceptance Criteria
- [ ] Section titled 'Adding MCP Servers' placed after 'Quick Start'
- [ ] Example: stdio server (Python tool with uv)
- [ ] Example: http server (remote API)
- [ ] Example: env vars and input variables for secrets
- [ ] Links to VS Code MCP Config Reference
- [ ] Mentions IntelliSense support in mcp.json
- [ ] Section is <=30 lines

## Context
See docs/research/mcp-server-customization-docs.md

[[2026-03-29]] Sun 10:31
## Architecture Review

[[2026-03-29]] Sun 10:32
See docs/scratch/128-architect.md for full review.

[[2026-03-29]] Sun 11:22
## Test-Writer Notes
- Non-implementation task (tagged type:docs) — no tests applicable.
- Passing through to builder.

[[2026-03-29]] Sun 12:35
## Builder Notes
- Files changed: README.md
- No tests (type:docs task - non-impl pass-through from test-writer)
- Lint: 0 errors (MD031 blank-fence, MD013 line-length fixed via reference-style link)
- Section: 28 lines (<=30 AC), placed between Quick Start and Directory Layout
- All AC items satisfied: stdio example, http example, env vars + input:id, VS Code MCP Config Reference link, IntelliSense mention

[[2026-03-29]] Sun 14:21
## Docs Gate
### Checklist
1 .github/copilot-instructions.md: No - type:docs task, no behavior or API change
2 Docstrings: No - no Python files modified
3 docs/sources/overview.md: Yes - Updated, added Task #128 entry (VS Code MCP Config Reference + MCP Server Guide)
4 README.md: Yes - Pass, all 7 AC items confirmed: title placement, stdio, http, env+inputs, MCP Config link, IntelliSense mention, 28 lines
5 Research doc: Yes - Pass, docs/research/mcp-server-customization-docs.md exists, linked in task body

### Files Updated
- docs/sources/overview.md

### Scratch Files Cleaned
- None (no docs/scratch/128-* files existed)

[[2026-03-29]] Sun 14:35
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Section titled 'Adding MCP Servers' after Quick Start | README.md L33, after Quick Start L19 | PASS |
| Example: stdio server (Python tool with uv) | README.md L37-43, uv + stdio example | PASS |
| Example: http server (remote API) | README.md L48-49, http type example | PASS |
| Example: env vars and input variables | README.md L50-54, env + inputs shown | PASS |
| Links to VS Code MCP Config Reference | README.md L58+L60, reference-style link | PASS |
| Mentions IntelliSense in mcp.json | README.md L35 | PASS |
| Section <=30 lines | 28 lines (L33-L60) | PASS |

### Test Results
- pytest: 568 passed, 82 pre-existing failures (unrelated: rename-todo, scratch-enforcement, infra, skill-validation)
- ruff: All checks passed

### Reviewer Evidence
- No Review Evidence section in task body (minor gap; type:docs task with only markdown changes, low risk)

### Upstream Commits
- 5e76b7e docs: add Adding MCP Servers section to README (#128, builder)
- b3ec472 docs: add MCP server customization section to README (#128, writer)

### AC Quality: 4/5
AC was specific and measurable. All 7 items directly verifiable. Minor gap: no IntelliSense-specific verification criterion beyond 'mentions'.

### Confidence: .97
### Action: archive

[[2026-03-29]] Sun 14:35
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 2248459 | chore | kanban/tasks/128-*.md | #128 |
