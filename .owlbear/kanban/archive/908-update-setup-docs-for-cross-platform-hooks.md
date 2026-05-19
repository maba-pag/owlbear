---
id: 908
title: Update setup docs for cross-platform hooks
status: archived
priority: needed
created: 2026-04-17T08:43:52.908745+00:00
updated: 2026-04-17T10:07:28.622185+00:00
tags:
- phase-2
- scope:setup
- type:docs
- platform
parent: 890
depends_on:
- 900
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md` (step 6)

From research #900: `setup/init.py` has no stale `.ps1` references, but the documentation does.

## Acceptance Criteria

- [ ] `setup/setup-guide.md` lines 51-52: `.ps1` hook names replaced with `.py` equivalents and all 7 hooks listed
- [ ] `setup/setup-guide.md` line 25: `powershell` code fence replaced with `shell` or cross-platform example
- [ ] `setup/sharing-guide.md` line 30: `powershell` code fence replaced with `shell` or cross-platform example
- [ ] `grep -i "\.ps1\|powershell" setup/*.md` returns no results
- [ ] Quick Start example in setup-guide.md works on macOS (no Windows-only paths)

## Files

- `setup/setup-guide.md` (edit)
- `setup/sharing-guide.md` (edit)
[[2026-04-17]]

## Superseded

All ACs covered by #901 (commit 5f73bb92). Grep gate `grep -i "\.ps1\|powershell" setup/*.md` returns 0 results. Archiving as superseded.
