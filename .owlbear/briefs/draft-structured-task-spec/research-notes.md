# Research Notes — Structured Task Specification in Frontmatter

## Verified Findings

### F1: List field precedent is well-established
- `tags` (list[str]) and `depends_on` (list[int]) are existing list-typed frontmatter fields
- Both use `Field(default_factory=list)` in the Pydantic model
- Both appear in `_CANONICAL_FIELDS` for serialization ordering
- Both have atomic add/remove operations in `edit_task` (engine: `add_tags`/`remove_tags`, `add_deps`/`remove_deps`)
- MCP uses singular naming: `add_tag`/`remove_tag`, `add_dep`/`remove_dep`
- Serialization is automatic via Pydantic `model_dump()` + ruamel.yaml

### F2: Task model structure
- `Task` (models.py:413) — full internal model, `extra='allow'` (preserves unknown YAML keys)
- `TaskSummary` (models.py:451) — used by `list_tasks`, `extra='ignore'`, excludes `body` and `created`
- `TaskFull` (models.py:488) — used by `show_task`/`start_work`, extends TaskSummary, adds `body`, `created`, `updated`
- New fields must be added to all three model classes

### F3: Canonical field ordering controls serialization
- `_CANONICAL_FIELDS` list at storage.py:200–216 determines YAML key order
- Unknown/extra fields are appended after canonical fields (storage.py:408–414)
- New fields need explicit placement in this list

### F4: `edit_task` parameter patterns
- Engine `edit_task` (engine.py:1140) accepts individual keyword args, NOT a dict/model
- Atomic list ops use `add_*`/`remove_*` pairs (lists of values)
- Scalar fields use direct assignment (`title=`, `priority=`, `block_reason=`)
- MCP server (server.py:438) maps MCP params to engine kwargs conditionally

### F5: Proof bundle is defined in `r-pipeline-protocol` only
- Taxonomy table: skip | existing | smoke | behavioral | critical
- Modifiers: `+challenge`, `+reader` (escalation only)
- Currently written as `Proof bundle: behavioral` in task body by `w-task-decomposition`
- Read by `w-tdd-red`, `w-code-review` via body string matching
- No code-level validation — agents interpret the string ad-hoc

### F6: AC is read by agents via ad-hoc body parsing
- `w-code-review` extracts "every AC line from the task body" and maps to an evidence table
- `w-tdd-red` reads AC from body markdown sections
- `body_parser.py` exists (body_parser.py:43–73) with `parse_body()` returning `Section` objects, but agents don't use it for AC — they do string matching
- No structured AC field exists anywhere in the model

### F7: `create_task` builds Task object directly
- Engine `create_task` (engine.py:1007) constructs `Task(...)` with explicit kwargs
- MCP `create_task` (server.py:340) accepts: title, body, depends_on, parent, priority, tags
- New fields would need explicit parameters in both engine and MCP

### F8: write_task serialization is automatic
- `write_task()` (storage.py:363) calls `model_dump()`, removes `body` and `claimed_by`, writes YAML frontmatter + body
- List fields serialize to YAML sequences automatically
- No special handling needed for new list[str] or str fields
- Canonical field order list must be updated

## Candidate Implications

### I1: AC follows the tags pattern closely
Adding `ac` is structurally identical to adding `tags` — same type (list[str]), same atomic ops needed (`add_ac`/`remove_ac`), same serialization. The implementation path is clear and low-risk.

### I2: Proof bundle is simpler than AC
Single optional string field with a closed set of valid values. Could be implemented as a `Literal` type or validated against a config-driven enum. Modifiers (`+challenge`, `+reader`) mean it's not a pure enum — it's `base[+modifier[+modifier]]`.

### I3: TaskSummary inclusion decision matters
If `ac` is added to `TaskSummary`, every `list_tasks` call returns AC for all tasks. Could be: full list (useful but verbose), count only (`ac_count: int` computed field), or omitted (defer to `show_task`). `proof_bundle` is a single string and cheap to include in summaries.

### I4: Migration script is straightforward
Current body AC follows a `## Acceptance Criteria` or `## AC` heading with bullet items. `body_parser.py` already parses body sections. A migration script would: parse body → extract AC section → write items to frontmatter → optionally remove section from body. Proof bundle is a regex: `Proof bundle: (\w+(?:\+\w+)*)`.

### I5: Agent skill updates are bounded
Only three skills reference proof bundle by name (`w-tdd-red`, `w-code-review`, `w-task-decomposition`). AC references are more diffuse but agents reading `show_task` will see the new field automatically. Skill updates can be a follow-up sweep.

### I6: `pick_tasks` AC inclusion is valuable
`pick_tasks` dispatches tasks to agents. If dispatch entries include `ac`, agents see criteria immediately without a separate `show_task` call. This reduces round-trips but increases response size. The `proof_bundle` field is almost certainly worth including in dispatch (it determines agent scope).

## Open Research Questions

### Q1: AC storage format — list-of-strings vs alternatives
- List-of-strings: simple, matches `tags` pattern, ordered, easy YAML
- YAML map (`{AC1: "description", AC2: "description"}`): key lookup, but ordering is fragile in YAML
- List-of-objects (`[{name: "AC1", text: "..."}, ...]`): extensible, but over-engineered for current needs
- **Recommendation for Phase 2:** list-of-strings is the KISS choice; the naming convention (prefix like `AC1:`) provides enough structure for referencing

### Q2: Proof bundle validation strictness
- Closed enum (`Literal["skip", "existing", "smoke", "behavioral", "critical"]`) is clean but doesn't handle modifiers
- Regex validation (`^\w+(\+\w+)*$`) is flexible but permissive
- Config-driven validation (valid bundles defined in kanban config YAML) is consistent with how status/priority work
- **Recommendation for Phase 2:** start with string + regex validation; config-driven if needed later

### Q3: Dual-read transition period
- Forward-only: new tasks get frontmatter fields, old tasks keep body AC
- Should show_task/start_work merge both sources (frontmatter AC + body AC section)?
- Or rely on agent improvisation to handle the inconsistency?
- **Recommendation for Phase 2:** no merge — forward-only with agent improvisation, optional migration script

### Q4: AC in list_tasks response shape
- Full list: useful but potentially large
- Count only: `ac_count: int` computed field — lightweight, still informative
- Nothing: defer to show_task
- `proof_bundle` should definitely be in TaskSummary (single string, useful for board views)
