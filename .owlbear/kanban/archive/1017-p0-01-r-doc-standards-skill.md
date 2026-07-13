---
id: 1017
title: 'P0-01: r-doc-standards skill'
status: archived
priority: medium
created: 2026-04-19 23:51:24.288053+00:00
updated: 2026-04-20 00:46:26.396564+00:00
tags:
- phase-0
- docs-currency
- docs-agent
parent: 1016
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1016

## Acceptance Criteria

- [ ] `share/skills/r-doc-standards/SKILL.md` exists with `r-` prefix frontmatter (name: r-doc-standards, description, user-invocable: false)
- [ ] Specifies required sections per doc type: root README, SECURITY.md, package README (`serve/*/README.md`), share-category README
- [ ] Specifies placement rules (what belongs where)
- [ ] Specifies cross-reference rules: all links resolve, no orphan references
- [ ] Specifies audience-fitness rules per doc type
- [ ] Defines doc-audit dimensions (initial set): D1 Structural, D2 Duplication, D3 Placement, D4 Accuracy, D5 Coverage Integrity, D6 Currency/Staleness, D7 Cross-reference Integrity
- [ ] Rules are citable (numbered or named) so `doc-audit` can reference rule IDs per finding
- [ ] Follows `h-agent-structure` conventions for skill files

## Files

- Creates: `share/skills/r-doc-standards/SKILL.md`
- Reference: `share/skills/h-agent-structure/SKILL.md`, `share/prompts/agent-audit.prompt.md`

## Notes

