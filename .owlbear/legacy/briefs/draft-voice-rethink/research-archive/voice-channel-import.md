# Fix Broken Voice Channel Import in Bootstrap

> **Owning task:** #458 — Fix broken voice channel import in bootstrap
> **Date:** 2026-03-06  **Status:** Complete

## 1. Context and Question

`create_channel("voice")` in `bootstrap.py` L241 does:

```python
from owlbear.channels.voice import VoiceChannel
```

No such module exists — `VoiceChannel` lives at `owlbear.voice.channel`.
This is a latent `ModuleNotFoundError` triggered at runtime.

**Decision required:** Fix the import path (Option A) or relocate `VoiceChannel` to `channels/` (Option B)?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | OwlBear architecture-audit.md (ARC-02, ARC-03) | local: `docs/architecture-audit.md` | 1.0 — directly describes bug and both options |
| 2 | OwlBear config-dependency-audit.md (F-04) | local: `docs/config-dependency-audit.md` | 1.0 — confirms broken import, recommends fix |
| 3 | OwlBear integration-audit.md (INT-01) | local: `docs/integration-audit.md` | 1.0 — confirms CRIT severity |
| 4 | Rasa `core/channels/` | `github.com/RasaHQ/rasa/tree/main/rasa/core/channels` | 0.7 — co-locates all channels (incl. `twilio_voice.py`) in one dir |
| 5 | BearClaw CLI `cli.py` L264 | local: `src/bearclaw/cli.py` | 0.9 — already uses correct import `owlbear.voice.channel` |

## 3. Analysis

### Option comparison

| Criterion | A: Fix import (.90) | B: Relocate to channels/ (.45) |
|-----------|---------------------|-------------------------------|
| Diff size | 1 line changed | 4+ files: move, update imports, update `__init__.py`, update CLI |
| KISS | High — minimal change | Low — restructuring for aesthetics |
| YAGNI | Passes — solves the bug | Fails — no functional benefit |
| Cohesion | voice/ keeps STT+TTS+channel together | Breaks: channel separated from its STT/TTS deps |
| Consistency | CLI already uses `owlbear.voice.channel` | Would need to update CLI too |
| Risk | Near zero | Medium — could break other imports |
| Prior art | Rasa `twilio_voice.py` is thin (Twilio does STT/TTS server-side) — OwlBear voice has local STT/TTS subsystem | Rasa pattern works when channels are thin wrappers, not rich subsystems |

### Why voice/ is different from channels/

`channels/` contains thin I/O adapters: `cli.py` (~80 LOC), `slack.py` (~200 LOC, delegates to SDK).
`voice/` is a rich subsystem: `channel.py` + `stt.py` + `tts.py` + `streaming_stt.py` (~600 LOC total).
The channel is tightly coupled to its STT/TTS engines — extracting it breaks package cohesion.

## 4. Recommendation (.90 confidence)

**Option A: Fix the import path.** Change L241 in `bootstrap.py` from:

```python
from owlbear.channels.voice import VoiceChannel
```

to:

```python
from owlbear.voice import VoiceChannel
```

This matches the CLI pattern (L264), uses the `voice/__init__.py` re-export, and is a single-line fix.

**Do NOT relocate.** VoiceChannel belongs with its STT/TTS subsystem. Relocating creates a separation-without-benefit that violates KISS and YAGNI.

## 5. Follow-up Tasks

```shell
kanban\kanban-md.exe edit 458 --body "Research complete. Fix: change bootstrap.py L241 from 'from owlbear.channels.voice import VoiceChannel' to 'from owlbear.voice import VoiceChannel'. Do NOT relocate VoiceChannel — it belongs with voice/ subsystem. See docs/research/voice-channel-import.md. AC: (1) voice channel starts without ImportError, (2) existing tests pass, (3) ruff clean."
```

No additional tasks needed — this is a one-line bugfix. The related concern (ARC-03: should VoiceChannel live in channels/) is resolved by this research: **no, keep it in voice/**.
