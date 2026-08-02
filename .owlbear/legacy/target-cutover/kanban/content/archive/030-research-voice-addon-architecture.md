---
id: 30
title: Research voice addon architecture
status: archived
priority: medium
created: 2026-03-26 18:05:24.833345+01:00
updated: 2026-03-27 12:40:23.599484+01:00
started: 2026-03-27 12:38:58.653198+01:00
completed: 2026-03-27 12:38:58.653198+01:00
tags:
- phase-3
- scope:voice
- research
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Design the voice component as a standalone addon that integrates with owlbear without being tightly coupled.

## Acceptance Criteria

- [ ] Research current local voice models (Whisper variants, Moonshine, etc.)
- [ ] Decide: standalone app started by owlbear vs independent process
- [ ] Design the interface between voice and owlbear (pipes, MCP server, or API)
- [ ] Evaluate if integration is simple enough to be worth it vs staying fully standalone
- [ ] Assess resource usage (local model on laptop - memory, CPU, battery)
- [ ] Write findings to docs/research/voice-addon-architecture.md
- [ ] Create follow-up tasks

## Context

v1 had voice as an integrated module (Whisper STT + pyttsx3 TTS). v2 treats voice as a separate system. This task explores whether a lightweight integration makes sense (e.g., owlbear spawns the voice process, voice feeds prompts to owlbear) vs fully standalone.

[[2026-03-26]] Thu 18:58

## Research

Recommend standalone voice addon process with stdio JSON protocol (.85 confidence).

**Key findings:**

- STT: Moonshine Voice (Small Streaming) â€” sub-200ms latency, built-in VAD, validated by v1
- TTS: Kokoro (82M, Apache-2.0) primary, pyttsx3 fallback â€” best quality/license combo
- Architecture: Owlbear spawns voice process, communicates via line-delimited JSON on stdio
- Resource: ~350MB (minimal) to ~850MB (with Kokoro) RAM on 16GB laptop â€” workable
- Piper TTS rejected: GPL-3.0 license incompatible with MIT project

**Follow-up tasks created at ideation:**

- #49 Voice addon stdio protocol
- #50 Voice addon STT with Moonshine
- #51 Voice addon TTS with Kokoro + pyttsx3 fallback
- #52 owlbear-voice workspace package

See docs/research/voice-addon-architecture.md for full analysis.

[[2026-03-26]] Thu 19:22

## Architecture Review

**Verdict:** Approve

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Research current local voice models | Met: Doc 3.1 (STT) + 3.2 (TTS) with trade-off matrices | None |
| Decide standalone vs independent process | Met: Doc 3.3 evaluates 4 options, selects stdio pipes (.85) | None |
| Design interface between voice and owlbear | Met: Doc 3.3 + 4, line-delimited JSON protocol specified | None |
| Evaluate if integration is worth it | Met: Doc 3.5 worth-it matrix, clear verdict (.80) | None |
| Assess resource usage | Met: Doc 3.4, two configs (350MB minimal, 850MB with Kokoro) | None |
| Write findings to research doc | Met: docs/research/voice-addon-architecture.md exists, complete | None |
| Create follow-up tasks | Met: #49-#52 exist at ideation | None |

### Architecture Notes

