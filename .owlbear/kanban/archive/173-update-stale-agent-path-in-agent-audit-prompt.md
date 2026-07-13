---
id: 173
title: Update stale agent path in agent-audit prompt
status: archived
priority: medium
created: 2026-03-29 19:49:58.694150+02:00
updated: 2026-03-30 04:32:22.616889+02:00
started: 2026-03-30 04:32:22.239466+02:00
completed: 2026-03-30 04:32:22.239466+02:00
tags:
- phase-1
- scope:docs
- type:docs
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Fix stale .github/agents reference in agent-audit.prompt.md.

## AC
- [ ] agent-audit.prompt.md L16: change .github/agents to agents/
- [ ] Grep verify no .github/agents refs in prompt files

## Context
See docs/research/github-v1-cleanup.md sec 3.

[[2026-03-29]] Sun 20:56
## Architecture Review
Verdict: APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| L16: change .github/agents to agents/ | Verified stale ref at L16. Exact text: .github/agents/*.agent.md should become agents/*.agent.md | Keep as-is |
| Grep verify no .github/agents refs in prompt files | Confirmed single occurrence â€” grep check is meaningful post-verification | Keep as-is |

### Architecture Notes
Docs-only path fix in a prompt file. No Python code, no module layering, no security surface. TDD N/A for markdown-only change. Research doc (github-v1-cleanup.md sec 3) directly supports this. Single-domain (docs). Minimal scope â€” KISS-aligned.

### Dependencies
- None required. agents/ directory already exists at repo root.

### Changes Made
- Reviewed and approved â€” no AC changes needed.

[[2026-03-29]] Sun 21:16
## Test-Writer Notes
- Non-implementation task (tagged type:docs) — no tests applicable.
- Passing through to builder.

[[2026-03-30]] Mon 03:16
## Review Evidence
Reviewed: 2026-03-30

type:docs only. Changed: .github/prompts/agent-audit.prompt.md (commit 62da80f).

AC1: L16 .github/agents path fixed to agents/ - confirmed via git show 62da80f - PASS
AC2: Grep .github/prompts for .github/agents refs - 0 results - PASS

Security: N/A markdown only. No tests applicable (type:docs).

Verdict: PASS confidence .97

## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Path fix in prompt file only; no behavior/API/convention change |
| 2 | Docstrings | No | N/A | No Python modules created or modified |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | No | N/A | Task references existing github-v1-cleanup.md (not produced by this task) |
| 6 | No docs impact | Yes | Pass | One-line path fix in .github/prompts/agent-audit.prompt.md L16; agents/ path confirmed correct |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/173-* files found)

[[2026-03-30]] Mon 04:31
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| L16: change .github/agents to agents/ | read_file L16 shows agents/*.agent.md; commit 62da80f | PASS |
| Grep verify no .github/agents refs in prompt files | grep_search .github/prompts/** returns 0 matches | PASS |

### Test Results
- pytest: 4 collection errors in unrelated modules (voice, planner, mcp-project). No failures in task scope.
- ruff: N/A (docs-only, no Python)

### Reviewer Evidence
Present and detailed (.97 confidence). AC mapping complete.

### AC Quality Score: 5/5
Specific file, line, and verification step. Led to clean implementation.

### Deduction breakdown: none
### Confidence: 1.0
### Action: archive

-t

[[2026-03-30]] Mon 04:32
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| L16: change .github/agents to agents/ | read_file L16 shows agents/*.agent.md; commit 62da80f | PASS |
| Grep verify no .github/agents refs in prompt files | grep_search .github/prompts/** returns 0 matches | PASS |

### Test Results
- pytest: 4 collection errors in unrelated modules (voice, planner, mcp-project). No failures in task scope.
- ruff: N/A (docs-only, no Python)

### Reviewer Evidence
Present and detailed (.97 confidence). AC mapping complete.

### AC Quality Score: 5/5
Specific file, line, and verification step. Led to clean implementation.

### Deduction breakdown: none
### Confidence: 1.0
### Action: archive
