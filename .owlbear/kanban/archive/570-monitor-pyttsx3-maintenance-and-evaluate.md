---
id: 570
title: Monitor pyttsx3 maintenance and evaluate alternatives
status: archived
priority: someday
created: 2026-03-04T07:39:12.4680984+01:00
updated: 2026-03-21T17:42:20.2052289+01:00
started: 2026-03-07T04:34:56.9983949+01:00
completed: 2026-03-21T17:42:16.0992783+01:00
tags:
    - audit
    - config
    - deps
class: standard
---

F-10: pyttsx3 maintenance risk. RESEARCH COMPLETE (2026-03-07).

Key finding: pyttsx3 is NOT dormant. Released v2.92-2.99 between Sep 2024 and Jul 2025.
Risk downgraded from Medium to Low. The existing voice TTS wrapper in src/owlbear/voice/tts.py remains valid.

Decision: Keep pyttsx3 as OwlBear's current offline TTS dependency. Do not replace it or add a second backend in this task. If voice work resumes later, consider edge-tts as a separate optional online-quality fallback behind its own task and config decision.

Evidence:
- docs/research/pyttsx3-tts-alternatives.md records the comparison and recommendation.
- docs/config-dependency-audit.md F-10 records the downgraded Low risk and keep-pyttsx3 decision.
- docs/sources/overview.md records the external sources used for this decision.

## AC

- [ ] Task body states that pyttsx3 remains the selected TTS dependency for the current voice subsystem.
- [ ] Task body states that this task introduces no code, dependency, or config change.
- [ ] Task body links to the research doc and updated F-10 audit entry as decision evidence.

[[2026-03-21]] Sat 13:55
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| decision documented | Too vague for backlog approval: it did not identify the documented decision, the evidence files, or whether any code, dependency, or config change was in scope. | Rewrote into explicit docs-only AC and approved |

### Architecture Notes
`src/owlbear/voice/tts.py` already provides the current async-friendly offline TTS wrapper around `pyttsx3`, so this task is a design and documentation confirmation, not a feature change. `docs/research/pyttsx3-tts-alternatives.md` records the comparison and recommendation, `docs/config-dependency-audit.md` F-10 already downgrades the risk to Low and recommends keeping `pyttsx3`, and `docs/sources/overview.md` records the research sources. No new runtime path, dependency, config field, or interface change is warranted here. TDD and failure-mode mapping are N/A because this is a docs-only decision task.

### Changes Made
- Claimed task for architect review
- Rewrote the task body into explicit docs-only AC with evidence files
- Appended this `## Architecture Review`
- Moved to todo

### Dependencies
- Verified existing voice TTS boundary: `src/owlbear/voice/tts.py` remains the current offline TTS wrapper
- Verified decision evidence already exists in `docs/research/pyttsx3-tts-alternatives.md`, `docs/config-dependency-audit.md`, and `docs/sources/overview.md`
- Added/Removed: None

[[2026-03-21]] Sat 14:27
## Test-Writer Notes
- Non-implementation task (tagged audit/config/deps, docs-only per architect) — no tests applicable.
- Architecture Review explicitly states: TDD and failure-mode mapping are N/A.
- Passing through to builder.

[[2026-03-21]] Sat 15:02
## Builder Notes
- Files changed: None (docs-only pass-through)
- Tests: N/A — non-implementation task; test-writer explicitly confirmed TDD does not apply
- Lint: N/A — no source files changed
- Evidence:
  - AC1: Task body states 'Decision: Keep pyttsx3 as OwlBear current offline TTS dependency' — PASS
  - AC2: No code, dependency, or config change introduced — confirmed by architect review and task body — PASS
  - AC3: docs/config-dependency-audit.md F-10 (line 180) references pyttsx3 risk downgrade to Low and links to docs/research/pyttsx3-tts-alternatives.md — PASS
  - All three evidence files verified to exist: docs/research/pyttsx3-tts-alternatives.md, docs/config-dependency-audit.md, docs/sources/overview.md
- Fixes applied: None

