---
id: 992
title: '1a: Expand h-agent-structure — stub vs. authority taxonomy + boundary-fitness'
status: todo
priority: needed
created: 2026-04-18T21:23:32.394740+00:00
updated: 2026-04-18T21:34:38.495723+00:00
tags:
- type:docs
- scope:skills
parent: 984
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #984

## Objective
Expand `share/skills/h-agent-structure/SKILL.md` with two additions:
1. **Instruction file taxonomy** — formalize the distinction between instruction stubs (3-line pointers in `share/instructions/`) and authority instruction files (`agent-common.instructions.md`, `owlbear-system.instructions.md`, etc.) that legitimately contain rules. Define naming, placement, and content rules for each type.
2. **Boundary-fitness language** — tighten the loading model rules (80% rule, file-type semantics, path complexity) so the audit's Structural dimension can probe "is this file the right loading-model unit?" with a clear authority anchor.

## Acceptance Criteria
- [ ] `h-agent-structure/SKILL.md` contains a section defining instruction stubs vs. authority instruction files with naming, placement, and content rules for each.
- [ ] Boundary-fitness section includes the 80% rule, loading-model unit fit, and file-type semantic guidance.
- [ ] Existing content preserved; additions are additive.
- [ ] No rules duplicated from other skills — references only.

## Files
- `share/skills/h-agent-structure/SKILL.md`
[[2026-04-18]]
## Architecture Review

### AC Assessment

| AC line | Assessment | Action |
|---------|-----------|--------|
| AC1: section defining stubs vs. authority instruction files | REFINE — ambiguous whether to expand existing "Instruction Stub Format" section or create parallel section | Clarified: expand existing section (rename heading, add authority file sub-section) |
| AC2: boundary-fitness section with 80% rule, loading-model unit fit, file-type semantics | REFINE — "loading-model unit fit" is undefined jargon; "includes the 80% rule" ambiguous (restate vs reference) | Clarified below |
| AC3: existing content preserved; additions additive | PASS — clear and verifiable |
| AC4: no rules duplicated from other skills | PASS — clear and verifiable |

### Refined Acceptance Criteria

- [ ] The existing "Instruction Stub Format" section is expanded into an "Instruction File Taxonomy" section (or similar) covering both stubs and authority files. Sub-sections for each type with naming, placement, and content rules. Existing stub table preserved.
- [ ] Authority instruction file rules define: (a) when an instruction file legitimately contains rules directly (vs. pointing to a skill), (b) naming convention, (c) `applyTo` scope expectations, (d) note that `copilot-instructions.md` is a separate loading mechanism (not an instruction file) — it already appears in the Loading Model table.
- [ ] New "Boundary Fitness" section (under Principles or as a peer section) provides criteria for determining whether content is in the correct loading-model unit. Must include: (a) reference (not restatement) of the existing 80% Rule, (b) path-coverage heuristic — if a single execution path touches <30% of a file, the file likely bundles unrelated concerns, (c) reference (not restatement) of the existing File Type Selection table for file-type semantic guidance.
- [ ] Existing content preserved; additions are additive. Renaming the "Instruction Stub Format" heading is permitted.
- [ ] No rules duplicated from other skills — references only. No duplication within the file (Rule of Two applies internally).

### Builder Guidance

- The two authority files (`agent-common.instructions.md` ~130 lines, `owlbear-system.instructions.md` ~160 lines) have different `applyTo` scopes: `agent-common` fires on `share/agents/**` (domain-scoped), `owlbear-system` fires on `**` (universal). The taxonomy should note this distinction but need not create sub-categories — scope is already visible in the `applyTo` field.
- The boundary-fitness section should enable a downstream audit prompt to ask: "Is this content in the right loading-model unit?" with a clear checklist. Think auditor-facing, not builder-facing.
- Do NOT move the 80% Rule or File Type Selection table — reference them from the new section.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One file, one topic: expanding h-agent-structure |
| Interface clarity | PASS (after refine) | AC tightened to resolve ambiguities |
| Dependency correctness | PASS | No deps; independent of sibling tasks 1b, 1c |
| Module layering | PASS | Docs-only change in share/skills/ |
| TDD compliance | PASS | Tagged type:docs — non-impl pass-through |
| KISS/YAGNI | PASS | Minimal additions to existing file |
| Premise challenge | PASS | File currently lacks authority file taxonomy and boundary-fitness criteria |
| Pattern consistency | PASS | Follows existing handbook skill structure |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | Agent ecosystem structure only |

### Challenge Results
- Challenger: reconsider (confidence 0.50)
- Architect response: accepted — refined AC to resolve all three ambiguities (80% rule reference vs restate, "loading-model unit fit" replaced with concrete language, section placement clarified)

### Verdict: REFINE → APPROVE
### Action Taken: Tightened AC to resolve ambiguities identified by challenger. Task advanced to todo with refined AC in architecture review note.