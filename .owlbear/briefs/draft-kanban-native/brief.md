# Kanban Native Engine

## Investment Tier: Shared

## Problem

OwlBear's task board depends on kanban-md, a Go binary (v0.33.0) that blocks three trajectories:

1. **Distribution.** Platform-specific binary download undermines "clone = install." New users must run setup.ps1 to fetch a Windows/Mac/Linux artifact.
2. **Ownership.** Workarounds accumulate around kanban-md bugs (edit_task claiming, TASK_CLAIMED retry) and unused features (classes, assignees, due dates, estimates).
3. **Simplification.** Every board operation goes through subprocess → CLI flag assembly → JSON parse. The engine could be a direct Python library call.

Prior research (#144, March 2026) recommended keeping kanban-md, but was calibrated for single-operator scope. OwlBear's ambition has since grown toward distribution and richer tooling.

## Outcomes

1. **Native Python board engine** — a `KanbanEngine` module inside `serve/mcp-kanban/` replaces all kanban-md subprocess calls. `uv sync` is the only setup step. No binary artifact needed.
2. **Behavioral compatibility** — same 8 MCP tools with equivalent behavioral contracts. Existing 700+ task files, config.yml, activity.jsonl, and next_id handling preserved. One intentional change: session-stable claim identity (improvement over per-call name generation).
3. **Cross-platform** — runs on Mac (primary), Linux, and Windows without platform-specific artifacts.

## Approach

Build the native board engine as modules inside the existing `serve/mcp-kanban/` package. The `KanbanEngine` class replaces `_run_kanban()` subprocess calls. No separate package needed — only the MCP server consumes the engine.

**Dependencies:** pydantic (already present), ruamel.yaml (new), stdlib only.

### Architecture

```
VS Code agents → MCP server (serve/mcp-kanban) → KanbanEngine (internal module)
```

The MCP server is the sole consumer. The orchestrator CLI (`serve/orchestrator/`) is unused and out of scope — if it ever needs board data, it should use MCP.

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Engine placement | Inside `serve/mcp-kanban/` | Only one consumer (MCP server). Extract to separate package later if needed. |
| YAML library | ruamel.yaml (round-trip mode, `typ='rt'`) | Preserves field order, comments, quoting. Timestamp resolver disabled to prevent Go-nanosecond → Python-microsecond precision drift on round-trip. Adds one dependency (~160KB). |
| File locking | None (YAGNI) | Matches kanban-md behavior. Atomic writes via temp + `os.replace()`. Add locking if contention materializes. |
| Compound operations | In the engine | `start_work()` / `end_work()` are engine methods. MCP server is thin passthrough. |
| Claim identity | Session-stable | One agent-name generated per engine instance, reused for all claim/retry. Intentional improvement: kanban-md generates per-call, which breaks retry logic. |
| Unknown YAML fields | Preserved on round-trip | Engine doesn't model `class`, `assignee`, `due`, `estimate` but doesn't destroy them on read-write. |
| YAML safety | Safe loading only | No unsafe loaders, no `!!python/` tags. Path containment validated before every I/O. Slug allowlist enforced (`[a-z0-9-]`, max 80 chars). Windows reserved filenames rejected. |

### Migration Plan

| Phase | What | Risk Level |
|-------|------|-----------|
| 1. Engine modules | Build engine modules inside `serve/mcp-kanban/` with unit tests and 700-file round-trip test | High — correctness foundation |
| 2. MCP server migration | Replace `_run_kanban()` with engine API calls. Exercises hardest paths: compound ops, claiming, status advancement. | High — behavioral contract |
| 3. Cleanup sweep | Remove binary, setup.ps1, update docs/guides/fixtures/templates/skills that reference kanban-md | Low — mechanical but broad |

### Alternatives Considered
- **Cross-compile Go binary** — solves platform only, not ownership or simplification.
- **Keep kanban-md + augment** (prior research recommendation, .90 confidence) — no longer fits distribution ambition.

## Scope

**In:**
- `serve/mcp-kanban/src/owlbear_mcp_kanban/` — new engine modules (KanbanEngine class, Pydantic models, YAML I/O, activity logging)
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — replace `_run_kanban()` subprocess with engine API calls
- `serve/mcp-kanban/pyproject.toml` — add ruamel.yaml dependency
- `tests/` — migrate/update kanban-related tests
- `.owlbear/kanban/setup.ps1` — remove (binary no longer needed)
- `seed/.owlbear/kanban/setup.ps1` — remove from seed template
- `setup/setup-guide.md`, `setup/sharing-guide.md` — update instructions
- `.owlbear/kanban/README.md` — update board reference docs
- `share/skills/h-mcp-kanban/SKILL.md`, `share/skills/w-retro/SKILL.md` — update binary references

**Out:**
- New features (bulk tags, improved edit semantics) — follow-up brief
- TypeScript GUI — follow-up project
- File locking — add if contention materializes
- Board viewer CLI command — follow-up (known regression: `kanban-md board` console output goes away; MCP `list_tasks` still available)
- Orchestrator CLI migration — unused; if ever needed, should use MCP
- E2E smoke scripts / dispatch integration tests that directly use the binary — update only if they touch MCP server

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Behavioral drift from kanban-md | High | Golden snapshot parity tests: capture kanban-md output before deletion, compare against engine output |
| next_id duplication under concurrent creates | Medium | Atomic writes prevent file corruption; true ID collision requires concurrent creates (rare — agents don't create tasks in parallel). Accept risk; add locking if observed. |
| Claiming protocol fidelity | High | Dedicated claims test suite. Session-stable identity is an intentional improvement over per-call generation. Document the behavioral change. |
| activity.jsonl schema undocumented | Medium | Reverse-engineer action vocabulary and field shapes from live log before implementation. Validate with existing retro parser. |
| `kanban-md board` console output goes away | Low | `bearclaw status` and MCP `list_tasks` still available. Follow-up project for richer board viewing. |
| Broad seam count in cleanup | Low | Exhaustive seam inventory captured in this Brief (see Scope section). Mechanical but thorough. |

## Key Decisions

| ID | Decision | Trade-off |
|----|----------|-----------|
| D1 | ruamel.yaml for lossless round-trip | One extra dependency (~160KB) |
| D2 | No locking (YAGNI, match kanban-md) | Theoretical concurrent ID collision risk |
| D3 | Compound ops in engine | Larger engine surface, but centralized lifecycle logic |
| D4 | KISS — replace only, no new features | Defers improvements to follow-up brief |
| D5 | GUI deferred to separate project | Engine API is clean enough for future consumers |
| D6 | Engine inside mcp-kanban (not separate package) | Only one consumer; extract later if needed |
| D7 | Orchestrator CLI out of scope | Unused; should use MCP if ever needed |

## Implementation Details

### Task File Format (YAML frontmatter + Markdown body)

Location: `.owlbear/kanban/tasks/<id>-<slug>.md`

```yaml
---
id: <int>                            # from config.yml next_id
title: <string>
status: <enum>                       # research|backlog|todo|in-progress|review|docs|done
priority: <enum>                     # someday|nice-to-have|important|needed|critical
created: <ISO 8601 string>
updated: <ISO 8601 string>
tags: [<string>, ...]
parent: <int|null>
depends_on: [<int>, ...]
blocked: <bool>
block_reason: <string|null>
claimed_by: <string|null>
claimed_at: <ISO 8601 string|null>
# Preserved but not modeled by engine:
started: <ISO 8601 string|null>      # set by kanban-md on first move to in-progress
completed: <ISO 8601 string|null>    # set by kanban-md on archive
class: <string>                      # always "standard" in OwlBear
---

Markdown body (free-form, conventions include ## Objective, ## AC, ## Context, date-stamped notes)
```

- Slug frozen at creation; no file rename on title edit
- Frontmatter `id` is canonical identity (filename prefix is convenience)
- Duplicate frontmatter IDs are a hard error
- Unknown fields preserved on round-trip

### config.yml Schema

```yaml
version: <int>
board:
  name: <string>
tasks_dir: <string>                  # relative to kanban dir
statuses:
  - name: <string>                   # NB: list of dicts, not flat strings
  ...
priorities:
  - <string>
  ...
defaults:
  status: <string>
  priority: <string>
  class: <string>                    # preserved but not used by engine
claim_timeout: <duration string>     # e.g. "1h"
tui:                                 # preserved but not used by engine
  title_lines: <int>
  hide_empty_columns: <bool>
next_id: <int>                       # atomically incremented on create
```

### activity.jsonl Format

Append-only, one JSON object per line:
```json
{"timestamp":"<ISO 8601>","action":"<verb>","task_id":<int>,"detail":"<string>"}
```

Action vocabulary (from live log): `create`, `edit`, `move`, `claim`, `release`, `block`, `unblock`, `archive`

### KanbanEngine API Surface (preliminary)

```python
class KanbanEngine:
    def __init__(self, kanban_dir: Path): ...

    # Read operations
    def load_config(self) -> BoardConfig: ...
    def list_tasks(self, *, status=None, tag=None, priority=None, ...) -> list[TaskRecord]: ...
    def show_task(self, task_id: str) -> TaskRecord: ...

    # Write operations
    def create_task(self, title: str, *, body="", ...) -> TaskRecord: ...
    def move_task(self, task_id: str, status: str) -> TaskRecord: ...
    def edit_task(self, task_id: str, *, body=None, ...) -> TaskRecord: ...

    # Compound operations
    def start_work(self, task_id: str) -> TaskRecord: ...
    def end_work(self, task_id: str, note: str, outcome: str, ...) -> TaskRecord: ...

    # Identity
    @property
    def agent_name(self) -> str: ...  # generated once, reused
```

### Behavioral Contracts to Replicate

| Behavior | Current Implementation | Native Engine Must |
|----------|----------------------|-------------------|
| Status advancement | `end_work(success)` → index current status in config statuses → move to next. Last status → archive. | Same — read statuses from config, advance by index. |
| Claim | `start_work()` → blocked guard → generate name → `edit --claim <name>` | Same — check blocked → assign `claimed_by` + `claimed_at` |
| Release | `end_work(*)` → `--release` flag on edit | Same — clear `claimed_by` + `claimed_at` |
| Block | `end_work(block)` → `--block <reason>` | Same — set `blocked=true` + `block_reason` |
| Archive | `move_task("archived")` or last-status advancement | Move task file to archived location or mark status |
| Agent name | `agent-name` CLI subcommand → random adjective-noun | Generate from same word pool, session-stable |
| Timestamp | `--timestamp` on edit → prepend `[[YYYY-MM-DD]]` to appended body | Same — prepend date prefix to append_body |
| Lean list output | `list_tasks` strips body/created/updated/class/claimed_by → synthesizes `claimed: bool` | Same — MCP server still applies lean transform |

## Context

- Prior research: `.owlbear/research/kanban-replacement-options.md` — recommended keep kanban-md at .90 confidence; overridden by distribution ambition growth
- Voice deliberation: `.owlbear/briefs/draft-kanban-native/opinions/` — architect (.82), data (.82), security (.88) confidence
- Synthesis: `.owlbear/briefs/draft-kanban-native/synthesis.md` — .78 combined confidence
- Board config: `.owlbear/kanban/config.yml` — 7 statuses, 5 priorities, next_id=704, claim_timeout=1h
