---
id: 1279
title: 'Architect calibration: carry PDS component contracts from brief into AC lines'
status: in-progress
priority: nice-to-have
created: 2026-05-02T14:02:13.981726+00:00
updated: 2026-05-02T15:58:47.245238+00:00
tags:
- phase-2
- quality
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Originated from #1250 audit (AC quality 2/5). The architect failed to carry PDS component contracts from the brief into testable AC lines, causing 5 architecture re-passes on a single RED task.

Lesson documented at: `/memories/repo/inbox/1250-auditor.md`

## Calibration Targets

1. **Generic "select" instead of PDS Select (`p-select`)** — AC must name exact design-system element/selector when the brief specifies one
2. **"Populated from priorities prop" without exact-ordered-match** — AC must specify assertion strength (exact match vs superset) when order matters
3. **"Does not render controls" conflating DOM absence with accessibility-tree hiding** — AC must distinguish removal from visual/a11y hiding when test strategy differs
4. **"Preserving other fields" satisfiable by single-control proof** — AC must require per-control verification when the requirement applies to each control individually

## Acceptance Criteria

- [ ] Architect checklist updated to include a "PDS contract carry-forward" gate at AC drafting
- [ ] Each of the 4 gaps above has a concrete "instead of X, write Y" example in the checklist


## Refined Acceptance Criteria

_Supersedes original AC above — architect refinement for precision._

