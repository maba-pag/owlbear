# pyttsx3 Maintenance & TTS Alternatives Research

> **Owning task:** #570 — Monitor pyttsx3 maintenance and evaluate alternatives
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

The config-dependency-audit (F-10) flagged pyttsx3 as "dormant" (last release 2023).
OwlBear uses pyttsx3 in `src/owlbear/voice/tts.py` as an optional `[voice]` extra.
Voice I/O is planned but not yet a core feature. Should we keep pyttsx3, switch to
an alternative, or defer the decision?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| pyttsx3 PyPI (release history) | <https://pypi.org/project/pyttsx3/#history> | .95 |
| pyttsx3 GitHub issues | <https://github.com/nateshmbhat/pyttsx3/issues> | .90 |
| edge-tts PyPI | <https://pypi.org/project/edge-tts/> | .90 |
| edge-tts GitHub | <https://github.com/rany2/edge-tts> | .85 |
| pyttsx4 PyPI | <https://pypi.org/project/pyttsx4/> | .60 |
| Coqui TTS PyPI | <https://pypi.org/project/TTS/> | .50 |

## 3. Key Finding — Audit Was Stale

The audit (2026-03-03) stated "last PyPI release 2023." This is **outdated**.
pyttsx3 had a burst of activity in 2024-2025:

| Version | Date |
|---------|------|
| 2.92 | 2024-09-14 |
| 2.95 | 2024-09-14 |
| 2.97 | 2024-09-14 |
| 2.98 | 2024-09-27 |
| 2.99 | 2025-07-08 |

The project is no longer dormant. However, 74 open issues remain, including
macOS NSSpeechSynthesizer deprecation (#347) and run-loop bugs (#403, #402).

## 4. Comparison Matrix

| Criterion | pyttsx3 (.75) | edge-tts (.70) | pyttsx4 (.30) | Coqui TTS (.20) |
|-----------|---------------|----------------|---------------|-----------------|
| **Offline** | Yes | **No** (network) | Yes | Yes |
| **Last release** | 2025-07 | 2025-12 | 2023-06 | 2023-12 |
| **Maintained** | Moderate | Active (10.2k stars) | Stale | Stale |
| **Deps** | Minimal (pyobjc on Mac) | Minimal | Minimal | Heavy (torch) |
| **Python 3.12+** | Works (Windows) | Works | Untested | **No** (<3.12) |
| **Windows** | SAPI5 | Cross-platform | SAPI5 | Cross-platform |
| **macOS** | Deprecated driver | Works | Deprecated driver | Works |
| **Linux** | espeak-ng | Works | espeak-ng | Works |
| **Voice quality** | System voices | Neural (high) | System voices | Neural (high) |
| **Async-native** | No (thread offload) | Yes | No | No |
| **License** | MIT | **GPL-3.0** | MIT | MPL-2.0 |
| **KISS alignment** | High | High | Low | Low |

## 5. Analysis

**pyttsx3 is adequate for current needs.** It is no longer dormant, works on
Windows (OwlBear's primary platform), runs offline (aligns with "laptop-resident"
principle), and the existing `TTSEngine` wrapper in `voice/tts.py` cleanly handles
the blocking API via `asyncio.to_thread`.

**edge-tts is the strongest alternative** for voice quality, but requires network
access (contradicts offline-first) and is GPL-3.0 (license compatibility concern
if OwlBear is ever distributed as proprietary software).

**pyttsx4 and Coqui TTS are not viable.** pyttsx4 is a one-person fork with no
activity since 2023. Coqui TTS is a heavy ML framework that doesn't support
Python 3.12+ and is overkill for simple TTS output.

### Risks

| Risk | Mitigation |
|------|------------|
| pyttsx3 macOS driver deprecated | OwlBear is Windows-first; macOS not a priority |
| pyttsx3 run-loop bugs | Existing `asyncio.to_thread` wrapper isolates the daemon |
| edge-tts service discontinuation | Microsoft Edge TTS is a core browser feature; low risk |
| edge-tts GPL-3.0 contamination | Only add as optional extra, never bundle |

## 6. Recommendation (.80 confidence)

**Keep pyttsx3. No action needed now.** The risk level should be downgraded from
"Medium" to "Low" given the 2024-2025 release activity.

When voice features are actively developed (currently `someday` priority), consider
adding edge-tts as an **optional online-quality fallback** behind a config flag
(e.g., `tts_backend: pyttsx3 | edge-tts`). This preserves offline-first while
offering high-quality neural voices when network is available.

Update the config-dependency-audit to correct the stale "last release 2023" claim.

## 7. Follow-up Tasks

See kanban commands below.
