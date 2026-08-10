# Structured Task Specification in Frontmatter (AC + Proof Bundle)

## Problem

Two key specification fields currently live as freeform text in the task body instead of structured frontmatter:

1. **Acceptance Criteria (AC):** Typically under a `## Acceptance Criteria` heading. This mixes specification with volatile content — work logs, agent notes from `end_work`, and other discussion accumulates in the same body over multiple work sessions.

2. **Proof Bundle:** A recently introduced single-axis complexity/testing taxonomy (`skip | existing | smoke | behavioral | critical`) that replaces the old per-AC `td:N` annotations. Currently written as a `Proof bundle: behavioral` line in the body. Determines test-writing scope, challenger/code-reader involvement, and reviewer depth.

Both are stable specification — the body chatter is the volatile part. Pulling them into structured frontmatter makes them machine-readable, separately queryable, and keeps the body for operational notes.

## Proposed Direction

### AC field

Add an `ac` field to task frontmatter — a list of named strings:

```yaml
ac:
  - "AC1: Each AC is a named string in frontmatter"
  - "AC2: show_task returns ac field in response"
  - "AC3: edit_task supports add_ac / remove_ac"
```

### Proof bundle field

Add a `proof_bundle` field to task frontmatter — a single enum string:

```yaml
proof_bundle: behavioral  # skip | existing | smoke | behavioral | critical
```

Optional escalation modifiers as separate flags or a combined format (`behavioral+challenge`). The taxonomy is already defined in `r-pipeline-protocol`:

| Bundle | Test-writer | Challenger | Code-reader | Reviewer scope |
|--------|------------|------------|-------------|----------------|
| `skip` | SKIP | skip | skip | lint only |
| `existing` | SKIP | skip | skip | named tests + lint |
| `smoke` | smoke tests | skip | skip | scoped tests + lint |
| `behavioral` | full TDD | yes | skip | scoped tests + lint + coverage |
| `critical` | full TDD | yes | yes | full suite + lint + coverage |

### Naming convention

AC entries are prefixed with a name (e.g., `AC1:`, `AC2:`, or semantic names like `AC-lint:`). The prefix prevents confusion when ACs are added or removed mid-lifecycle — inserting between AC2 and AC3 becomes `AC2.5:` or a semantic name, rather than renumbering everything. Agents can reference specific ACs by name in body text or reviews.

### Design questions for ideation

- **Storage format:** List of named strings (simple, ordered) vs YAML map (structured key lookup) vs list of objects (extensible with metadata). Leaning toward list-of-strings for simplicity.
- **API surface:** Should `list_tasks` expose AC? Options: count only (`ac_count: int`), full list, or nothing (defer to `show_task`). Trade-off is response size vs usefulness.
- **MCP tool changes:** `create_task` gains `ac` parameter. `edit_task` gains `add_ac` / `remove_ac` (atomic operations, like existing `add_tag` / `remove_tag`). `show_task` response includes `ac` field.
- **pick_tasks integration:** Dispatch entries could include AC so agents see criteria immediately upon pickup without a separate `show_task` call.
- **Body predicate migration:** Current status predicates check for `## Acceptance Criteria` section in the body. These would shift to checking `len(task.ac) > 0`. Dual-read period may be needed.
- **Migration of existing tasks:** Options range from big-bang script (parse body sections, move to frontmatter) to forward-only (only new tasks use frontmatter AC) to dual-read (predicate checks both locations).
- **Cockpit UI:** Task detail view shows AC as a checklist. Task list shows AC count as a badge.
- **Frontmatter size:** AC lists are typically 3–8 items. Long AC text is fine as a single YAML string but readability in raw files should be considered.

### Extensions to consider (later, not initial scope)

- **AC status tracking:** A separate `ac_status` field or map (`{AC1: "met", AC2: "unmet"}`) for evidence — but this is closer to the "structured evidence" pattern and should probably be a distinct feature.
- **Required AC patterns:** If task types are ever added, different types could require different AC structures.
- **AC templates:** Common AC patterns (e.g., "tests pass", "lint clean", "docs updated") that can be auto-populated.
- **Proof bundle in dispatch guidance:** `pick_tasks` could use `proof_bundle` to annotate dispatch entries with expected scope ("this is a critical task — expect full TDD + challenger + code-reader").

### Cockpit display

- **AC:** Task detail view shows AC as a checklist. Task list shows AC count as a badge.
- **Proof bundle:** Visual complexity indicator on task cards — e.g., a signal-strength icon (1–5 bars mapping to skip→critical), a color-coded badge, or a simple text label. Gives the user instant visibility into expected task weight while browsing the board.

## Key Insight

Move the stable thing (specification) to structure; leave the volatile thing (work log, discussion) in freeform body. AC and proof bundle are both specification — they define what the task should accomplish and how thoroughly it should be verified. Neither should live in the volatile body.

## Compatibility

Fully backward-compatible: tasks without `ac` default to `[]`, tasks without `proof_bundle` default to `None` (or a sensible default like `"behavioral"`). No breaking changes to existing MCP tools or cockpit API.
