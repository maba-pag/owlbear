## Retired Kanban decomposition

**Status:** Superseded by the native Delivery runtime. The names and API below describe the retired
implementation and are retained only as historical proposal context.

### Status quo

**Current state:**

- `engine.py` — 2,738 LOC (the god-class problem)
- `agent_view.py` — 1,221 LOC (also over limit)
- Everything else is ≤700 LOC

The engine.py has these logical domains visible from the method outline:

1. **Module-level helpers** (lines 117–427): `WorkSession`, validators, session collectors, utility functions
2. **Core engine init + config** (lines 428–582): `__init__`, properties, `refresh_config`
3. **Dependency projection** (lines 583–691): transitions, dep status computation
4. **Task CRUD** (lines 691–930): `list_tasks`, `show_task`
5. **Request lifecycle** (lines 930–1271): `create_request`, `get_request`, `list_requests`, `sweep_requests`, `resolve_request`
6. **Validation** (lines 1272–1399): body size, archival, status predicates
7. **Mutations** (lines 1400–2220): `create_task`, `edit_task`, `move_task`, `claim_task`, `release_task`, `start_work`, `end_work`
8. **Maintenance** (lines 2221–2465): `sweep`, `cleanup`, `repair_storage`
9. **Activity/Sessions** (lines 2465–2738): events, sessions, activity log

### Proposal

**Status quo:** `engine.py` is a 2,738 LOC single-class god-file. `agent_view.py` is 1,221 LOC. 16 other files are all ≤700 LOC.

**Problem:** At 2,738 LOC, `engine.py` violates the "split functions > 50 lines" and general readability principle. The `KanbanEngine` class has ~44 methods spanning 5+ distinct responsibility domains. Need to decide *how* to split without breaking the API.

**Options:**

- **(a) Mixin-based decomposition** — Split `KanbanEngine` into mixins (`RequestMixin`, `MutationMixin`, `SessionMixin`, etc.) that compose into the same class. Pro: Zero API change, callers still see one `KanbanEngine`; Con: Mixins are a known anti-pattern (implicit `self` coupling, IDE confusion); Risk: Harder to reason about method resolution order; Confidence: 0.5

- **(b) Domain-module extraction with delegation** — Extract request lifecycle, sessions/activity, and maintenance into standalone modules with free functions or small classes that the engine *delegates to*. Engine remains the facade but thins to ~800 LOC of orchestration. Pro: Each file is independently testable, clear boundaries, engine stays the single public entry; Con: Some methods need access to engine state (tasks_dir, config) — must be passed explicitly; Risk: Low — internal refactor, public API unchanged; Confidence: 0.85

- **(rec) (c) Responsibility-split modules** — Same as (b) but also split `agent_view.py` which is 1,221 LOC. Extract `pick_tasks` dispatch logic into `dispatch_picker.py` and keep `agent_view.py` as a thin orchestrator. Pro: Gets *both* over-limit files under 800; Con: Two packages touched; Risk: Low; Confidence: 0.8

**Recommendation:** Option (c). The natural seams are:

| New module | Source lines | Responsibility |
|---|---|---|
| `requests.py` | ~340 LOC | Request lifecycle (create, get, list, sweep, resolve) |
| `sessions.py` | ~270 LOC | Session derivation, activity log, compaction |
| `maintenance.py` | ~280 LOC | `sweep`, `cleanup`, `repair_storage` |
| `validators.py` | ~130 LOC | Body size, archival, status predicates, AC validation |
| `engine.py` (residual) | ~750 LOC | Core: init, config, deps, `list_tasks`, `show_task`, mutations (create/edit/move/claim/release/start/end) |

Mtations alone are 820 LOC (lines 1400–2220). That suggests one more split:

| New module | Source lines |
|---|---|
| `mutations.py` | ~820 LOC — `create_task`, `edit_task`, `move_task` |
| `work_cycle.py` | ~400 LOC — `claim_task`, `release_task`, `start_work`, `end_work` |
| `engine.py` (residual) | ~500 LOC — Init, config, deps, `list_tasks`, `show_task`, facade delegation |

And for `agent_view.py`:

| New module | Source lines |
|---|---|
| `dispatch_picker.py` | ~500 LOC — `pick_tasks` + bucket helpers |
| `agent_view.py` (residual) | ~720 LOC — `list_tasks`, `show_task`, `create_task`, `edit_task`, `move_task`, `start_work`, `end_work` |

**Expected outcome:** No file > 800 LOC. Public API (`from owlbear_kanban import KanbanEngine, AgentView`) unchanged. Internal modules use explicit parameter passing, not mixins.

## Memory

- allow searching for memory IDs in cockpit

## Code index — push detail into file headers, keep the index thin

### Status quo

`serve/tools` already generates navigation indexes (`uv run indexes` → `doc-index`, `py-index`,
`ts-index`), and `h-codebase-orientation` already tells agents to use them as wayfinders. Two
problems in practice:

- **The indexes are too long to read.** `.owlbear/py-index.md` is ~3,000 lines, `ts-index.md` ~1,100,
  `doc-index.md` ~1,100. An agent looking for one module pays to scan thousands of lines — the
  index costs nearly as much attention as searching the source it was meant to replace.
- **Nothing regenerates them.** They are not wired into any hook or CI step, so they drift silently.
  As of 2026-08-02 the newest `serve/` change was 2026-08-02 while `py-index.md` was last
  regenerated 2026-07-14.

### Proposal

Invert where the detail lives, the way a C/C++ header declares an interface next to the code it
belongs to:

- **Full detail moves into an auto-generated header block at the top of each source file** — roughly
  the first 20 lines: what the module is for, what it exports, what it depends on. An agent that
  opens the file gets the summary immediately, with zero index lookup.
- **The index file shrinks to a routing table** — one line per file: path plus a one-sentence
  purpose. Enough to pick the right file, nothing more.

Generation stays a script, not an agent, so it costs no tokens and cannot drift into opinion.
Regeneration should run as part of the linter pass so headers and index are always current.

**Open questions:**

- Is there an existing standard or tool for generated per-file header summaries worth adopting
  instead of hand-rolling one? Check before building.
- Header blocks are generated content inside human-edited files — needs a stable delimiter and a
  check that regeneration never eats hand-written content below it.
- Does the same treatment fit `doc-index`, or is that one already short enough to leave alone?

**Expected outcome:** An agent finds the right file from a short index, then gets that file's full
structure from its own first lines. No 1,000-line index reads, no stale indexes.
