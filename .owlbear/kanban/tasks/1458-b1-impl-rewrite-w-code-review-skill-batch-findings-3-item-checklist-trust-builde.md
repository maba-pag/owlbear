---
id: 1458
title: 'B1-impl: Rewrite w-code-review skill — batch findings, 3-item checklist, trust
  builder evidence'
status: review
priority: critical
created: 2026-05-08T19:47:09.269589+00:00
updated: 2026-05-09T04:16:01.148002+00:00
tags:
- pipeline
- ws-reviewer
- scope:agents
- agent
parent: 1403
depends_on:
- 1407
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Rewrite `share/skills/w-code-review/SKILL.md` per research in `.owlbear/research/1407-reviewer-rewrite.md`. Key changes: (1) replace first-failure gating with batch-all-findings, (2) replace 12-check system with 3-item checklist (AC→code mapping, test→AC alignment, proof sufficiency), (3) read builder quality-runner output instead of re-executing, (4) remove TestFromAC immutability rule, (5) remove security review (CI/SAST handles), (6) output template: Review Evidence (findings) + Observations (opinions), (7) PASS case one-line confirmation. Also update `r-pipeline-protocol` trust model and reviewer contract section. Update code-reader consumer contract within w-code-review.


## Acceptance Criteria

- [ ] Code-reader consumer contract in `w-code-review/SKILL.md` defines output sections aligned with 3-item checklist (AC→code mapping, test→AC alignment, proof sufficiency + observations); old 8-section format (`test_writer-audit`, `security_review`, `test_integrity`, `test_quality`, `data_safety`, `test_gaps`, `necessity_check`, `informational`) removed (td:0)
- [ ] Depth-aware dispatch table in Step 2 references current step numbering only — no references to old §5.0 or obsolete step numbers (td:0)
- [ ] No redundant steps: the scoped 3-item checklist is the sole operative review workflow; any overlapping Steps that duplicate checklist coverage are consolidated (td:0)
- [ ] `r-pipeline-protocol` Reviewer Contract section uses D2 trust-the-builder language; no "never trust self-reports" phrasing remains (td:0)
- [ ] Skill file ≤200 lines (research target: 120–150; upper bound allows builder flexibility) (td:0)
- [ ] Output template has exactly two verdict-adjacent sections: `Review Evidence` (AC-cited findings) and `Observations` (non-blocking opinions); PASS verdict includes one-line confirmation template (td:0)

[[2026-05-09]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One logical change: reviewer model alignment across w-code-review skill + r-pipeline-protocol contract |
| Interface clarity | PASS | Code-reader consumer contract is the key interface; AC specifies old sections to remove and new 3-item alignment |
| Dependency correctness | PASS | #1407 research complete (doc on disk), h-ac-quality skill exists (A1 done), CI/SAST baseline confirmed (#1413 research complete). All brief prerequisites satisfied. |
| Module layering | PASS | N/A — skill files, no code imports |
| TDD compliance | PASS | Non-impl task; `agent` pass-through tag added |
| KISS/YAGNI | PASS | Research targets 120–150 lines from current ~310; AC caps at ≤200 with flexibility |
| Premise challenge | PASS | Research #1407 substantiates need; current skill has contradictory code-reader contract (claims 3-item model but lists 8 old sections) |
| Pattern consistency | PASS | Follows established skill file patterns |
| Security surface | PASS | N/A — no system boundaries |
| Single domain | PASS | Pipeline skills domain only |

### Codebase Evidence

- `w-code-review/SKILL.md` lines 118–127: code-reader contract still lists old 8 sections (`security_review`, `data_safety`, `necessity_check`, etc.) contradicting the "3-item checklist model" claim on line 117
- `w-code-review/SKILL.md` line 71: depth-aware dispatch table references `TestFromAC audit (§5.0)` — old step numbering
- `r-pipeline-protocol/SKILL.md` lines 68–77: Evidence Principles and Reviewer Contract already use D2 trust-the-builder language; no "never trust self-reports" found — protocol appears aligned, AC4 is a verification gate

### Challenge Results
- Challenger: SKIPPED — all AC lines td:0

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Added 6 AC lines (all td:0), added `agent` pass-through tag, advanced to todo.
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- All AC lines annotated `(td:0)`.
- Passing through to builder.
[[2026-05-09]]
## Builder Notes
- Implementation: rewrote `share/skills/w-code-review/SKILL.md` to the D2 reviewer model (batch-all-findings, builder-evidence-first, scoped 3-item checklist, updated code-reader consumer contract).
- AC alignment evidence:
  - Removed obsolete 8-section code-reader output contract and replaced with 4 sections: `ac_to_code_mapping`, `test_to_ac_alignment`, `proof_sufficiency`, `observations`.
  - Depth-aware dispatch table now references current step flow only; no legacy `§5.0` or old-step references remain.
  - Workflow consolidated so the 3-item checklist is the sole operative review path.
  - Output template now uses exactly two verdict-adjacent sections: `Review Evidence` and `Observations`, with one-line PASS confirmation template.
  - File is within size cap: 164 lines (<=200).
  - `share/skills/r-pipeline-protocol/SKILL.md` already satisfied trust-model AC (`Reviewer Contract (D2 trust-the-builder)` present; no "never trust self-reports" phrase), so no protocol edit was needed.
- Quality evidence (quality-runner):
  - Tests: N/A (td:0 markdown skill task)
  - Lint: clean (markdownlint exit 0) on `share/skills/w-code-review/SKILL.md` and `share/skills/r-pipeline-protocol/SKILL.md`
  - Coverage: N/A (non-executable markdown)
- Commit: `1a757cd8` — `docs: rewrite reviewer workflow for D2 trust model (#1458, builder)`
- Files changed: `share/skills/w-code-review/SKILL.md`