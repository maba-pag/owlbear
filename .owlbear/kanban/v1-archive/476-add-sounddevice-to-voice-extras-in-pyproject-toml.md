---
id: 476
title: Add sounddevice to voice extras in pyproject.toml
status: archived
priority: needed
created: 2026-03-04T07:37:54.7016203+01:00
updated: 2026-03-06T19:28:20.034565+01:00
started: 2026-03-06T15:47:02.3086125+01:00
completed: 2026-03-06T19:28:20.034565+01:00
tags:
    - audit
    - config
    - deps
class: standard
---

F-05: voice/channel.py imports sounddevice (with graceful guard) but the package is not in [voice] extras. Users installing owlbear[voice] get moonshine, numpy, pyttsx3 but not sounddevice. Voice recording silently fails.

See docs/config-dependency-audit.md F-05.

## Acceptance Criteria

- [ ] `sounddevice>=0.4` added to `[project.optional-dependencies]` voice list in pyproject.toml
- [ ] `uv lock` resolves without errors
- [ ] No source code changes needed (import guard in channel.py is correct as-is)
- [ ] ruff clean
