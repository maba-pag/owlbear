---
id: 1274
title: 'P1-08: Update memory skill documentation'
status: backlog
priority: important
created: 2026-05-02T03:43:38.563184+00:00
updated: 2026-05-03T16:22:55.637716+00:00
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