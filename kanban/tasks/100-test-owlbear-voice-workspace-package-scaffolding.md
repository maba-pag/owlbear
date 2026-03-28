---
id: 100
title: 'Test: owlbear-voice workspace package scaffolding'
status: backlog
priority: nice-to-have
created: 2026-03-28T04:10:07.8252463+01:00
updated: 2026-03-28T04:10:07.8252463+01:00
tags:
    - phase-3
    - scope:voice
    - test
depends_on:
    - 7
class: standard
---

## Objective
Verify owlbear-voice package scaffolding meets AC from task #52.

## Acceptance Criteria
- [ ] Test pyproject.toml exists at packages/voice/pyproject.toml
- [ ] Test pyproject.toml declares name=owlbear-voice and hatchling build-backend
- [ ] Test base dependencies listed (moonshine-voice, numpy, pyttsx3, sounddevice)
- [ ] Test [kokoro] optional extra declared
- [ ] Test entry point owlbear-voice declared
- [ ] Test __init__.py stub exists at packages/voice/src/owlbear_voice/__init__.py
- [ ] Test main.py stub exists with callable main()
- [ ] Test packages/voice/tests/__init__.py exists
- [ ] Test root pyproject.toml ruff src includes packages/voice/src
- [ ] Test owlbear_voice is importable