Research is thorough. Good catch on Piper GPL-3.0 license exclusion. Stdio pipes recommendation is sound: process isolation keeps ML model failures contained, minimal IPC overhead. Follow-up task decomposition (#49 protocol, #50 STT, #51 TTS, #52 package scaffold) is clean single-responsibility split. No architectural concerns.

### Changes Made

- Approved task, moved to todo

### Dependencies

- Verified: no upstream dependencies
- Follow-ups (#49-#52) are independent of this task (at ideation, awaiting their own architect gate)

[[2026-03-26]] Thu 20:08

## Test-Writer Notes

- Non-implementation task (tagged research) â€” no tests applicable.
- Passing through to builder.

[[2026-03-27]] Fri 03:22

## Builder Notes

- Non-implementation task (research tag) — no code changes needed.
- Passing through to review.

[[2026-03-27]] Fri 05:17

## Review Evidence

## Review: #30 - Research voice addon architecture

### Test Results

- pytest: not applicable. This is a research-only task with no task-scoped automated tests or TestFromAC classes.

### Lint Results

- ruff: not applicable. The reviewed artifacts are markdown and kanban metadata only.

### Coverage

- not applicable.

### Pass 1 - CRITICAL

- Test-Writer AC Coverage: not applicable. Task 30 is a research card and Test-Writer Notes correctly marked it as non-implementation.
- Security Review: no security issues found in the research content itself.
- Test Integrity: not applicable. No TestFromAC classes or builder-authored test edits exist for this task.
- Test Quality: not applicable.
- Data Safety: no data safety issues found in the research content itself.
- Implementation-Aware Test Gaps:
  docs/research/voice-addon-architecture.md:111-118 ends with only a fenced block of kanban create commands. The research-doc guardrails require a numbered Follow-up Tasks list with title, priority rationale, dependencies, one-line AC, concrete create commands, and recorded created task IDs.
  git status shows docs/research/voice-addon-architecture.md as untracked. The primary deliverable exists in the worktree but is not cleanly handed off as a tracked artifact.
  kanban/tasks/030-research-voice-addon-architecture.md is contaminated by unrelated Copilot Memory review content. The task body is a voice research card at lines 15-25, but repeated later sections at lines 75-95, 104-124, 129-149, and 154-174 discuss Copilot Memory and docs/research/copilot-memory.md. Downstream agents read task bodies for context, so this is a blocking metadata defect.

### Pass 2 - INFORMATIONAL

- The core voice research is otherwise strong and maps to the intended architecture questions.
- Follow-up task bodies do link back to the research doc: task 49 line 26, task 50 line 39, task 51 line 36, task 52 line 27.

### AC Compliance

- Research current local voice models: PASS. docs/research/voice-addon-architecture.md sections 3.1 and 3.2 compare Moonshine, Whisper, Kokoro, pyttsx3, Piper, and Silero.
- Decide standalone app started by owlbear versus independent process: PASS. Section 3.3 evaluates four options and recommends a standalone process with stdio pipes.
- Design the interface between voice and owlbear: PASS. Sections 3.3 and 4 specify line-delimited JSON on stdio.
- Evaluate whether integration is worth it versus staying fully standalone: PASS. Section 3.5 includes a worth-it matrix and recommendation.
- Assess resource usage: PASS. Section 3.4 provides RAM, CPU, and battery estimates for minimal and higher-quality configurations.
- Write findings to docs/research/voice-addon-architecture.md: FAIL. The file exists but is currently untracked in git status, so the deliverable is not cleanly handed off.
- Create follow-up tasks: FAIL. Tasks 49-52 exist, but the research doc Follow-up Tasks section does not satisfy repository guardrails and task 30 body context is corrupted by unrelated Copilot Memory review text.

### Verdict: FAIL

### Action Taken

- Returning task 30 to todo for research-doc handoff fixes and task-body cleanup.

[[2026-03-27]] Fri 07:49

## Test-Writer Notes (Rerun)

- Non-implementation task (tagged research) -- no tests applicable.
- Passing through to builder.

[[2026-03-27]] Fri 08:24

## Builder Notes

- Files changed: docs/research/voice-addon-architecture.md, kanban/tasks/030-research-voice-addon-architecture.md
- Tests: not applicable (research-only task; no TestFromAC class for this task)
- Lint: markdown content updated; no python lint scope for this task
- Evidence: follow-up section now includes numbered tasks with priority rationale, dependencies, one-line AC, commands, and created IDs (#49-#52); unrelated repeated Copilot Memory architecture-review blocks removed from task body
- Fixes applied: normalized follow-up handoff format and cleaned task-body contamination from unrelated review content

[[2026-03-27]] Fri 10:22

## Review Evidence

## Review: #30 - Research voice addon architecture

### Test Results

- Scoped pytest on the existing rename regression slice reported 4 passed, 24 deselected in 0.03s.
- The executed tests directly covered the two files changed in this review cycle: the task 30 body rename entries and the voice-addon-architecture research doc rename entries in the task-64 rename regression test module.
- No task-scoped TestFromAC classes exist for task 30; this is a research-only card.

### Lint Results

- Scoped ruff on the task-64 rename regression test module passed.

### Coverage

- Not applicable. Task 30 has no Python implementation deliverable.

### Pass 1 - CRITICAL

- Test-Writer AC Coverage: not applicable. Task 30 is a research card and the Test-Writer Notes correctly mark it as non-implementation.
- Security Review: no security issues found in the research content or kanban metadata.
- Test Integrity: not applicable. No TestFromAC classes or builder-authored test edits exist for this task.
- Test Quality: not applicable.
- Data Safety: no data safety issues found.
- Implementation-Aware Validation:
  - The prior handoff failure is fixed. docs/research/voice-addon-architecture.md lines 111-163 now contain a numbered Follow-up Tasks section with priority rationale, dependencies, one-line AC, create command, and created task ID for all four follow-ups.
  - The primary deliverable is tracked. git ls-files confirmed docs/research/voice-addon-architecture.md is in the repository.
  - The live task body is voice-scoped and clean. Current Copilot Memory mentions are only historical review notes documenting the prior failure at task lines 128-131, 146, and 168, not active contamination.
  - Follow-up task traceability is present: task 49 line 26, task 50 line 39, task 51 line 40, and task 52 line 30 all link back to docs/research/voice-addon-architecture.md.

### Pass 2 - INFORMATIONAL

- The task body still contains a few mojibake sequences in older summary bullets at lines 43-46 and 93. The research doc itself is clean, and the issue does not affect task traceability or AC completion.

### AC Compliance

- Research current local voice models: PASS. docs/research/voice-addon-architecture.md lines 24-51 compare Moonshine, Whisper, Kokoro, pyttsx3, Piper, and Silero.
- Decide standalone app started by owlbear versus independent process: PASS. docs/research/voice-addon-architecture.md lines 53-69 evaluate four architectures and recommend a standalone process with stdio pipes.
- Design the interface between voice and owlbear: PASS. docs/research/voice-addon-architecture.md lines 64-69 and 97-104 specify line-delimited JSON over stdio.
- Evaluate whether integration is worth it versus staying fully standalone: PASS. docs/research/voice-addon-architecture.md lines 84-93 include the worth-it matrix and recommendation.
- Assess resource usage: PASS. docs/research/voice-addon-architecture.md lines 71-82 provide RAM, CPU, and battery estimates.
- Write findings to docs/research/voice-addon-architecture.md: PASS. The file exists, is tracked, and sections 1-5 are complete.
- Create follow-up tasks: PASS. docs/research/voice-addon-architecture.md lines 111-163 record four follow-up tasks and created IDs, and tasks 49-52 exist with backlinks to this research doc.

### Verdict: PASS

### Action Taken

- Advancing task 30 to docs.

[[2026-03-27]] Fri 12:38

## Audit

Confidence: .97 Action: archive

[[2026-03-27]] Fri 12:38

### AC Verification

All 7 AC items PASS:

1. Research local voice models: Doc 3.1 STT (Moonshine/Whisper), 3.2 TTS (Kokoro/pyttsx3/Piper) with trade-off matrices
2. Decide standalone vs independent: Doc 3.3 evaluates 4 architectures, selects stdio pipes (.85)
3. Design interface: Doc 3.3 + 4 specify line-delimited JSON on stdio
4. Evaluate integration worth: Doc 3.5 worth-it matrix, verdict worth building (.80)
5. Assess resource usage: Doc 3.4 at 350MB minimal, 850MB with Kokoro on 16GB laptop
6. Write findings to research doc: docs/research/voice-addon-architecture.md tracked + committed
7. Create follow-up tasks: #49 (ideation), #50 (todo), #51 (backlog), #52 (backlog) all exist with backlinks

### Research Task Checklist

- Research doc exists: PASS
- Follow-up tasks created on board: PASS (#49-#52)
- Follow-up tasks link back: PASS (reviewer Pass 1 confirmed)
- Follow-up section format: PASS (numbered, priority/deps/AC/commands/IDs)

### Test Results

- pytest: 82 passed, 36 failed, 2 collection errors. All failures from other tasks. No task-30-related failures.
- ruff: not applicable (no Python source deliverable)

### AC Quality Score: 4/5

AC specific with 7 clear items. Could have specified evaluation criteria more granularly but intent was clear.

### Confidence: .97

### Action: archive

[[2026-03-27]] Fri 12:38

### AC Verification

All 7 AC items PASS:

1. Research local voice models: Doc 3.1 STT (Moonshine/Whisper), 3.2 TTS (Kokoro/pyttsx3/Piper) with trade-off matrices
2. Decide standalone vs independent: Doc 3.3 evaluates 4 architectures, selects stdio pipes (.85)
3. Design interface: Doc 3.3 + 4 specify line-delimited JSON on stdio
4. Evaluate integration worth: Doc 3.5 worth-it matrix, verdict worth building (.80)
5. Assess resource usage: Doc 3.4 at 350MB minimal, 850MB with Kokoro on 16GB laptop
6. Write findings to research doc: docs/research/voice-addon-architecture.md tracked + committed
7. Create follow-up tasks: #49 (ideation), #50 (todo), #51 (backlog), #52 (backlog) all exist with backlinks

### Research Task Checklist

- Research doc exists: PASS
- Follow-up tasks created on board: PASS (#49-#52)
- Follow-up tasks link back: PASS (reviewer Pass 1 confirmed)
- Follow-up section format: PASS (numbered, priority/deps/AC/commands/IDs)

### Test Results

- pytest: 82 passed, 36 failed, 2 collection errors. All failures from other tasks. No task-30-related failures.
- ruff: not applicable (no Python source deliverable)

### AC Quality Score: 4/5

AC specific with 7 clear items. Could have specified evaluation criteria more granularly but intent was clear.

### Confidence: .97

### Action: archive

[[2026-03-27]] Fri 12:40

## Commits

3d1709e chore: archive task #30 voice addon research (kanban board file)
