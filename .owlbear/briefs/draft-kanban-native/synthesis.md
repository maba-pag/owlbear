# Synthesis — Kanban Native Engine

## Convergences

### Direction: Replace kanban-md with native Python engine
All three voices (Architect, Data Person, Security) fully support replacing the Go binary with a native Python `KanbanEngine` class. No voice questions whether this should be done. The Architect frames it structurally (eliminate subprocess, enable thin MCP wrapper), the Data Person frames it as data stewardship (controlled persistence layer), and Security frames it as a trust-boundary opportunity (treat all on-disk data as untrusted input in a distribution model).

### Placement: `serve/kanban-engine/` as a shared dependency
The Architect explicitly proposes this location with reasoning against alternatives (inside mcp-kanban or orchestrator would create inverted dependencies). Data Person and Security operate within this assumption without contesting it.

### Lossless YAML round-trip for unknown fields
All voices agree the engine must preserve fields it doesn't manage (class, assignee, due, estimate, future unknowns) through read-write cycles. The Architect specifies a full-fidelity persistence model. The Data Person details the mechanism (round-trip mode preserving field order, comments, quoting). Security requires `extra="allow"` or equivalent in Pydantic models. No voice suggests dropping unknown fields.

### Atomic file writes via temp + `os.replace()`
All three voices converge on the write strategy: write to a temp file in the same directory, then `os.replace()` for atomic rename. The Data Person details the crash model. Security specifies this as a requirement for all file mutations (task files, config.yml).

### Frontmatter `id` as canonical identity (not filename)
Data Person and Security agree explicitly. Data Person specifies two-tier lookup (fast path from filename, integrity scan from frontmatter). Security specifies preference for frontmatter `id` when filename disagrees.

### Duplicate frontmatter IDs are a hard error
Data Person and Security both specify this — engine MUST refuse to load until a human resolves the conflict.

### Slug frozen at creation; no file rename on title edit
Data Person states this explicitly. Security's slug validation rules are consistent with this approach.

### activity.jsonl format preservation
All voices emphasize preserving the existing on-disk format. Data Person provides the exact action vocabulary (`create`, `edit`, `move`, `claim`, `release`, `block`, `unblock`, `handoff`, `delete` — notably no `archive` action; archive logs as `move` to archived). The Architect warns the schema is undocumented and must be reverse-engineered from live data. Security addresses append locking.

### Session-stable claim identity
Data Person and Security both require the engine to generate one agent name per instance and reuse it for all claim operations within that session. The Architect's `generate_agent_name()` method on `KanbanEngine` is consistent with this. Security explicitly calls out that the current kanban-md per-call generation breaks retry logic.

### Config statuses as objects, not flat strings
Architect and Data Person both flag that statuses are `- name: research` shaped (list of dicts), not plain strings. Both warn that misparsing this breaks status advancement.

### Timestamps as strings in the API model
Data Person provides the strongest reasoning (Go nanosecond precision vs Python microsecond precision causes drift on round-trip). The Architect's `TaskRecord` model with injectable `now: datetime | None` is compatible. Security's schema specifies ISO timestamp strings.

### YAML safe loading is non-negotiable
Security marks this as CRITICAL and the single highest-impact vulnerability. Data Person requires "no arbitrary tag constructors." The Architect doesn't discuss it explicitly but specifies no unsafe dependencies. All voices are aligned that unsafe YAML loading is unacceptable.

### Path containment within the board directory
Security details this extensively (symlink resolution, Windows reserved names, slug allowlists). Data Person specifies that `tasks_dir` resolution must stay within the board root. No voice disagrees.

### Migration order: engine first, then MCP, then orchestrator, then cleanup
The Architect provides a five-step migration plan. Data Person and Security don't propose alternative orderings.

### Canonical `TaskRecord` model
Data Person defines the full field set. The Architect's API model aligns. Security's schema validation requirements are compatible with the same model.

---

## Disagreements

### 1. YAML library — PyYAML vs ruamel.yaml
- **Architect:** Explicitly names "pydantic + PyYAML + stdlib only" as the dependency set. Zero extras.
- **Data Person:** Explicitly selects `ruamel.yaml` with `YAML(typ='rt')` and `preserve_quotes=True`. Argues PyYAML loses formatting, field ordering, and comment preservation — making lossless round-trip impossible.
- **Security:** References both PyYAML (`yaml.safe_load()`) and ruamel.yaml without taking a firm position, but several security requirements (safe round-trip mode, alias limits) are easier to satisfy with ruamel.yaml.

**Nature of tension:** The Data Person's position that PyYAML *cannot* satisfy the lossless round-trip requirement (which all voices agree on) directly contradicts the Architect's dependency choice. If the Data Person is correct, the Architect's PyYAML selection would violate a convergence point.

### 2. Concurrency / locking strategy
- **Architect:** No file-level locking. Match kanban-md's existing behavior (one-shot processes, no locks). Add a board-level lockfile only if contention materializes — YAGNI.
- **Data Person:** Board-level write lock (`.board.lock` via `filelock`) for ALL mutations from day one. Readers do NOT acquire the lock. Detailed crash-model analysis justifies this.
- **Security:** Per-resource advisory locking rated HIGH priority. Config.yml gets exclusive lock for read-modify-write. activity.jsonl gets brief exclusive lock per append. References `portalocker` or manual `fcntl`/`msvcrt`.

**Nature of tension:** Three distinct positions ranging from no locking (Architect) to global write lock (Data Person) to granular per-resource locks (Security). The Architect argues YAGNI; Data Person and Security argue the multi-consumer reality (MCP server + orchestrator CLI) makes this a day-one requirement.

