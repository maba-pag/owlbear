---
id: 1633
title: 'AC lint checklist: canonical enum/token literals for cockpit/frontend tasks'
status: archived
priority: important
created: 2026-05-16T08:36:17.402556+00:00
updated: 2026-05-16T13:57:38.902486+00:00
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
archival_reason: completed
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

[[2026-05-16T15:27:14+02:00]]
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Tagged `quality` (non-implementation task).
- Passing through to builder.

[[2026-05-16T15:33:52+02:00]]
## Builder Notes
- Implementation: Added canonical-literal checklist content in [share/skills/h-ac-quality/SKILL.md](share/skills/h-ac-quality/SKILL.md) and integrated canonical-literal verification into the Two-Pass Validation mechanical lint pass.
- Files changed: [share/skills/h-ac-quality/SKILL.md](share/skills/h-ac-quality/SKILL.md)
- Proof bundle handling: `skip` (no TestFromAC gate required for this process/documentation task).
- AC coverage evidence:
  - AC-1: Added 3 bad->good literal examples (enum/union, PDS token, CSS custom property).
  - AC-2: Added a 5-step verifier procedure.
  - AC-3: Added canonical source map table with authoritative source locations.
  - AC-4: Added a canonical-literal check bullet under the existing `1. Mechanical lint pass` list.
- Quality-runner (scoped):
  - Initial run failed markdownlint `MD056` due to unescaped table pipes in one example cell.
  - Applied targeted fix by rewriting the table example cell to comma-separated values.
  - Final run: tests passed 0, failed [], lint clean true, violations [], coverage overall 0 (not applicable for docs-only skill update), markdownlint exit 0.
- Verification: Re-read and grep-verified presence of `## Canonical Literal Verification`, `--pds-spacing-md`, and `CardSignal` canonical values in the updated skill.
- Commit: `2a6a92058d32b7df344d4d69a27c61fc329d9160` (`docs: add canonical literal AC checklist (#1633, builder)`).

[[2026-05-16T15:46:10+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1633 -> docs | AC mapped to code and evidence sufficient.
- Blocking findings: none.

| AC | Evidence | Status |
|---|---|---|
| AC-1 | `share/skills/h-ac-quality/SKILL.md:129` adds the inline `## Canonical Literal Verification` section, and `share/skills/h-ac-quality/SKILL.md:137-148` adds 3 concrete bad -> good examples covering enum/union (`CardSignal`), PDS spacing token (`--pds-spacing-md`), and CSS custom property (`--pds-signal-claimed`). The cited literals match canonical sources at `serve/cockpit/web/src/utils/computeSignal.ts:1` and `serve/cockpit/web/src/tokens.css:31,53`. | PASS |
| AC-2 | `share/skills/h-ac-quality/SKILL.md:150,152-156` provides a 5-step verifier procedure that tells reviewers to identify literals, locate the canonical source, confirm exact spelling with `grep_search`/`read_file`, compare wording, and rewrite mismatches. | PASS |
| AC-3 | `share/skills/h-ac-quality/SKILL.md:158,162-165` adds a canonical source map for enum/union literals, PDS design tokens, CSS custom properties, and PDS component prop/type literals. The external package reference is grounded by `serve/cockpit/web/package.json:21`. | PASS |
| AC-4 | `share/skills/h-ac-quality/SKILL.md:86` adds a canonical-literal verification check to the `1. Mechanical lint pass`, and the checklist remains inline in the same skill file at `share/skills/h-ac-quality/SKILL.md:129`. | PASS |

- Builder evidence reviewed first: proof bundle is `skip`, and the builder supplied scoped markdownlint-clean evidence after fixing MD056; no independent rerun was required under the reviewer trust model.
- Commit proof: builder commit `2a6a92058d32b7df344d4d69a27c61fc329d9160` is present in `.git/logs/HEAD:3354`.
- Safety/security: documentation/process-only update; no runtime code paths or dependency set changed.

## Observations
- No non-blocking findings.
- The checklist now gives planners, architects, and reviewers a concrete literal-verification pattern for cockpit/frontend ACs, which directly addresses the hallucinated-label failure identified in audit #1631.

[[2026-05-16T15:49:08+02:00]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | N/A (no update needed) | `share/**` maps to `share/README.md` + `share/WIRING.md`. Task modified internal content of an existing skill — no new skill added, no skill renamed, no count change. `share/README.md` skill count (35) unchanged. `share/WIRING.md:181` entry for `h-ac-quality` (consumers: architect, challenger, planner) unchanged — skill role/interface unchanged. No stale or orphaned references found. |
| 2 | External attribution | No | N/A | No external sources used. Canonical references (computeSignal.ts, tokens.css) are internal codebase files. |
| 3 | Research doc | No | N/A | No research artifact exists for this task. |
| 4 | Deletion detection | No | N/A | No files deleted. Only `share/skills/h-ac-quality/SKILL.md` was modified. |

### Verification Layers
- Layer 1 — Confirmed `## Canonical Literal Verification` section present in SKILL.md (lines ~129–165). Confirmed canonical-literal check bullet present in `1. Mechanical lint pass` (~line 86) with cross-reference to the new section. No stale mentions in share/README.md or share/WIRING.md.
- Layer 2 — Editorial read: the new section integrates cleanly after `## Bad -> Good Transformations`. The 3 bad→good examples, 5-step verifier, and canonical source map are coherent and internally consistent. share/README.md and share/WIRING.md remain accurate — no docs impact from this content-only skill edit.

### Scratch Cleanup
- No `.owlbear/scratch/1633-*` files found.

[[2026-05-16T15:57:38+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 4648 passed, 19 failed (all pre-existing — FileNotFoundError for missing task-scoped test files from other tasks, engine accessor migration issues, environment timeouts), 14 skipped, lint clean
- None of the 19 failures relate to a docs-only skill file edit
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (single file `share/skills/h-ac-quality/SKILL.md`, process/quality domain)
- purpose match: PASS (adds canonical-literal verification checklist as specified by AC and #1631 audit follow-up)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
ACs were specific and verifiable throughout. Task required re-baseline after 2 failed builder cycles (hallucination), but the ACs themselves were precise — the gap was builder execution, not architect specification. Re-baseline added effective anti-hallucination guardrails.

### Commit Integrity
- upstream commit presence: PASS (`2a6a9205` — `docs: add canonical literal AC checklist (#1633, builder)`, 1 file changed, 39 insertions)
- kanban commit packaging: pending (this step)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive
