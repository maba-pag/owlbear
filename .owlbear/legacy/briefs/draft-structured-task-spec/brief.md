# Brief — Structured Task Specification in Frontmatter

## Problem & Driver

Two stable specification fields — Acceptance Criteria (AC) and Proof Bundle — live as freeform markdown in task bodies, mixed with volatile operational content (work logs, agent notes, `end_work` output). Neither is machine-queryable. Both get buried as the body grows.

**Driver:** Structural cleanliness. Specification defines what the task should accomplish and how thoroughly it should be verified. It belongs in structured frontmatter, not in the volatile body. The body becomes operational notes only.

**Project type:** existing-feature/refactor. Modifies `serve/kanban/` (models, storage, engine), `serve/mcp-kanban/` (MCP tools), and pipeline agent skills.

## Scope

**In scope:**

- `ac` and `proof_bundle` as first-class Task frontmatter fields
- Model changes across Task, TaskSummary, TaskFull, DispatchEntry
- Engine changes: create_task, edit_task (dual AC mutation + proof_bundle), search extension
- MCP tool changes: create_task, edit_task, show_task parameter additions
- Pipeline skill updates: read AC + proof_bundle from frontmatter instead of body
- Recommended first-run migration script for proof_bundle
- Engine-level defense-in-depth guardrails (AC max items/length)

**Out of scope:**

- Cockpit UI rendering (AC checklist, proof_bundle badge) — follow-up task
- AC status tracking (met/unmet per criterion) — separate feature
- AC templates or naming convention enforcement
- Changes to the proof_bundle taxonomy itself

## Field Design — AC

**Field:** `ac: list[str] = Field(default_factory=list)`

**Semantics:** Ordered list of named acceptance criteria strings. Each string is a single criterion. Ordering is semantically meaningful (list, not set). Naming convention (e.g., `AC1:` prefix, semantic names) is organic — not enforced by schema.

**Example:**

```yaml
ac:
  - "AC1: Each AC is a named string in frontmatter"
  - "AC2: show_task returns ac field in response"
  - "AC3: edit_task supports add_ac / remove_ac"
```

**Mutation API:**

- **Full replacement:** `ac=["new", "list"]` — replaces the entire list
- **Atomic ops:** `add_ac=["new item"]` / `remove_ac=["exact string"]` — append to end / remove by exact match
- Full replacement and atomic ops are **mutually exclusive per call** (following the `body`/`append_body` precedent)
- Uniqueness enforced at engine write path (duplicate add is rejected with actionable error listing existing items)

**Model placement:**

| Model | `ac` |
|-------|------|
| Task | yes |
| TaskSummary | no |
| TaskFull | yes |
| DispatchEntry | no |

**Search:** Engine search must include frontmatter AC items so AC text remains discoverable after leaving the body.

**Guardrails:** Max 20 items, max 500 chars per item. Engine-level, prevents accidental bloat.

## Field Design — Proof Bundle

**Field:** `proof_bundle: str | None = None`

**Semantics:** Single-axis complexity/testing taxonomy. Determines test-writing scope, challenger involvement, and reviewer depth. Values from `r-pipeline-protocol`:

| Base | Test-writer | Challenger | Code-reader |
|------|------------|------------|-------------|
| `skip` | SKIP | skip | skip |
| `existing` | SKIP | skip | skip |
| `smoke` | smoke tests | skip | skip |
| `behavioral` | full TDD | yes | skip |
| `critical` | full TDD | yes | yes |

Modifiers: `+challenge`, `+reader` (escalation only). Combined format: `behavioral+challenge`.

**Validation (hybrid):**

- **Model:** Normalizing `@field_validator` — lowercase, sort modifiers alphabetically. No membership check on read. Garbage strings survive deserialization in normalized form.
- **Engine:** Membership check against hardcoded `frozenset` of all valid combinations in `create_task`/`edit_task`. Invalid values rejected with actionable error.
- **Frozenset composition:** Enumerate from `r-pipeline-protocol` taxonomy (bases × modifier subsets).

**Default:** `None` (no proof strategy specified). No silent default to `behavioral` — explicit over implicit.

**Model placement:**

| Model | `proof_bundle` |
|-------|----------------|
| Task | yes |
| TaskSummary | yes |
| TaskFull | yes (inherited) |
| DispatchEntry | yes |

## Model Changes

**`Task` (models.py):**

- Add `ac: list[str] = Field(default_factory=list)`
- Add `proof_bundle: str | None = None`
- Add normalizing `@field_validator` for `proof_bundle` (lowercase, sort modifiers)

