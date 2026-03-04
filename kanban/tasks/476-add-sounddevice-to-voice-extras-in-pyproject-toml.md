---
id: 476
title: Add sounddevice to voice extras in pyproject.toml
status: ideation
priority: needed
created: 2026-03-04T07:37:54.7016203+01:00
updated: 2026-03-04T07:37:54.7016203+01:00
tags:
    - audit
    - config
    - deps
class: standard
---

F-05: voice/channel.py imports sounddevice (with graceful guard) but the package is not in [voice] extras. Users installing owlbear[voice] get moonshine, numpy, pyttsx3 but not sounddevice. Voice recording silently fails. AC: sounddevice>=0.4 in voice extras. See docs/config-dependency-audit.md.
