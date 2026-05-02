# Split owlbear-system.instructions.md — Directory Structure Extraction

> **Owning task:** #1282 — P1-02: Split owlbear-system.instructions.md — extract directory table to .github/copilot-instructions.md
> **Date:** 2026-05-03 **Status:** Complete

## 1. Context and Question

Task #1282 is part of the P1 phase of the neutral-shared-layer brief (#1280). The always-loaded system instruction (`applyTo: "**"`) contains a project-specific Directory Structure table with `serve/` paths that confuse consumer agents. The table should live in the project-local `.github/copilot-instructions.md` instead.

**Question:** What exactly needs to change, and are there complications?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `share/instructions/owlbear-system.instructions.md` | Codebase | 1.0 — the file being edited |
| `.github/copilot-instructions.md` | Codebase | 1.0 — the destination file |
| `tests/test_neutral_shared_1281.py` | Codebase | 0.9 — validation tests with xfail marker |
| `.owlbear/briefs/draft-neutral-shared/brief.md` | Codebase | 0.9 — authoritative brief |
| `seed/.github/copilot-instructions.md` | Codebase | 0.7 — seed template (scope: #1284) |
| VS Code `.instructions.md` schema | Docs | 0.8 — confirms `applyTo` is frontmatter-only |

## 3. Analysis

### Current State

**owlbear-system.instructions.md §2 System Awareness** has three subsections:
- `### Tech Stack` — generic, stays
- `### Pipeline` — generic, stays
- `### Directory Structure` — project-specific, 10 rows including `serve/`, extract

After the table, a general reference line exists: "For file placement rules, commit format, priorities, and tags, see `r-project-standards`." — stays in §2.

**`.github/copilot-instructions.md`** already has a `## Directory Structure` section with a 6-row summary table (added by #1281 builder). This should be replaced with the richer extracted table.

### `serve/` Reference Audit

| File:Line | Content | Status |
|-----------|---------|--------|
| `owlbear-system.instructions.md:40` | `serve/` in Directory Structure table | Removed by extraction |
| `doc-standards.instructions.md:3` | `serve/*/README.md` in `applyTo:` frontmatter | P2 scope (#1290), excluded per AC |

After extraction: zero non-exempt `serve/` references in `share/instructions/`. AC5 satisfied.

### Stale Content

`scripts/` directory does not exist on disk (confirmed `ls -d scripts/` fails). The extracted table should drop this row.

### Implementation Approach

| Step | Action |
|------|--------|
| 1 | Remove `### Directory Structure` subsection (table + heading) from `owlbear-system.instructions.md` |
| 2 | Replace the existing `## Directory Structure` table in `.github/copilot-instructions.md` with the extracted detailed table (minus stale `scripts/`, plus `tests/`) |
| 3 | Update frontmatter `description` from `"OwlBear system instructions — ..."` to `"System instructions — ..."` |
| 4 | Remove `@pytest.mark.xfail` from `test_instructions_have_no_serve_refs` in `tests/test_neutral_shared_1281.py` |

### Frontmatter Change

```yaml
# Before
description: "OwlBear system instructions — decision heuristics, system awareness, memory governance, and operational fundamentals"
# After
description: "System instructions — decision heuristics, system awareness, memory governance, and operational fundamentals"
```

### xfail Marker

`tests/test_neutral_shared_1281.py` line 71 has `@pytest.mark.xfail(strict=False, reason="RED: implementation in #1282")`. Once the `serve/` reference is removed, this test passes. The marker must be removed as part of #1282's implementation (per #1281 loop-breaker 3 downstream note).

## 4. Recommendation (confidence: 0.92)

Proceed with the 4-step implementation approach above. This is a straightforward content extraction with no design decisions, no new dependencies, and no architectural risk. Existing tests in `test_neutral_shared_1281.py` validate all AC conditions.

**Risks:**
- None material. The only complication was the stale `scripts/` entry, which is trivially resolved by dropping it.

Challenge: skipped — trivial scope, no trade-off decisions, no library choices.

## 5. Follow-up Tasks

No new tasks needed. Sibling tasks #1283 (cross-reference updates) and #1284 (init.py changes) already exist and cover the remaining P1 scope.

**AC refinement for architect:** Add explicit AC line: "Remove `@pytest.mark.xfail` from `test_instructions_have_no_serve_refs` in `tests/test_neutral_shared_1281.py`."
