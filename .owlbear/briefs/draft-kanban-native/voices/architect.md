# Architect — Kanban Native Engine

## Architectural Stance

Replace the kanban-md Go binary with a native Python board engine in a new standalone package `serve/kanban-engine/`. The engine is a pure Python library (pydantic + PyYAML + stdlib only) exposing a synchronous `KanbanEngine` class. The MCP server becomes a thin wrapper mapping MCP tools to engine methods. The orchestrator calls the engine directly. No subprocess, no binary, no platform-specific setup.

## Structural Reasoning

### 1. Placement: `serve/kanban-engine/`

The engine is a **shared dependency** consumed by both mcp-kanban and orchestrator. It must live outside either consumer to avoid inverted dependencies. The alternatives and why they're rejected:

- **Inside mcp-kanban:** Orchestrator would import from an MCP server package — inverted dependency, wrong abstraction layer.
- **Inside orchestrator:** MCP server would import from a dispatch system — same inversion problem.
- **Top-level share/ or v1/:** These directories serve different purposes (agent definitions, legacy code).

A new `serve/` package follows the existing isolated-package convention. Yes, this incurs repo plumbing cost (pyproject.toml source lists, Ruff paths, coverage config, package-count test assertions). This cost is mechanical, enumerable, one-time.

**Dependencies:** pydantic, PyYAML, standard library. Zero MCP, zero CLI framework, zero async requirements.

### 2. API Surface: `KanbanEngine` class

```
KanbanEngine(kanban_dir: Path)
```

**Constructor:**
- Loads immutable config from config.yml: statuses (list of name-objects), priorities, board name, claim_timeout.
- Does NOT cache mutable config. `next_id` is read fresh from config.yml on each `create()` call and written back atomically, preserving all other config fields.

**9 synchronous methods:**

| Method | Maps to | Compound? |
|--------|---------|-----------|
| `list_tasks(...)` | kanban-md list | No |
| `show_task(id)` | kanban-md show | No |
| `create_task(...)` | kanban-md create | No |
| `move_task(id, status)` | kanban-md move | No |
| `archive_task(id)` | kanban-md archive | No |
| `edit_task(...)` | kanban-md edit | No* |
| `start_work(id)` | MCP start_work tool | Yes |
| `end_work(id, ...)` | MCP end_work tool | Yes |
| `generate_agent_name()` | kanban-md agent-name | No |

*`edit_task` includes internal claim retry: if edit fails with TaskClaimed and the claimer matches the provided agent_name, retry with claim override. This is board semantics (the engine understands claims), not consumer policy.

**Why start_work and end_work belong in the engine:**
These are compound board lifecycle operations — they compose board primitives (show, edit-with-claim, status-advance, release, archive). They currently live in the MCP server only because the subprocess wrapper was there. With a native engine, the MCP server becomes a thin passthrough, and the compound board logic lives where it structurally belongs.

**What stays ABOVE the engine (consumer layer):**
- `pick_tasks`: dispatch policy (listing + gate evaluation + priority sorting + agent routing). These are orchestration concerns.
- MCP tool annotations, output schemas, structuredContent, tool exclusion.
- CLI argument parsing.

**Two model layers:**
- **Persistence model** (engine-internal): full-fidelity representation of on-disk task files. ALL fields preserved: id, title, status, priority, created, updated, started, completed, tags, depends_on, claimed_by, claimed_at, class, body, file, parent, blocked, block_reason. Unknown/future fields preserved on write-back.
- **API model** (engine return type): rich model exposing all fields. Consumers project at their boundary (MCP strips fields from list output, orchestrator selects what it needs).

**Domain exceptions:**
- `TaskNotFound` — task ID doesn't exist
- `TaskClaimed` — task claimed by another agent
- `InvalidStatus` — status not in config
- `TaskBlocked` — task has active block

**Injectable parameters for deterministic testing:**
- `agent_name: str | None = None` — override random agent name
- `now: datetime | None = None` — override timestamp

**File I/O contracts:**
- **Task files:** YAML frontmatter (all fields, lossless round-trip) + Markdown body. Read all fields including unused ones (class, assignee, due, estimate). Write preserves field order and unknown fields.
- **config.yml:** Lossless round-trip. Statuses are objects (`- name: research`), not flat strings. Only next_id is mutated; all other fields (version, board metadata, tui settings, defaults.class) preserved exactly.
- **activity.jsonl:** Append-only. Entry schema matches kanban-md's exact output format (field names derived from live data, e.g., `detail` not `details`).

