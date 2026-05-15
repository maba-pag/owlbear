---
description: "Review MCP memory entries with lifecycle context, source grounding, and guided approve/edit/reject decisions"
---

# Memory Review

Run a guided MCP memory review session. This prompt is the user approval surface for curated entries, with enough task, agent, skill, and nearby-memory context for the user to judge whether future agents will understand and use each entry correctly.

## Interaction Protocol

Use the user's language unless they ask otherwise.

Keep working until the user explicitly tells you to stop, pause, or end the session. Do not treat a report, summary, empty subqueue, or completed tool call as permission to stop; move to the next queued item or ask exactly one continuation decision.

Present exactly one memory entry or decision item at a time before calling `askQuestions`. Do not list multiple entries and ask for one bulk decision.

Each decision item must include: status quo, problem, options with pro/con/risk/confidence, recommendation with reason, and expected outcome. Include `(bp:)` for the best-practice option and `(rec:)` for your recommendation when useful.

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

## 3. Per-Entry Context Bundle

For each selected entry, build the context bundle before asking for an action. If a context source is unavailable, say exactly what was unavailable and continue with a lower context confidence instead of stopping.

### 3.1 Read The Entry

Call `ob-memory/read_memory` for the exact entry ID. Capture:

- title
- content
- categories
- confidence
- state
- source_agent
- scope_agents
- created_at, updated_at, approved_at

### 3.2 Recover Source Task Context

Try to identify the task or work item that produced the memory:

1. Parse task IDs from title and content using patterns such as `#1234`, `task #1234`, `Task #1234`, and `{id}-` filenames.
2. If a task ID is found, search `.owlbear/kanban/tasks/` and `.owlbear/kanban/archive/` for that ID. Include ignored files if the search tool supports it.
3. If no task ID is found, search task/archive text for distinctive title words plus `source_agent` and relevant file/tool names from the content.
4. Read the best matching task file when found. Extract only the context needed to judge the memory: title, acceptance criteria or objective, changed/reviewed files, audit/review notes, and outcome.
5. If no task is found, mark `source task: not found` and lower the context-confidence note. Do not invent provenance.

### 3.3 Load Agent And Skill Context

Read the agent definitions that explain how the entry will be used:

1. Read `share/agents/{source_agent}.agent.md` when it exists.
2. Read definitions for scoped agents in `scope_agents` when there are three or fewer scoped agents.
3. When there are more than three scoped agents, read the source agent plus the two scoped agents most directly named or implied by the entry content, and state which scoped agents were not loaded.
4. From loaded agent definitions, capture persona, critical rules, boundaries, and direct `required_reading` skill names that shape whether the memory is actionable.
5. Read up to three relevant direct skills from `required_reading`, prioritizing workflow/rules skills mentioned by the entry content, source task, or categories. Do not load transitive skill chains unless a direct skill says they are required for understanding this entry.

### 3.4 Check Nearby Memories

Use the preflight metadata to find likely duplicates, conflicts, and superseded entries:

1. Compare title, categories, source_agent, and scope_agents against `curated` and `approved` metadata.
2. Read likely overlaps before calling something a duplicate or conflict.
3. Treat approved entries as stronger evidence than curated entries, unless the current entry is newer and clearly corrects the old one.

## 4. Understandability And Quality Rating

Before presenting action options, rate whether a future scoped agent could understand and apply the entry.

Use this 1-5 **agent readability** scale:

| Rating | Meaning |
|--------|---------|
| 5 | Standalone, cites task/file/tool context, directly actionable for scoped agents. |
| 4 | Mostly standalone; minor context helps but the action is clear. |
| 3 | Understandable only after source task or agent context is loaded. |
| 2 | Ambiguous action, scope, or evidence; needs rewrite before approval. |
| 1 | Not usable as memory; generic, contextless, duplicate, stale, or misleading. |

Also check the `h-memory-structure` quality bar:

- specific task ID, file path, or tool name
- actionable in the next 30 seconds
- non-obvious
- single insight
- correct scope_agents for intended consumers
- category fit
- confidence calibration

### 4.1 Provenance Gate

Treat provenance as an approval gate, not a decorative note.

- If a source task is found, use it to judge whether the memory accurately captures a durable lesson from that task.
- If no source task is found but the entry cites exact files, tools, tests, commands, or task-like evidence that makes the lesson independently checkable, it may still reach readability 4.
- If no source task is found and the entry lacks equivalent exact evidence, cap agent readability at 3 and recommend `Edit before approval` or `Skip for now`, not `Approve`.
- When editing for provenance, prefer adding the missing task ID or exact file/tool/test context to the content rather than adding generic explanation.
- If provenance cannot be recovered, record that in the review card and explain what future agents would be unable to verify.

## 5. Review Card

Present exactly one review card for the current entry, then call `askQuestions`.

Use this structure:

```markdown
**Entry:** {id} - {title}
**Lifecycle state:** {state}; source={source_agent}; scope={scope_agents}; categories={categories}; confidence={confidence}
**Source task context:** {task title/objective/outcome or "not found"}
**Agent context:** {loaded source/scoped agents and the role rules that matter}
**Skill context:** {loaded relevant skills or "none needed beyond memory authorities"}
**Nearby memories:** {duplicates/conflicts/superseded candidates or "none found"}
**Agent readability:** {1-5}/5 - {reason}
**Status quo:** {what this memory currently says and who would recall it}
**Problem:** {approval blocker, edit need, duplicate/staleness concern, or "none"}
**Options:**
- Approve - Pro: {...}; Con: {...}; Risk: {...}; Confidence: {...}
- Edit before approval - Pro: {...}; Con: {...}; Risk: {...}; Confidence: {...}
- Reject/retire - Pro: {...}; Con: {...}; Risk: {...}; Confidence: {...}
- Skip for now - Pro: {...}; Con: {...}; Risk: {...}; Confidence: {...}
**Recommendation:** {one option, with reason}
**Expected outcome:** {state/content change and effect on future recall}
```

Place `(bp:)` and `(rec:)` only on the option justified by the context bundle, provenance gate, and readability rating. Do not mark `Approve` as recommended unless the entry meets the provenance gate and readability is at least 4.

Do not recommend approval for entries rated below 4 unless the user explicitly accepts the risk after seeing the context gap.

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
- If the user did not explicitly confirm deletion/retirement in their answer, ask one confirmation decision naming the exact entry ID and reason.
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
