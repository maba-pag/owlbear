---
id: 901
title: Update setup and sharing docs for macOS
status: research
priority: important
created: 2026-04-16T22:54:41.755078+00:00
updated: 2026-04-16T22:54:41.755078+00:00
tags:
- phase-3
- scope:docs
- type:docs
- platform
parent: 890
depends_on:
- 897
- 900
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] setup/setup-guide.md updated: macOS prerequisites added, cross-platform commands shown (forward-slash paths, python ../owlbear/setup/init.py)
- [ ] Windows-only limitation note (same drive) scoped to Windows only, not presented as universal
- [ ] setup/sharing-guide.md updated: macOS section added covering hook behavior, MCP server startup
- [ ] PowerShell-only examples replaced with cross-platform alternatives or annotated
- [ ] No instructions assume powershell binary is available

## Files
- `setup/setup-guide.md` (edit)
- `setup/sharing-guide.md` (edit)