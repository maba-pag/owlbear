---
id: 1108
title: Mode-6 rename collision guard in attempt_repair
status: archived
priority: medium
created: 2026-04-22T23:36:37.892632+00:00
updated: 2026-04-23T09:25:37.544565+00:00
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

[[2026-04-23]]
## Research
- Research doc: .owlbear/research/1108-mode6-rename-collision-guard.md
- Sources: 6 studied (all codebase-internal), 4 high-relevance
- Recommendation: Add `new_path.exists()` guard before `path.replace(new_path)` in mode-6 repair; quarantine on collision (confidence: 0.90)
- Follow-up tasks created: #1109 (Add exists-guard to mode-6 rename in attempt_repair)
- Decision requests: none (T1 — autonomous bug fix)

## Challenge Results
- Challenger: SKIPPED — trivial single-option bug fix with no design trade-off ambiguity
[[2026-04-23]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Research into mode-6 rename collision only |
| Interface clarity | N/A | Research deliverable, no code interface |
| Dependency correctness | PASS | No dependencies; #1109 correctly depends on this |
| Module layering | N/A | Research deliverable |
| TDD compliance | N/A | Research deliverable |
| KISS/YAGNI | PASS | Focused research, well-scoped |
| Premise challenge | PASS | Bug verified — `path.replace(new_path)` at corruption.py:394 with no existence check; `Path.replace()` silently overwrites; `scan_and_fix` dedup uses filename-prefix, not frontmatter, so doesn't prevent the collision |
| Pattern consistency | N/A | Research deliverable |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | kanban domain only |

### Codebase Verification
- Confirmed `path.replace(new_path)` at `serve/kanban/src/owlbear_kanban/corruption.py:394` — no existence guard
- Confirmed `_quarantine()` inner helper at line 324 hard-codes detail to `"quarantined to {path}"` — #1109 AC-2 will need builder to call `move_to_quarantine` directly (noted for #1109 review)
- Confirmed `move_to_quarantine` at `storage.py:427` also uses unchecked `replace()` — low risk (quarantine is last-resort), separate concern if needed
- Confirmed function is `scan_and_fix` not `scan_and_repair` as stated in research doc (cosmetic error, analysis unaffected)

### Challenge Results
- Challenger: reconsider (confidence 0.58)
- Architect response: OVERRIDDEN with rebuttal — challenger concerns are either about #1109 (separate architecture review) or minor documentation blemishes; core finding independently verified against codebase; recommendation is KISS-aligned for laptop-resident single-user tool

### Verdict: APPROVE
### Action Taken: Tagged `research` for non-impl pass-through. Advanced to todo.
[[2026-04-23]]
## Test-Writer Notes
- Non-implementation task (research deliverable) — no tests applicable.
- Architect explicitly flagged for non-impl pass-through in Architecture Review section.
- No AC exists in this task; no testable Python interfaces introduced.
- Implementation AC and test guidance live in #1109 (Add exists-guard to mode-6 rename in attempt_repair), which has tag `tdd:red` and is currently in `research` status — it must progress through the pipeline to reach test-writer.
- Passing through to builder.
[[2026-04-23]]
## Archived
Research-only deliverable completed. Implementation scope lives in #1109. All pipeline stages (research, architect, test-writer) passed through with "no work needed." Archived during manual board triage.