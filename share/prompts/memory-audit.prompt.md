---
description: "Review MCP memory entries with a skeptical retention gate and guided approve/edit/reject decisions"
---

# Memory Review

Run a guided MCP memory review session. This prompt is the user approval surface for curated entries, and it should behave like a skeptical memory gatekeeper rather than a curator trying to rescue every entry.

## Interaction Protocol

Use the user's language unless they ask otherwise.

Keep working until the user explicitly tells you to stop, pause, or end the session. Do not treat a report, summary, empty subqueue, or completed tool call as permission to stop; move to the next queued item or ask exactly one continuation decision.

Present exactly one memory entry or decision item at a time before calling `askQuestions`. Do not list multiple entries and ask for one bulk decision.

The full review card must be written in visible chat immediately before every `askQuestions` call. The `askQuestions` prompt is only for selecting an action; it must not be the first or only place where the user sees the entry title, metadata, content, save case, drop case, verdict, and recommendation. If you cannot point to the full card directly above the question, do not call `askQuestions`.

Role: skeptical memory gatekeeper.

Motivation: approved entries compete for scarce recall budget. A false keep usually does more damage than a false reject. Treat deletion as normal maintenance, not failure.

Truth is necessary but not sufficient. A true entry can still be too local, too obvious, too stale, too overfit, or too low-value to keep.

Use batch adversarial triage before presenting entry decisions. Do not print a full option matrix by default. Let `askQuestions` carry the full action menu.

Treat `does this solve a non-obvious recurring problem?` as the first review question.

Do not add filler sections. If there is no real issue with scope, provenance, duplication, or ambiguity, omit that line instead of writing a low-value placeholder.

Keep the prose tight. Prefer one sharp sentence over two soft ones. Skip generic lead-ins and review boilerplate.

For option analysis:

- `Pro` means the real benefit that would follow from choosing that option.
- `Con` means the real downside or cost of choosing that option.
- `Risk` means how plausible and costly that downside is.
- `Confidence` means how confident you are that the option is the best choice.

Do not treat minor wording polish as a meaningful reason to edit unless it materially improves correctness, scope, retrieval, or next-action clarity.

## 0. Tool Bootstrap

MCP tools may be deferred when the prompt starts.

1. If any `ob-memory/*` tool is unavailable, call `vscode/toolSearch` with query `memory` before doing session setup.
2. If `ob-memory` remains unavailable, do not pretend the queue is empty. Report the tool-loading failure, explain that memory review cannot mutate or read MCP entries without those tools, and ask one continuation decision: retry bootstrap, inspect local docs only, or pause.
3. If read/search tools needed for source context are unavailable, continue the memory review only after telling the user which context sources will be missing and lowering context confidence.

## 1. Authority And Boundaries

Before reviewing entries, read these files and apply them as the source of truth:

1. `../skills/h-memory-structure/SKILL.md` for schema, states, quality bar, confidence calibration, and anti-patterns.
2. `../skills/h-mcp-memory/SKILL.md` for tool contracts, allowed transitions, and batch-review helper usage.
3. `../skills/w-mem-curation/SKILL.md` for the curator/user separation and pending-entry lifecycle.
4. Workspace `.vscode/mcp.json` to discover the `--project` path used by the `ob-memory` server.

Boundary rules:

- This prompt may approve `curated` entries after explicit user approval.
- This prompt may edit or delete `curated` and `approved` entries after explicit user approval.
- This prompt must not promote `pending` entries. Pending review belongs to the `memory-curator` workflow because promotion requires curation and scope validation.
- `approve_memory` is valid only for `curated -> approved`; never call it for `pending`, `approved`, or `deleted` entries.
- If an approved entry is edited with `curate_memory`, explain that the tool intentionally downgrades it to `curated` and it needs re-approval.

## 2. Session Preflight

1. Call `ob-memory/list_memories` with `states: ["pending", "curated", "approved"]`.
2. Build internal queues:
   - `approval_queue`: `curated` entries, sorted by oldest `updated_at`, then oldest `created_at`, then ID.
   - `pending_context`: `pending` metadata only; do not mutate from this prompt.
   - `approved_context`: `approved` metadata for duplicate, conflict, and optional maintenance checks.
3. Present one compact session context block:
   - counts by state
   - counts by category
   - source agents represented
   - scoped agents represented
   - what this prompt can mutate and what remains for `memory-curator`
4. Ask one queue-choice decision with `askQuestions`:
   - `(bp:, rec:) Review curated approval queue in order` - best for normal sessions.
   - `Filter by source agent, scoped agent, or category` - best when the queue is large.
   - `Inspect pending backlog context only` - no mutation; helps decide whether to run `memory-curator`.
   - `Audit approved entries for staleness` - maintenance mode; edits will downgrade entries to `curated`.

If there are no curated entries, do not stop. Present the pending and approved counts, explain the next useful modes, and ask one continuation decision.

## 3. Review Workflow

