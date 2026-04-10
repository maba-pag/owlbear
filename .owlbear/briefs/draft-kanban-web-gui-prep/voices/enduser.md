# End-User Voice — Kanban Engine Data Contract & API Usability

## User Experience Stance

The engine's public API should be shaped around what a human sees on a kanban board — not around agent dispatch mechanics. The restructuring must produce a board API that a GUI adapter can consume with minimal translation, where the engine owns the canonical task model, valid board states, and transition rules, and consumers project what they need at their own boundary.

Seven design requirements for a GUI-friendly engine API:

### 1. Engine returns full `TaskRecord`; projection belongs at boundaries

The engine must always return the canonical `TaskRecord` from every method. The MCP adapter projects lean dicts for LLM token economy. The GUI adapter passes through rich objects. This eliminates the current third ad-hoc representation (hand-built dicts in `list_tasks`) while preserving token efficiency for agents. The key principle: **one canonical model in the engine, consumer-specific projections at each boundary.**

### 2. Board metadata must be queryable

The GUI needs to render status columns in the right order and populate priority dropdowns with valid values. The engine should expose a `board_config()` method (or equivalent) returning:

- Valid statuses with display order (column sequence)
- Valid priorities with display order (dropdown sequence)

Without this, the GUI either hardcodes values (maintenance trap) or parses config files directly (coupling to storage format).

### 3. Status transitions should be discoverable

Currently `move_task()` accepts arbitrary status strings. A GUI needs to know which "Move to" options are meaningful from a given state. The engine should expose valid transitions — either as a method (`valid_transitions(status) → list[str]`) or as metadata on the board config. Even with ~7 statuses, 42 possible transitions without guidance forces the GUI to either show everything (overwhelming) or hardcode rules (drift risk).

### 4. Claim semantics invisible to GUI consumers

The GUI NEVER claims tasks. The engine's `claimed_by` field should appear as a read-only display indicator in the GUI boundary model ("Assigned: coder-agent"), not as an operational concept requiring understanding of claim/release flows. The GUI adapter should not expose `claim_task()` or `release_task()` at all. `release_task()` may be offered as an OPTIONAL admin action but claim mechanics are fundamentally agent infrastructure.

### 5. Board-level change signal via in-memory revision counter

15-second polling should not fetch the full task list every cycle. The board is individual YAML files — directory mtime only tracks add/remove, not per-file edits, so filesystem stat alone doesn't suffice without walking all files. Cheapest solution: a single `int` revision counter on the engine instance, incremented on every write. GUI adapter calls `revision()` → compares to last known → fetches full board only on mismatch. No persistence needed; loss on restart forces one full refresh (acceptable).

### 6. Agent-only methods clearly documented, not hidden

`start_work()` and `end_work()` encode agent-specific behavior (auto-claim, outcome routing, note requirements). The GUI should use `move_task()` and `edit_task()` directly. The board API module should document which methods are agent-oriented vs human-oriented even if both remain available on the engine. This is a documentation and discoverability concern, not an access-control one.

### 7. `get_board()` convenience method

A `get_board()` that returns tasks grouped by status column in display order saves every GUI consumer from reimplementing the same grouping. This is a domain operation (a board *is* columns), not a presentation concern. Five lines of code that eliminates repeated boilerplate in every adapter.

## Usability Reasoning

These seven points reduce cognitive load for a GUI adapter developer in three ways:

- **No shape ambiguity.** One canonical model eliminates the "which task shape did I get?" problem. Projection at boundaries is explicit and intentional.
- **No implicit knowledge.** Board metadata, valid transitions, and method semantics are queryable or documented — the adapter doesn't need to reverse-engineer the engine to build correct UI.
- **No wasted work.** Revision counter avoids unnecessary polling. `get_board()` avoids reimplementing grouping. Rich objects avoid fetching detail after listing.

## Key Trade-offs

| This approach costs | What it avoids |
|---|---|
| `board_config()` and `valid_transitions()` are new methods to implement and maintain | GUI hardcoding status/priority values and drifting from engine config |
| In-memory revision counter adds mutable state to a currently stateless-per-call engine | Full board fetch on every 15s poll cycle, or complex filesystem polling |
| `get_board()` adds a convenience method that duplicates achievable behavior | Every consumer reimplementing grouping-by-status logic |
| Documenting agent-vs-human method distinction | GUI developers calling `start_work()` when they meant `move_task()` |

## Warnings

1. **`end_work()` is deceptively named.** A GUI developer will assume it means "mark task done." It actually means "agent reporting outcome + routing" and requires parameters like `note` and `outcome`. If it stays in the public API, its name and docs must make the agent-specificity obvious.

2. **Priority and status as strings** invite typos and invalid values at the GUI boundary. The engine currently accepts arbitrary strings. With `board_config()` exposing valid values, the GUI adapter can validate before calling — but the engine should also reject invalid values with clear errors, not silently accept them.

3. **`edit_task()` parameter surface is large** (14 optional kwargs). For the GUI's SHOULD-tier operations (edit priority, blocked, block_reason, status), this is fine — they'll use 2-4 params per call. But the sprawling signature may intimidate adapter developers. Consider whether the docstring or board API facade can highlight the common GUI subset.

## Confidence

0.85 — Position refined through two Critic cycles. The core principles (canonical model, queryable metadata, boundary projection) are sound. Minor uncertainty on whether `valid_transitions()` is worth the maintenance cost vs. simpler documentation, and on the exact revision-counter implementation (engine instance vs. module-level). These are implementation details that won't change the architectural direction.
