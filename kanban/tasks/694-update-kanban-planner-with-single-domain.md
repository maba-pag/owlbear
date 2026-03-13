---
id: 694
title: Update kanban-planner with single-domain decomposition gate
status: archived
priority: needed
created: 2026-03-08T17:11:34.1980337+01:00
updated: 2026-03-09T11:22:39.4941579+01:00
started: 2026-03-08T18:32:47.987623+01:00
completed: 2026-03-09T11:22:39.4941579+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
class: standard
---

## Context

Add single-domain decomposition gate to kanban-planner.agent.md. The domain list must
align with OwlBear's architecture layers (see architecture.instructions.md), not generic
web-app categories. See docs/research/task-decomposition-rules.md for background.

## Changes Required

In kanban-planner.agent.md:

- critical_rules: add "Single domain per task" rule with domain table (11 domains)
- step 3: add domain classification check — each task targets exactly one domain; multi-domain → split
- step 5: tasks tagged with `scope:{domain}` (aligns with existing tag taxonomy)
- bad_example: multi-domain task being flagged
- good_example: properly domain-scoped tasks from a multi-domain feature

## Acceptance Criteria

- [ ] critical_rules: "Single domain per task" rule with enumerated domain table (11 domains)
- [ ] Domain table maps each domain to its module path scope
- [ ] Domains: config, memory, core, tools, channels, bootstrap, providers, cli, agent-config, test-infra, docs
- [ ] Step 3: domain classification check — each task targets exactly one domain; multi-domain → split
- [ ] Step 5: tasks tagged with `scope:{domain}` (aligns with existing tag taxonomy)
- [ ] Edge case note: ancillary config.py field addition is NOT a domain violation (domain = primary concern)
- [ ] bad_example: multi-domain task (e.g., "Implement tool and add CLI command") being flagged for splitting
- [ ] good_example: properly domain-scoped tasks from a multi-domain feature

## Architecture Review

### AC Assessment

| Original AC | Assessment | Action |
|-------------|-----------|--------|
| "backend logic, frontend UI, database schema" domain list | Wrong — generic web-app categories; "backend" meaningless for 8-layer Python agent system; "frontend" doesn't exist; "database" is impl detail of memory/ | Rewrite — align with architecture.instructions.md |
| "step 3 checks domain as part of decomposition" | Correct intent, needs specificity | Refine — state what the check IS |
| "examples show domain-aware decomposition" | Good, needs positive + negative examples | Keep with more specificity |

### Domain List Rationale

Original 7 domains (backend, frontend, database, cli, config, test-infra, docs) fail because:

1. **"backend" covers 8+ distinct layers** — core/, tools/, memory/, channels/, providers/, safety/, bootstrap/, projects/. Tasks touching core/hooks.py and tools/web_search.py are both "backend" but cross architecture boundaries.
2. **"frontend" doesn't exist** — no ui/ directory, no .tsx files. YAGNI.
3. **"database" is an implementation detail** — SQLite is internal to memory/knowledge/.
4. **"docs" conflates documentation with agent configuration** — changing architect.agent.md and writing README.md are different concerns.

Refined 11-domain list aligned with architecture.instructions.md module layering:

| Domain | Module scope | Examples |
|--------|-------------|----------|
| config | `config.py` | Add pydantic-settings field |
| memory | `memory/` | Knowledge graph, sessions, WIP, embeddings |
| core | `core/`, `safety/` | Hooks, errors, retry, guards, delegation |
| tools | `tools/`, `projects/`, `planning/` | Toolset implementations |
| channels | `channels/` | Slack, CLI channel, messaging protocol |
| bootstrap | `bootstrap/`, `daemon.py`, `heartbeat.py` | Assembly + runtime wiring |
| providers | `providers/`, `auth/` | LLM integration + OAuth |
| cli | `bearclaw/` | Typer CLI commands |
| agent-config | `.github/agents,skills,instructions,prompts/`, `src/owlbear/agents/` | Agent customization files |
| test-infra | Shared conftest, fixtures, factories | NOT individual test files (those pair with impl) |
| docs | `docs/`, `README.md`, `SECURITY.md` | Documentation and research |

