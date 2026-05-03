# r-doc-standards Chain Migration Analysis

> **Owning task:** #1290 — P2-06: Migrate r-doc-standards chain atomically
> **Date:** 2026-05-03  **Status:** Complete

## 1. Context and Question

Task #1290 requires extracting OwlBear-specific scope enumeration from `share/skills/r-doc-standards/SKILL.md` while keeping the chain of 3 files (skill ↔ instruction ↔ prompt) intact. The question: what content to extract, where to put it, and whether sufficient generic substance remains.

## 2. Current State (Sources)

| Source | Location | Finding |
|--------|----------|---------|
| r-doc-standards/SKILL.md | share/skills/ | 200 lines, no `serve/` paths (already uses `workspace/` template vars). 5 sections: doc types, placement, xref, audience, audit dims |
| doc-standards.instructions.md | share/instructions/ | 7 lines. applyTo includes `serve/*/README.md`. References `.owlbear/prompts/doc-audit.prompt.md` |
| doc-audit.prompt.md | .owlbear/prompts/ | Already moved (not at share/prompts/). Heavily references STR-*, PLC-3 rule IDs |
| test_path_neutrality_1285.py | tests/ | 9 tests, ALL PASSING. Asserts skill at `share/skills/`, chain links intact, prompt at `.owlbear/prompts/` |
| h-agent-structure/SKILL.md | share/skills/ | References `workspace/*/README.md` in stub table |

## 3. Analysis

### Content Classification

| Section | Lines | Generic? | Extraction target? |
|---------|-------|----------|-------------------|
| Intro + Citation Format | ~15 | Partially ("Rules for OwlBear docs") | Genericize intro |
| § 1 Doc Types (STR-1 to STR-13) | ~50 | No — defines 5 OwlBear doc types | **Extract** |
| § 2 Placement (PLC-1 to PLC-5) | ~20 | Partially — PLC-1/2/5 generic; PLC-3 table + PLC-4 OwlBear-specific | **Extract PLC-3/PLC-4** |
| § 3 Cross-Reference (XREF-1 to XREF-5) | ~15 | Fully generic | Keep |
| § 4 Audience (AUD-1 table + AUD-2/3/4) | ~20 | Mixed — AUD-1 table OwlBear-specific; AUD-2/3 mention "OwlBear"; AUD-4 generic | **Extract AUD-1**, genericize AUD-2/3 |
| § 5 Audit Dimensions (DIM-1 to DIM-8) | ~20 | Generic framework | Keep (update refs) |

### Constraint: Skill MUST Stay in share/

Tests from #1285 assert the skill exists at `share/skills/r-doc-standards/SKILL.md` and contains the string `share/instructions/doc-standards.instructions.md`. Moving the entire file fails AC7.

### Post-Extraction Content (~80 lines)

Retained in shared skill:
- Citation format (ID prefix table)
- § 3 XREF-1 through XREF-5 (cross-reference integrity)
- § 4 AUD-2 through AUD-4 (genericized — replace "OwlBear" with project-neutral phrasing)
- § 5 DIM-1 through DIM-8 (audit dimensions framework)
- Companion wiring reference line

Sufficient substance: Yes. Cross-ref rules + audit dimensions = a reusable documentation quality framework.

### Extracted Content Destination

| Option | Pros | Cons | Score |
|--------|------|------|-------|
| `.owlbear/instructions/doc-types.instructions.md` | Auto-triggers via applyTo; instruction stubs are the established pattern | Creates a 4th chain member; need applyTo for OwlBear doc paths | 0.75 |
| `.owlbear/skills/r-doc-standards-local/SKILL.md` | Matches skill pattern; doc-audit prompt already loads skills by name | New skill to maintain; unusual to have a "local extension" skill | 0.60 |
| Inline in doc-audit.prompt.md | Single location; prompt already references rule IDs | Bloats the prompt (~70 lines); violates single-responsibility | 0.40 |

**Recommendation: Option 1** — `.owlbear/instructions/doc-types.instructions.md` with `applyTo: "README.md,SECURITY.md,serve/*/README.md,share/README.md,setup/*.md"`. The doc-audit prompt adds a line: "Also read `.owlbear/instructions/doc-types.instructions.md` for project-specific doc-type definitions." (confidence: 0.80)

### Instruction Stub Update

Shared stub becomes generic:
- Description: "Documentation quality rules — cross-references, audience fitness, audit dimensions"
- applyTo: `"**/*.md"` or keep current pattern (harmless on consumer projects without `serve/`)
- Content references the reduced generic skill

### Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| DIM section references extracted STR/PLC rules | Audit dims lose concrete examples | DIM text says "project-defined doc-type rules" instead of citing STR-* directly |
| doc-audit prompt uses STR-* rule IDs heavily | Prompt would reference rules not in the shared skill | Prompt loads both shared skill AND local instruction — rule IDs still resolve |
| 4-member chain harder to maintain | Future updates touch more files | Wiring doc + tests enforce consistency |

## 4. Recommendation (confidence: 0.82)

**Keep skill in share/, extract to local instruction, update doc-audit prompt.**

1. Extract § 1, PLC-3/PLC-4, AUD-1 table → `.owlbear/instructions/doc-types.instructions.md`
2. Reduce shared skill to generic framework (XREF + genericized AUD + DIM)
3. Update shared instruction stub description
4. Update doc-audit.prompt.md to load both sources
5. Single atomic commit

Challenge: FALLBACK — trivial T1 reorganization, no architecture/security implications.

## 5. Follow-up Tasks

Task moves to backlog. Builder implements per above. No additional follow-ups needed — this IS the implementation task (it's at research awaiting advancement).
