---
id: 746
title: 'P1-01: Archive voice I/O research docs to handoff location'
status: docs
priority: needed
created: '2026-04-10T10:36:20.117217+00:00'
updated: '2026-04-11T13:22:45.392802+00:00'
tags:
- phase-1
- type:archive
- cleanup
- scope-reduction
parent: 745
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context
Brief: see parent #745. Scratch tier — straightforward file move.

Voice research docs are valuable to the future dictation project. Archive them under the existing handoff brief before the deletion pass removes the originals.

## Acceptance Criteria
1. All 11 voice I/O research docs copied to `.owlbear/briefs/draft-voice-rethink/research-archive/`:
   - `voice-addon-architecture.md`, `voice-addon-stt-moonshine.md`, `voice-channel-import.md`, `voice-io.md`, `voice-panel-handbook.md`, `voice-process-manager.md`, `voice-protocol-models.md`, `voice-stdio-protocol.md`, `voice-tts-kokoro-pyttsx3.md`, `moonshine-streaming.md`, `moonshine-vs-whisper.md`
2. Originals deleted from `.owlbear/research/`
3. Handoff doc `.owlbear/briefs/draft-voice-rethink/handoff-dictation-project.md` updated with archive manifest listing all moved files

## CRITICAL
Do NOT touch `voice-panel-handbook.md` in `share/skills/` — that is the ideation voice panel, NOT voice I/O. Only the `.owlbear/research/voice-panel-handbook.md` copy is in scope.

## Files
- Source: `.owlbear/research/voice-*.md`, `.owlbear/research/moonshine-*.md`
- Target: `.owlbear/briefs/draft-voice-rethink/research-archive/`
- Edit: `.owlbear/briefs/draft-voice-rethink/handoff-dictation-project.md`

[[2026-04-11]]
## Test-Writer Notes

**Test file:** `tests/test_archive_voice_research_746.py`
**Class:** `TestFromAC_OriginalsDeleted`
**Total:** 11 tests, all FAIL ✓
**Ruff:** clean

### AC Coverage

| AC | Coverage | Notes |
|----|----------|-------|
| AC1: 11 files copied to research-archive/ | Pre-completed | All 11 files + voicechannel-adapter.md already present — no RED tests possible |
| AC2: Originals deleted from .owlbear/research/ | 11 tests (all FAIL) | One per file, asserting non-existence |
| AC3: Handoff doc updated with archive manifest | Pre-completed | ## Research Archive table already present in handoff doc with all 11 entries |

### Test categories
- **Error/state** (11): assert-not-exists for each of the 11 source files still in `.owlbear/research/`

### Pre-completed state (verified on HEAD)
- AC1: research-archive/ already contains all 11 + voicechannel-adapter.md (12 total)
- AC3: handoff-dictation-project.md already has full ## Research Archive manifest table
- Only AC2 (delete originals) is outstanding — all 11 originals confirmed still present in .owlbear/research/

### Fail confirmation
pytest: **0 passed, 11 failed** on current HEAD
[[2026-04-11]]
## Builder Notes
- Deleted all 11 voice I/O research originals from `.owlbear/research/` (AC2)
- AC1 (archive copies) and AC3 (handoff manifest) were pre-completed
- Confirmed `share/skills/h-voice-panel/` untouched (ideation voice panel preserved)
- pytest: 11 passed, 0 failed — all `TestFromAC_OriginalsDeleted` tests GREEN
[[2026-04-11]]
## Builder Notes
- Task arrived at `review` with all AC already satisfied (prior builder completed).
- Verified: pytest 11 passed, 0 failed on `tests/test_archive_voice_research_746.py`.
- No changes needed — releasing claim without action.
[[2026-04-11]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 0a | Review Evidence present | — | **BLOCKED** | `## Review Evidence` section absent from task body |

### Verdict
Rejected at pre-flight. The reviewer did not append the mandatory `## Review Evidence` section before advancing to `docs`. The second Builder Notes block confirms tests passed but does not substitute for the structured evidence section required by the pipeline protocol.

### Files Updated
None (rejected before assessment)

### Scratch Files Cleaned
None found (`.owlbear/scratch/746-*` — no matches)
[[2026-04-11]]
## Review Evidence

### Tests
pytest `tests/test_archive_voice_research_746.py`: **11 passed, 0 failed** (exit 0)

### Lint
ruff `tests/test_archive_voice_research_746.py`: **clean** (exit 0)

### Coverage
N/A — no source modules modified; task is pure filesystem deletion.

### TestFromAC Integrity

| Original Test | Change Made | Assessment |
|---|---|---|
| test_voice_addon_architecture_deleted_from_research | None | PRESERVED |
| test_voice_addon_stt_moonshine_deleted_from_research | None | PRESERVED |
| test_voice_channel_import_deleted_from_research | None | PRESERVED |
| test_voice_io_deleted_from_research | None | PRESERVED |
| test_voice_panel_handbook_deleted_from_research | None | PRESERVED |
| test_voice_process_manager_deleted_from_research | None | PRESERVED |
| test_voice_protocol_models_deleted_from_research | None | PRESERVED |
| test_voice_stdio_protocol_deleted_from_research | None | PRESERVED |
| test_voice_tts_kokoro_pyttsx3_deleted_from_research | None | PRESERVED |
| test_moonshine_streaming_deleted_from_research | None | PRESERVED |
| test_moonshine_vs_whisper_deleted_from_research | None | PRESERVED |

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1: 11 files copied to research-archive/ | 12 files confirmed present in `.owlbear/briefs/draft-voice-rethink/research-archive/` (11 required + voicechannel-adapter.md) | Pre-completed — no test required | PASS |
| AC2: Originals deleted from .owlbear/research/ | file_search for `voice-*.md` and `moonshine-*.md` in `.owlbear/research/` returns 0 results; 11 tests assert non-existence — all pass | TestFromAC_OriginalsDeleted (11 tests) | PASS |
| AC3: Handoff doc updated with archive manifest | `## Research Archive` heading confirmed at line 135; `voice-addon-architecture.md` entry confirmed at line 141 in `handoff-dictation-project.md` | Pre-completed — no test required | PASS |
| CRITICAL: share/skills/h-voice-panel/ untouched | file_search confirms only `SKILL.md` present — no deletions | N/A | PASS |

### Test Quality

| Dimension | Rating | Notes |
|---|---|---|
| Assertion specificity | STRONG | `assert not path.exists()` — precise, would fail if file still present |
| Negative/error-path coverage | STRONG | All 11 paths covered individually |
| Mutation resilience | STRONG | Any un-deleted file causes immediate test failure |
| Test independence | STRONG | No fixtures, no shared mutable state |
| Descriptive names | STRONG | Names identify the exact file and operation |

### Builder Process Quality
Two `## Builder Notes` sections: first builder implemented the deletion; second builder arrived post-completion, verified tests, and released without changes. No loop pattern — distinct approaches, non-overlapping work.

### Security
Pure file deletion. No code changes, no injection surface, no new dependencies. No OWASP concerns.

### Deductions
None.

### Verdict
**PASS #746 → docs | confidence .97**