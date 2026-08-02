---
id: 1274
title: 'P1-08: Update memory skill documentation'
status: archived
priority: medium
created: 2026-05-02T03:43:38.563184+00:00
updated: 2026-05-03T17:55:48.457105+00:00
tags:
- phase-1
- scope:docs
parent: 1266
depends_on:
- 1273
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Update skill documentation to reflect the new file-based architecture, tool API, and curation workflow.

Brief: see parent #1266

## Scope

**In scope:**
- `share/skills/h-mcp-memory/SKILL.md` — tool reference (5 tools, params, access rules)
- `share/skills/h-memory-structure/SKILL.md` — entry shape, file format, frontmatter schema
- `share/skills/w-mem-curation/SKILL.md` — curation workflow (state promotion, delete/purge, approval flow)
- `share/skills/r-pipeline-protocol/SKILL.md` — update Post-task Reflection section to reference new tool names

**Out of scope:**
- Agent file changes (no `.agent.md` modifications in this task)
- Consumer documentation (README updates for the package if needed — separate task)
- Instruction stub changes (existing `applyTo` patterns remain valid)

## Acceptance Criteria

- [ ] h-mcp-memory documents all 5 tools with params, return values, and access restrictions (td:0)
- [ ] h-memory-structure documents the YAML frontmatter schema including an explicit enumeration of all 9 category values (`knowledge`, `behaviour`, `pitfall`, `process`, `tool`, `goal`, `personality`, `preference`, `context`), the 4 states, and confidence range (td:0)
- [ ] w-mem-curation documents the explicit state machine: `pending → curated` (via `update_entry`), `curated → approved` (via `approve_entry`), `{pending,curated,approved} → deleted` (via `delete_entry`); includes a transitions table and references which tool triggers each transition (td:0)
- [ ] r-pipeline-protocol Post-task Reflection references `store_learning` (not old tool name) (td:0)
- [ ] No references to SQLite, old tool names, or old schema remain in updated skills (td:0)
- [ ] All skill files pass markdown lint (no broken links, valid frontmatter) (td:0)

Test-writer: SKIP (all AC lines td:0 — documentation content only)

## Builder Guidance

**This IS implementation work.** The deliverable is edited SKILL.md files. Do NOT pass through.

**Current state (from prior review cycle):**
- AC 1 (h-mcp-memory): ALREADY SATISFIED — file has all 5 tools documented with params, returns, access rules, and category table. No edits needed.
- AC 4 (r-pipeline-protocol): ALREADY SATISFIED — `store_learning` reference is in place. No edits needed.
- AC 5 (no old references): ALREADY SATISFIED — no SQLite/old tool references found. No edits needed.
- AC 6 (markdown lint): ALREADY SATISFIED — all 4 files pass markdownlint. No edits needed.

**Remaining work (focus here):**

1. **AC 2 — h-memory-structure** (`share/skills/h-memory-structure/SKILL.md`):
   - The `categories` field in the Entry Shape table says "One or more values from the 9-value enum" but never lists them.
   - Add an inline enumeration after the Entry Shape table. Either a brief list or a table with values and meanings (can mirror `h-mcp-memory` § Categories). Reference source: `serve/mcp-memory/src/owlbear_mcp_memory/models.py` `MemoryCategory` literal.

2. **AC 3 — w-mem-curation** (`share/skills/w-mem-curation/SKILL.md`):
   - The workflow handles states implicitly but lacks an explicit state machine section.
   - Add a `## State Machine` section (or subsection under Architecture) with a transitions table:

     | From | To | Trigger | Tool | Actor |
     |------|----|---------|------|-------|
     | `pending` | `curated` | Curator promotes after review | `update_entry(state="curated")` | curator agent |
     | `curated` | `approved` | User signs off | `approve_entry` | human user |
     | `pending` | `deleted` | Noise/duplicate pruned | `delete_entry` | curator agent |
     | `curated` | `deleted` | Superseded or invalidated | `delete_entry` | curator agent |
     | `approved` | `deleted` | Obsolete knowledge purged | `delete_entry` | curator agent |

   - The "purge flow" means: periodic curation can mark approved entries as deleted when they become obsolete; document this explicitly.