### 3. Migration Structure

**Engine-first, consumer-by-risk, five steps:**

1. **Build engine package** with full test suite. This is where risk concentrates.
   - Unit tests: method-level, fixture-based, all boundary cases.
   - Round-trip: parse all 700+ existing task files (assert no errors); write-back fidelity on representative subset.
   - Config fidelity: parse → modify next_id → write back → verify all other fields preserved.

2. **Dual-output parity** (before touching any consumer). Run kanban-md binary and native engine on identical board state for representative operations. Capture binary output as golden snapshots. These snapshots become the regression baseline that persists after binary deletion.

3. **Migrate MCP server** first. This exercises ALL code paths including the hardest ones (create, edit, claim/release, start_work, end_work, archive). If the engine has compatibility gaps, the MCP server surfaces them immediately. The MCP server is rewired (subprocess → engine calls), not rewritten — tool annotations, output schemas, structuredContent, tool exclusion all stay.

4. **Migrate orchestrator** second. board.py becomes `engine.list_tasks()`. cli.py status command maps engine output to counts. Straightforward after engine is proven.

5. **Cleanup sweep:**
   - Delete: kanban-md binary, `.owlbear/kanban/setup.ps1`.
   - Update: seed content, `README.md`, `setup-guide.md`, `sharing-guide.md`, `.owlbear/kanban/README.md`, MCP handbook (`h-mcp-kanban`), `e2e_smoke.py`.
   - Update repo plumbing: root `pyproject.toml` (sources, Ruff, coverage), package-count test assertions.
   - Rewrite affected tests — see testing strategy below.

### 4. Concurrency

Match existing behavior. No file-level locking. kanban-md has none either — it's invoked as one-shot processes. The engine preserves the same concurrency profile: synchronous read → modify → write cycles, with application-level claim retry for optimistic conflict resolution. If contention appears under real multi-consumer load, add a board-level lockfile — but YAGNI for now.

### 5. Testing Strategy

**Test migration taxonomy:**

| Category | Action | Examples |
|----------|--------|---------|
| **Board behavior** | SURVIVE — rewrite to test engine directly | Task creation fields, status advancement, claim/release, filter semantics |
| **On-disk mutation** | SURVIVE — rewrite fixtures from binary-backed to engine-backed | dispatch integration (post-dispatch body mutation), e2e dispatch (resulting board state) |
| **MCP protocol** | SURVIVE — rewrite backend from mock subprocess to engine instance | Tool exclusion, output schemas, structuredContent, tool annotations |
| **Planner/board-reader** | SURVIVE — replace subprocess + JSON parse with engine call | board.py read_board, planner model assertions (claimed_by, class, body, file fields) |
| **Subprocess mechanics** | DIE — implementation detail no longer exists | Binary discovery (KANBAN_BIN), subprocess call-count assertions, mock stdout/stderr parsing |

**New test layers:**
- Engine unit tests (method-level, deterministic via injected agent_name/now).
- Round-trip parsing (700+ files).
- Golden parity snapshots (captured from binary before deletion).

## Key Trade-offs

| Cost | Benefit |
|------|---------|
| Re-implement kanban-md's file I/O (YAML frontmatter parsing, config handling, activity logging) | Eliminate binary dependency; clone = install; pure Python stack |
| New workspace package (repo plumbing ceremony) | Clean dependency direction; no coupling between consumers |
| Test suite rewrite for ~20 binary-specific tests | Direct engine testing; faster test execution (no subprocess overhead) |
| Absorb compound operations (start_work/end_work) into engine | Thin MCP server; eliminates biggest source of server complexity |
| Lossless round-trip commitment for all frontmatter fields | 700+ existing files work without migration; unused fields preserved |

## Warnings

1. **activity.jsonl schema is undocumented.** The entry format must be reverse-engineered from live data, not invented. Get this wrong and the retro workflow (w-retro) breaks silently.
2. **Config statuses are objects, not strings.** `- name: research`, not `- research`. Engine config parser must handle this shape; misparse breaks status advancement.
3. **Claim retry in edit is subtle.** The current MCP server retries when error contains "TASK_CLAIMED" and agent name matches. The engine must replicate this exact semantic, including the single-retry limit.
4. **Test rewrite scope is larger than it appears.** Dispatch integration tests, e2e tests, and planner board-reader tests all depend on binary-backed fixtures. Budget for this.
5. **Golden snapshots have non-deterministic elements.** Agent names and timestamps vary per run. Snapshot parity tests must normalize or inject deterministic values.

## Confidence

0.82