- [ ] `share/skills/w-arch-review/SKILL.md` → Known Pitfalls section includes a new `#1250 PDS contract carry-forward` entry that defines the gate: when a Brief or research doc specifies design-system components (PDS or equivalent), AC lines must carry the exact component contracts into testable criteria (td:0)
- [ ] The Known Pitfalls entry includes all 4 "instead of X, write Y" examples corresponding to the Calibration Targets: (1) generic element → exact PDS selector, (2) "populated from prop" → exact-ordered-match assertion, (3) "does not render" → DOM absence vs a11y hiding distinction, (4) "preserving fields" → per-control verification (td:0)
- [ ] `share/skills/w-arch-review/SKILL.md` → Verification Checklist includes a new checkbox: "For frontend tasks referencing Briefs with design-system components, AC names exact selectors and assertion strategies (not generic HTML elements)" (td:0)

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: PDS contract carry-forward gate for architect workflow |
| Interface clarity | PASS (after refine) | Original "checklist" was ambiguous; refined to exact file paths and sections |
| Dependency correctness | PASS | No dependencies needed |
| Module layering | N/A | Documentation-only task |
| TDD compliance | N/A | Non-impl task, tagged `quality` for pass-through |
| KISS/YAGNI | PASS | Addresses evidenced 5-rework cycle on #1250 |
| Premise challenge | PASS | No existing gate covers design-system contract carry-forward; #1250 audit proves the gap |
| Pattern consistency | PASS | Follows existing Known Pitfalls pattern (#1225 entries) |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Architect workflow domain only |

### Design Diverge
- Trigger: skipped — single clear approach (Known Pitfalls entry + Verification Checklist checkbox)

### Challenge Results
- Challenger: SKIPPED — all AC lines td:0

### Test Depth
- Max depth: td:0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Refined AC to specify exact target files (`w-arch-review/SKILL.md` Known Pitfalls + Verification Checklist), tagged `quality` for pipeline pass-through, all td:0.
[[2026-05-02]]
## Architecture Review

Refined AC from vague "checklist updated" to exact file targets: `w-arch-review/SKILL.md` Known Pitfalls section (new #1250 entry with 4 "instead of X, write Y" examples) + Verification Checklist (new checkbox). Tagged `quality` for pipeline pass-through. All AC lines td:0 — Test-writer: SKIP, Challenger: SKIPPED.
[[2026-05-02]]
## Test-Writer Notes
- Non-implementation task (tagged `quality`) — no tests applicable.
- All AC lines are (td:0); architect explicitly marked Test-writer: SKIP.
- Passing through to builder.
[[2026-05-02]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Verified task body contains Test-writer pass-through note and all AC lines are (td:0).
- Passing through to review.
[[2026-05-02]]
## Review Evidence
### Test Results
- Tests not applicable. All refined AC lines are tagged `(td:0)`, so no task-scoped test file or `TestFromAC_*` coverage was expected.

### Lint
- `markdownlint-cli2` on [share/skills/w-arch-review/SKILL.md](share/skills/w-arch-review/SKILL.md): clean, 0 issues.

### Coverage
- Not applicable for this td:0 documentation task.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Skipped. No `TestFromAC_*` classes apply because every AC line is `(td:0)`.

#### Security Review
- No security findings. Scope is a markdown skill artifact only; no runtime surface changed.

#### Test Integrity
- Skipped. No task-scoped test files and no `TestFromAC_*` content in scope.

#### Test Quality
- Skipped. No tests applicable.

#### Data Safety
- No findings. This task only requires skill-document wording changes.

#### Implementation-Aware Test Gaps
- FAIL: the required artifact change was not made. [share/skills/w-arch-review/SKILL.md#L214-L238](share/skills/w-arch-review/SKILL.md#L214-L238) still contains the existing Verification Checklist and Known Pitfalls content ending with the prior `#1225` entries only. A targeted search in that file returned no matches for `#1250` / `PDS contract carry-forward` and no match for the required checklist text about exact selectors and assertion strategies.

#### Necessity Check
- N/A. No dependency or integration change.

#### Builder Process Quality
- CLEAN on retry count: one builder pass, no loop.
- However, the builder note says "no code changes needed" even though every refined AC line requires edits to [share/skills/w-arch-review/SKILL.md](share/skills/w-arch-review/SKILL.md). This is an implementation miss, not a routing or test-gap issue.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `share/skills/w-arch-review/SKILL.md` Known Pitfalls includes a new `#1250 PDS contract carry-forward` entry defining the gate | [share/skills/w-arch-review/SKILL.md#L230-L238](share/skills/w-arch-review/SKILL.md#L230-L238) shows the Known Pitfalls section ending with existing `#1225` bullets only; search in the target file found no `#1250` / `PDS contract carry-forward` entry | N/A (`td:0`) | FAIL |
| Known Pitfalls entry includes all 4 concrete "instead of X, write Y" examples for the calibration targets | [share/skills/w-arch-review/SKILL.md#L230-L238](share/skills/w-arch-review/SKILL.md#L230-L238) contains no new `#1250` pitfall text at all, so none of the 4 required examples are present | N/A (`td:0`) | FAIL |
| Verification Checklist includes the new checkbox about exact selectors and assertion strategies | [share/skills/w-arch-review/SKILL.md#L214-L228](share/skills/w-arch-review/SKILL.md#L214-L228) shows the full checklist block and it does not include the required checkbox; targeted search for the exact checkbox text returned no match | N/A (`td:0`) | FAIL |

### Deductions
- `-0.30` Missing required `#1250` Known Pitfalls entry.
- `-0.30` Missing all 4 required calibration examples.
- `-0.25` Missing required Verification Checklist checkbox.
- `-0.05` Builder note misclassified the task as no-change despite file-content AC.

### Verdict
- FAIL -> `in-progress`
- Confidence: 0.10

### Required Follow-up
- Add the new `#1250 PDS contract carry-forward` Known Pitfalls entry to [share/skills/w-arch-review/SKILL.md](share/skills/w-arch-review/SKILL.md).
- In that entry, include all 4 calibration examples: exact PDS selector, exact-ordered-match assertion, DOM absence vs a11y hiding distinction, and per-control verification.
- Add the Verification Checklist checkbox requiring exact selectors and assertion strategies for frontend tasks referencing design-system components.
- Re-run markdown lint after the file is updated.

### Post-task Reflection
- Doc-only and quality-tagged tasks still need direct artifact inspection; pass-through routing is not proof of completion.
- For content AC, builder notes should name the edited artifact explicitly; "no code changes needed" masked a straightforward miss.
- On td:0 tasks, target-file no-match searches are strong review evidence when the AC requires exact wording or a new named entry.