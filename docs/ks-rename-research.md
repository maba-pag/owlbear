# Rename ks_CLI Functions to Full knowledge_source_ Prefix

> **Owning task:** #560 — Rename ks_CLI functions to full knowledge_source_ prefix
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

The code quality audit (F-17) flagged that `ks_add`, `ks_list`, `ks_show`, `ks_remove` use an abbreviated `ks_` prefix while all other CLI subcommand functions use full group names (`project_create`, `slack_auth`, `voice_listen`, etc.). Should we rename for consistency, or keep the abbreviation?

**Key constraint:** The `@command("add")` decorator controls the user-facing CLI name. The Python function name (`ks_add` vs `knowledge_source_add`) is **internal only** — users always type `bearclaw knowledge-source add`. This is a pure code-quality rename with zero user-facing impact.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Typer docs — Custom Command Name | <https://typer.tiangolo.com/tutorial/commands/name/> | .90 — confirms function name ≠ CLI name |
| Typer docs — SubCommands Single File | <https://typer.tiangolo.com/tutorial/subcommands/single-file/> | .95 — canonical pattern: `items_create`, `users_delete` |
| OwlBear code-quality-audit.md (F-17) | docs/code-quality-audit.md L220 | 1.0 — the finding that triggered this task |
| OwlBear cli.py (existing code) | src/bearclaw/cli.py | 1.0 — current naming inventory |

## 3. Analysis

### Current naming inventory (all CLI subcommand functions)

| Group | Functions | Pattern |
|-------|-----------|---------|
| project | `project_create`, `project_list`, `project_switch`, `project_archive`, `project_new` | `{group}_{action}` |
| voice | `voice_listen`, `voice_speak`, `voice_brainstorm` | `{group}_{action}` |
| **knowledge-source** | **`ks_add`, `ks_list`, `ks_show`, `ks_remove`** | **abbreviated** |
| slack | `slack_auth`, `slack_test`, `slack_status` | `{group}_{action}` |
| browser | `start`, `stop`, `browser_status` | mixed (separate issue) |
| auth | `login`, `status` | standalone (separate issue) |

**Only knowledge-source uses an abbreviation.** 15 of 19 subcommand functions follow `{group}_{action}`. The `ks_` prefix is the sole outlier.

### Option comparison

| Criterion | A: Rename to `knowledge_source_*` (.85) | B: Keep `ks_*` (.30) | C: Shorten to `ksource_*` (.15) |
|-----------|------------------------------------------|----------------------|----------------------------------|
| Consistency | Full alignment with 15/19 existing functions | Only outlier remains | New abbreviation, still inconsistent |
| Typer convention | Matches official `items_create` pattern | Violates convention | Violates convention |
| Readability | Immediately clear what group it belongs to | Requires context | Marginally better than ks_ |
| Breaking change | **None** — function names are internal | N/A | None |
| Effort | 4 function renames + update docs references | Zero | Same as A |
| Risk | Near zero — explicit `@command("add")` decouples CLI names | N/A | Same as A |

### Interaction with #481 (CLI split)

Task #481 plans to extract knowledge-source commands into `bearclaw/commands/knowledge_source.py`. If that split happens first, the functions could drop the prefix entirely (just `add`, `list`, `show`, `remove` in their own module). However:

- #481 is `backlog/important`, not yet in progress
- Renaming now is cheap (4 lines) and can be absorbed into #481 when that lands
- If #481 extracts to a separate module, the prefix becomes redundant — the builder can drop it then

**Recommendation:** Rename now for consistency. If #481 later drops the prefix entirely, that's fine — no wasted work either way.

## 4. Recommendation (.85 confidence)

**Rename `ks_*` to `knowledge_source_*`.** Rationale:

1. Matches the Typer official convention (`items_create`, `users_delete`)
2. Aligns with 15/19 existing functions in the codebase
3. Zero user-facing impact (CLI names unchanged)
4. 4 trivial function renames in one file
5. No test changes needed (tests invoke via CLI string, not function name)

**Risk:** Essentially none. The `@command("add")` decorator fully decouples the CLI command name from the Python function name. No external consumers reference these functions.

## 5. Follow-up Tasks

The research confirms this is a straightforward rename. The existing task #560 covers the implementation. No additional tasks needed beyond what already exists.

```
kanban\kanban-md.exe edit 560 --body "## Research Findings\n\nSee docs/ks-rename-research.md. Rename confirmed as correct approach (.85 confidence).\n\n## Acceptance Criteria\n\n- [ ] Rename ks_add -> knowledge_source_add\n- [ ] Rename ks_list -> knowledge_source_list\n- [ ] Rename ks_show -> knowledge_source_show\n- [ ] Rename ks_remove -> knowledge_source_remove\n- [ ] CLI command names unchanged (add, list, show, remove)\n- [ ] All tests pass (no test changes expected)\n- [ ] ruff clean\n- [ ] Update docs/code-quality-audit.md F-17 as resolved"
```