### 3. Additional dependencies beyond pydantic + stdlib
- **Architect:** pydantic + PyYAML + stdlib only. Explicitly "zero MCP, zero CLI framework, zero async requirements."
- **Data Person:** ruamel.yaml + filelock — two additional dependencies, both justified by specific technical requirements.
- **Security:** Mentions portalocker as an option for cross-platform locking.

**Nature of tension:** Cascading from Disagreements 1 and 2. If ruamel.yaml and file locking are accepted, the dependency set grows beyond the Architect's specification.

### 4. Compound operations (start_work / end_work) — engine or consumer?
- **Architect:** Explicitly places `start_work()` and `end_work()` as engine methods. Argues these are compound board lifecycle operations that belong where primitives live; MCP server becomes a thin passthrough.
- **Data Person:** Does not address placement of compound operations. Focuses on data-layer primitives.
- **Security:** Does not address placement.

**Nature of tension:** Only the Architect takes a position. This is uncontested rather than disagreed-upon, but it has significant architectural impact (engine surface area, testing complexity, consumer coupling).

### 5. YAML resource limits (billion-laughs protection)
- **Security:** Explicitly requires depth limits (e.g., 50 levels) and alias expansion caps to prevent resource exhaustion.
- **Architect:** Does not mention resource limits.
- **Data Person:** Does not mention resource limits (though disabling timestamp resolver is addressed).

**Nature of tension:** Security raises this as part of the CRITICAL YAML deserialization surface. The other voices don't address it — likely an omission rather than disagreement, but the implementation cost and complexity are non-zero.

### 6. Timestamp resolver disabling
- **Data Person:** Explicitly requires disabling `tag:yaml.org,2002:timestamp` from the YAML resolver to prevent automatic datetime parsing and precision drift.
- **Architect:** Does not mention this technique. Specifies timestamps as strings in the API model and injectable `now` parameter, but doesn't address the YAML-layer mechanism.
- **Security:** Specifies timestamps as ISO strings in the schema but doesn't address the YAML resolver behavior.

**Nature of tension:** The Data Person identifies a specific technical risk (7-digit Go nanoseconds silently truncated to 6-digit Python microseconds on round-trip). If this is real, it affects every task file on every write cycle. The mechanism (resolver disabling) is specific to ruamel.yaml, reinforcing Disagreement 1.

---

## Recommendation

**Build the native KanbanEngine in `serve/kanban-engine/` as a pure Python library with Pydantic models, lossless YAML round-trip, atomic file writes, session-stable claim identity, and frontmatter-as-truth task identity.**

The migration should follow the Architect's five-step plan: engine with test suite → dual-output parity snapshots → MCP server migration → orchestrator migration → cleanup sweep.

**Implementation specifics where voices converge (act on these):**
- `TaskRecord` Pydantic model with all timestamps as `str`
- Config statuses parsed as `list[dict]` (object shape, not flat strings)
- Slug frozen at creation, `[a-z0-9-]` allowlist, max 80 chars
- Duplicate frontmatter IDs are a hard error
- activity.jsonl preserves exact existing action vocabulary
- Agent name generated once per engine instance
- All file writes via temp + `os.replace()`
- Path containment validated with `Path.resolve()` before every I/O operation
- YAML safe loading only — no unsafe loaders, no `!!python/` tags
- Windows reserved filename rejection
- Error messages use relative paths only

**Open tensions flagged in the recommendation:**

| Tension | Impact on implementation | Voices |
|---------|------------------------|--------|
| YAML library choice | Determines whether lossless round-trip is achievable; cascading dep impact | Architect (PyYAML) vs Data Person (ruamel.yaml) |
| Locking strategy | Determines concurrency safety for multi-consumer use | Architect (none/YAGNI) vs Data Person (board lock) vs Security (per-resource) |
| start_work/end_work placement | Determines engine surface area and MCP server complexity | Architect (in engine) — uncontested but consequential |

**Confidence: 0.78**

Strong alignment on direction, data contracts, and security baseline. The three open tensions (YAML library, locking, compound operation placement) are implementation-shaping decisions that will cascade through the task decomposition. They need resolution before detailed task planning.

---

## Open Questions

1. **PyYAML or ruamel.yaml?** The Data Person argues PyYAML cannot satisfy the lossless round-trip requirement that all voices agree on (field order, unknown field preservation, comment survival). The Architect names PyYAML explicitly. This must be resolved first — it affects the dependency set, timestamp handling approach, and round-trip fidelity guarantees. *(Data Person vs Architect)*

2. **Locking from day one or YAGNI?** The Architect says match kanban-md (no locking) and add only if contention appears. The Data Person says multi-consumer reality (MCP + orchestrator) demands a board-level write lock immediately. Security rates locking as HIGH priority with per-resource granularity. The user must decide whether locking is a day-one requirement or a follow-up. *(Architect vs Data Person vs Security)*

3. **If locking: board-level or per-resource?** If locking is accepted, the Data Person proposes a single `.board.lock` for all mutations (simpler, coarser), while Security proposes per-resource locks on config.yml and activity.jsonl (finer-grained, more complex). *(Data Person vs Security)*

4. **Should start_work / end_work be engine methods?** The Architect argues these compound operations belong in the engine, making the MCP server a thin passthrough. No voice opposes this, but it increases engine surface area and couples board lifecycle semantics into the library. The user should confirm this placement before task decomposition. *(Architect — uncontested)*

5. **YAML resource limits (billion-laughs)?** Security requires depth and alias limits. Is this in scope for the initial build or a hardening follow-up? The threat model (cloned repos as attack surface) suggests it matters, but the implementation cost depends on the chosen YAML library. *(Security — uncontested)*
