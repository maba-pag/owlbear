# Kanban Native — Context

## Project Type
Feature change to existing project (OwlBear).

## Tier
**Shared** — core infrastructure heading toward distribution; multi-consumer, replaces proven dependency.

## Problem Statement

OwlBear's task board depends on kanban-md, a Go binary (v0.33.0). This dependency blocks three trajectories:

1. **Distribution.** OwlBear is evolving from single-laptop tool to shareable system. A platform-specific Go binary requires per-OS download, setup scripts, and binary management — friction that undermines "clone = install."
2. **Feature ownership.** kanban-md has behaviors OwlBear doesn't need (classes, assignees, due dates) and lacks behaviors it does need (bulk tag operations, reliable claiming/release). Workarounds accumulate in the MCP server layer.
3. **GUI ambition.** A TypeScript GUI for board viewing/editing is desired. A native Python board engine with well-defined file I/O becomes a clean data layer that both MCP and a future GUI can consume directly — without an intermediary binary.

The prior research (March 2026, #144) recommended keeping kanban-md, but was calibrated for a single-operator scope. The ambition has since grown toward distribution and richer user-facing tooling.

### Scope of change
The kanban-md binary is consumed by:
- MCP server (serve/mcp-kanban) — primary consumer, 8 tools
- Orchestrator (serve/orchestrator/planner/board.py, cli.py) — board context injection
- Test fixtures (mock_acp_agent.py, dispatch integration)
- Setup scripts (.owlbear/kanban/setup.ps1)
A native engine replaces ALL of these seams.

### Prior Research
- Research #144 (2026-03-21) evaluated 4 alternatives and recommended "keep kanban-md with targeted augmentation" at .90 confidence.
- That research did NOT deeply evaluate cross-platform as a driving requirement.
- BearClaw board research (#905) also recommended staying on the kanban-md CLI seam.

### Critic Challenges (M1)
- Scope is broader than MCP server alone — orchestrator, tests, and setup scripts also depend on the binary.
- Cross-platform could potentially be solved by cross-compiling the Go binary (without rewriting).
- Unused features are already stripped at the MCP boundary.
- Bug evidence is concentrated in advanced edit_task path, not the dominant start_work/end_work lifecycle.
- Compatibility contract undefined: what happens to existing task files, config.yml, next_id, activity.jsonl?
- GUI ambition is orthogonal to the engine question.

## Outcomes

| # | Outcome | Success Indicator |
|---|---------|-------------------|
| O1 | **Native Python board engine** — a Python library (KanbanEngine) replaces ALL kanban-md subprocess calls across MCP server, orchestrator, tests, and setup. No binary needed. | `_run_kanban()` deleted; no subprocess calls to kanban-md anywhere; `uv sync` is the only setup step |
| O2 | **Behavioral compatibility** — same 8 MCP tools, same behavioral contract. Existing 700+ task files, config.yml, activity.jsonl, next_id handling all preserved. Existing tests pass. | All current MCP tool tests pass; existing board loads correctly; claiming/release/status-advance semantics unchanged |
| O4 | **Cross-platform** — runs on Mac (primary), Linux, Windows | CI or manual verification on Mac and Windows |

### Approach constraints
- **KISS.** Only replace the .exe — no new features. Can DROP unused kanban-md features (classes, assignees, due dates, estimates) if it saves work.
- **GUI deferred.** TypeScript GUI is a separate follow-up project; not in scope here.
- **Feature additions deferred.** Bulk tags, improved edit semantics — separate follow-up brief.

## Landscape Summary (M3)

### Engine surface to replicate
8 operations: config load, list (filtered), show, create, move, archive, edit (with claim/release/block), agent-name generation.

### File I/O scope
- **Read:** `config.yml` (statuses, priorities, defaults, next_id, claim_timeout), task files `tasks/<id>-<slug>.md` (YAML frontmatter + Markdown body)
- **Write:** task files (create/update), `activity.jsonl` (append-only log), `config.yml` (next_id increment)

### Call sites to migrate
| Consumer | Location | Current pattern |
|----------|----------|-----------------|
| MCP server | `serve/mcp-kanban/server.py` | `_run_kanban()` → async subprocess, 8 tools |
| Orchestrator board | `serve/orchestrator/planner/board.py` | `read_board()` → async subprocess, list --json |
| Orchestrator CLI | `serve/orchestrator/cli.py` | `subprocess.run()` → sync, list --json + status |
| Setup script | `.owlbear/kanban/setup.ps1` | Downloads kanban-md.exe binary |

### Droppable features (unused by OwlBear)
`class`, `assignee`, `due`, `estimate`, `completed` — OwlBear never sets or queries these.

### Critical behavioral contracts
- Status advancement via ordered status list from config
- Claim identity generation (random agent names)
- Claim retry on TASK_CLAIMED error in edit_task
- Release on end_work (all outcomes)
- Block/unblock with block_reason
- activity.jsonl logging (create, edit, claim, release, move, archive)
- next_id auto-increment on create
- claim_timeout enforcement
