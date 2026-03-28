---
id: 52
title: Create owlbear-voice workspace package
status: todo
priority: nice-to-have
created: 2026-03-26T18:57:37.151058+01:00
updated: 2026-03-28T04:10:31.7148767+01:00
tags:
    - phase-3
    - scope:voice
    - config
depends_on:
    - 7
    - 100
class: standard
---

## Objective

Scaffold the owlbear-voice package as a uv workspace member under packages/voice/.

[[2026-03-28]] Sat 04:09
## Acceptance Criteria

### Package structure
- [ ] packages/voice/pyproject.toml: name=owlbear-voice, version=0.1.0, requires-python>=3.12
- [ ] Build-backend: hatchling (matching existing workspace members)
- [ ] [tool.hatch.build.targets.wheel] packages = [src/owlbear_voice]
- [ ] Base dependencies: moonshine-voice>=0.0.49; numpy>=1.26; pyttsx3>=2.90; sounddevice>=0.4
- [ ] Optional-dependencies: kokoro = [kokoro>=0.9.4, soundfile]
- [ ] Scripts entry: owlbear-voice = owlbear_voice.main:main
- [ ] packages/voice/src/owlbear_voice/__init__.py stub (empty or version-only)
- [ ] packages/voice/src/owlbear_voice/main.py stub with no-op main() function
- [ ] packages/voice/tests/ directory with __init__.py

[[2026-03-28]] Sat 04:09
### Workspace integration
- [ ] Root pyproject.toml ruff src list includes packages/voice/src
- [ ] uv sync succeeds with the new workspace member (base deps only)
- [ ] Import owlbear_voice succeeds from the workspace venv

[[2026-03-28]] Sat 04:09
### Constraints
- hatchling build backend (NOT uv_build) to match all five existing workspace members
- No implementation code beyond stubs; voice logic belongs to downstream tasks
- Kokoro deps stay behind the [kokoro] optional extra only

## Context

See docs/research/voice-addon-architecture.md and docs/research/bearclaw-voice-workspace-package.md

[[2026-03-28]] Sat 04:10
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
All four original AC lines were vague. Rewrote into 13 testable lines across Package Structure and Workspace Integration sections, plus 3 constraints.

### Architecture Notes
- Build backend: research doc proposed uv_build, but all 5 existing workspace members use hatchling. AC corrected to hatchling for consistency.
- Package layout follows established pattern: packages/voice/src/owlbear_voice/ (matches packages/knowledge/src/owlbear_knowledge/ etc.)
- Dependency #7 (monorepo skeleton) already archived. No missing deps.
- kokoro Python <3.13 constraint is a package-level resolution constraint, not a workspace member constraint. Acceptable as optional extra.
- Single domain: scope:voice (config/scaffolding). No layering concerns.
- No new security surface (scaffolding only, no runtime code).

### Changes Made
- Rewrote task body with 13 testable AC lines
- Created #100 (Test: owlbear-voice workspace package scaffolding) at backlog
- Added depends_on #100 for TDD sequencing

### Dependencies
- Verified: #7 (monorepo skeleton) archived
- Verified: #64 (rename to owlbear-voice) archived
- Added: #100 (TDD RED test task) at backlog
