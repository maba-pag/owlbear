---
id: 1633
title: 'AC lint checklist: canonical enum/token literals for cockpit/frontend tasks'
status: todo
priority: important
created: 2026-05-16T08:36:17.402556+00:00
updated: 2026-05-16T13:19:39.985527+00:00
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

## Builder Guidance (Re-baselined after 2 failed cycles)

**CRITICAL: The required content DOES NOT currently exist in `share/skills/h-ac-quality/SKILL.md`.** Two prior builder passes hallucinated that it did. The builder MUST:

1. **Add new content** to `share/skills/h-ac-quality/SKILL.md` — do not claim existing content satisfies the ACs.
2. **Verify after editing** by re-reading the file and confirming the new sections are present via `read_file` or `grep_search`.
3. **Commit the change** — there MUST be a non-empty `git diff` for `share/skills/h-ac-quality/SKILL.md`.

### What to add (implementation spec):

**Location:** After the existing `## Bad -> Good Transformations` section (around line 96), add a new `## Canonical Literal Verification` section containing:

1. **3 bad→good examples** (satisfies AC-1):
   - Enum/union: Bad uses invented labels → Good cites `CardSignal` values from `computeSignal.ts`
   - PDS token: Bad uses generic CSS → Good cites `--pds-spacing-md` from `tokens.css`
   - Component prop/CSS custom property: Bad uses invented prop values → Good cites actual type union or CSS variable

2. **5-step verifier procedure** (satisfies AC-2):
   Steps like: identify the literal → locate canonical source → grep/read → compare → rewrite if mismatched

3. **Canonical source map** (satisfies AC-3):
   | Category | Source file | Example |
   Table mapping literal categories to their authoritative locations

4. **Mechanical lint integration** (satisfies AC-4):
   Add a bullet to the existing "1. Mechanical lint pass" list (around line 78) adding a canonical-literal check step, and cross-reference the new section.

### Canonical sources (verified):
- `CardSignal` → `serve/cockpit/web/src/utils/computeSignal.ts` (6 values: `dr-pending | blocked | claimed | deps-unmet | ready | unknown`)
- CSS custom properties → `serve/cockpit/web/src/tokens.css` (spacing, radius, shadow, notification tokens)
- PDS components → `@porsche-design-system/components-react` type exports

[[2026-05-16T15:19:39+02:00]]
[[2026-05-16T15:19:20+02:00]]
## Architecture Review (Re-baseline)
### Context
Task returned from reviewer after 2 failed builder cycles. Both times, the builder hallucinated that the required canonical-literal checklist content was already present in `h-ac-quality/SKILL.md` when it was not. Reviewer correctly identified this and routed back to backlog.

### Action Taken
Re-baselined task body with explicit builder guidance:
- Stated unambiguously that the content DOES NOT exist
- Provided exact insertion location (after line ~96, `## Bad -> Good Transformations`)
- Specified the 4 sections to add with content requirements
- Required post-edit verification via `read_file`/`grep_search`
- Required non-empty `git diff` as proof of actual change
- Included verified canonical source references from live code

### AC Assessment
| AC | Assessment | Action |
|-----|-----------|--------|
| AC-1 | Precise, verifiable | No change needed |
| AC-2 | Precise, verifiable | No change needed |
| AC-3 | Precise, verifiable | No change needed |
| AC-4 | Precise, verifiable | No change needed |

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: literal-accuracy checklist for frontend/cockpit ACs |
| Interface clarity | PASS | AC specifies content requirements and verification method |
| Dependency correctness | PASS | No deps |
| Module layering | N/A | Documentation/process task |
| TDD compliance | PASS | proof_bundle=skip, quality tag ensures test-writer pass-through |
| KISS/YAGNI | PASS | Minimal scope — checklist + lint integration |
| Premise challenge | PASS | h-ac-quality has no literal-accuracy coverage; #1631 audit confirmed gap |
| Pattern consistency | PASS | Follows h-ac-quality existing Bad→Good pattern |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Process/quality domain only |

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Proof-Bundle Validation
- Planner assignment: skip
- Final bundle: skip
- Existing proof scope: N/A
- Test-writer: SKIP

### Verdict: APPROVE (re-baseline with explicit builder guidance)
### Action Taken: Replaced task body with detailed implementation spec and anti-hallucination guardrails, advanced backlog → todo