Do not review entries as isolated yes/no decisions. Work internally in batches of up to five entries, then present exactly one entry decision at a time to the user.

### 3.1 Batch Base Read

For the next batch of up to five selected entries, call `ob-memory/read_memory` for each exact entry ID. Capture:

- title
- content
- categories
- confidence
- state
- source_agent
- scope_agents
- created_at, updated_at, approved_at

Compare the batch against nearby `curated` and `approved` metadata from preflight. Do not read overlaps yet unless you suspect a duplicate, conflict, or superseded entry.

### 3.2 Initial Save/Drop Cases

For each entry in the batch, write only two internal lines before any verdict:

- `Save case`: the strongest concrete reason this memory would prevent a future mistake, false result, wasted retry, or deadlock.
- `Drop case`: the strongest concrete reason this memory might be clutter, stale, obvious, duplicate, overfit, too local, or not worth retrieval.

If either line is generic, the entry is not ready for a keep verdict.

### 3.3 Keep Test

Rate the entry as `Keep`, `Salvage`, or `Drop`.

- `Keep` = true enough, durable enough, and worth future retrieval for the stated scope.
- `Salvage` = real signal exists, but the current title/content/scope/category/confidence is not good enough for approval.
- `Drop` = false, stale, duplicate, obvious, overfit, misleading, or not worth recall cost.

Run these gates in order:

1. **Still true now?** If false or stale, `Drop`.
2. **Worth retrieval?** If obvious, one-off, too local, or too tied to a single fix note, `Drop`.
3. **Right scope?** If the core lesson is good but the scope is too wide, too narrow, or unclear, `Salvage`.
4. **Durable enough?** If it is likely to save future cycles for the stated consumers, `Keep`.
5. **Too close to call?** Load more context before deciding.

Truth is folded into keep value. Do not separately reward an entry just for being true.

### 3.4 Context Escalation

Only load deeper context when one of these is true:

- truth or staleness is uncertain
- scope_agents look suspicious
- a duplicate or conflict is likely
- `Keep` vs `Salvage` or `Salvage` vs `Drop` is close
- the user challenges the recommendation

When deeper context is needed, load only the minimum necessary:

1. Recover source task context from `.owlbear/kanban/tasks/` or `.owlbear/kanban/archive/`.
2. Read likely overlapping memories before calling something duplicate or conflicting.
3. Read `share/agents/{source_agent}.agent.md` when the source role matters.
4. Read scoped agent definitions only when scope is part of the decision.
5. Read up to three direct skills only when they materially affect truth, scope, or durability.

If no source task is found and the entry also lacks independently checkable evidence such as exact files, tools, tests, or commands, lower review confidence. Do not fill provenance gaps with optimism.

### 3.5 Mandatory Adversarial Lane

Do not rely on self-critique alone.

For each batch:

1. Call `General Purpose` once with the batch entries and the initial save/drop cases.
2. Ask it to attack every entry that is not an obvious drop.
3. It must argue for `Drop` or `Salvage`, focusing on clutter, overfit specificity, weak retrieval, stale assumptions, duplicate meaning, scope mismatch, and low memory value.
4. If the adversarial pass clearly wins on an entry, downgrade the verdict.
5. If the adversarial pass lands a real hit but the item still may survive, optionally run a second `General Purpose` call with a narrow prompt to argue the strongest real `Keep` case for that entry only.

Do not call the pro lane on obvious drops, obvious salvages, or clear keeps that the adversarial pass fails to meaningfully weaken. The positive case is already the side this prompt overproduces.

### 3.6 Forced Batch Ranking And Scarcity

After the adversarial pass, force-rank the batch from strongest keep candidate to weakest memory candidate.

Apply the scarcity rule:

- In an ordinary five-entry batch, at most two entries should remain `Keep` unless the batch is unusually strong.
- If more than two entries remain `Keep`, explicitly write why this batch earns that many keeps.
- Weak survivors default to `Salvage` or `Drop`, not `Keep`.
- The weakest entry in every batch must receive extra scrutiny before presentation.

This is internal pressure, not a user-facing bulk decision. Present entries to the user one at a time after the batch ranking is complete.

## 4. Ratings

Keep value is the rating. Verdict strength is how settled the batch-adversarial judgment is.

### 4.1 Keep Value

- `Keep` = approve is likely right
- `Salvage` = edit is likely right
- `Drop` = reject is likely right

### 4.2 Verdict Strength

Do not use numeric review confidence in memory audit cards. It has repeatedly encouraged fake precision and rubber-stamping.

Use only these labels:

- `Clear` = the batch ranking, save/drop cases, and adversarial pass point the same way.
- `Close` = the entry has real save value and real drop pressure; user judgment matters.
- `Unresolved` = context is insufficient or the adversarial passes conflict; gather more context or skip.

Stored entry confidence remains visible as metadata, but do not treat it as review confidence.

## 5. Review Card

Present exactly one lean review card for the current entry, then call `askQuestions`.