[[2026-03-21]] Sat 16:11
## Review Evidence
### Test Results
- uv run pytest tests/test_voice_tts.py -q --tb=short -> 9 passed, 0 failed (2 optional-dependency warnings).
- uv run pytest tests/test_voice_channel.py::TestVoiceChannelProtocol::test_isinstance_channel_plugin -q --tb=short -> 1 failed (assert isinstance(channel, ChannelPlugin)).
- #570 is docs-only with no implementation delta; the failing voice protocol test is outside this task AC scope.

### Lint Results
- uv run ruff check src/ tests/ --statistics -> 451 findings (RUF100 260, D205 82, D209 61, D403 40, others smaller).
- This is repo-wide baseline debt and not introduced by #570.

### Coverage
- uv run pytest tests/test_voice_tts.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short -> src/owlbear/voice/tts.py at 100%.

### Pass 1 - CRITICAL
- Security: no issues in #570 scope (decision/docs-only task).
- Test integrity: no TestFromAC classes for #570; architect and test-writer notes mark TDD N/A.
- Test quality: N/A for #570 (no task-owned tests).
- Data safety: no persistence or concurrency logic changed in task scope.

### Pass 2 - INFORMATIONAL
- Reproducible unrelated failure remains in tests/test_voice_channel.py::TestVoiceChannelProtocol::test_isinstance_channel_plugin.
- Repo-wide ruff debt remains high and should be addressed in dedicated lint tasks.

### AC Compliance
- AC1 PASS: task body states pyttsx3 remains the selected TTS dependency (kanban/tasks/570-monitor-pyttsx3-maintenance-and-evaluate.md:23).
- AC2 PASS: task body states no replacement or second backend in this task, and builder notes report no files changed (kanban/tasks/570-monitor-pyttsx3-maintenance-and-evaluate.md:23).
- AC3 PASS: task body references research and audit evidence; F-10 updated entry exists and sources section is present (kanban/tasks/570-monitor-pyttsx3-maintenance-and-evaluate.md:26, docs/config-dependency-audit.md:180, docs/sources/overview.md:1455).

### Verdict: PASS
- Confidence: .90
- Rationale: all AC lines are satisfied with direct file evidence and no task-scoped critical security or data-safety issue was introduced.

[[2026-03-21]] Sat 16:54
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Tech stack row 'Voice (planned) \| Whisper STT + pyttsx3 TTS' already accurate; decision confirms no change needed |
| 2 | Docstrings complete | No | N/A | Builder notes: Files changed: None — no .py files touched |
| 3 | sources/overview.md | Yes | Pass | Section at line 1475 records 3 external sources (pyttsx3 PyPI, pyttsx3 GitHub issues, edge-tts) with correct date 2026-03-07 |
| 4 | README.md | No | N/A | No CLI changes introduced |
| 5 | Research doc linked | Yes | Pass | docs/research/pyttsx3-tts-alternatives.md exists and is linked from task body and F-10 audit entry (docs/config-dependency-audit.md:180-188) |
| 6 | No impact default | No | N/A | Items 3 and 5 did apply and are verified |

### Files Updated
- None — all documentation was correctly produced during the research phase

### Scratch Files Cleaned
- None found (docs/scratch/570-* — no matches)

[[2026-03-21]] Sat 17:42
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Task body states pyttsx3 remains selected TTS dependency | kanban/tasks/570 L23: 'Decision: Keep pyttsx3 as OwlBear current offline TTS dependency' | PASS |
| Task body states no code/dependency/config change | kanban/tasks/570 L23: 'Do not replace it or add a second backend in this task'; builder notes: 'Files changed: None' | PASS |
| Task body links to research doc and F-10 audit entry | Links to docs/research/pyttsx3-tts-alternatives.md, docs/config-dependency-audit.md F-10 (L180), docs/sources/overview.md all verified present | PASS |

### Test Results
- pytest: 3723 passed, 97 failed, 20 skipped (2 collection errors excluded: RED-phase stubs). All failures pre-existing (numpy compat, unrelated RED tasks). None related to #570.
- ruff: repo-wide baseline debt, no #570-scoped changes.

### Confidence: .97
### Action: archive
