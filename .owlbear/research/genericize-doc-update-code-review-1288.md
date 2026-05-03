# Genericize w-doc-update and w-code-review

> **Owning task:** #1288 — P2-04: Genericize w-doc-update and w-code-review
> **Date:** 2026-05-03 **Status:** Complete

## 1. Context and Question

Task #1288 requires genericizing `w-doc-update/SKILL.md` and `w-code-review/SKILL.md` to remove hardcoded `serve/` paths, using the prose-first notation convention from the neutral-shared-layer brief (decisions D5, D8).

**Question:** Is the work already complete, and does the current implementation match the brief's notation convention?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| Builder commit | `8e442bdc` (#1285) | 1.0 — implementation that changed the files |
| Brief | `.owlbear/briefs/draft-neutral-shared/brief.md` | 1.0 — notation convention authority |
| Test gate | `tests/test_path_neutrality_1285.py` | 1.0 — automated verification |
| w-doc-update pre-change | `git show 8e442bdc~1:share/skills/w-doc-update/SKILL.md` | 0.9 — baseline |
| w-code-review pre-change | `git show 8e442bdc~1:share/skills/w-code-review/SKILL.md` | 0.9 — baseline |
| Sibling skills (h-pytest, h-vitest, h-quality-runner) | Current state | 0.8 — consistency check |

## 3. Analysis

### Changes already made (commit 8e442bdc)

| File | Line | Before | After |
|------|------|--------|-------|
| w-doc-update/SKILL.md | 50 | `serve/*/README.md` | `workspace/*/README.md` |
| w-code-review/SKILL.md | 52 | `serve/{package}/src/` | `workspace/{package}/src/` |
| w-code-review/SKILL.md | 104 | `serve/{package}/src/` | `workspace/{package}/src/` |

### AC Assessment

| AC Line | Status | Evidence |
|---------|--------|----------|
| AC1: 3 IN-scope path entries genericized | ✅ Done | 3 total serve/ refs removed (1 + 2) |
| AC2: lint_paths template genericized | ✅ Done | Both occurrences changed |
| AC3: No serve/ paths remain | ✅ Done | `grep -n 'serve/' ...` = 0 hits |
| AC4: Notation follows Brief convention | ⚠️ Partial | Uses `workspace/` prefix, not prose-first + framed examples |
| AC5: Tests from #1285 pass | ✅ Done | `test_no_serve_path_refs_in_skill_files` PASSED |

### Notation Convention Gap

The brief (D5, D8) specifies:
- Inline conceptual nouns: "your source packages"
- Framed examples: `> Example (OwlBear-dev): serve/cockpit/web/`

The builder used `workspace/` as a blanket substitute. This was applied **consistently across all 14 affected skills** in a single commit. No framed examples were added to any file.

### Why `workspace/` is acceptable for tool-invocation templates

The brief's notation convention has a genuine tension with **executable templates** containing per-task fill-in variables (`{package}`, `{module}`, `{task_id}`). These templates predate the neutrality effort and serve a different purpose than documentation prose.

- `{package}` = per-task variable (reviewer fills from each task's scope)
- `workspace/` = project-resolution prefix (neutral replacement for `serve/`)
- The h-quality-runner routing logic depends on the `workspace/` convention for toolchain selection

Applying prose-first to YAML invocation specs would make them harder to copy-paste and create inconsistency with the routing logic in h-quality-runner.

### Comparison: notation approaches

| Approach | Pros | Cons |
|----------|------|------|
| `workspace/{package}/src/` (current) | Consistent across 14 files, tests pass, routing works | Not a real path, not prose-first per brief |
| Prose-first + framed example | Matches brief D5/D8, more educational | Awkward in YAML templates, inconsistent with routing |
| Drop prefix entirely (`{package}/src/`) | Minimal, relies on copilot-instructions.md | Breaks routing logic, unclear |

## 4. Recommendation (confidence: 0.82)

**Accept current state as complete.** The core requirement (remove serve/ hardcoding) is met and verified by automated tests. The `workspace/` convention is consistent across all 14 affected skills, integrates with h-quality-runner routing, and is understood by agents.

The notation gap (AC4) is real but cosmetic — it doesn't affect agent behavior. Revising notation for 2 skills while 12 others use the same `workspace/` convention would create worse inconsistency than the current uniform approach.

If notation refinement is desired, it should be a single low-priority task covering all 14 skills uniformly (scope: phase-3 cosmetic).

Challenge: proceed — confidence in original: 0.82

## 5. Follow-up Tasks

None required for task advancement. Optional follow-up:
- Notation refinement (nice-to-have, phase-3 cosmetic): revise `workspace/` to prose-first across all affected skills — deferred per brief's Phase 3 trigger ("Defer until consumer friction reports").