## Prior Cycle (reference only)

Previous pipeline cycle (2026-05-03) failed at review: builder incorrectly classified as non-impl pass-through. AC 2 and AC 3 were not met. AC 1, 4, 5, 6 verified PASS by reviewer. Full review evidence retained for context above.
[[2026-05-03]]
## Architecture Review

**Verdict:** APPROVE (refined) — backlog → todo

### AC Assessment

| AC line | Assessment | Action |
|---------|-----------|--------|
| h-mcp-memory documents 5 tools | Already satisfied per reviewer evidence | No change, td:0 |
| h-memory-structure documents schema + 9 categories | FAIL in prior cycle — "9-value enum" referenced but not enumerated | Tightened: AC now lists all 9 values explicitly; builder guidance specifies exact edit location |
| w-mem-curation state machine + purge flow | FAIL in prior cycle — states handled implicitly, no explicit transitions table | Tightened: AC now specifies exact transitions table with tool/actor mapping |
| r-pipeline-protocol references store_learning | Already satisfied per reviewer evidence | No change, td:0 |
| No old references remain | Already satisfied per grep evidence | No change, td:0 |
| Markdown lint passes | Already satisfied | No change, td:0 |

### Architecture Notes

- All 6 AC lines are td:0 (documentation content, no testable Python interface). Test-writer: SKIP.
- Prior cycle failure was a routing defect: builder incorrectly classified as non-impl pass-through. Fixed via explicit "Builder Guidance" section stating this IS implementation work.
- Source of truth for categories: `serve/mcp-memory/src/owlbear_mcp_memory/models.py` `MemoryCategory` literal.
- State machine transitions derived from `h-mcp-memory` tool documentation (update_entry state rules, approve_entry, delete_entry).
- No new modules, no code changes, no security surface.

### Dependency Analysis

- Parent #1266 (archived): restructured mcp-memory module — committed initial versions of all 4 scoped files.
- Dep #1273 (archived): MCP tool layer implementation — all tools exist and function.
- No blocking dependencies remain.

### Challenge

