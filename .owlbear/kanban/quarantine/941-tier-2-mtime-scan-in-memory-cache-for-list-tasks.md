---
id: 941
title: 'Tier 2: Mtime-scan in-memory cache for list_tasks()'
status: archived
priority: needed
created: 2026-04-17T20:16:32.182032+00:00
updated: 2026-04-17T21:52:08.649641+00:00
tags:
- cockpit
- engine
- phase-0
- type:build
parent: 920
depends_on:
- 921
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Add mtime-based in-memory task cache to `KanbanEngine` so `list_tasks()` re-parses only changed files. Target: <30ms warm reads at 1500 tasks.

## Context

Research #921 found `list_tasks()` at 1500 tasks takes ~1000ms (all in YAML parsing). Even with the Tier 1 parser switch (~390ms), the cockpit's 3s polling needs sub-150ms reads. An mtime cache brings warm reads to scandir+stat cost only (~25ms). See `.owlbear/research/list-tasks-perf-921.md`.

## Acceptance Criteria

- [ ] `KanbanEngine` caches parsed `Task` objects keyed by `(path, mtime_ns)`
- [ ] `list_tasks()` uses `os.scandir()` to detect new/deleted/modified files
- [ ] Only modified files are re-parsed; cached objects returned for unchanged files
- [ ] Cache invalidates correctly for: file creation, file deletion, file modification
- [ ] Engine's existing `revision` counter increments normally on writes (cache-coherent)
- [ ] Cold load latency unchanged from current behavior
- [ ] Warm read p99 <50ms at 1500 tasks (benchmark verification)
- [ ] Thread-safety: cache is per-instance (no shared state concerns for single-process cockpit)

## Files

- `serve/kanban/src/owlbear_kanban/engine.py`
- Tests in `serve/kanban/tests/` or `tests/`

## Design Notes

- Use `os.scandir()` instead of `glob()` — returns `DirEntry` with `stat()` already cached
- Cache structure: `dict[Path, tuple[float, Task]]` where float is `st_mtime_ns`
- Needs decomposition: may split into cache infrastructure + integration tasks
[[2026-04-17]]

## Research

- Research doc: .owlbear/research/mtime-cache-941.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: Simple mtime dict with lazy scandir invalidation — `dict[str, tuple[int, Task]]` per directory, ~35 LOC (confidence: 0.82)
- Challenge: reconsider (0.60 confidence in original) → accepted 6 corrections: AC type bug (float→int), revised latency estimate (25→35ms), refresh_config cache-clear, scandir/stat claim correction, lazy eviction clarification, archive_dir guard
- Follow-up tasks created: #942 (implement cache, research), #943 (extend to show_task/find_task_path, research)
- Decision requests: none — T1 autonomous (perf optimization, no new capability/arch change)
[[2026-04-17]]

## Planning

### Decomposition: Mtime-scan in-memory cache

Decomposition was performed by the researcher during the research phase. The planner validated the decomposition is correct and complete.

- Existing follow-up tasks: #942 (implement cache in list_tasks), #943 (extend to show_task/find_task_path)
- Dependency chain: #941 (this gate) → #942 → #943
- All three are children of #920

### Scope Overlap: #930 (Cockpit Cache)

