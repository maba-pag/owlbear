---
id: 741
title: Delete v1/ directory and v1-archive kanban tasks
status: in-progress
priority: important
created: '2026-04-10T04:29:46.8972445+02:00'
updated: '2026-04-10T06:59:32.996097+00:00'
tags:
- cleanup
- v1-analysis
parent: null
depends_on:
- 735
- 736
- 737
- 738
- 739
- 740
blocked: false
block_reason: null
claimed_by: rare-glen
claimed_at: '2026-04-10T06:59:32.996097+00:00'
class: standard
---

## Objective

Delete the v1/ directory and .owlbear/kanban/v1-archive/ after all v1-derived tasks are completed or triaged. The v1 feature inventory at .owlbear/research/v1-feature-inventory.md preserves all feature knowledge.

## Context

v1 was the PydanticAI-based standalone daemon architecture. v2 is the VS Code Copilot Chat + MCP architecture. A full feature analysis was performed (2026-04-10) cataloging 164 features across 18 domains. The report is at .owlbear/research/v1-feature-inventory.md. Two ideation briefs were created for larger ideas (.owlbear/briefs/draft-browser-knowledge-extraction/ and .owlbear/briefs/draft-voice-interaction-rethink/).

## What to delete

- v1/ — entire directory (v1 source code, tests, docs, .owlbear/, .venv/, etc.)
- .owlbear/kanban/v1-archive/ — 999 archived v1 kanban tasks

## What to keep

- .owlbear/research/v1-feature-inventory.md — the comprehensive feature catalog
- .owlbear/briefs/draft-browser-knowledge-extraction/ — ideation brief
- .owlbear/briefs/draft-voice-interaction-rethink/ — ideation brief
- Tasks #735-740 — v1-derived work items

## Acceptance Criteria

- [ ] v1/ directory deleted
- [ ] .owlbear/kanban/v1-archive/ deleted
- [ ] .owlbear/research/v1-feature-inventory.md still exists and is accessible
- [ ] Git commit with clear message about v1 removal
- [ ] No references to v1/ paths remain in active configuration files

[[2026-04-10]]
## Architecture Review

### Scope Refinement

**CRITICAL:** Do NOT delete `.owlbear/kanban/v1-archive/`. The kanban engine actively uses this directory — `_ARCHIVE_DIR_NAME = "v1-archive"` in `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py:37`. It contains 1016 archived tasks, 317 of which are v2-era (ID ≥ 700). Deleting it would destroy v2 archive history and break `list_tasks(archived=True)`. A separate task #744 handles renaming `v1-archive` → `archive`.

**Original AC2 overridden:** "`.owlbear/kanban/v1-archive/` deleted" → replaced by refined AC below.

### Refined Acceptance Criteria

- [ ] `v1/` directory deleted (`rm -rf v1/`)
- [ ] `.owlbear/research/v1-feature-inventory.md` still exists and accessible
- [ ] v1/ references removed from active config files:
  - `pyproject.toml`: lines 27 (`norecursedirs = ["v1"]`) and 39 (`exclude = ["v1/"]`)
  - `.gitignore`: lines 79-85 (v1 build artifacts section)
  - `.mega-linter.yml`: line 31 (`v1/` in FILTER_REGEX_EXCLUDE), lines 47-50 (ruff v1/ exclude)
  - `.vscode/settings.json`: lines 83 (`v1/.venv`), 138-139 (`v1/.venv`, `v1/**`)
  - `.cspell.json`: line 82 (`v1/**`)
  - `.github/copilot-instructions.md`: line 11 (remove `v1/` from dev branch contents)
- [ ] Do NOT touch `.owlbear/kanban/v1-archive/` — leave for #744
- [ ] Do NOT touch `.owlbear/sources/overview.md` v1 references — those are historical source tracking
- [ ] Git commit with message: `chore: delete v1/ directory and clean v1/ config references #741`

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Refined to v1/ directory deletion + config cleanup only |
| Interface clarity | PASS | Inputs/outputs clear: delete directory, edit config files |
| Dependency correctness | PASS | All 6 deps (#735-740) confirmed done |
| Module layering | N/A | No module changes |
| TDD compliance | N/A | type:config — no testable Python code |
| KISS/YAGNI | PASS | Minimal scope after refinement |
| Premise challenge | PASS | v1/ directory is dead code; deletion is warranted |
| Pattern consistency | PASS | Mirrors #740 cleanup pattern |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Cleanup/config domain only |

### Challenge Results
- Challenger: FALLBACK — no challenger agent available in current tool set
- Architect response: N/A — straightforward deletion task with no design decisions

### Non-impl tagging
Task requires `type:config` pass-through tag — no testable Python code produced.

### Verdict: APPROVE (refined scope)
### Action Taken: Refined AC to exclude v1-archive deletion (moved to #744). Narrowed to v1/ directory + config reference cleanup. Advanced to todo.
[[2026-04-10]]
## Test-Writer Notes
- Non-implementation task (tagged type:config) — no tests applicable.
- AC covers: `rm -rf v1/`, config file edits (pyproject.toml, .gitignore, .mega-linter.yml, .vscode/settings.json, .cspell.json, .github/copilot-instructions.md), and a git commit. No testable Python interfaces produced.
- Passing through to builder.