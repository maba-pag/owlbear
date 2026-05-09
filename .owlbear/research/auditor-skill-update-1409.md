# Auditor Skill Update — Regression + Intent Focus

> **Owning task:** #1409 — C1: Auditor skill update
> **Date:** 2026-05-09 **Status:** Complete

## 1. Context and Question

The brief (parent #1403) identified overlapping mandates between reviewer and auditor: reviewer checks correctness (auditor's job), auditor re-checks completeness (reviewer's job). After B1 (#1407) rewrote `w-code-review` with full AC compliance tables, finding vs. opinion separation, and trust-builder evidence model, the auditor skill needs to shed overlapping checks and sharpen its unique value: regression detection, intent verification, and architect quality scoring.

**Question:** Which current auditor checks overlap with the post-B1 reviewer, what replaces them, and how does the scoring rubric change?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `share/skills/w-task-verification/SKILL.md` | Current auditor skill | 1.0 |
| `share/skills/w-code-review/SKILL.md` (post-B1) | Current reviewer skill | 1.0 |
| `share/skills/r-pipeline-protocol/SKILL.md` | Pipeline trust model | 0.9 |
| `share/agents/auditor.agent.md` | Agent persona + boundaries | 0.9 |
| `.owlbear/briefs/draft-pipeline-review-rethink/brief.md` | C1 spec | 1.0 |

## 3. Analysis

### Overlap Matrix: Current Auditor vs. Post-B1 Reviewer

| Auditor Check | Reviewer Equivalent | Overlap | Recommendation |
|---|---|---|---|
| AC spot-check (1-2 items) | Step 7: full AC compliance table | **Full** | Remove |
| AC deviations | Step 7: AC compliance + Step 5 criticals | **Full** | Remove |
| File exists | Step 1: source control changes | **Full** | Remove |
| Lint (as separate gate) | Step 2/3: quality-runner scoped lint | **Partial** | Fold into full-suite |
| Full test suite (mode=full) | Reviewer runs scoped tests only | **None** | Keep (primary value) |
| Reviewer evidence read | N/A (reviewer writes it) | **None** | Keep (trust-verify) |
| Research task verification | Not in reviewer scope | **None** | Keep |
| Architect quality audit | Not in reviewer scope | **None** | Keep (unique) |
| Commit integrity | Not in reviewer scope | **None** | Keep (unique) |

### Proposed Auditor Focus (4 pillars)

| Pillar | Purpose | Source of uniqueness |
|--------|---------|---------------------|
| **Regression detection** | Full suite catches cross-task breakage | Reviewer runs scoped tests only |
| **Intent verification** | Does implementation match task purpose? | Reviewer maps AC lines; auditor checks "right thing built" |
| **Architect quality scoring** | AC specificity, edge cases, design direction | Only pipeline stage assessing upstream architect work |
| **Commit integrity** | Upstream commits present; kanban committed after archival | Only agent that verifies commit discipline |

### Scoring Rubric Changes

| Criterion | Current | Proposed | Rationale |
|-----------|---------|----------|-----------|
| AC line with no specific evidence | -.02 each | **Remove** | Reviewer's responsibility post-B1 |
| Lint violations | -.05 | -.05 (keep, from full-suite) | Full-suite lint catches cross-task regressions |
| AC quality score ≤ 3 | -.03 | -.03 (keep) | Unique auditor scope |
| Missing reviewer evidence section | -.02 | -.03 (increase) | Auditor trusts reviewer more; missing evidence is bigger concern |
| Full-suite test failures in task scope | -.05 | -.10 (rename: regression failures) | Primary value; higher weight justified |
| Intent mismatch | N/A | **-.05 (new)** | Implementation doesn't match task purpose |
| Evidence integrity concern | N/A | **-.05 (new)** | Full suite contradicts reviewer evidence |

### Output Template Changes

| Section | Current | Proposed |
|---------|---------|----------|
| AC Verification table (per-AC-line) | Present | **Remove** (reviewer produces this) |
| Regression Detection | Implicit in test results | **New explicit section** |
| Intent Verification | Not present | **New section**: scope alignment + purpose match |
| Test Results | pytest + ruff summary | Keep (from full-suite) |
| Architect Quality | Score only | Keep |
| Deduction Breakdown | Current rubric | Updated rubric |

### Risk: Intent Verification Scope Creep

Intent verification must stay high-level to avoid re-doing the reviewer's AC mapping. The boundary:
- **Auditor checks:** "Changed files are in the right domain. The implementation addresses the task's stated purpose. No extraneous scope added."
- **Reviewer checks:** "Each AC line has evidence. Tests exercise assertions. Code quality meets standards."

If the auditor starts reading individual functions to verify behavior, that's reviewer territory.

## 4. Recommendation

**T1 — Autonomous.** Skill modification within existing pipeline. No new capabilities, no architecture changes, no user-facing behavior changes.

Update `w-task-verification` with the 4-pillar model, updated scoring rubric, and simplified output template. Also update `auditor.agent.md` persona to reflect the narrower, sharper focus.

Confidence: .85 — the 4-pillar model is well-defined by the brief and the overlap analysis is unambiguous. The .15 uncertainty is in calibrating intent verification scope (risk of too broad or too narrow).

Challenge: skipped (T1 autonomous, overlap analysis is mechanical and directly driven by brief decisions).

## 5. Follow-up Tasks

1. **Implementation:** Update `w-task-verification/SKILL.md` — apply 4-pillar model, updated rubric, simplified output template
2. **Implementation:** Update `auditor.agent.md` persona and boundaries — reflect regression + intent focus
3. **Verification:** Diff comparison with B1's reviewer scope to confirm no overlap (AC P3 from task)
