---
id: 907
title: remove get_changed_files from agent tool groups to prevent context 
  overflow
status: done
priority: critical
created: 2026-04-16T23:53:20.950904+00:00
updated: 2026-04-16T23:53:20.950904+00:00
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