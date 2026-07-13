---
id: 52
title: Create owlbear-voice workspace package
status: archived
priority: medium
created: 2026-03-26 18:57:37.151058+01:00
updated: 2026-03-29 15:27:19.200098+02:00
started: 2026-03-29 15:26:58.615976+02:00
completed: 2026-03-29 15:26:58.615976+02:00
tags:
- phase-3
- scope:voice
- config
depends_on:
- 7
- 100
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-03-29]] Sun 12:29
## Test-Writer Notes
- Test file: tests/test_voice_workspace_package.py
- Classes: TestFromAC_VoiceDepVersionConstraints, TestFromAC_VoiceKokoroVersionConstraint, TestFromAC_VoiceEntryPointTarget, TestFromAC_VoiceWorkspaceMembership
- Tests per category: happy 8, edge 0, error 0, boundary 0
- Total: 8 tests (+ 21 in tests/test_voice_package_scaffolding.py for task #100)
- ruff: clean
- Pre-built scaffold: voice package was scaffolded before TDD phase ran; all 8 tests PASS on HEAD (expected). No RED state achievable without removing implementation.
- AC coverage:
  - AC1-4 (files, metadata, build backend, wheel config): covered by test_voice_package_scaffolding.py (#100)
  - AC5 (base dep version pins): TestFromAC_VoiceDepVersionConstraints (4 tests)
  - AC6 (kokoro version pin): TestFromAC_VoiceKokoroVersionConstraint (1 test)
  - AC7 (exact entry point target): TestFromAC_VoiceEntryPointTarget (1 test)
  - AC8-10 (stubs, tests dir): covered by test_voice_package_scaffolding.py (#100)
  - AC11 (ruff src): covered by test_voice_package_scaffolding.py (#100)
  - Workspace integration: TestFromAC_VoiceWorkspaceMembership (2 tests) â€” was missing from file despite docstring reference
  - AC12 (import): covered by test_voice_package_scaffolding.py (#100)

[[2026-03-29]] Sun 15:16
## Docs Gate
### Checklist
All 6 items evaluated with evidence.
- Item 1 (.github/copilot-instructions.md): N/A - packages/voice/ already in directory table line 144; scaffolding only, no behavior change
- Item 2 (Docstrings): Pass - __init__.py and main.py both have module and function docstrings
- Item 3 (sources/overview.md): Pass - pydantic-ai monorepo cited at line 2669 referencing bearclaw-voice-workspace-package.md
- Item 4 (README.md CLI): N/A - no existing CLI commands section in README; owlbear-voice is a no-op stub
- Item 5 (Research doc): Pass - docs/research/bearclaw-voice-workspace-package.md exists and linked from task body
- Item 6 (Scratch files): Pass - no docs/scratch/52-* files found

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-29]] Sun 15:26
## Audit
### AC Verification
All 12 AC lines verified against source files and test results.
- Package structure (AC1-9): pyproject.toml fields, stubs, tests dir all confirmed
- Workspace integration (AC10-12): ruff src list, imports, workspace resolution confirmed
- Constraints: hatchling backend, stubs only, kokoro behind optional extra

### Test Results
- Task-specific: 29 passed (test_voice_workspace_package.py + test_voice_package_scaffolding.py)
- Full suite: 568 passed, 82 failed (pre-existing, 8 unrelated test modules)
- ruff: clean

### Upstream Commits
- 73942da test: workspace membership + entry-point tests (#52, test-writer)
- 9f5306e feat: add version pins to owlbear-voice dependencies (#52, builder)
- 4cdde41 test: failing tests for voice package version constraints (#52, test-writer)

### Architect Quality
AC rewritten from 4 vague lines to 13 testable items + 3 constraints. Corrected build backend from uv_build to hatchling. Score: 5/5.

### Confidence: .97
### Action: archive

[[2026-03-29]] Sun 15:27
## Commits
ce460ae chore: archive task #52 voice workspace package (#52, auditor)
