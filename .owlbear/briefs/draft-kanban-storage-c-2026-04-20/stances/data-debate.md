# Data Modeler — Critic Debate Log

## Cycle 1: Structured body enforcement scope

**Critic:** "You propose structural validation on every write, not just status transitions. But D15 says predicates fire on `move_task` and `end_work` transitions. `edit_task(body=...)` doesn't fire predicates. You're adding a new validation surface that Brief B didn't spec. Is that storage's job or engine's job?"

**Response:** Storage validates **structural well-formedness** (parseable sections, valid heading levels, non-corrupt structure). Engine validates **semantic predicates** (required sections for a given status). These are different layers. Storage rejects a body it can't parse into `list[Section]`; the engine rejects a body that's missing sections for the destination status. The storage validation is a parse-or-reject gate — analogous to JSON schema validation before business logic. This is squarely storage's job.

**Outcome:** Position held. Clarified the distinction: storage validates structure; engine validates semantics via predicates.

## Cycle 2: Archive file compatibility under new schema

**Critic:** "Archive files won't have `archival_reason` or `archival_refs`. Status is `archived` but the D37 rules require `archival_reason` when status=`archived`. Your read path will either choke on these or silently create inconsistent data."

**Response:** Good catch. Archive files are NOT migrated (locked M1 finding). The read path must tolerate missing optional fields via Pydantic defaults (`archival_reason=None`, `archival_refs=[]`). An archived task with `archival_reason=None` is legacy data, not corruption. The D37 write-time rules prevent NEW archival without a reason; they don't retroactively invalidate old data.

**Outcome:** Position refined. Added explicit rule: read-time validation is LENIENT for legacy archive files. Missing `archival_reason` on archived tasks defaults to `None` and is NOT corruption. Write-time D37 rules remain strict.

## Cycle 3: Normalization scope

**Critic:** "You propose stripping trailing whitespace and normalizing inter-section spacing. But Markdown uses trailing double-space for line breaks (`  \\n`). Normalizing that destroys formatting. Also, current system has zero data issues — normalization introduces mutation for no proven benefit."

**Response:** Accepted. Trailing whitespace stripping would destroy Markdown line breaks. Over-normalization for no proven benefit. Revised to minimal normalization: LF line endings only. Everything else preserved as-is. The round-trip is byte-exact after LF normalization — predictable, minimal surprise, no formatting destruction.

**Outcome:** Position changed. Normalization narrowed to LF-only. Trailing whitespace, inter-section spacing, and all other formatting preserved verbatim.

## Cycle 4: Corruption in list_tasks — skip vs raise

**Critic:** "You say list_tasks should skip corrupt files and surface via guidance. But outcome 5 says 'corruption is loud and early.' Stuffing corruption into guidance alongside body-size warnings is not loud. And the response envelope is frozen — you can't add a `corruption` field."

**Response:** Real tension. Raising CorruptionError on the first corrupt file makes the entire board unqueryable until the file is manually fixed. That's loud but operationally catastrophic — a single corrupted file (which could be a git merge artifact) takes down all board operations. The pragmatic answer: **list_tasks skips corrupt files and surfaces via structured guidance with `[CORRUPT]` prefix for machine-parseable detection.** Duplicate IDs (D19) are the exception — raise immediately because ID uniqueness is a global invariant that can't be scoped to one file.

For targeted operations (show_task/edit_task/move_task on a specific corrupt file): raise CorruptionError immediately. That's loud and early for the specific file.

Note for Mediator: if the panel consensus wants a dedicated `corruption` field on ListTasksResponse, that requires a Decision-Request against Brief B's frozen envelope schema.

**Outcome:** Position held with clarification. Dual strategy: skip+guidance for list_tasks (operational continuity), raise for targeted ops (loud and early). D19 duplicates always raise.

## Cycle 5: Predicate extensions — YAGNI concern

**Critic:** "You propose `required_frontmatter_field` and `section_not_empty`. What board configuration TODAY would use them? If you can't name a concrete use case in the current config.yml, this is speculative future-proofing."

**Response:** `required_frontmatter_field` — concrete use case: require `tags` to be non-empty before a task leaves `research`. Currently tags are optional everywhere, which means tasks reach `in-progress` without any classification, making dispatch and filtering harder. This is a real operational gap the orchestrator skill works around manually.

`section_not_empty` — concrete use case: the `required_sections` predicate checks section EXISTENCE but not CONTENT. An agent can create an empty `## Acceptance Criteria` section and pass the gate. `section_not_empty` catches stub sections. This happens in practice when agents scaffold sections during task creation.

**Outcome:** Position held. Both extensions have concrete current-config use cases. Not speculative.
