---
id: 898
title: Update seed/ with .py hooks and clean settings
status: research
priority: needed
created: 2026-04-16T22:54:12.457895+00:00
updated: 2026-04-16T22:54:12.457895+00:00
tags:
- phase-2
- scope:setup
- config
- platform
parent: 890
depends_on:
- 894
- 895
- 896
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] All .ps1 files in seed/.owlbear/hooks/ replaced with .py equivalents (copies from .owlbear/hooks/)
- [ ] 7 .py hooks present in seed/.owlbear/hooks/ (fix drift: seed currently has 6, missing deny-scratch-only-writes)
- [ ] Windows-only terminal profiles removed from seed/.vscode/settings.json (no pwsh.exe paths)
- [ ] No .ps1 references remain in seed/
- [ ] grep -r ".ps1" seed/ returns no results
- [ ] grep -r "powershell" seed/ returns no results

## Files
- `seed/.owlbear/hooks/*.py` (new, replacing .ps1)
- `seed/.vscode/settings.json` (edit)