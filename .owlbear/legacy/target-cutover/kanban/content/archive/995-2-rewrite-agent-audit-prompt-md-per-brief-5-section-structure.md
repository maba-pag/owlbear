---
id: 995
title: '2: Rewrite agent-audit.prompt.md per Brief 5-section structure'
status: archived
priority: medium
created: 2026-04-18T21:23:39.614381+00:00
updated: 2026-04-19T13:23:52.961303+00:00
tags:
- type:docs
- scope:prompt
parent: 984
depends_on:
- 992
- 993
- 994
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #984

## Objective

Rewrite `.github/prompts/agent-audit.prompt.md` as a maximum-quality ecosystem audit prompt following the 5-section structure defined in the Brief.

## Structure (5 sections)

1. **Preamble** — role, stakes, behavioral contract, trust signals
2. **Audit Surface and Standards** — two surfaces with weighting, standards loading order, references-not-restates
3. **Seven Audit Dimensions** — Structural (with boundary-fitness), Duplication, Content Placement, Quality, Pipeline Integrity, SNR, Memory Governance and Content — each with negative-space probes
4. **Process** — scan-first, severity-first, continuous one-finding-at-a-time loop with finding cards, confidence scores, conditional phase breaks, queue re-evaluation
5. **Verification** — pipeline trace, rejection-routing, SNR spot-check, coverage summary, "run from the top?"

## Carry Forward

- Pipeline-integrity routing tables from current prompt
- Dynamic file discovery via `file_search`
- Standards-first loading order

## Drop

- Static FINDINGS / REMEDIATION PLAN batch output template

## Acceptance Criteria

- [ ] Single self-contained `.prompt.md` under `.github/prompts/`.
- [ ] All 7 dimensions x both surfaces covered (with MCP-unavailable degradation path).
- [ ] Continuous loop without silent stalls; uses `askQuestions` literal at every user-facing turn.
- [ ] Re-scan prompted on queue exhaustion.
- [ ] Each finding card includes confidence on recommendation AND each option.
- [ ] References (does not duplicate) rules in `h-agent-structure`, `h-memory-structure`, `r-pipeline-protocol`, `r-project-standards`.
- [ ] Pipeline routing tables carried forward from current prompt.

## Files

- `.github/prompts/agent-audit.prompt.md`
[[2026-04-19]]

## Architecture Review

### Verdict: REJECT (stale duplicate)

**Reason:** This task is a leftover from an earlier planning step, superseded by #1003 which was created during the parent #984 architecture review split.

**Evidence:**

- Dependencies #992, #993, #994 no longer exist (deleted/replaced by #1000, #1001, #1002)
- #1003 ("Rewrite agent-audit.prompt.md per Brief #984") covers the identical scope with corrected dependencies (#1000, #1001, #1002)
- #1003 is already in `review` status with builder commit `79d70f0c`

**Recommendation:** Delete or archive this task — it has no valid dependencies and no remaining purpose. All work is tracked under #1003.
[[2026-04-19]]

## Research

Stale duplicate — no research doc needed.

**Findings:**

- #995 scope is identical to #1003 ("Rewrite agent-audit.prompt.md per Brief #984")
- #1003 completed full pipeline: builder commit `79d70f0c`, review PASS (0.95 confidence), docs gate clean
- #995 dependencies (#992, #993, #994) deleted; replaced by #1000, #1001, #1002 under parent #984's architecture review split
- Architecture review on #995 already flagged REJECT (stale duplicate)

**Disposition:** Closed as duplicate. All work delivered under #1003. No follow-up tasks, no decision requests.
[[2026-04-19]]

## Audit

### Disposition: Stale Duplicate — verified

# 995 and #1003 target identical scope ("Rewrite agent-audit.prompt.md") under the same parent #984. #1003 completed the full pipeline and is already archived. No deliverables were produced under #995

### AC Verification (duplicate check)

| Claim | Evidence | Status |
|-------|----------|--------|
| #1003 covers identical scope | Both tasks: same parent #984, same target file, same objective | PASS |
| #1003 completed pipeline | #1003 archived; builder commit `79d70f0c`, review PASS noted in body | PASS |
| Old deps superseded | #992→#1000, #993→#1001, #994 kept; #1002 added. All archived under #984 | PASS |
| No deliverables under #995 | No builder or reviewer sections in body; Architecture Review = REJECT (stale) | PASS |

### Test Results

- pytest: N/A — no deliverables, no code changes
- ruff: N/A — no code changes
- Quality-Runner skipped: zero deliverables means zero regression risk

### Architect Quality: 4/5

Original AC was specific and well-structured. Staleness caused by architecture review re-planning (parent #984 split into #1000–#1003), not AC quality issues.

### Deduction Breakdown

- Start: 1.00
- Atypical pipeline path (duplicate bypassed normal code review): -0.02
- Total: 0.98

### Confidence: 0.98

### Action: archive