**`TaskSummary` (models.py):**

- Add `proof_bundle: str | None = None` (cheap single string, useful for board views)
- Do NOT add `ac`

**`TaskFull` (models.py):**

- Add `ac: list[str] = Field(default_factory=list)`
- `proof_bundle` inherited from `TaskSummary`

**`DispatchEntry` (if applicable):**

- Add `proof_bundle: str | None = None`
- Do NOT add `ac`

## Storage & Engine Changes

**Storage (`storage.py`):**

- Add `ac` and `proof_bundle` to `_CANONICAL_FIELDS`: `...depends_on, ac, proof_bundle, blocked...`

**Engine `create_task`:**

- Add `ac: list[str] | None = None` and `proof_bundle: str | None = None` parameters
- Validate `proof_bundle` against frozenset before writing
- Apply AC guardrails (max items, max length)

**Engine `edit_task`:**

- Add `ac: list[str] | None = None` (full replacement)
- Add `add_ac: list[str] | None = None`, `remove_ac: list[str] | None = None` (atomic ops)
- Mutual exclusion: `ac` and `add_ac`/`remove_ac` cannot both be set in the same call
- Add `proof_bundle: str | None = None`
- Validate `proof_bundle` against frozenset
- Uniqueness check on AC add (reject duplicates with actionable error)
- Apply AC guardrails

**Engine search:**

- Extend search to include frontmatter `ac` items so AC text remains discoverable

## MCP Tool Changes

**`create_task` (server.py):**

- Add `ac: list[str] | None = None` and `proof_bundle: str | None = None` parameters
- Map to engine kwargs

**`edit_task` (server.py):**

- Add `ac: list[str] | None = None` (full replacement)
- Add `add_ac: str | None = None`, `remove_ac: str | None = None` (singular naming, following `add_tag`/`remove_tag` convention)
- Add `proof_bundle: str | None = None`
- Map to engine kwargs (singular → plural for atomic ops)

**`show_task` (server.py):**

- No parameter changes needed — `TaskFull` already includes new fields via model; they appear in the response automatically

## Skill Updates

Same-release delivery. The following skills must read `ac` and `proof_bundle` from frontmatter instead of parsing body text:

| Skill | Current behavior | Change |
|-------|-----------------|--------|
| `w-tdd-red` | Reads AC from body markdown sections; reads proof bundle from body string match | Read `ac` field from `show_task` response; read `proof_bundle` field |
| `w-tdd-green` | References proof bundle for scope | Read `proof_bundle` field |
| `w-code-review` | Extracts "every AC line from task body"; reads proof bundle from body | Read `ac` field; read `proof_bundle` field |
| `w-arch-review` | References proof bundle for routing | Read `proof_bundle` field |
| `w-task-decomposition` | Writes `Proof bundle: X` to body | Write `proof_bundle` parameter in `create_task` |

**Builder scope note:** The builder should grep `share/skills/` for all remaining references to `Proof bundle` and `Acceptance Criteria` body patterns to catch any consumers not listed here.

## Migration

**Proof bundle migration (recommended first-run):**

- Iterate task files in the tasks directory
- Extract `Proof bundle: X` from body text (regex: `Proof bundle:\s*(\S+)`)
- Write extracted value to frontmatter `proof_bundle` field
- Optionally remove the `Proof bundle:` line from body
- Ship as a standalone script or engine utility method

**AC migration:** Not required. Forward-only — new tasks use frontmatter AC. Legacy tasks retain body AC. Agents handle both (read frontmatter if present, fall back to body inspection for legacy tasks).

## Delivery Constraints

- Ship schema + skill updates together (same release)
- Cockpit UI is a separate follow-up task
- All engine changes must have test coverage

## Acceptance Criteria

- AC1: `ac` (list[str]) and `proof_bundle` (str|None) are first-class frontmatter fields in the Task model
- AC2: `proof_bundle` appears in TaskSummary and DispatchEntry; `ac` does not
- AC3: Model normalizes `proof_bundle` (lowercase, sort modifiers) without membership validation
- AC4: Engine validates `proof_bundle` membership against frozenset in create/edit paths
- AC5: `edit_task` supports dual AC mutation (full replacement OR atomic add/remove, mutually exclusive)
- AC6: MCP tools (`create_task`, `edit_task`, `show_task`) expose both fields
- AC7: Engine search includes frontmatter AC items
- AC8: Pipeline skills read AC and proof_bundle from frontmatter instead of body text
- AC9: Migration script extracts proof_bundle from body to frontmatter
- AC10: Engine enforces AC guardrails (max 20 items, max 500 chars per item)