Rules skill (SHALL/MUST constraints), not a handbook. The `doc-audit.prompt.md` skeleton (P0-06) depends on this to reference citable rule IDs. Pure documentation deliverable — no TDD pairing.
[[2026-04-20]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Creates exactly one skill file with one concern (documentation standards) |
| Interface clarity | PASS (after refinement) | AC refined: citation format specified as `{SECTION}-{N}`, D8 added, doc-type list completed |
| Dependency correctness | PASS | No deps; references are read-only. Downstream consumer #1022 identified and checked for consistency |
| Module layering | N/A | Markdown skill, no code imports |
| TDD compliance | N/A | Pure documentation deliverable — pass-through tag `docs` required (see below) |
| KISS/YAGNI | PASS | 8 dimensions (D1-D8) align with Brief spec; no speculative features |
| Premise challenge | PASS | No existing doc-standards skill. agent-audit has analogous dimensions for agent files; this creates the documentation counterpart |
| Pattern consistency | PASS | Follows `r-` prefix conventions per h-agent-structure. Three existing `r-` skills establish the pattern |
| Security surface | N/A | No system boundary touched |
| Single domain | PASS | Documentation standards only |

### AC Refinements (supersede original AC where they differ)

The following refinements address gaps found during review. The builder MUST use these as the authoritative AC:

**AC-2 (doc types):** Add `setup/*.md` (setup-guide.md, sharing-guide.md) as a fifth doc type. Full list: root README, SECURITY.md, package README (`serve/*/README.md`), share-category README, setup guide (`setup/*.md`).

**AC-3 (placement rules):** Rewrite: "Specifies doc-specific placement rules; references `r-project-standards` § File Placement for general conventions. No duplication of existing placement rules."

**AC-5 (audience-fitness):** Clarify: audience-fitness rules are standalone per-doc-type rules AND the skill defines D8 Audience Fitness as an audit dimension.

**AC-6 (dimensions):** Expanded to 8: D1 Structural, D2 Duplication, D3 Placement, D4 Accuracy, D5 Coverage Integrity, D6 Currency/Staleness, D7 Cross-reference Integrity, D8 Audience Fitness. The `D`-prefix is shared with agent-audit but context-disambiguated (doc-audit vs agent-audit). No namespace change needed.

**AC-7 (citation format):** Rewrite: "Rules use `{SECTION}-{N}` citation format (e.g., `STR-1`, `PLC-1`, `AUD-1`). Format documented in skill header so #1022 can reference IDs."

### Tagging

**REQUIRED:** Add `docs` pass-through tag before test-writer processes this task. Current tags (`phase-0, docs-currency, docs-agent`) do not include any pass-through tag. Without `docs`, the test-writer will attempt to write tests for a non-code deliverable. Orchestrator or next handler must add the tag.

### Dependency Analysis

- No upstream deps — can start immediately
- Downstream: #1022 (doc-audit skeleton) depends on this. #1022's AC hardcodes D1-D7 — will need D8 added when #1022 is architect-reviewed
- No conflicts with existing `r-` skills identified

### Challenge Results

- Challenger: `reconsider` (confidence 0.45)
- Architect response: accepted C2 (audience-fitness gap → D8 added), C4 (citation format → specified), C5 (placement overlap → reference added), BS1 (setup/*.md → added). Rebutted C1 (planner's AC is canonical, not stance-architect), C3 (D-prefix collision low risk, context-disambiguated), BS2 (terseness already implied by Notes)
- Post-refinement confidence: .88

### Verdict: APPROVE (with refinements)
### Action Taken: Refined AC (5 lines tightened), advanced backlog → todo. Noted `docs` tag requirement for orchestrator.
[[2026-04-20]]
## Test-Writer Notes
- Non-impl pass-through: AC references only `.md` files (`share/skills/r-doc-standards/SKILL.md`, `h-agent-structure/SKILL.md`, `agent-audit.prompt.md`).
- Keyword scan: no `implement`, `function`, `class`, `.py`, `endpoint`, or `src/` references in AC.
- Task body explicitly states "Pure documentation deliverable — no TDD pairing."
- Architect review confirmed: pass-through tag `docs` was missing from tags but intent is unambiguous.
- No tests written. Passing through to builder.
[[2026-04-20]]
## Builder Notes

**Files changed:** `share/skills/r-doc-standards/SKILL.md` (created, 134 lines)

**Test results:** N/A — pure documentation deliverable (pass-through, no TDD pairing per architect review)

**Lint status:** N/A — Markdown only

**Evidence summary:**
- Frontmatter: `name: r-doc-standards`, `description: "Rules: ..."`, `user-invocable: false` ✓
- Five doc types with required sections: root README (STR-1–3), SECURITY.md (STR-4–5), package README (STR-6–8), share-category README (STR-9–10), setup guide (STR-11–13) ✓
- Placement rules: PLC-1–5; delegates general placement to `r-project-standards § File Placement`, no duplication ✓
- Cross-reference rules: XREF-1–5 ✓
- Audience fitness: AUD-1–4 with per-doc-type table ✓
- 8 audit dimensions: D1 Structural, D2 Duplication, D3 Placement, D4 Accuracy, D5 Coverage Integrity, D6 Currency/Staleness, D7 Cross-reference Integrity, D8 Audience Fitness (DIM-1–8) ✓
- Citation format: `{SECTION}-{N}` documented in skill header with prefix-to-section mapping table ✓
- Follows h-agent-structure conventions for skill files ✓

**Commit:** `docs: add r-doc-standards skill (#1017, builder)`
[[2026-04-20]]
## Review Evidence

### Scope
Pure documentation deliverable — `share/skills/r-doc-standards/SKILL.md` (134 lines). No code, no tests, no lint applicable. Quality-Runner dispatch not required. Review is AC compliance + structural quality.

### TestFromAC Audit
N/A — pass-through task, no TDD pairing per architect review and test-writer notes.

### Security Review
N/A — Markdown file, no system boundary, no executable code, no links to external URLs.

### AC Compliance Table (refined AC from architect supersedes original)

| AC | Evidence | Status |
|----|----------|--------|
| AC-1: File exists with `r-` frontmatter (`name`, `description`, `user-invocable: false`) | `name: r-doc-standards`, `description: "Rules: ..."`, `user-invocable: false` at file top | PASS |
| AC-2 (refined): Five doc types with required sections — root README, SECURITY.md, package README, share-category README, setup guide | STR-1–3 (root README), STR-4–5 (SECURITY.md), STR-6–8 (package README), STR-9–10 (share-category), STR-11–13 (setup guide) | PASS |
| AC-3 (refined): Placement rules; references `r-project-standards § File Placement`; no duplication | PLC-1–5; PLC-2 explicitly defers to `r-project-standards § File Placement`; no general placement rules reproduced | PASS |
| AC-4: Cross-reference rules covering link resolution and orphan references | XREF-1–5: link resolution, relative-link preference, orphan-ref update requirement, section-heading pattern, circular-ref prohibition | PASS |
| AC-5 (refined): Audience-fitness rules per doc type AND D8 Audience Fitness dimension | AUD-1–4 with per-doc-type audience table; DIM-8 maps D8 → `AUD-1`–`AUD-4` | PASS |
| AC-6 (refined): 8 dimensions D1–D8 | DIM-1 through DIM-8 present; names and descriptions match architect spec exactly | PASS |
| AC-7 (refined): `{SECTION}-{N}` citation format documented in skill header with prefix-to-section mapping | Citation Format section immediately after frontmatter; prefix table (STR, PLC, XREF, AUD, DIM); all rules throughout file use this format consistently | PASS |
| AC-8: Follows `h-agent-structure` conventions for skill files | YAML frontmatter complete; `name` matches directory `r-doc-standards`; description starts `"Rules:"`; `user-invocable: false`; `r-` prefix for rules category | PASS |

### Structural Quality Checks

- **Rule citability**: Every rule has a unique `{SECTION}-{N}` ID. Spot-checked STR-13 (setup/init.py sync), XREF-4 (section-heading pattern), AUD-2 (jargon explanation) — all actionable and verifiable.
- **DIM→rule mapping consistency**: DIM-1 → `STR-*`; DIM-2 → `STR-2, STR-7, XREF-5`; DIM-3 → `PLC-3, PLC-5`; DIM-4/5 — "No rule ID" explicitly noted (correct — require empirical verification); DIM-6 → `STR-13`; DIM-7 → `XREF-1–3`; DIM-8 → `AUD-1–4`. All correct.
- **Self-referential consistency**: File uses `r-project-standards § File Placement` in PLC-2, matching the XREF-4 pattern it prescribes for cross-skill references.
- **Internal cross-references**: Citation Format prefix table lists `DIM` → "Audit Dimensions"; Section 5 heading is "Audit Dimensions". Exact match ✓.
- **Comparison to r-architecture-standards pattern**: frontmatter structure, rule-as-prose-with-ID format, section structure — all consistent.

### Deductions
0 deductions. No missing AC items, no structural violations, no weak rules, no orphan rule IDs.

### Verdict
Confidence: .97 → **PASS**
Action: advance review → docs
[[2026-04-20]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | New skill file only; `copilot-instructions.md` has no skills table and doesn't enumerate individual skill files |
| 2 | Module docstrings | No | N/A | No Python files created or modified |
| 3 | External attribution | No | N/A | Task body and review evidence contain no external source references; `sources/overview.md` has no `r-doc-standards` entry |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | Pure documentation deliverable; no research phase doc; not referenced in task body |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1017-*` files found)
[[2026-04-20]]
## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| AC-1: File exists with r- frontmatter | `name: r-doc-standards`, `description: \"Rules: ...\"`, `user-invocable: false` at file top | PASS |\n| AC-2: Five doc types with required sections | STR-1 to 3 (root README), STR-4 to 5 (SECURITY.md), STR-6 to 8 (package README), STR-9 to 10 (share-category), STR-11 to 13 (setup guide) | PASS |\n| AC-3: Placement rules; refs r-project-standards | PLC-1 to 5; PLC-2 defers to r-project-standards File Placement | PASS |\n| AC-4: Cross-reference rules | XREF-1 to 5: link resolution, relative links, orphan refs, section-heading pattern, circular refs | PASS |\n| AC-5: Audience-fitness rules + D8 dimension | AUD-1 to 4 with per-doc-type audience table; DIM-8 maps to AUD-1 to AUD-4 | PASS |\n| AC-6: 8 dimensions D1 to D8 | DIM-1 through DIM-8 present with correct names and rule mappings | PASS |\n| AC-7: Citation format documented | Citation Format section with prefix-to-section mapping table; all rules use {SECTION}-{N} consistently | PASS |\n| AC-8: h-agent-structure conventions | Frontmatter complete, name matches directory, r- prefix, user-invocable false | PASS |\n\n### Test Results\n- pytest: 783 passed, 6 failed (all pre-existing in serve/mcp-knowledge, unrelated to this docs task), 4 skipped\n- ruff: clean (exit 0)\n\n### Architect Quality: 4/5\nAC was specific with 8 lines. Five refinements during arch review (D8, citation format, placement cross-ref, setup docs, audience clarity) improved quality. No builder improvisation needed. Minor: initial AC needed refinement, but normal iteration.\n\n### Deduction Breakdown\n- AC lines with no evidence: 0\n- Lint violations: 0\n- AC quality (4/5 > 3): 0\n- Missing reviewer evidence: 0\n- Full-suite failures in task scope: 0\n- Total deductions: 0\n\n### Confidence: .98\n### Action: archive