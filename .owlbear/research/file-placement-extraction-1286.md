# File Placement & Layout Extraction

> **Owning task:** #1286 — P2-02: Extract file-placement and layout sections to .github/copilot-instructions.md
> **Date:** 2026-05-03 **Status:** Complete

## 1. Context and Question

Task #1286 is part of the "Neutral Shared Layer" brief (Phase 2). Two skills contain project-layout information that is OwlBear-dev-specific and confuses consumer agents:

- `r-project-standards` §2 File Placement — table prescribing where contributors put files (`.owlbear/research/`, `share/agents/`, `workspace/*/src/`). Consumers have different layouts.
- `h-python-conventions` Project Layout — source/test directory paths. Consumers have different package structures.

**Question:** How to extract these safely into `.github/copilot-instructions.md` without breaking cross-references or test expectations?

## 2. Sources Studied

| Source | Relevance |
|--------|-----------|
| `.owlbear/briefs/draft-neutral-shared/brief.md` — §Notation Convention, §Graceful Degradation | 1.0 — defines extraction pattern and concrete-path-in-local-config rule |
| `tests/test_path_neutrality_1285.py` — AC2 test | 0.9 — defines the pass criteria (`serve/` scan after exclusions) |
| `.owlbear/briefs/draft-neutral-shared/research-notes.md` — File-by-File Assessment | 0.8 — confirms entire §2 is contributor-specific |
| `share/skills/r-doc-standards/SKILL.md` lines 71, 96 | 0.7 — cross-reference impact analysis |

## 3. Analysis

### Current state

| File | `serve/` refs | `workspace/` refs | Extraction scope |
|------|---------------|-------------------|------------------|
| r-project-standards/SKILL.md | 0 | 1 (`workspace/*/src/`) | Entire §2 (table + intro + cleanup note) |
| h-python-conventions/SKILL.md | 0 | 2 (`workspace/*/src/`, `workspace/*/tests/`) | `## Project Layout` section (3 bullet points) |

### Implementation approach

| Step | Action | Risk |
|------|--------|------|
| 1 | Remove §2 from r-project-standards; renumber §3→§2, §4→§3, §5→§4 | Low — content moves, not deleted |
| 2 | Update r-project-standards frontmatter description (remove "file placement") | None |
| 3 | Remove `## Project Layout` from h-python-conventions | Low |
| 4 | Add `## 6. File Placement` to copilot-instructions.md with concrete paths (`serve/*/src/`) | None |
| 5 | Add `## 7. Project Layout` to copilot-instructions.md with concrete paths | None |

### Cross-reference impact (OUT OF SCOPE)

| Reference | Location | Impact | Handled by |
|-----------|----------|--------|------------|
| `r-project-standards § File Placement` | r-doc-standards PLC-2, XREF-4 | Dangling after extraction | Sibling task (r-doc-standards split, likely #1289) |
| "file placement" mention | r-pipeline-protocol line 18 | Descriptive only, not a link | Cosmetic — acceptable as-is |

### Path mapping (generic → concrete)

| In skill (removed) | In copilot-instructions.md (added) |
|---------------------|-------------------------------------|
| `workspace/*/src/` | `serve/*/src/` |
| `workspace/*/tests/` | `serve/*/tests/` |

## 4. Recommendation

Proceed with direct extraction. Confidence: **0.90**.

- Brief explicitly defines this operation
- AC is unambiguous about what to remove and retain
- No `serve/` paths currently exist in either skill (AC4 already satisfied)
- The extraction removes `workspace/` generic placeholders from shared skills (they served no purpose for consumers who have different layouts)

Challenge: skipped — trivial extraction per approved brief, no decision ambiguity.

## 5. Follow-up Tasks

No new tasks needed — sibling tasks #1287–#1291 cover all related work (r-doc-standards chain, architecture standards, quality-runner routing, etc.). The cross-reference in r-doc-standards is handled by the r-doc-standards split task.
