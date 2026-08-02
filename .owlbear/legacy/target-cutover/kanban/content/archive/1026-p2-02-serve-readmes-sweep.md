---
id: 1026
title: 'P2-02: serve/* READMEs sweep'
status: archived
priority: medium
created: 2026-04-19 23:52:56.658285+00:00
updated: 2026-04-20 03:59:04.368927+00:00
tags:
- phase-2
- docs-currency
- docs-sweep
parent: 1016
depends_on:
- 1024
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1016

## Acceptance Criteria

- [ ] 7 missing READMEs authored: `serve/orchestrator/README.md`, `serve/kanban/README.md`, `serve/browser/README.md`, `serve/mcp-kanban/README.md`, `serve/mcp-knowledge/README.md`, `serve/mcp-memory/README.md`, `serve/mcp-browser/README.md`
- [ ] 2 existing READMEs verified/fixed: `serve/cockpit/README.md` (verify accuracy), `serve/knowledge/README.md` (stale install paths)
- [ ] Each README follows `r-doc-standards` package README structure
- [ ] Each README accurately describes: package purpose, API surface, configuration (env vars), entry points, dependencies
- [ ] Doc-index regenerated after changes

## Files

- Creates: 7 new `serve/*/README.md` files
- Modifies: `serve/cockpit/README.md`, `serve/knowledge/README.md`

## Notes

Each new README requires reading the actual package source to describe it accurately. Use `pyproject.toml` for entry points and deps. Pure documentation — no TDD pairing.
[[2026-04-20]]
## Architecture Review

### Refined Acceptance Criteria

The original AC understates the scope of the two existing READMEs and omits `serve/tools/`. Revised AC below supersedes the original:

- [ ] 8 missing READMEs authored: `serve/orchestrator/README.md`, `serve/kanban/README.md`, `serve/browser/README.md`, `serve/mcp-kanban/README.md`, `serve/mcp-knowledge/README.md`, `serve/mcp-memory/README.md`, `serve/mcp-browser/README.md`, `serve/tools/README.md`
- [ ] `serve/cockpit/README.md` restructured to STR-6/7/8 compliance: current 257-line file violates STR-6 (no parent README link), STR-7 (duplicates endpoint list, launch commands, and stack description from `copilot-instructions.md` §3/§4), STR-8 (non-standard heading structure). Cut duplicated content, add required headings, add parent link. Scope the cockpit README to the Python backend; the `web/` frontend is covered by `copilot-instructions.md` §3.
- [ ] `serve/knowledge/README.md` restructured to STR-6/7/8 compliance: stale `packages/knowledge` install paths (should be `serve/knowledge`), missing parent README link (STR-6), missing required headings for launch/usage and configuration (STR-8), 60+ line module tables likely violate STR-7 — cut to summary + link to source
- [ ] Each README follows `r-doc-standards` rules STR-6 (purpose, entry points, config, parent link), STR-7 (no duplication of copilot-instructions.md), STR-8 (headings: name/purpose, launch/usage, configuration, dependencies)
- [ ] Each README accurately describes: package purpose, API surface, configuration (env vars), entry points, dependencies — sourced from actual `pyproject.toml` and package source
- [ ] Doc-index regenerated after all README changes in a single pass

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: package README documentation sweep |
| Interface clarity | PASS | Refined AC specifies exact STR rules, explicit scope for cockpit/knowledge rewrites |
| Dependency correctness | WARN | `depends_on: [1024]` and `parent: 1016` reference tasks not found on board (archived or deleted). Task is self-contained — non-blocking but references are stale |
| Module layering | N/A | Pure documentation, no code |
| TDD compliance | PASS | Documentation-only task, no TDD pairing needed. Needs `type:docs` tag for test-writer pass-through |
| KISS/YAGNI | PASS | Straightforward template-follow for new READMEs, standards-compliance for existing |
| Premise challenge | PASS | Verified: 8 of 10 serve/ packages lack README; both existing READMEs have STR violations |
| Pattern consistency | PASS | STR-6/7/8 provide clear template; cockpit README provides reference (after cleanup) |
| Security surface | N/A | No security surface |
| Single domain | PASS | All documentation, single domain |