Challenge: SKIP — all AC lines td:0 per Step 2.1.
[[2026-05-03]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.
[[2026-05-03]]
## Builder Notes
- Implementation: updated share/skills/h-memory-structure/SKILL.md and share/skills/w-mem-curation/SKILL.md.
- AC2: added explicit schema enumeration for all 9 category values, all 4 states, and confidence range in h-memory-structure.
- AC3: added explicit `## State Machine` section in w-mem-curation with required transitions table and tool/actor mapping, including approved->deleted purge flow note.
- Validation: `npx --yes markdownlint-cli share/skills/h-memory-structure/SKILL.md share/skills/w-mem-curation/SKILL.md` passed.
- Legacy-reference check: `rg -n -i -e 'sqlite|add_learning|get_learnings|curate_learning|old schema' ...` returned no matches in edited files.
- Tests: 0 task tests (td:0 documentation task; test-writer skipped).
- Coverage: n/a (documentation-only task).
- ruff: n/a (no Python source changes).
- Commit: `3c1e77fe` (`docs: update memory skill docs (#1274, builder)`).

### Post-task Reflection
- Problem faced: the prior cycle failed due a non-impl pass-through misclassification despite explicit AC requiring doc edits.
- Workaround applied: followed Builder Guidance directly and limited changes to AC2/AC3-only insertions.
- Pattern discovered: td:0 doc tasks still require concrete artifact edits and validation evidence before advancing.
- Quality gap noted: markdownlint tool alias can vary (`markdownlint` vs `markdownlint-cli`), so fallback invocation should be documented in future runbooks.
[[2026-05-03]]
## Review Evidence
### Test Results
- Task depth: td:0 documentation task; no task tests were required or run.
- quality-runner report: no tests requested; ruff exit 0 and skill validation exit 0 on the four scoped skill files.

### Lint
- Direct AC-specific validation: `npx --yes markdownlint-cli share/skills/h-mcp-memory/SKILL.md share/skills/h-memory-structure/SKILL.md share/skills/w-mem-curation/SKILL.md share/skills/r-pipeline-protocol/SKILL.md` exited 0 with no output.
- quality-runner supplemental lint/validation: clean.

### Coverage
- N/A for td:0 documentation task.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Not applicable. All AC lines are `(td:0)` and test-writer correctly skipped.

#### Security Review
- No security issues. Builder commit `3c1e77fe` changed only `share/skills/h-memory-structure/SKILL.md` and `share/skills/w-mem-curation/SKILL.md`.

#### Builder Process Quality
- CLEAN. `rg -n '^## Review Evidence$' .owlbear/kanban/tasks/1274-p1-08-update-memory-skill-documentation.md` returned no matches, so loop-breaker retry count is 0 by header count.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| h-mcp-memory documents all 5 tools with params, return values, and access restrictions | Tool summary and per-tool parameter/return/access sections are present in [share/skills/h-mcp-memory/SKILL.md](share/skills/h-mcp-memory/SKILL.md#L14) and [share/skills/h-mcp-memory/SKILL.md](share/skills/h-mcp-memory/SKILL.md#L24). | PASS |
| h-memory-structure documents the YAML frontmatter schema including all 9 categories, 4 states, and confidence range | Schema table and explicit enumerations are present in [share/skills/h-memory-structure/SKILL.md](share/skills/h-memory-structure/SKILL.md#L13), matching the live enum/state fields in [serve/mcp-memory/src/owlbear_mcp_memory/models.py](serve/mcp-memory/src/owlbear_mcp_memory/models.py#L30). | PASS |
| w-mem-curation documents the explicit state machine and tool-triggered transitions | Required transitions table and purge-flow note are present in [share/skills/w-mem-curation/SKILL.md](share/skills/w-mem-curation/SKILL.md#L19). | PASS |
| r-pipeline-protocol Post-task Reflection references `store_learning` | Post-task Reflection names `store_learning` in [share/skills/r-pipeline-protocol/SKILL.md](share/skills/r-pipeline-protocol/SKILL.md#L223). | PASS |
| No references to SQLite, old tool names, or old schema remain in updated skills | FAIL: stale singular field name `scope_agent` still appears in [share/skills/h-memory-structure/SKILL.md](share/skills/h-memory-structure/SKILL.md#L102) and [share/skills/h-memory-structure/SKILL.md](share/skills/h-memory-structure/SKILL.md#L119), but the live schema and tool signatures use `scope_agents` in [serve/mcp-memory/src/owlbear_mcp_memory/models.py](serve/mcp-memory/src/owlbear_mcp_memory/models.py#L36), [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L101), and [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L170). | FAIL |
| All skill files pass markdown lint | Direct `markdownlint-cli` run exited 0 across all four scoped files. | PASS |

### Deductions
- -0.18: AC5 violation due to stale `scope_agent` references remaining in `h-memory-structure`.
- Final confidence: 0.82

### Verdict
- FAIL. Route to `in-progress`.

### Required Follow-up
- Replace the stale singular field name `scope_agent` with `scope_agents` in both places in [share/skills/h-memory-structure/SKILL.md](share/skills/h-memory-structure/SKILL.md).
- Rerun `markdownlint-cli` on the four scoped skill files after the wording fix.
[[2026-05-03]]
## Builder Notes
- Implementation: updated `share/skills/h-memory-structure/SKILL.md` only.
- Fix applied: replaced stale singular field references with canonical `scope_agents` naming in content-quality and anti-pattern sections.
- Tests: 0 task tests (all AC lines are `td:0`; test-writer skip remains valid).
- Coverage: n/a (documentation-only task).
- ruff: n/a (no Python source changes).
- Markdown lint: `npx --yes markdownlint-cli share/skills/h-mcp-memory/SKILL.md share/skills/h-memory-structure/SKILL.md share/skills/w-mem-curation/SKILL.md share/skills/r-pipeline-protocol/SKILL.md` -> pass (exit 0).
- Evidence check: `rg -n "scope_agent" share/skills/h-memory-structure/SKILL.md` shows only `scope_agents` occurrences (no stale singular field name remaining).
- Commit: `78448069` (`docs: fix scope_agents naming in memory structure skill (#1274, builder)`).

### Post-task Reflection
- Problem faced: prior review evidence indicated AC5 fail was narrowly scoped to stale field naming in one file.
- Workaround applied: performed a surgical one-file correction instead of re-editing already-passing AC areas.
- Pattern discovered: documentation AC regressions often come from schema-name drift even when larger sections are complete.
- Quality gap noted: grep pattern matching can return normalized matches (`scope_agents`) even when searching for `scope_agent`; verify the actual rendered lines before concluding.
[[2026-05-03]]
## Review Evidence
### Test Results
- Task depth: td:0 documentation task; no task tests were required or run.
- Quality-runner lint-only pass initially hit a markdown lint environment limitation; the mandated retry succeeded cleanly.

### Lint
- Quality-runner retry reported clean lint with markdown lint exit code 0.
- Direct `markdownlint-cli` validation across `share/skills/h-mcp-memory/SKILL.md`, `share/skills/h-memory-structure/SKILL.md`, `share/skills/w-mem-curation/SKILL.md`, and `share/skills/r-pipeline-protocol/SKILL.md` exited 0 with no output.
- Editor diagnostics reported no errors in the same four skill files.

### Coverage
- Not applicable for a td:0 documentation task.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Not applicable. All AC lines are td:0 and test-writer correctly skipped.

#### Security Review
- No security issues. Latest builder commit `78448069` changed only `share/skills/h-memory-structure/SKILL.md`.

#### Test Integrity
- Not applicable. No `TestFromAC_*` files or classes are in scope, and the latest builder commit touched no test files.

#### Test Quality
- Not applicable. No task tests were required for this td:0 documentation task.

#### Data Safety
- No issues. Documentation-only change.

#### Implementation-Aware Gap Analysis
- FAIL: AC1 remains incomplete. `share/skills/h-mcp-memory/SKILL.md:48-50` documents `query_memory` with only `states`, but the public MCP surface exposes additional parameters `categories`, `scope_agents`, `min_confidence`, and `limit` at `serve/mcp-memory/src/owlbear_mcp_memory/server.py:97-104`, matching the implementation at `serve/mcp-memory/src/owlbear_mcp_memory/tools.py:124-131`.
- Rebuttal to the stale prior PASS record: earlier task notes and the prior review marked AC1 satisfied, but the live public API is the controlling source of truth for this review. The builder retry changed only `share/skills/h-memory-structure/SKILL.md`, so AC1 stayed untouched and still fails.

#### Necessity Check
- Not applicable. No dependency, integration, or external capability was added.

#### Builder Process Quality
- CLEAN on builder retry shape: two builder sections, with the second limited to the exact stale-field-name fix from the prior review.
- Routing note: the task file already contains one prior `## Review Evidence` section at `.owlbear/kanban/tasks/1274-p1-08-update-memory-skill-documentation.md:139`. Per `share/skills/r-pipeline-protocol/SKILL.md:107-108`, a second reviewer fail routes to backlog.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| h-mcp-memory documents all 5 tools with params, return values, and access restrictions | FAIL: `share/skills/h-mcp-memory/SKILL.md:48-50` documents `query_memory` only with `states`; public MCP registration exposes `states`, `categories`, `scope_agents`, `min_confidence`, and `limit` at `serve/mcp-memory/src/owlbear_mcp_memory/server.py:97-104`, and the implementation matches at `serve/mcp-memory/src/owlbear_mcp_memory/tools.py:124-131`. | FAIL |
| h-memory-structure documents the YAML frontmatter schema including all 9 categories, 4 states, and confidence range | `share/skills/h-memory-structure/SKILL.md:17-33` enumerates the fields, 9 categories, 4 states, and inclusive confidence range; this matches `serve/mcp-memory/src/owlbear_mcp_memory/models.py:11-22` and `serve/mcp-memory/src/owlbear_mcp_memory/models.py:30-38`. | PASS |
| w-mem-curation documents the explicit state machine and tool-triggered transitions | `share/skills/w-mem-curation/SKILL.md:19-31` contains the required transitions table and purge-flow note. | PASS |
| r-pipeline-protocol Post-task Reflection references `store_learning` | `share/skills/r-pipeline-protocol/SKILL.md:223-241` references `store_learning` and its category mapping. | PASS |
| No references to SQLite, old tool names, or old schema remain in updated skills | A legacy-string sweep across the four scoped skill files found no matches for `sqlite`, `add_learning`, `get_learnings`, `curate_learning`, `old schema`, or stale singular `scope_agent`. | PASS |
| All skill files pass markdown lint | Quality-runner retry reported clean lint, direct `markdownlint-cli` validation exited 0 with no output, and editor diagnostics reported no errors. | PASS |

### Deductions
- -0.20: AC1 remains unmet because `query_memory` parameter documentation is incomplete against the live public MCP surface.
- -0.02: Earlier task guidance and the prior review incorrectly marked AC1 satisfied, so the verdict depends on overruling stale task-local assumptions with current source-of-truth inspection.
- Final confidence: 0.78

### Verdict
- FAIL. This is the second review failure on the current task file state, so the loop-breaker rule sends it to backlog.

### Required Follow-up
- Re-open AC1 at architecture review instead of inheriting the earlier PASS assumption.
- If AC1 truly requires full parameter coverage, update `share/skills/h-mcp-memory/SKILL.md` so the `query_memory` section documents `categories`, `scope_agents`, `min_confidence`, and `limit` in addition to `states`.
- Re-run markdown lint on the four scoped skill files after the documentation fix.
[[2026-05-03]]

[[2026-05-03]]
## Architecture Review (cycle 2)

**Verdict:** APPROVE (refined) — backlog → todo

### AC Assessment

| AC line | Assessment | Action |
|---------|-----------|--------|
| AC1: h-mcp-memory documents all 5 tools with params | FAIL in prior cycle — `query_memory` only documents `states`; live MCP surface exposes 5 params | Builder guidance updated with exact params to add |
| AC2: h-memory-structure documents schema + 9 categories | PASS (satisfied in prior build) | No change, td:0 |
| AC3: w-mem-curation state machine | PASS (satisfied in prior build) | No change, td:0 |
| AC4: r-pipeline-protocol references store_learning | PASS (satisfied in prior build) | No change, td:0 |
| AC5: No old references remain | PASS (fixed in prior build) | No change, td:0 |
| AC6: Markdown lint passes | PASS | No change, td:0 |

### Architecture Notes

- All AC lines remain td:0. Test-writer: SKIP.
- Only AC1 requires further work: `query_memory` section in `share/skills/h-mcp-memory/SKILL.md` must document all 5 parameters to match the public MCP surface at `serve/mcp-memory/src/owlbear_mcp_memory/server.py:97-104`.
- No structural changes, no new modules, no security surface.

### Dependency Analysis

- Dep #1273 (done/archived): tools exist and function. No blockers.

### Challenge

Challenge: SKIP — all AC lines td:0 per Step 2.1.

### Updated Builder Guidance

**Only AC1 remains.** All other AC lines are satisfied from prior cycles.

**AC1 fix — `share/skills/h-mcp-memory/SKILL.md`:**

The `query_memory` section (around line 40-50) currently documents only `states`. Add the missing 4 parameters to the parameter table to match the live implementation at `serve/mcp-memory/src/owlbear_mcp_memory/tools.py:124-131`:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `states` | list[str] \| null | `null` | Optional explicit state filter (default: curated + approved) |
| `categories` | list[str] \| null | `null` | Filter by category values |
| `scope_agents` | list[str] \| null | `null` | Filter by agent scope |
| `min_confidence` | float \| null | `null` | Minimum confidence threshold (inclusive) |
| `limit` | int \| null | `null` | Maximum entries to return |

After editing, verify with `markdownlint-cli` on all 4 scoped files.

[[2026-05-03]]
APPROVE (refined) — cycle 2. Only AC1 remains: query_memory param table needs 4 additional params documented. Builder guidance updated with exact table.
[[2026-05-03]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.
[[2026-05-03]]
## Builder Notes
- Implementation: updated `share/skills/h-mcp-memory/SKILL.md` only.
- Fix applied: expanded `query_memory` docs to include all supported parameters (`states`, `categories`, `scope_agents`, `min_confidence`, `limit`) in both Tool Summary and the parameter table.
- Tests: 0 task tests (all AC lines are `td:0`; test-writer skip remains valid).
- Coverage: n/a (documentation-only task).
- ruff: n/a (no Python source changes).
- Markdown lint: `npx --yes markdownlint-cli share/skills/h-mcp-memory/SKILL.md share/skills/h-memory-structure/SKILL.md share/skills/w-mem-curation/SKILL.md share/skills/r-pipeline-protocol/SKILL.md` -> pass (exit 0).
- API/doc parity check: `rg -n "query_memory|states|categories|scope_agents|min_confidence|limit" share/skills/h-mcp-memory/SKILL.md` confirms all 5 query params are documented.
- Commit: `22f9c1ab` (`docs: complete query_memory params in memory skill (#1274, builder)`).

### Post-task Reflection
- Problem faced: prior cycle assumptions marked AC1 as complete, but reviewer evidence showed drift against the live MCP signature.
- Workaround applied: verified the current server/tool signatures first, then made a one-file surgical doc correction.
- Pattern discovered: API parameter drift in handbook docs is easiest to catch by matching the public MCP registration signature.
- Quality gap noted: task-local historical guidance can become stale across retries; source code must remain the final authority.
[[2026-05-03]]
## Review Evidence
### Test Results
- Task depth: td:0 documentation task; no task tests were required or run.
- Quality-runner retry reported 0 requested tests, 0 failures, markdownlint exit code 0, and no execution errors for the four scoped skill files.

### Lint
- Quality-runner retry reported clean markdown lint for [share/skills/h-mcp-memory/SKILL.md](share/skills/h-mcp-memory/SKILL.md), [share/skills/h-memory-structure/SKILL.md](share/skills/h-memory-structure/SKILL.md), [share/skills/w-mem-curation/SKILL.md](share/skills/w-mem-curation/SKILL.md), and [share/skills/r-pipeline-protocol/SKILL.md](share/skills/r-pipeline-protocol/SKILL.md).
- VS Code diagnostics reported no errors in the same four files.

### Coverage
- Not applicable for a td:0 documentation task.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Not applicable. All AC lines are td:0 and the test-writer correctly skipped.

#### Security Review
- No security issues. This is documentation-only scope, and the latest binding builder retry is the one recorded at [task 1274](.owlbear/kanban/tasks/1274-p1-08-update-memory-skill-documentation.md#L318-L325).

#### Test Integrity
- Not applicable. No TestFromAC files or classes are in scope.

#### Test Quality
- Not applicable. No task tests were required for this td:0 task.

#### Data Safety
- No issues. Documentation-only change.

#### Implementation-Aware Gap Analysis
- PASS. The latest binding architecture refinement narrowed the remaining work to AC1 at [task 1274](.owlbear/kanban/tasks/1274-p1-08-update-memory-skill-documentation.md#L263-L311). The live docs now satisfy that refined contract: [share/skills/h-mcp-memory/SKILL.md](share/skills/h-mcp-memory/SKILL.md#L14-L22) documents all five tools in the summary; [share/skills/h-mcp-memory/SKILL.md](share/skills/h-mcp-memory/SKILL.md#L38-L56) documents `query_memory`; and the parameter rows at [share/skills/h-mcp-memory/SKILL.md](share/skills/h-mcp-memory/SKILL.md#L50-L54) match the live MCP signature at [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L97-L104).
- Access restrictions and return values are also documented for every tool in [share/skills/h-mcp-memory/SKILL.md](share/skills/h-mcp-memory/SKILL.md#L24-L109), matching the live entry-shape and role gates at [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L57), [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L173), [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L204), and [serve/mcp-memory/src/owlbear_mcp_memory/tools.py](serve/mcp-memory/src/owlbear_mcp_memory/tools.py#L218).

#### Necessity Check
- Not applicable. No dependency, integration, or external capability was added.

#### Builder Process Quality
- CLEAN. The task has earlier review sections at [task 1274](.owlbear/kanban/tasks/1274-p1-08-update-memory-skill-documentation.md#L139) and [task 1274](.owlbear/kanban/tasks/1274-p1-08-update-memory-skill-documentation.md#L198), but the later architecture rewrite at [task 1274](.owlbear/kanban/tasks/1274-p1-08-update-memory-skill-documentation.md#L263-L311) materially refined scope. Current review is anchored to that latest contract, and the current repo state satisfies it.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| h-mcp-memory documents all 5 tools with params, return values, and access restrictions | [share/skills/h-mcp-memory/SKILL.md](share/skills/h-mcp-memory/SKILL.md#L14-L22) lists all five tools; [share/skills/h-mcp-memory/SKILL.md](share/skills/h-mcp-memory/SKILL.md#L24-L109) provides per-tool params, return values, and access restrictions; `query_memory` specifically documents `states`, `categories`, `scope_agents`, `min_confidence`, and `limit` at [share/skills/h-mcp-memory/SKILL.md](share/skills/h-mcp-memory/SKILL.md#L50-L54), matching [serve/mcp-memory/src/owlbear_mcp_memory/server.py](serve/mcp-memory/src/owlbear_mcp_memory/server.py#L97-L104). | PASS |
| h-memory-structure documents the YAML frontmatter schema including an explicit enumeration of all 9 category values, the 4 states, and confidence range | [share/skills/h-memory-structure/SKILL.md](share/skills/h-memory-structure/SKILL.md#L13-L35) defines the entry shape; category/state/range enumerations are explicit at [share/skills/h-memory-structure/SKILL.md](share/skills/h-memory-structure/SKILL.md#L31), [share/skills/h-memory-structure/SKILL.md](share/skills/h-memory-structure/SKILL.md#L32), and [share/skills/h-memory-structure/SKILL.md](share/skills/h-memory-structure/SKILL.md#L33), matching [serve/mcp-memory/src/owlbear_mcp_memory/models.py](serve/mcp-memory/src/owlbear_mcp_memory/models.py#L11-L22) and [serve/mcp-memory/src/owlbear_mcp_memory/models.py](serve/mcp-memory/src/owlbear_mcp_memory/models.py#L33-L36). | PASS |
| w-mem-curation documents the explicit state machine and tool-triggered transitions | [share/skills/w-mem-curation/SKILL.md](share/skills/w-mem-curation/SKILL.md#L19-L31) contains the state machine table and the explicit approved-to-deleted purge-flow note. | PASS |
| r-pipeline-protocol Post-task Reflection references `store_learning` | [share/skills/r-pipeline-protocol/SKILL.md](share/skills/r-pipeline-protocol/SKILL.md#L229-L237) names `store_learning`, its parameters, and the updated category mapping. | PASS |
| No references to SQLite, old tool names, or old schema remain in updated skills | Targeted regex sweeps for `sqlite`, `add_learning`, `get_learnings`, `curate_learning`, `old schema`, and singular `scope_agent` returned no matches in the four scoped skill files. | PASS |
| All skill files pass markdown lint | Quality-runner retry reported clean markdown lint for the four scoped skill files, and editor diagnostics reported no errors. | PASS |

### Deductions
- -0.02: shared terminal contamination prevented direct `git show` extraction of commit `22f9c1ab`; changed-file scope was reconstructed from the latest builder note at [task 1274](.owlbear/kanban/tasks/1274-p1-08-update-memory-skill-documentation.md#L318-L325) plus current file inspection.
- Final confidence: 0.96

### Verdict
- PASS. Advance to docs.

### Action
- Released task to `docs`.
[[2026-05-03]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No IN-scope prose docs reference the changed skill files |
| 2 | Module docstrings | No | N/A | No Python source files modified (models.py/tools.py referenced for verification only, not changed) |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | Research doc | No | N/A | No research doc produced for this task |
| 5 | Diagram maintenance (describes match) | No | N/A | No diagram describes-match for SKILL.md files |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation requested |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| share/skills/h-memory-structure/SKILL.md | OUT | N/A — agent-executable SKILL.md |
| share/skills/h-mcp-memory/SKILL.md | OUT | N/A — agent-executable SKILL.md |
| share/skills/w-mem-curation/SKILL.md | OUT | N/A — agent-executable SKILL.md |
| share/skills/r-pipeline-protocol/SKILL.md | OUT | N/A — agent-executable SKILL.md |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None

No docs impact — all changed files are OUT-of-scope agent-executable SKILL.md files. Advancing to done.
[[2026-05-03]]
## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: h-mcp-memory documents all 5 tools with params, return values, access restrictions | Spot-checked: SKILL.md L14-22 (summary), L38-56 (query_memory with all 5 params). Matches live MCP surface at server.py:97-104. | PASS |
| AC2: h-memory-structure documents YAML schema, 9 categories, 4 states, confidence range | Reviewer evidence at h-memory-structure/SKILL.md L13-35. Trusted reviewer detail. | PASS |
| AC3: w-mem-curation documents explicit state machine | Spot-checked: SKILL.md L19-31 has transitions table with From/To/Trigger/Tool/Actor and purge-flow note. | PASS |
| AC4: r-pipeline-protocol references store_learning | Spot-checked: SKILL.md L229-237 references store_learning with params and category mapping. | PASS |
| AC5: No old references remain | Reviewer grep evidence (no sqlite/old tool names/stale scope_agent). Trusted. | PASS |
| AC6: All skill files pass markdown lint | Reviewer and quality-runner markdownlint exit 0 on all 4 scoped files. | PASS |

### Test Results

- pytest: 3827 passed, 128 failed, 4 skipped. All 128 failures are in unrelated modules (engine accessor migration, storage, cockpit events). Zero task-scope failures: task changed only SKILL.md documentation files.
- ruff: 1 violation in serve/knowledge/copilot_auth.py (T201 print). Not in task scope.

### Commit Verification

Three builder commits confirmed via git log:
- 22f9c1ab docs: complete query_memory params in memory skill (#1274, builder)
- 78448069 docs: fix scope_agents naming in memory structure skill (#1274, builder)
- 3c1e77fe docs: update memory skill docs (#1274, builder)

### Architect Quality: 4/5

AC was specific and verifiable. Minor gap: AC1 was initially marked satisfied but reviewer caught incomplete query_memory params, requiring a cycle 2 architecture refinement. The cycle 2 guidance was precise and well-targeted. Score docked from 5 for the initial false-positive on AC1.

### Deduction Breakdown

- Start: 1.00
- AC lines without evidence: 0 (all 6 verified)
- Lint violations in scope: 0
- AC quality <=3: N/A (score 4)
- Missing reviewer evidence: 0 (present, detailed, 0.96 confidence)
- Full-suite task-scope failures: 0

### Confidence: .98

### Action: archive