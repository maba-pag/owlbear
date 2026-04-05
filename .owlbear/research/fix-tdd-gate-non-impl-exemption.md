# Fix TDD Gate to Exempt Non-Impl Pass-Through Tags

> **Owning task:** #630 — Fix TDD gate to exempt non-impl pass-through tags
> **Date:** 2026-04-05 **Status:** Complete

## 1. Context and Question

`gates.py` `check_tdd()` and `server.py` `_check_pick_gates()` reject any
in-progress task without `## Test-Writer Notes`. The w-dispatch-planning spec
(lines 65, 114, 158) explicitly exempts tasks with non-impl pass-through tags.
The code does not implement this exemption. Discovered during #619 architect review.

**Question:** What is the correct fix, and is the risk high enough to warrant it?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `serve/orchestrator/src/owlbear/planner/gates.py` L34-40 | 1.0 | `check_tdd()` — no tag check |
| 2 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L537-545 | 1.0 | `_check_pick_gates()` — no tag check |
| 3 | `share/skills/w-dispatch-planning/SKILL.md` L65,114,158 | 1.0 | Authoritative spec: non-impl tags exempt from TDD gate |
| 4 | `share/skills/w-tdd-red/SKILL.md` Step 1/1a | 0.9 | Test-writer always adds `## Test-Writer Notes` on pass-through |
| 5 | `share/skills/w-arch-review/SKILL.md` L78-80 | 0.8 | Architect tags non-impl tasks before approval |
| 6 | `serve/orchestrator/src/owlbear/planner/models.py` L23 | 0.8 | `Task.tags: list[str]` available in model |
| 7 | `tests/test_planner_gates.py` | 0.7 | No tag-based tests exist |
| 8 | `tests/test_pick_tasks_620.py` | 0.7 | No non-impl tag tests exist |

## 3. Analysis

### Practical Impact Assessment

| Scenario | Current behavior | Expected behavior | Impact |
|----------|-----------------|-------------------|--------|
| In-progress + quality tag + no TW Notes | FAIL (blocked) | PASS (exempt) | **Bug** |
| In-progress + agent tag + no TW Notes | FAIL (blocked) | PASS (exempt) | Bug |
| In-progress + no tags + no TW Notes | FAIL (blocked) | FAIL (blocked) | Correct |
| Normal task after test-writer pass-through | PASS (TW Notes added) | PASS | No impact |

**Mitigating factor:** The test-writer's Step 1a adds `## Test-Writer Notes` to
pass-through tasks, so in the **happy path** the missing exemption doesn't
manifest. However, the defense-in-depth principle requires the gate to match
the spec — race conditions or manual task moves can trigger the bug.

### Fix Approach

| Approach | Effort | Risk | KISS score |
|----------|--------|------|------------|
| A. Add tag set constant + intersection check | ~5 LOC x2 | Low | High |
| B. Import dispatch-planning constant from shared module | ~20 LOC | Medium (new dep) | Low |
| C. Do nothing (rely on test-writer adding header) | 0 LOC | Medium (spec-code drift) | N/A |

**Recommendation:** Approach A — define `_NON_IMPL_TAGS` frozenset in each file,
check `task.tags & _NON_IMPL_TAGS` (or `set(task.get("tags",[])) & _NON_IMPL_TAGS`).
Mirrors the existing inline-copy pattern used for all gates between the two files.

### Authoritative Tag List (from w-dispatch-planning L65)

`research`, `docs`, `type:config`, `type:docs`, `test`, `type:test`, `agent`, `quality`

### w-dispatch-planning SKILL.md Status

Lines 65, 114, 158 already document the exemption correctly. **No SKILL.md changes needed.**

## 4. Recommendation

Add `_NON_IMPL_TAGS` frozenset and tag-intersection check to both `check_tdd()`
in `gates.py` and `_check_pick_gates()` in `server.py`. (confidence: 0.92)

Challenge: N/A — T1 bug fix, no recommendation trade-off to challenge.

## 5. Follow-up Tasks

Task #630 itself has complete AC. No additional follow-up tasks needed — #630
covers both code locations, test requirements, and SKILL.md verification.
