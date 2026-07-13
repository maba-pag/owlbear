---
id: 548
title: Verify exit code 2 routing via -File invocation in subagent context
status: archived
priority: medium
created: 2026-04-02 14:52:11.663043+02:00
updated: 2026-04-04 18:08:53.301537+02:00
started: 2026-04-04 18:08:53.301537+02:00
completed: 2026-04-04 18:08:53.301537+02:00
tags:
- scope:agents
- hooks
- research
- type:test
class: standard
archival_reason: completed
archival_refs: []
---

## Context
See docs/research/posttooluse-subagent-output-routing.md s3.4 (task #532).
The #532 empirical spike found exit code 2 was NOT model-facing when using powershell -Command one-liners. However, #210 uses powershell -File which handles exit codes differently. PS 5.1 -File mode propagates script exit codes as process exit codes. The hooks engine may correctly classify exit code 2 as BlockingError with -File.

## Acceptance Criteria
- [x] Create a minimal .ps1 script that reads stdin, exits with code 2 and writes to stderr
- [x] Add as PostToolUse hook to builder.agent.md using -File invocation
- [x] Record hooks output channel classification: **NonBlockingError**
- [x] Record whether stderr content appears in Chat Debug View: **does NOT appear**
- [x] Remove test hook after verification (confirmed removed; probe-exit2.ps1 deleted)
- [ ] Update docs/research/exit-code-2-file-mode-routing.md:
  - Change status from "Theoretical complete, empirical pending" to "Complete"
  - s3.2: Add empirical result row: -File mode yields NonBlockingError (same as -Command)
  - s3.5 track record: #548 prediction=BlockingError, outcome=NonBlockingError (0-for-3)
  - s4: .60 prediction disproven; exit code 2 not viable in PostToolUse subagent context via either PS 5.1 mode
- [ ] Update docs/research/posttooluse-subagent-output-routing.md:
  - s3.4: Add -File verification (#548) confirmed NonBlockingError, scoped to PostToolUse subagent context
  - s4: Replace "Do not dismiss exit code 2 entirely" sentence with conclusion citing #548

[[2026-04-02]] Thu 17:40
## Research
Theoretical analysis complete. Doc: docs/research/exit-code-2-file-mode-routing.md
Confidence: .60 (lowered from .85 after challenge)

Key finding: PS 5.1 -Command mode converts exit 2 to process exit code 1, explaining #532 NonBlockingError. -File mode preserves exit codes per MS docs, predicting BlockingError for exit 2.

Risks: hooks engine spawn intermediary (cmd.exe wrapping), unproven causal attribution of #532.

Action request: docs/decisions/pending/548-exit-code-2-file-verification.md
User must perform empirical spike to confirm prediction.

[[2026-04-02]] Thu 17:40
## Challenge Results
- Challenger recommendation: reconsider
- Confidence in original: .55
- Key challenges: C1 (hooks engine spawn intermediary), C2 (causal attribution assumed), C3 (.85 too high given 0-for-2 track)
- Researcher response: accepted C1/C2/C3. Lowered confidence to .60.

## Action Completed

Output: 2026-04-02 19:03:54.272 [info] [#6] [PostToolUse] Completed (NonBlockingError) in 1736ms
2026-04-02 19:03:54.272 [info] [#6] [PostToolUse] Output: PROBE_EXIT2_FILE_548: tool=create_file. ; 'PROBE_EXIT2_FILE_548' does NOT appear in debug chat log, only in GH CP Chat Hooks Output.

[[2026-04-04]] Fri 07:45
## Architecture Review
See docs/scratch/548-architect.md for full evidence.

### Verdict: APPROVED (after refinement)
Refined AC #6 into section-level update instructions for both research docs with scope qualifiers. Marked AC 1-5 complete. Advanced to todo.

[[2026-04-04]] Sat 16:00
## Test-Writer Notes
- Non-implementation task (tagged research, type:test) — no tests applicable.
- Remaining AC items are .md documentation updates only (docs/research/exit-code-2-file-mode-routing.md, docs/research/posttooluse-subagent-output-routing.md).
- Passing through to builder.

[[2026-04-04]] Sat 16:23
## Builder Notes\n\n### Files Changed\n- docs/research/exit-code-2-file-mode-routing.md (4 edits)\n- docs/research/posttooluse-subagent-output-routing.md (2 edits)\n\n### Changes Applied\n1. exit-code-2-file-mode-routing.md status → \"Complete\"\n2. s3.2 renamed + empirical row added: -File yields NonBlockingError (#548)\n3. s3.5 track record: #548 outcome = NonBlockingError (0-for-3)\n4. s4 replaced with Conclusion: .60 prediction disproven, exit code 2 not viable via either PS 5.1 mode\n5. posttooluse-subagent-output-routing.md s3.4: -File verification paragraph added citing #548\n6. posttooluse-subagent-output-routing.md s4: replaced \"Do not dismiss exit code 2 entirely\" with conclusion citing #532 and #548\n\n### Test/Lint\nDocumentation-only task — no tests applicable (confirmed by test-writer notes).\nNo code changed.

[[2026-04-04]] Sat 16:57
Documentation-only task. Both target research docs verified against all AC sub-items. exit-code-2-file-mode-routing.md: status→Complete, s3.2 empirical row added, s3.5 #548 outcome row updated, s4 replaced with Conclusion. posttooluse-subagent-output-routing.md: s3.4 -File verification paragraph added (scoped to PostToolUse subagent context), s4 conclusion updated citing #532 and #548. No tests applicable (test-writer confirmed). Builder process CLEAN (1 note cycle). All AC items satisfied. Confidence: .96 → PASS.

[[2026-04-04]] Sat 17:15
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Documentation-only task; no code changed (confirmed by builder and test-writer notes) |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | Yes | Updated | MS PS 5.1 `about_PowerShell_exe` cited in research s2 table but absent from sources/overview.md — added `## Exit Code 2 via -File Invocation Routing (Task #548)` section; committed 2978b38 |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Verified | exit-code-2-file-mode-routing.md: status=Complete ✓, s3.2 empirical row present ✓, s3.5 #548 outcome=NonBlockingError (0-for-3) ✓, s4 Conclusion present ✓. posttooluse-subagent-output-routing.md: s3.4 -File verification paragraph present ✓, s4 Exit code 2 paragraph cites #532 and #548 ✓ |

### Review Evidence Note
No `## Review Evidence` heading present. The [[2026-04-04]] Sat 16:57 note contains substantive review content (AC verification, confidence .96 → PASS, builder process CLEAN). Task status transition to docs confirms reviewer approval. Accepted as sufficient.

### Files Updated
- docs/sources/overview.md (added #548 MS PS 5.1 attribution, commit 2978b38)

### Scratch Files Cleaned
- docs/scratch/548-* — none found (already cleaned)

[[2026-04-04]] Sat 18:08
## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| Create .ps1 script (exit 2, stderr) | Task body Action Completed: hook output logged | PASS |\n| Add as PostToolUse hook (-File) | Task body: hook invocation #6 logged | PASS |\n| Record classification: NonBlockingError | Task body: Completed (NonBlockingError) in 1736ms | PASS |\n| Record stderr in Debug View: does NOT appear | Task body: does NOT appear in debug chat log | PASS |\n| Remove test hook after verification | Task body: confirmed removed, probe-exit2.ps1 deleted | PASS |\n| Update exit-code-2-file-mode-routing.md (4 sub-items) | Diff verified: status to Complete, s3.2 empirical row, s3.5 0-for-3, s4 Conclusion | PASS |\n| Update posttooluse-subagent-output-routing.md (2 sub-items) | Diff verified: s3.4 -File paragraph, s4 conclusion citing #532 and #548 | PASS |\n\n### Test Results\npytest: 1323 passed, 159 failed, 1 error (all pre-existing, none in task scope, docs-only task)\nruff: 4 pre-existing violations, none in task scope\n\n### Architect Quality: 4/5\nOriginal AC6/7 vague. Architect refined into section-level sub-items. Adequate.\n\n### Deduction Breakdown\nMissing Review Evidence heading: -0.02 (content present but non-standard location)\nBuilder did not commit deliverables (committed as leftover 3491ed5)\n\n### Confidence: .98\n### Action: archive
