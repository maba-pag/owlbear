---
id: 96
title: Add bearclaw voice CLI subcommand for testing voice I/O
status: todo
priority: low
created: 2026-02-27T03:08:09.5547373+01:00
updated: 2026-02-27T03:39:53.7062577+01:00
started: 2026-02-27T03:32:43.6434085+01:00
tags:
    - phase-5
    - voice
    - cli
depends_on:
    - 95
class: standard
---

## Acceptance Criteria

- [ ] `voice_app = typer.Typer(name="voice", ...)` registered on `app` via `app.add_typer(voice_app)` in `src/bearclaw/cli.py`
- [ ] `bearclaw voice listen` -- records audio (default 5s) and prints transcription to stdout
- [ ] `bearclaw voice speak TEXT` -- speaks the given text via TTS
- [ ] `--duration` option on `listen` command (default 5.0 seconds)
- [ ] Graceful error with helpful message if `[voice]` extras not installed (try import, catch ImportError, print "Install with: uv sync --extra voice")
- [ ] Test file: `tests/test_cli_voice.py` -- test command registration on app, test ImportError handling (graceful exit), test listen/speak with mocked VoiceChannel
- [ ] TDD: write tests first, then implement

Depends on: #95
See docs/voice-io-research.md section 4.

Note: `bearclaw voice chat` (interactive agent loop) deferred -- requires agent integration which is out of voice I/O module scope. Create as separate task when agent loop is ready.
