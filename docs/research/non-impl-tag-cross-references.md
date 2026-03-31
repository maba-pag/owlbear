# Non-Impl Tag List Cross-Reference Strategy

> **Owning task:** #218 — Sync non-impl tag list cross-references across skill files
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

The non-impl tag list (`research`, `docs`, `type:config`, `type:docs`, `test`,
`type:test`, `agent`, `quality`) is duplicated across 3 files. Task #215 expanded
the list from 4 to 8 tags but identified synchronization risk (section 3.4 of
`docs/research/gate4-tw-missing-tag-exemptions.md`). How should cross-references
be added so future tag additions stay synchronized?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `.github/copilot-instructions.md` L15 | Internal | DRY principle: "Single source of truth for every piece of knowledge" |
| S2 | `agent-common.instructions.md` L279 | Internal | Existing pattern: "This table is the single source of truth" |
| S3 | Kubernetes contributor guide (README.md) | External | "single source of truth" declaration pattern in docs |
| S4 | GitLab CTRT docs — Related Topics convention | External | Cross-reference sections as standard docs practice |
| S5 | `docs/research/gate4-tw-missing-tag-exemptions.md` §3.4 | Internal | Original risk identification and impact map |
| S6 | GitHub Actions `paths-ignore` / CI lint patterns | External | Script-based sync validation in CI pipelines |

## 3. Analysis

### 3.1 Verified file inventory

| File | Location | Role |
|------|----------|------|
| `skills/dispatch-planning/SKILL.md` | L21 (table) + L27-28 (paragraph) | **Authoritative** — defines the tag list |
| `skills/tdd-red/SKILL.md` | L26 (Step 1 item 3) | Secondary — uses the list for pass-through logic |
| `.github/prompts/agent-audit.prompt.md` | L107-108 | Secondary — uses the list for audit verification |

**Not present:** `.github/copilot-instructions.md` — the #215 research doc mentioned
4 files, but copilot-instructions does not contain the list. Only 3 files have it.

**Tag-independent:** `skills/tdd-workflow/SKILL.md` checks for "Non-implementation task"
text in TW notes, not tags. No cross-reference needed.

### 3.2 Approach comparison

| Approach | Complexity | Maintenance | Agent-readable | KISS/YAGNI |
|----------|------------|-------------|----------------|------------|
| HTML comment markers (rec:) | Low | Manual, guided | Yes — visible in raw md | Best fit |
| Prose cross-reference (bp:) | Low | Manual, guided | Yes | Good |
| Validation script | Medium | Auto-checked | N/A (CI) | Over-engineered |
| Markdown include/template | High | Auto-synced | N/A (build-time) | Over-engineered |

### 3.3 Recommended pattern

Combine HTML comment + prose note. At each secondary location, add directly above
the tag list:

```markdown
<!-- NON_IMPL_TAGS: Authoritative list at skills/dispatch-planning/SKILL.md
     (agent dispatch table). Update there first, then sync here. -->
```

At the authoritative location (dispatch-planning SKILL.md), add:

```markdown
<!-- NON_IMPL_TAGS: This is the authoritative list. Secondary copies:
     skills/tdd-red/SKILL.md (Step 1 item 3),
     .github/prompts/agent-audit.prompt.md (Non-impl paragraph). -->
```

**Why HTML comments work here:** These files are read by LLM agents consuming raw
markdown. HTML comments are visible in raw source (which agents read via `read_file`)
but don't clutter rendered output. The keyword `NON_IMPL_TAGS` is grep-searchable,
making all locations discoverable with `grep_search NON_IMPL_TAGS`.

## 4. Recommendation (.90 confidence)

Use HTML comment markers with a `NON_IMPL_TAGS` keyword at all 3 locations. This
satisfies both AC items:

1. Each file gets a cross-reference comment pointing to dispatch-planning SKILL.md
2. The `NON_IMPL_TAGS` keyword is grep-searchable — updating requires: (a) change
   the authoritative list, (b) `grep NON_IMPL_TAGS` to find all secondary copies

Risk: Manual sync is still required. Mitigation: the comment is explicit about
update-there-first-then-sync-here, and the grep keyword makes it findable. A
validation script is not warranted for 3 files (YAGNI).

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add NON_IMPL_TAGS cross-reference comments to 3 skill files" --priority nice-to-have --status ideation --tags "scope:agents,quality,type:config" --body "## Acceptance Criteria\n- [ ] dispatch-planning SKILL.md has NON_IMPL_TAGS comment listing secondary locations\n- [ ] tdd-red SKILL.md has NON_IMPL_TAGS comment pointing to dispatch-planning as authoritative\n- [ ] agent-audit.prompt.md has NON_IMPL_TAGS comment pointing to dispatch-planning as authoritative\n- [ ] grep NON_IMPL_TAGS returns exactly 3 files\n\n## Context\nSee docs/research/non-impl-tag-cross-references.md for recommended pattern. Created from #218 research."
```
