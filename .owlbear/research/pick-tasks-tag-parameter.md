# pick_tasks Tag Parameter

> **Owning task:** #628 — Update pick_tasks AC to add optional tag parameter
> **Date:** 2026-04-05 **Status:** Complete

## 1. Context and Question

The orchestrator needs tag-based scope filtering (e.g., "Orchestrate: phase-2"). Without a `tag` parameter, `pick_tasks` returns all eligible tasks and the orchestrator can't filter without 25 `show_task` calls. Research from #622 (`wire-pick-tasks-orchestrator.md` §3.3) recommended Option B: add `tag: str` passthrough to `_run_kanban --tag`. This doc validates that finding against current codebase state.

## 2. Sources Studied

| # | Source | Rel. | What taken |
|---|--------|:----:|------------|
| S1 | `server.py` L162-226: `list_tasks` | 1.0 | Existing `--tag` passthrough: `if tag: args += ["--tag", tag]` — exact pattern to copy |
| S2 | `server.py` L141-161: `_run_kanban` | 1.0 | Uses `create_subprocess_exec` (no shell) — tag values safe from injection |
| S3 | `server.py` L549-580: `pick_tasks` | 1.0 | Current signature: `pick_tasks(ctx, *, limit=25)` — no tag param yet |
| S4 | `wire-pick-tasks-orchestrator.md` §3.3 | .95 | 3 options analyzed; Option B selected after challenger review (confidence .82) |
| S5 | `test_pick_tasks_620.py` L80-98 | .90 | Signature tests check for `limit` only; adding `tag` won't break them |
| S6 | `test_pick_tasks_620.py` L110-260+ | .90 | All tests mock `_run_kanban` returns; none assert specific CLI args passed |

## 3. Analysis

### 3.1 Validation: Existing Research Holds

| Criterion | Finding |
|-----------|---------|
| Option B (tag passthrough) still correct? | Yes. `list_tasks` proves the pattern works (S1). No alternative emerged. |
| Zero-config preserved? | Yes. Default `""` or `None` means no `--tag` arg passed to CLI. |
| Dependency chain valid? | Yes. #620 (done)→#621 (review)→#628→#622 (depends on [621,628]). |
| Tests break? | No. #620 tests don't assume absence of `tag`; they check `limit` exists (S5). |
| Security concern? | None. `create_subprocess_exec` prevents injection (S2). |

### 3.2 Parameter Type: `str = ""` vs `str | None = None`

| Aspect | `str = ""` | `str or None = None` |
|--------|------------|---------------------|
| Consistency with `list_tasks` | Match (S1) | Mismatch |
| Guard idiom | `if tag:` | `if tag is not None:` |
| MCP schema | `{type: string, default: ""}` | `{anyOf: [string, null], default: null}` |
| Empty-string edge case | Treated as "no filter" | Could pass `--tag ""` if not guarded |
| Complexity | Lower | Slightly higher |

**Recommendation (.85):** Use `str = ""` to match the `list_tasks` pattern. Both work; consistency within the same file wins. The AC specifies `str | None = None` — builder may follow AC literally; either is correct.

### 3.3 Implementation Scope

~3 LOC change in `server.py`:
1. Add `tag: str = ""` to `pick_tasks` signature
2. Add `if tag: args = [*args, "--tag", tag]` before `_run_kanban` call (or inline in the args build)
3. No changes to gates, sort, or return format

### 3.4 Test Impact

| Test file | Impact | Action needed |
|-----------|--------|---------------|
| `test_pick_tasks_620.py` (33 tests) | None — mocks don't assert CLI args | No change |
| `test_pick_tasks_621.py` (6 tests) | None — null body tests, no tag refs | No change |
| New #628 tests | Needed | 4-5 tests: param exists, default, tag forwarded, empty tag skipped |

## 4. Recommendation (confidence: .88)

Proceed with implementation as designed. The change is a trivial passthrough following the `list_tasks` pattern already proven in the same file. Recommend `str = ""` over `str | None = None` for consistency, but either is acceptable.

Challenge: SKIP — trivial validation of existing researched finding; 3-LOC passthrough of existing CLI flag using proven pattern in the same file. No new capability, no architecture change.

Tier: **T1 (Autonomous)** — adds optional parameter to existing tool using existing pattern. T2 advisory already communicated via #622 research.

## 5. Follow-up Tasks

No new follow-up tasks needed. #628 itself is the follow-up from #622 research. The dependency chain (#621→#628→#622) is already correct and complete.

AC item assessment for builder:
- "Update #621 AC" — append note to #621 body documenting the tag extension
- "Update #619 arch decision" — add `tag` to tool signature in #619 body
- "Update #620 tests" — not needed; tests don't assume no tag param