### Challenge Results
- Challenger: reconsider (confidence 0.50)
- Key concerns: (C1) cockpit README is a rewrite not verify, (C2) knowledge README also structural overhaul, (C3) type:docs tag needed, (C4) scope too large
- Architect response: ACCEPTED C1/C2/C3 — AC rewritten to reflect actual rewrite scope for both existing READMEs, added tools README. REBUTTED C4 — all 10 files are one doc type, one concern, one domain; splitting "new vs rewrite" adds pipeline overhead without proportional benefit. The doc-writer handles both additive and subtractive docs work.

### Tagging Note
Task needs `type:docs` tag for clean test-writer pass-through. `edit_task` unavailable in current session — downstream agents or orchestrator should add the tag. The test-writer Step 2a heuristic (AC references only .md files) provides fallback detection.

### Verdict: APPROVE (with refinements)
### Action Taken: Refined AC to reflect actual scope (8 new READMEs, 2 structural rewrites), referenced specific STR rules, noted stale dependency references. Advanced to todo.
[[2026-04-20]]
## Test-Writer Notes
- Non-impl pass-through: AC references only `.md` files (8 new READMEs + 2 restructures + doc-index regen).
- No testable Python interfaces — no implementation intent found in AC.
- Step 2a heuristic: all Files entries are `serve/*/README.md`. Task body confirms "Pure documentation — no TDD pairing."
- Passing through to builder.
[[2026-04-20]]
## Builder Notes

### Files changed
- Created: `serve/orchestrator/README.md`, `serve/kanban/README.md`, `serve/browser/README.md`, `serve/mcp-kanban/README.md`, `serve/mcp-knowledge/README.md`, `serve/mcp-memory/README.md`, `serve/mcp-browser/README.md`, `serve/tools/README.md` (8 new)
- Rewritten: `serve/cockpit/README.md` (257 → 90 lines; removed duplicate endpoint list, launch commands, stack description, and frontend docs; kept engine surface allowlist, work sessions model, audit trail; added parent link)
- Rewritten: `serve/knowledge/README.md` (stale `packages/knowledge` paths fixed, headings restructured per STR-8, module tables condensed to summary, parent link added)
- Updated: `.owlbear/doc-index.md` (single-pass regen via `uv run doc-index`)

### AC verification
- [x] 8 missing READMEs authored (all verified against actual pyproject.toml and source)
- [x] `serve/cockpit/README.md` restructured: STR-6 (parent link ✓), STR-7 (no duplicate from copilot-instructions.md ✓), STR-8 (headings in order ✓)
- [x] `serve/knowledge/README.md` restructured: stale install paths fixed, parent link added, STR-8 headings ✓
- [x] Each README: purpose paragraph ✓, entry points ✓, configuration ✓, parent README link ✓
- [x] Doc-index regenerated (`uv run doc-index` exit 0)

### Lint/test status
Pure documentation task — no Python test pairing. No ruff changes.

