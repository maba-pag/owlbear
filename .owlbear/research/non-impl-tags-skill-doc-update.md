# NON_IMPL_TAGS Skill Doc Update for type:user-action

> **Owning task:** #666 — Update NON_IMPL_TAGS skill doc references for type:user-action
> **Date:** 2026-04-07 **Status:** Complete

## 1. Context and Question

Task #662 added `type:user-action` to the Python frozensets (`_NON_IMPL_TAGS` in gates.py, `_PICK_NON_IMPL_TAGS` in server.py). The skill documentation files that enumerate these tags were not updated. This research identifies all locations needing the update.

**Question:** Which skill doc locations list NON_IMPL_TAGS and need `type:user-action` added?

## 2. Sources Studied

| Source | Path | Relevance |
|--------|------|-----------|
| gates.py frozenset | serve/orchestrator/src/owlbear/planner/gates.py L24-29 | 1.0 — authoritative Python source |
| server.py frozenset | serve/mcp-kanban/src/owlbear_mcp_kanban/server.py L531-539 | 1.0 — authoritative Python source |
| w-dispatch-planning | share/skills/w-dispatch-planning/SKILL.md | 1.0 — authoritative doc list |
| w-tdd-red | share/skills/w-tdd-red/SKILL.md | 1.0 — secondary doc copy |
| w-arch-review | share/skills/w-arch-review/SKILL.md L89-91 | 1.0 — secondary doc copy |
| Task #662 body | Done — confirmed implementation at commit 6ee05d3 | .95 — dependency verification |

## 3. Analysis

### Locations requiring update

| # | File | Section | Current list (abbreviated) | Cross-ref comment |
|---|------|---------|---------------------------|-------------------|
| 1 | w-dispatch-planning/SKILL.md | Agent dispatch table, `todo` row | 8 tags, missing `type:user-action` | Authoritative (self-declared) |
| 2 | w-dispatch-planning/SKILL.md | Recipe 1 `TW:MISSING` gate flag | 8 tags, missing `type:user-action` | `<!-- NON_IMPL_TAGS — authoritative list -->` |
| 3 | w-tdd-red/SKILL.md | Step 1 item 1 | 8 tags, missing `type:user-action` | Points to w-dispatch-planning |
| 4 | w-arch-review/SKILL.md | Non-impl tagging note (L91) | 8 tags, missing `type:user-action` | Points to w-dispatch-planning |

### Cross-reference comment at w-dispatch-planning L5-7

```
<!-- NON_IMPL_TAGS: This is the authoritative list. Secondary copies:
     skills/w-tdd-red/SKILL.md (Step 1 item 3),
     skills/w-arch-review/SKILL.md (non-impl tagging note). -->
```

All three files named in this comment need the update.

### Risk assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Missed location | Very low | Agent skips test-writer for user-action tasks | Grep verified: 4 locations are exhaustive |
| AC scope mismatch (w-arch-review not in AC) | Low | Inconsistent cross-references | AC #3 requires consistency; w-arch-review is a declared secondary copy |

## 4. Recommendation (confidence: .95)

Add `type:user-action` to all 4 locations. Trivial text additions to existing comma-separated tag lists. No structural changes.

Challenge: FALLBACK — trivial docs task, challenger not warranted.

## 5. Follow-up Tasks

No additional follow-up tasks needed — task #666 itself is the implementation vehicle (type:docs, will pass through test-writer to builder). AC should be clarified to include w-arch-review location for completeness.
