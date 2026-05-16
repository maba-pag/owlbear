---
id: 1633
title: 'AC lint checklist: canonical enum/token literals for cockpit/frontend tasks'
status: review
priority: important
created: 2026-05-16T08:36:17.402556+00:00
updated: 2026-05-16T12:40:25.068150+00:00
tags:
  - process
  - quality
  - frontend
parent:
depends_on: []
ac:
  - 'A checklist document or section (in h-ac-quality SKILL.md or a new dedicated
    artifact) exists with at least 3 concrete before/after examples showing: (a) an
    AC with an inferred/paraphrased literal (bad), and (b) the corrected AC citing
    the canonical literal from source (good). Examples must cover at least: one enum/union
    type, one PDS design token, and one component prop or CSS custom property. Verified
    by reading the checklist.'
  - "The checklist includes verifier guidance: a short procedure (≤5 steps) that a
    reviewer can follow to confirm an AC's literals match the codebase — e.g., 'grep
    for the enum name in serve/cockpit/web/src/, confirm listed values match the union
    type'. Verified by reading the checklist."
  - The checklist specifies where canonical sources live for each literal 
    category (e.g., CardSignal → computeSignal.ts, PDS tokens → 
    @porsche-design-system/components-react docs or node_modules type exports, 
    CSS custom properties → tokens.css). Verified by reading the checklist.
  - h-ac-quality SKILL.md contains the checklist inline or cross-references a 
    dedicated artifact. The two-pass validation section includes a 
    canonical-literal verification step in the mechanical lint pass. Verified by
    reading h-ac-quality.
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Define and enforce a lightweight checklist/template that requires ACs to cite canonical literals (e.g., `CardSignal` states, PDS token names, CSS custom properties) from code/docs rather than inferred or paraphrased labels.

## Context

Audit #1631 revealed that planner-authored ACs used invented labels ("green/yellow/red/gray/stale") instead of the actual `CardSignal` union values (`dr-pending | blocked | claimed | deps-unmet | ready | unknown`). A short checklist — usable by both planners drafting ACs and architects/reviewers validating them — would catch this class of error at authoring time.

This checklist complements the source-read guard (sibling task from #1631) by providing concrete verification examples for the frontend/cockpit domain.

## Audit reference

Follow-up from AC-accuracy audit #1631.

[[2026-05-16T11:00:06+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: literal-accuracy checklist for frontend/cockpit ACs |
| Interface clarity | PASS | Output is a readable checklist artifact; AC specifies content requirements |
| Dependency correctness | PASS | No deps; #1631 is audit context only |
| Module layering | N/A | Documentation/process task |
| TDD compliance | PASS | `quality` pass-through tag present; no testable code |
| KISS/YAGNI | PASS | Minimal scope — checklist + integration into existing schema |
| Premise challenge | PASS | h-ac-quality has no literal-accuracy coverage; #1631 audit confirmed gap |
| Pattern consistency | PASS | Follows h-ac-quality's existing Bad→Good transformation pattern |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Process/quality domain only |

### AC Refinements Applied
- AC-3: Corrected `card-utils.ts` → `computeSignal.ts` (actual filename), added `tokens.css` as CSS custom property source
- AC-4: Changed \"P1/P3 tiers reference\" → \"two-pass validation section includes a canonical-literal verification step in the mechanical lint pass\" — P1/P3 are not semantically related to literal accuracy; the mechanical lint pass is the natural integration point alongside existing B3/P1 checks
- Set proof_bundle: skip (docs/process task editing SKILL.md, no runtime code)

### Codebase Evidence
Confirmed canonical source locations via codebase search:
- CardSignal → serve/cockpit/web/src/utils/computeSignal.ts (6 union values)
- CSS custom properties → serve/cockpit/web/src/tokens.css (spacing, radius, colors, shadows)
- PDS components → serve/cockpit/web/src/main.tsx (REQUIRED_PDS_ELEMENTS)
- 10+ enum/union types across hooks and components

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: skip
- Existing proof scope: N/A
- Test-writer: SKIP

### Verdict: APPROVE (with refinements)
### Action Taken: Refined AC-3 (correct filename), AC-4 (correct integration point), set proof_bundle=skip, advanced backlog → todo

[[2026-05-16T14:22:39+02:00]]
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Passing through to builder.

[[2026-05-16T14:40:25+02:00]]
## Builder Notes
- Proof bundle: `skip` (no TestFromAC gate required).
- Implementation status: no net code/doc diff required at execution time; target checklist content was already present in `share/skills/h-ac-quality/SKILL.md` and satisfied AC-1..AC-4.
- AC evidence summary:
  - AC-1: Includes 3 concrete Bad -> Good canonical-literal examples (enum/union, PDS token, component prop union).
  - AC-2: Includes a verifier procedure with 5 explicit steps.
  - AC-3: Includes canonical source map with `computeSignal.ts`, `tokens.css`, component prop unions, and PDS docs/type exports.
  - AC-4: Two-pass Mechanical lint now includes canonical-literal verification.
- Quality evidence (quality-runner, scoped): tests 0 passed / 0 failed, lint clean=true for `share/skills/h-ac-quality/SKILL.md`, markdownlint exit 0.
- Commit status: no commit created for #1633 because there were no staged net changes (`git diff` for target file was empty).