### Commit
`e6c36e91` — docs: author 8 new serve/* READMEs, rewrite cockpit and knowledge READMEs (#1026)
[[2026-04-20]]
## Review Evidence

### Test Results
- N/A — pure documentation task, no Python test pairing

### Lint
- N/A — no Python code changed

### Coverage
- N/A

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
- Skipped: no `TestFromAC_*` classes (documentation-only task, correct per test-writer pass-through)

#### Security Review
- No security surface. No code changes, no new dependencies, no executable output.

#### Test Integrity
- Skipped: no tests authored or modified

#### Test Quality
- Skipped: no tests in scope

#### Data Safety
- Skipped: no mutable state introduced

#### Implementation-Aware Gap Analysis
- Skipped: no implementation code

#### Necessity Check
- Skipped: no new dependencies added

#### Builder Process Quality
- Single `## Builder Notes` section, one clean attempt — CLEAN

---

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| 8 missing READMEs authored | All 8 files read and confirmed: `serve/orchestrator/README.md`, `serve/kanban/README.md`, `serve/browser/README.md`, `serve/mcp-kanban/README.md`, `serve/mcp-knowledge/README.md`, `serve/mcp-memory/README.md`, `serve/mcp-browser/README.md`, `serve/tools/README.md`. All appear in doc-index at lines 16934, 16958, 16968, 16978, 16988, 16999, 17008 | PASS |
| `serve/cockpit/README.md` restructured to STR-6/7/8 | 90-line file: purpose paragraph ✓, `## Launch / Usage` heading deferring to copilot-instructions.md per STR-7 ✓, `## Configuration` deferring to copilot-instructions.md ✓, parent link `→ Parent: [README.md](../../README.md)` ✓, STR-8 headings in order ✓ | PASS |
| `serve/knowledge/README.md` restructured to STR-6/7/8 | Stale `packages/knowledge` install path gone — now `serve/knowledge[<extra>]` ✓; parent link ✓; STR-8 headings in order ✓; module table condensed to 7-row summary ✓ | PASS |
| Each README follows STR-6/7/8 | All 10 READMEs verified: STR-6 (purpose, entry points/launch, config, parent link) ✓; STR-7 (no duplication of copilot-instructions.md — none of the new READMEs reproduce copilot-instructions content) ✓; STR-8 (required headings in order) ✓ | PASS |
| Each README accurately describes content sourced from pyproject.toml/source | Spot-checks: `KANBAN_TOOLS_EXCLUDE` confirmed in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:80`; orchestrator `kanban/` dir and `kanban/kanban-md` binary confirmed in `serve/orchestrator/src/owlbear/cli.py` (`_KANBAN_DIR`, `_KANBAN_BIN`); `gh` requirement confirmed from `_COPILOT_CMD = "gh"` | PASS |
| Doc-index regenerated after all changes in single pass | All 10 `serve/*/README.md` entries confirmed in `.owlbear/doc-index.md` (doc-index lines 424, 435, 16934, 16945, 16958, 16968, 16978, 16988, 16999, 17008) | PASS |

### Deductions
None.

### Verdict
PASS | confidence .97

All AC lines satisfied with specific file evidence. All 10 READMEs exist, are structurally compliant with STR-6/7/8, are accurate to source, and are indexed. No Pass 1 criteria triggered (documentation-only task). Builder process: clean single attempt.
[[2026-04-20]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pure documentation task — no behavior, API, or conventions changed; `copilot-instructions.md` content verified accurate (Cockpit Frontend §3, Cockpit Backend §4, Tools Package §5 entries untouched) |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | READMEs sourced from own `pyproject.toml` and package source; no external patterns used |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | No `.owlbear/research/1026*.md` exists — no research phase for this docs-sweep task |

### Files Updated
- None — all checklist items N/A

### Scratch Files Cleaned
- None — no `.owlbear/scratch/1026-*` files found

### Notes
- All 10 `serve/*/README.md` files confirmed present
- Review Evidence present and complete (PASS .97)
- Doc-index regenerated by builder in commit `e6c36e91`
[[2026-04-20]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 8 missing READMEs authored | All 8 files confirmed present (orchestrator 42L, kanban 68L, browser 48L, mcp-kanban 43L, mcp-knowledge 51L, mcp-memory 44L, mcp-browser 44L, tools 46L) | PASS |
| cockpit/README.md restructured STR-6/7/8 | 87 lines; parent link L5; no endpoint/stack duplication (references copilot-instructions.md §3/§4 instead); STR-8 headings present | PASS |
| knowledge/README.md restructured STR-6/7/8 | No stale `packages/knowledge` paths; parent link L5; STR-8 headings present; module tables condensed | PASS |
| Each README follows STR-6/7/8 | All 10 verified: parent link (L5 each), Launch/Usage heading, Configuration heading, Dependencies heading | PASS |
| Each README accurately describes content from pyproject.toml/source | Purpose paragraphs aligned with pyproject.toml descriptions across all 10 packages | PASS |
| Doc-index regenerated | All 10 serve/*/README.md entries confirmed in .owlbear/doc-index.md | PASS |

### Test Results
- pytest: 797 passed, 10 failed, 4 skipped — all 10 failures pre-existing from other tasks (#1033 pipeline diagram, #541 output schema, search_v2, phase_a_config); 0 failures in task scope
- ruff: clean, 0 violations

### Architect Quality: 4/5
Original AC understated scope ("verify/fix" for full rewrites). Architect caught and corrected: expanded to 8 new + tools README, rewrote cockpit/knowledge AC to reflect rewrite scope, referenced specific STR rules. Clean challenge acceptance. Minor upstream gap, well handled.

### Deduction Breakdown
- AC lines without evidence: 0 → no deduction
- Lint violations: 0 → no deduction
- AC quality ≤ 3: No (4/5) → no deduction
- Missing reviewer evidence: No (present, detailed, .97) → no deduction
- Full-suite failures in task scope: 0 → no deduction

### Confidence: .98
### Action: archive