### Architecture Notes

- Module layering from architecture.instructions.md is the authoritative decomposition — domains MUST align with it
- Edge case: adding a config.py field as part of a core feature is NOT a domain violation. Domain = where the primary logic change lives.
- Self-contained packages (projects/, planning/, skills/, voice/) classified by their primary interface layer
- `scope:{domain}` tag convention already exists in tag taxonomy — formalizing, not inventing
- #695 (architect gate) references "the canonical domain list from kanban-planner" — this task is its prerequisite

### Dependencies Verified

- No depends_on listed — correct, no blockers
- #695 depends on this task's domain list — verified
- TDD pairing: NOT REQUIRED — agent-config domain task (file edit, no Python code)

[[2026-03-08]] Sun 18:20
## Builder Notes
- Files changed: .github/agents/kanban-planner.agent.md
- Edits: domain rule + table in critical_rules, domain check in step 3, scope tag in step 5, multi-domain bad_example + good_example, red flag for domain violations, edge case note
- No tests (agent-config file, not Python code)
- Lint: N/A (markdown)

[[2026-03-08]] Sun 18:28
## Review Evidence
### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| critical_rules: Single domain rule + 11-domain table | Lines 39-54: rule text + table with 11 rows | PASS |
| Domain table maps domain to module path scope | Lines 41-53: two-column table (Domain, Module path scope) | PASS |
| All 11 domains present | config, memory, core, tools, channels, bootstrap, providers, cli, agent-config, test-infra, docs verified lines 42-53 | PASS |
| Step 3: domain classification check | Line 89: Domain scoping bullet with classify + split instruction | PASS |
| Step 5: scope:{domain} tagging | Line 115: Tags always include scope:{domain} from domain table | PASS |
| Edge case: config.py ancillary addition | Line 56: Edge case note present, domain = primary concern | PASS |
| bad_example: multi-domain flagged | Lines 213-219: web_read tool + CLI command split into two tasks | PASS |
| good_example: domain-scoped decomposition | Lines 228-236: diagram generation across tools/cli/docs | PASS |

### Test Quality
N/A -- agent config markdown file, no Python code or tests.

### Security: No issues (markdown config file, no executable code)
### Verdict: PASS confidence .95

[[2026-03-08]] Sun 18:32
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | No behavior change; scope:domain tags already in Tag taxonomy |
| 2 | Docstrings | No | N/A | No Python code modified |
| 3 | sources.md | Yes | Pass | 4 attribution rows present (ChatDev, MetaGPT, OpenHands, Fowler DDD) |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | docs/research/task-decomposition-rules.md exists, linked in task Context |
| 6 | No impact | -- | -- | Items 3+5 apply, evaluated above |

### Files Updated
- None

### Scratch Files Cleaned
- None (no 694-* files in docs/scratch/)

[[2026-03-09]] Mon 04:57
Wave 4, agent: auditor

[[2026-03-09]] Mon 11:22
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| critical_rules: Single domain rule + 11-domain table | kanban-planner.agent.md L40-55: rule text + 11-row table | PASS |
| Domain table maps domain to module path scope | kanban-planner.agent.md L41-53: two columns (Domain, Module path scope) | PASS |
| All 11 domains present (config..docs) | All 11 verified in table rows L42-52 | PASS |
| Step 3: domain classification check | task-decomposition/SKILL.md L28: domain scoping bullet present | PASS |
| Step 5: scope:{domain} tagging | task-decomposition/SKILL.md L52: Tags always include scope:{domain} | PASS |
| Edge case: config.py ancillary addition | kanban-planner.agent.md L55: Edge case note present | PASS |
| bad_example: multi-domain flagged | kanban-planner.agent.md L155-163: web_read+CLI split | PASS |
| good_example: domain-scoped decomposition | kanban-planner.agent.md L177-188: diagram feature 3-domain split | PASS |

### Test Results
- pytest: 1271 passed, 20 skipped (no regressions; task is agent-config markdown, no Python code)
- ruff: 3 pre-existing errors (screenshot.py E501, test_bootstrap_structure.py I001 x2)  unrelated to #694

### Confidence: .97
### Action: archive
