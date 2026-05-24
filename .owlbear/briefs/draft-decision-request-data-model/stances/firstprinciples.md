# First-Principles Stance — Decision Request Data Model

## Irreducible Claims

1. **Cockpit needs to know what controls to render without parsing prose.** This is real — the current `_extract_title` and `_format_plain_title` regex code proves it. A structural fix is justified.

2. **Downstream agents need the resolution answer in a machine-readable field.** Currently the only structured resolution is the `response` field (approved/rejected/needs-info). If the user chose "hybrid" from three options, no machine-readable field records that. The agent reads the task body where a summary was appended. This is fragile.

3. **Agents should express structured intent when creating a request.** The current `body` parameter forces agents to encode options, recommendations, and question type into prose. This works (agents are good at prose), but Cockpit can't reliably decode it.

## Borrowed Structure (assumed without evidence)

### The 5-kind × 6-response_mode matrix

The actual corpus of 42+ decision requests contains exactly two types: `decision` and `action`. The proposed 30-cell matrix (5 kinds × 6 response modes) has no empirical instances. Approval is a decision with specific options. Clarification is a decision with no options and free text required. Confirmation is a decision with yes/no options.

**Challenge:** Design from observed patterns, not from speculative completeness.

### Per-option confidence as a float

No resolved request in the archive shows evidence that confidence scores influenced the human's choice. Humans respond to: (a) the recommendation flag, (b) the rationale text, (c) their own judgment. A float like 0.62 vs 0.58 does not create actionable difference.

**Challenge:** What decision would a human make differently if confidence were 0.62 vs 0.65?

### File-per-request as the only storage model

The current system uses file-per-request with the filename as identity. The input doc preserves this. But with multiple requests per task and request IDs, you're building database semantics (unique ID generation, collision avoidance, state transitions, foreign keys) in a filesystem.

**Challenge:** The file-per-request model still works — but only if you accept that request_id IS the filename stem and don't layer additional identity schemes on top. Filesystem provides uniqueness and atomicity for free if you use it directly.

### `supersedes_request_id` / `parent_request_id`

Zero observed instances of DR chains. This is speculative graph structure borrowed from issue-tracking systems (Jira links, GitHub references). In a single-user kanban with ephemeral requests, the chain is: create → resolve. Period.

## The Actual Minimum

Three independent improvements, ordered by value density:

### Fix 1: Structured resolution (highest value, smallest change)

Add `selected_option_id` and `free_text` to the resolution fields. This alone closes the machine-readable loop without touching request creation at all.

### Fix 2: Optional structured options in request creation

Add `title` and `options` (list of `{option_id, label, recommended?, rationale?}`) to frontmatter. Cockpit renders cards when present; falls back to body rendering when absent. Agents are encouraged but not forced to provide structure.

### Fix 3: Adapted response controls in Cockpit

When options are present, render option cards with selection. When no options exist, render free text. Always allow free text augmentation. This is a UI change driven by the data from Fix 2.

These three fixes are independently valuable and independently deployable. The question is whether they should be designed together (ensuring consistency) or implemented incrementally (reducing risk of over-design).

## Questions That Must Be Answered Before Approach Choice

1. **Is the data model one unified Pydantic model, or separate request-creation vs. stored-state vs. resolution models?** The input doc shows one big YAML shape. In practice, creation input ≠ stored state ≠ resolution input. These are different schemas with different required fields.

2. **Does request_id = filename stem, or is it a separate generated field?** If separate, you need a generation scheme and a lookup index. If filename-based, you get filesystem uniqueness for free but lose human-readable filenames.

3. **Should the engine own ID generation, or the caller?** If MCP callers provide IDs, you get idempotent creation. If the engine generates them, you need a response payload and the caller can't predict the filename.

4. **What is the resolution flow?** Currently: user edits `response` field in frontmatter → engine sweeps pending dir → moves resolved files. The input doc implies: Cockpit API receives a resolve call → engine updates the file + unblocks task. Which is the canonical resolution path?

5. **How does the `kind` axis help Cockpit if `options` already determines the control shape?** If options present → cards. If no options → free text. If kind=action → done/blocked. What does `kind` add beyond what the data shape already implies?
