---
id: 52
title: Create owlbear-voice workspace package
status: backlog
priority: nice-to-have
created: 2026-03-26T18:57:37.151058+01:00
updated: 2026-03-26T19:35:31.1226218+01:00
tags:
    - phase-3
    - scope:voice
    - config
depends_on:
    - 7
class: standard
---

## Objective

Scaffold the owlbear-voice package as a uv workspace member.

## Acceptance Criteria

- [ ] pyproject.toml with moonshine-voice, kokoro, sounddevice deps
- [ ] Optional extras: [kokoro] for quality TTS, base has pyttsx3 only
- [ ] Entry point script for voice process
- [ ] Package importable from owlbear workspace

## Context

See docs/research/voice-addon-architecture.md and docs/research/monorepo-tooling.md

[[2026-03-26]] Thu 19:35

## Research

Key findings from docs/research/voice workspace package scaffolding:

- BLOCKER: Task #7 (monorepo skeleton) must complete first; added depends_on
- kokoro 0.9.4 requires Python <3.13 (torch/transformers heavy deps); must be optional extra
- moonshine-voice deps are lightweight (numpy, sounddevice, requests, tqdm)
- Naming inconsistency: should be owlbear-voice per v2 convention; created #64
- Proposed pyproject.toml with uv_build backend, [kokoro] optional extra
- v1 patterns portable: lazy model loading, async TTS wrappers, sounddevice capture

Follow-up tasks created:

- #64: Rename package naming to owlbear-voice (ideation)
