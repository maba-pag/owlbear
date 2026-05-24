# Simplifier Stance — Decision Request Data Model

## Simplification Opportunities

### 1. Collapse `kind` to two values: `decision` and `action`

The proposed 5-kind enum (`decision | action | approval | clarification | confirmation`) is over-specified. Looking at the 40+ resolved DRs in this workspace:

- **approval** = a decision with options `[approve, reject]`
- **clarification** = a decision with `response_mode: free_text`
- **confirmation** = a decision with options `[confirm, correct]`

These are presentation variants of the same primitive: "agent needs human input." Two kinds cover all real cases:

- `decision` — choose from options or provide free text
- `action` — user does something external, marks done/blocked

The response UI can vary based on the *options provided*, not a parallel enum. An approval is just a decision where the agent supplies approve/reject as options.

### 2. Drop `response_mode` as a separate axis

If kind=decision and options are provided → render option cards. If kind=decision and no options → render free text. If kind=action → render done/blocked. The shape of the *data* already determines the response control. A separate `response_mode` enum creates a second dimension agents must get right and introduces invalid combinations (e.g., `response_mode: select_option` with zero options).

Replace with a single boolean: `allow_free_text: true` (default true). Cockpit derives everything else from the presence/absence of options.

### 3. Drop per-option `confidence`

The 1534-decision.md uses per-option confidence, but note what the human actually acted on: the *recommendation flag* and *prose rationale*. Confidence scores like 0.62 vs 0.58 are false precision — they don't help a human choose between "MCP tools" and "Cockpit surface." The recommended flag + rationale text does that job.

Keep: `recommended: bool`, `rationale: str`
Drop: `confidence: float`

### 4. Reduce engine API to three operations

`create + resolve + list` covers every real workflow observed. Cancel and supersede are admin edge cases:

- **Cancel** = resolve with `status: cancelled` and a reason. Not a separate state machine transition.
- **Supersede** = create a new request, cancel the old one. Agents already know their own prior request IDs.

This avoids two additional state transitions, two additional MCP tools, and a `supersedes_request_id` foreign key.

### 5. Drop `blocking` flag

Every pending DR in this system already blocks the task — agents cannot proceed without answers. The input doc itself acknowledges "multiple parallel blocking requests" has "unspecified behavior." If the non-blocking case has no defined semantics and no observed usage, it's speculative. Remove the flag; every pending request blocks.

### 6. Drop `parent_request_id` and `supersedes_request_id`

No evidence of DR chains in resolved decisions. No agent workflow currently produces follow-up-to-follow-up requests. If needed later, it's a single optional field addition — trivial to add, costly to design correctly now.

## What Can Wait

| Deferral | Why it's safe |
|----------|---------------|
| `audience` / `assigned_to` / `visibility` | Single-user system today. Add when multi-user exists. |
| `impact`, `risk`, `cost`, `reversibility` per option | Nice-to-have enrichment; options work without them. |
| `sequence` numbering | Chronological sort by `created_at` suffices. Explicit numbering is only needed if display order diverges from creation order — no evidence it will. |
| `updated_at` | Requests are write-once until resolution. A mutable update timestamp implies edit-in-place semantics that don't exist yet. |
| Cockpit + agent instructions | Already identified as "after first useful step." Correct sequencing. |

## What Must Stay

| Element | Why |
|---------|-----|
| `request_id` as canonical identity | Multiple requests per task requires it. Non-negotiable. |
| Structured options with `option_id` + `label` | The entire point — stops Cockpit parsing prose for choices. |
| `recommended` flag on options | Agents have a view; humans should see it. |
| `title` + `body_markdown` separation | Enables card rendering without truncation heuristics. |
| Machine-readable resolution (`selected_option_id`, `free_text`, `resolved_by`, `resolved_at`) | Closes the loop mechanically. The core promise. |
| Full ISO 8601 timestamps | Cheap, necessary for ordering, no reason to regress. |

## Preserved Expectation

A real choice system: agents express structured options, Cockpit renders adapted controls, users select without prose-typing, answers flow back mechanically.

## After First Useful Step

Storage format + engine (create/resolve/list) + MCP tools + read API. This is the foundation. Cockpit resolver UI and agent instruction updates are the follow-on.

## Confidence

**0.85** — The proposed scope has real scope inflation in `kind` granularity, `response_mode` redundancy, and premature hierarchy fields. The cuts above preserve the expectation while removing ~40% of the data model surface area.