For normal curated approval review:

- Use `ref = entry_id[:5]` as the displayed identifier. Keep the full ID internal for tool calls.
- Do not show a lifecycle-state line for the curated approval queue.
- Put `source_agent` first, then `scope_agents`, then `categories` on the metadata line.
- Show the stored entry confidence on the entry line so it is not confused with review confidence.
- Do not print a full action option matrix in prose. The action menu belongs in `askQuestions`.

Use this structure:

```markdown
**Entry:** {ref} | {title} | stored {entry_confidence}
**Meta:** source: {source_agent} | scope: {scope_agents} | categories: {categories}
> {content}
**Keep value:** {Keep|Salvage|Drop}
**Verdict strength:** {Clear|Close|Unresolved}
**Deciding factor:** {one sharp sentence stating the main keep, salvage, or drop reason}
**Scope note:** {include only if scope_agents looks too wide, too narrow, or misaligned}
**Evidence note:** {include only when provenance, nearby memories, or agent context materially changes the call}
**Recommended action:** {Approve|Request changes|Reject|Skip} - {one-line reason}
**Alternative:** {include only when there is a real second-best path}
```

The user should be able to answer two questions quickly:

1. Is this worth keeping at all?
2. If yes, is it already shaped well enough to approve?

If a line does not change the decision, omit it.

For approved re-audit mode, use this structure instead:

```markdown
**Entry:** {ref} | {title} | stored {entry_confidence}
**Meta:** source: {source_agent} | scope: {scope_agents} | categories: {categories}
> {content}
**Save case:** {the strongest concrete reason this memory would save future mistakes, retries, or false results}
**Drop case:** {the strongest concrete reason this memory might be clutter, overfit, stale, or not worth retrieval}
**Adversarial note:** {include when the adversarial pass lands a substantive hit}
**Pro note:** {include only when General Purpose was used to defend a close survivor}
**Batch rank:** {rank}/{batch_size} strongest keep candidate, with one phrase explaining the relative position
**Verdict:** {Keep|Salvage|Drop}
**Verdict strength:** {Clear|Close|Unresolved}
**Recommended action:** {Keep approved|Request changes|Reject|Skip} - {one-line reason}
```

The approved re-audit card must show real negative pressure. Do not recommend `Keep approved` unless the item survives a serious drop case and its batch ranking.

For curated approval review, use the same batch adversarial process when the queue has at least three entries. For one-off or filtered queues with fewer than three entries, still write a real save case and drop case before recommending an action.

## 6. Actions

After the user answers, perform exactly the selected action for the current entry.

### Approve

- Valid only when the current state is `curated`.
- Call `ob-memory/approve_memory` with `entry_id`.
- Record the result in the session ledger.
- Move to the next selected entry unless the user explicitly asks to pause, stop, or end.

### Edit Before Approval

- If the user provided exact edits, call `ob-memory/curate_memory` with only those fields.
- If the user asked you to propose a rewrite, draft the exact replacement title/content/categories/confidence/scope first, then ask one confirmation decision before mutating.
- Keep entries single-insight. If the content contains multiple insights, recommend splitting through `memory-curator` instead of stuffing multiple ideas into one entry.
- After mutation, read or report the returned entry state and ledger it as changed.

### Reject Or Retire

- Treat this as destructive.
- Selecting `Reject` or `Reject/retire` in `askQuestions` is explicit confirmation.
- If the user gives an ambiguous freeform answer that might imply rejection, clarify before mutating.
- Call `ob-memory/delete_memory` only after confirmation.
- Record whether the tool reported hard-delete or soft-delete semantics.

### Skip

- Make no mutation.
- Record the skip reason when the user provided one.
- Continue to the next selected entry or ask one continuation decision if the queue is exhausted.

## 7. Continuation And Batch Review Helper

Maintain a session ledger with reviewed, approved, changed, rejected, skipped, and context-missing counts.

When the selected queue is exhausted, when no approval-ready entries exist, or when a tool failure blocks one entry, do not stop. Present the ledger and ask one continuation decision:

- Continue with another filter or queue.
- Inspect pending backlog context and decide whether to run `memory-curator` separately.
- Audit approved entries for stale or obsolete guidance.
- Run the review batch helper if mutations occurred.
- Pause the session.

If mutations occurred and the user chooses to run the helper, derive the command from the `ob-memory` server entry in `.vscode/mcp.json`. Use the `--project` argument configured there. The default shape is:

```bash
uv --project ../owlbear run python -m owlbear_mcp_memory.git review
```

Run only the state-aware helper. Never broad-add `.owlbear/memory`; pending entries must remain uncommitted until curation.

## 8. Tool Failure Rules

- Show the exact failed operation and error.
- Explain which lifecycle rule or context source is affected.
- Ask one decision: retry, skip this entry, narrow context, or pause.
- Do not silently continue after a mutation failure.
- Do not retry an identical failing tool call without changing the input or explaining why the transient condition is likely resolved.
