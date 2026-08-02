---
id: 907
title: remove get_changed_files from agent tool groups to prevent context
  overflow
status: archived
priority: medium
created: 2026-04-16T23:53:20.950904+00:00
updated: 2026-04-17T00:52:37.270853+00:00
tags:
- agents
- stability
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Problem

The `search` tool group in agent definitions includes `search/changes` (aka `get_changed_files`), which returns ALL changes in full — potentially thousands of LOC and tens of thousands of tokens. When an agent calls this, it can overflow the context window, effectively killing the agent mid-task.

## Fix

Replace the bare `search` tool group with explicit safe search tools in all 20 agent definitions:
`search/codebase, search/fileSearch, search/listDirectory, search/searchResults, search/textSearch, search/searchSubagent, search/usages`

This excludes `search/changes` while preserving all other search capabilities.

## AC

- [ ] No agent file contains bare `search` in tools (only `search/` prefixed)
- [ ] All 20 agents updated
- [ ] Only frontmatter tools lines changed, not prose body text
[[2026-04-17]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| No bare `search` in any agent tools | grep across all 22 agent files: zero bare `search` entries; all use `search/` prefix | PASS |
| All 20 agents updated | 20 search-enabled agents confirmed with identical safe tool set; 2 non-search agents (quality-runner, orchestrator) correctly excluded | PASS |
| Only frontmatter tools lines changed | Explore agent verified all modifications isolated to YAML `tools:` line; prose body text unchanged | PASS |

### Test Results

- pytest: timed out at 97% (task modifies zero Python files; cross-task regression risk negligible)
- ruff: 2 pre-existing violations in scope_transfer.py (S608, RUF100) unrelated to task scope

### Architect Quality: 4/5

Clear, specific AC with verifiable conditions. Minor gap: AC says "20 agents" but workspace has 22 agent files (2 correctly excluded by design, not called out in AC).

### Deduction Breakdown

- Missing reviewer evidence section: -.02

### Confidence: .98

### Action: archive
