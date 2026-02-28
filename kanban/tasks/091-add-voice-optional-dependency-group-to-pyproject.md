---
id: 91
title: Add [voice] optional dependency group to pyproject.toml
status: archived
priority: nice-to-have
created: 2026-02-27T03:07:31.092582+01:00
updated: 2026-02-28T23:52:43.6664709+01:00
started: 2026-02-27T03:32:41.6173249+01:00
completed: 2026-02-28T23:52:43.6664709+01:00
tags:
    - phase-5
    - voice
    - config
class: standard
---

## Acceptance Criteria

- [ ] `pyproject.toml` has `[project.optional-dependencies]` entry: `voice = ["faster-whisper>=1.0", "pyaudio>=0.2.14", "pyttsx3>=2.90"]`  
- [ ] `uv sync --extra voice` installs all three packages without errors
- [ ] `uv sync` (without --extra) does NOT install voice dependencies
- [ ] `src/owlbear/voice/__init__.py` exists (empty package init, exports nothing yet)
- [ ] Test: `tests/test_voice_init.py` verifies `import owlbear.voice` succeeds

See docs/voice-io-research.md section 4 for rationale.