Engine-level cache (#942) and cockpit-level cache (#930) are complementary layers:

- #942 makes list_tasks() warm reads <50ms (engine-internal, per-file granularity)
- #930 adds HTTP-level freshness checking for cockpit polling

If #942 lands first, #930's per-file scandir dict is redundant — cockpit cache can simplify to directory-level stat or rely on the engine's now-cheap list_tasks(). Note added for #930's future architect review.

## Architecture Review

### Task Role

# 941 is a research/decomposition gate task. Its deliverables are

1. Research doc: `.owlbear/research/mtime-cache-941.md` (complete)
2. Validated approach with 6 challenger corrections accepted
3. Decomposed follow-up tasks: #942, #943

**IMPORTANT FOR DOWNSTREAM AGENTS:** The implementation AC in this task body is SUPERSEDED by #942's refined AC. This task produces no testable Python code — treat as a research pass-through. The implementation work lives in #942 and #943.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Gate task: research + decomposition only |
| Interface clarity | PASS | Implementation interfaces defined in #942 AC |
| Dependency correctness | PASS | #941→#942→#943 chain is correct; #921 (prereq) done |
| Module layering | PASS | All changes within serve/kanban engine layer |
| TDD compliance | PASS | Test-writer handles #942/#943 via standard pipeline |
| KISS/YAGNI | PASS | ~35 LOC change, simple mtime dict, no over-engineering |
| Premise challenge | PASS | Research validated need: 1000ms→35ms for 1500-task reads |
| Pattern consistency | PASS | Per-instance state, lazy invalidation, fits engine pattern |
| Security surface | PASS | No new system boundaries — internal cache only |
| Single domain | PASS | Engine domain only (serve/kanban) |

### Stale AC Warning

The AC in #941's body has known bugs from before research corrections:

- Cache key type should be `str` not `Path`
- Mtime type should be `int` not `float` (float truncates at current epoch ns values)
- These are corrected in #942's AC — use #942 as the authoritative specification

### Challenge Results

- Challenger: reconsider (0.45 confidence in original APPROVE)
- Key concerns: (C1) decomposition rule, (C2) stale implementation AC, (C3) type:build tag, (C4) #930 overlap
- Architect response: accepted all concerns. Delegated to planner (C1 resolved). Stale AC documented with warning (C2). Tagging gap flagged to user (C3). #930 overlap analyzed as complementary (C4).

### Tagging Gap (requires manual fix)

Task is tagged `type:build` but produces no testable Python code. Needs `research` tag added for test-writer pass-through. The `edit_task` tool is unavailable — user must add the tag manually.

### Verdict: APPROVE

### Action Taken: Advanced to todo with planning section, architecture review, and stale-AC warning. Tagging gap flagged for manual resolution

[[2026-04-17]]

## Test-Writer Notes

- Non-implementation task — no tests applicable.
- Tagged `type:build` but Architecture Review explicitly states: "This task produces no testable Python code — treat as a research pass-through. The implementation work lives in #942 and #943."
- Tagging gap acknowledged by architect (needs `research` tag added manually).
- Passing through to builder.
[[2026-04-17]]

## Builder Notes

Pass-through gate task — no implementation code.

Architecture review and test-writer both confirmed: this task produces no testable Python code. Deliverables (research doc, validated approach, decomposed subtasks #942/#943) were completed in prior pipeline stages.

Advancing to review as pass-through.
[[2026-04-17]]

## Review Evidence

### Task Classification

Pass-through gate task — research + decomposition only. No Python code produced. Quality-runner and code-reader dispatch not applicable. Review scope: deliverable presence and quality.

### AC Compliance (gate task deliverables)

| Deliverable | Evidence | Status |
|-------------|----------|--------|
| Research doc at `.owlbear/research/mtime-cache-941.md` | File exists; 6 sources studied, latency analysis, type-bug correction (`float→int`), 6 challenger corrections accepted, Option A recommendation at 0.82 confidence | PASS |
| Validated approach with corrections | Research doc §4 documents all 6 corrections; task body Research section confirms | PASS |
| Decomposed follow-up task #942 | Task #942 exists (status: research), AC refined to incorporate all corrections — `dict[str, tuple[int, Task]]`, `refresh_config()` cache-clear, `archive_dir` guard, lazy invalidation clarification | PASS |
| Decomposed follow-up task #943 | Task #943 exists (status: research), correctly scoped as optional extension for `show_task()`/`_find_task_path()` | PASS |

### Quality Assessment

**Research doc:** STRONG — sources are primary (engine.py, task_io.py, models.py, prior research), latency table is concrete ($15ms scandir + $20ms filter/sort/convert = $35ms warm read), type-safety bug ($1.74 \times 10^{18} > 2^{53}$) caught and corrected, alternative approaches compared (A/B/C table), challenger review documented, memory footprint estimated (7.5MB at 1500 tasks).

**Decomposition:** STRONG — single implementation task (#942) is correct scope (~35 LOC), #943 correctly deferred as non-blocking extension, dependency chain `#941→#942→#943` is accurate.

**Stale AC warning:** Present and prominent in Architecture Review section — flags both type bugs (`Path→str`, `float→int`) and points downstream agents to #942 as authoritative spec.

### Known Non-Blocker

Tagging gap (`type:build` should include `research`) tracked and flagged by architect. Does not affect deliverable quality; test-writer and builder both handled pass-through correctly per the documented warning.

### No Code Changes

No files changed in source control — consistent with task scope.

### Verdict

0 deductions. Deliverables complete, research quality high, corrections thorough, decomposition correct. Confidence: .96 → PASS.
[[2026-04-17]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Research/decomposition gate — no Python code produced, no files changed in source control |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | Yes | Verified | `sources/overview.md` already contains #941 entry: Python `os.scandir`/`DirEntry` docs with URL, usage description, and research doc reference |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Verified | `.owlbear/research/mtime-cache-941.md` exists; linked from task body Research section; follow-up tasks #942 and #943 confirmed created (both visible in Review Evidence section) |

### Scratch Files

No `.owlbear/scratch/941-*` files found — nothing to clean.

### Files Updated

None required.

### Review Evidence Section

Present — passes Step 0a check.
[[2026-04-17]]

## Audit

### AC Verification (gate task deliverables)

| AC Line | Evidence | Status |
|---------|----------|--------|
| Research doc at `.owlbear/research/mtime-cache-941.md` | File exists: 6 sources, Option A recommendation at 0.82 confidence, 6 challenger corrections documented, type-safety bugs caught (float to int, Path to str) | PASS |
| Validated approach with corrections | Research doc S4 documents all 6 corrections; task body Research section confirms acceptance | PASS |
| Decomposed follow-up #942 | Task file exists at research status, AC refined with all corrections | PASS |
| Decomposed follow-up #943 | Task file exists at research status, scoped as optional extension | PASS |

### Test Results

- pytest: 263 passed, 6 failed (all in knowledge package, outside task scope — no code changes in this task)
- ruff: clean

### Architect Quality: 4/5

Correctly identified gate nature, documented stale AC warning prominently, accepted 6 challenger corrections, proper decomposition into #942/#943. Minor gap: original implementation AC left in place with warning rather than rewritten as gate-task AC.

### Deduction Breakdown

- No AC lines without evidence: 0
- Lint violations: 0
- AC quality 4/5 (above 3): 0
- Reviewer evidence: present and detailed: 0
- Full-suite failures in task scope: 0 (6 failures all in knowledge package, unrelated)

### Confidence: 1.00

### Action: archive
