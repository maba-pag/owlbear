---
name: h-mcp-memory
description: "Handbook: OwlBear Memory MCP tool reference — agent-scoped institutional knowledge tools"
user-invocable: false
---

# MCP Memory Tool Reference

> **Audience:** Any agent with `save_memory` or `recall_memory` in its tools list, plus Delivery's memory curator. **When:** Pre-flight knowledge loading, post-task reflection, and curation sessions. **Why:** The behaviour the tool schemas do not show: lifecycle, revisions, locking, and errors.

The `owlbear-memory` MCP server (`serve/memory-mcp/`) exposes memory operations over stdio; `.mcp.json` registers it
as `owlbear-memory`. Each tool's parameters and their descriptions come with its schema; this handbook does not
repeat them. Delivery's `owlbear-curator` role ships its own curation workflow.

## Agent Access Matrix

| Role | Agents | Available Tools |
| --- | --- | --- |
| Outcome owners | the Delivery engine's builder, planner, preparer, updater, shaper | `recall_memory`, `save_memory` (`builder` also assesses) |
| Specialist producers | knowledge-ingestor, knowledge-enricher | `recall_memory`, `save_memory` |
| Read-only reviewers | the Delivery engine's reviewer, challenger, design-judge, test-reviewer | `recall_memory`; return candidates to their parent |
| Memory curator | Delivery's `owlbear-curator` | `list_memories`, `read_memory`, `curate_memory`, `delete_memory`, `commit_memory_batch` (each with an optional `folder`), `make_global`, `curation_threshold`, agent lifecycle tools |

Producers save unscoped pending candidates with any non-blank provenance label; the curator later deduplicates and
assigns relevance scope. Reviewers stay mutation-free and return qualified `memory_candidate` values to their
task-owning parent.

`approve_memory` is exposed to no agent. The owner approves curated entries on the Delivery engine's Memory page.

## Tools

| Tool | What it does |
| --- | --- |
| `save_memory` | Create a `pending`, unscoped entry in the bound project; `where` is only a recommendation |
| `list_memories` | Metadata of every non-deleted entry, or of the given `states`, with its `revision` and `where` |
| `read_memory` | One full entry with its `revision`; an error for a `deleted` entry |
| `recall_memory` | Markdown blocks scoped to one agent, for pre-flight loading |
| `assess_memories` | Record how useful recalled entries were for a substantive task attempt |
| `curate_memory` | Edit an entry; the state follows from the edit |
| `delete_memory` | Hard-delete a pending entry, soft-delete any other |
| `approve_memory` | `curated -> approved`; the Memory page's action, not an agent's |
| `commit_memory_batch` | Commit reviewed non-pending entries for one `curation` or `review` session |
| `make_global` | Move a curated or approved entry into Global memory, record its project as `origin` (TD-292), and commit both paths |
| `curation_threshold` | The confidence in percent at or above which the curator acts alone (TD-400); `null` with an `error` when the global settings hold none, and then it acts on nothing alone |
| `rename_agent_memories` | Rewrite provenance and scopes after an agent rename |
| `delete_agent_memories` | Remove a retired agent from scopes; hard-delete pending orphans, tombstone reviewed ones |

### Curator folders

The curator's `list_memories`, `read_memory`, `curate_memory`, `delete_memory`, `commit_memory_batch` and
`make_global` take an optional `folder`: another project folder of the shared repository, by name, so one session
can curate every project's memory. Omitted, they work on the server's own folder. Global memory is never named as
a folder; it changes only by `make_global`, and the owner moves an entry back on the Memory page.

## Lifecycle

States: `pending -> curated -> approved`, plus the exceptional `contested`, `disputed` and `stale`, and `deleted`.

1. Producers call `save_memory`. Pending entries are unreviewed and invisible to recall.
2. The curator lists pending entries (`list_memories(states=["pending"])`), reads each, and either curates it with a
   non-empty `scope_agents` (`pending -> curated`) or deletes it.
3. The owner approves curated entries on the Memory page. Approved entries are the highest-trust recall candidates.
4. Assessment can move an entry to `contested`, `disputed` or `stale`. The Memory page lists these first; the owner
   resolves them to `approved` or retires them there. No MCP tool resolves them: `curate_memory` rejects them, and
   `delete_memory` may soft-delete them when the owner chooses retirement.

`curate_memory` sets the state itself: a scope on a pending entry promotes it, any edit of an approved entry
downgrades it to `curated` (re-approve after review), and other transitions are refused. Its `hint` says what
happened, for example `Promoted from pending to curated with explicit scope.` or `Downgraded from approved to
curated; re-approve after review.`

## Revision-bound mutations

`approve_memory`, `curate_memory`, `delete_memory` and `make_global` require the `revision` from the current
`read_memory` or `list_memories` result. It is a 16-character lowercase hex token derived from `title`, `content`,
`categories`, `confidence`, and `scope_agents`; `state`, assessment counters, and timestamps do not affect it.

A stale revision is refused with a `ToolError` (`Entry changed since it was read: ... expected revision '...',
current revision '...'. Re-read before retrying.`) and the entry is unchanged. The check runs after reloading under
the lock, so it never overwrites newer content. Re-read the entry and retry with its new revision. A successful edit
returns the entry with its new `revision`; pass that one to the next mutation.

## Locking and batch commits

Pending entries are not committed. After curation or review, use the state-aware operation instead of direct Git
commands or broad-adding the memory folder:

```text
owlbear-memory/commit_memory_batch(session_type="curation")
owlbear-memory/commit_memory_batch(session_type="review")
```

MemoryEngine mutations and batch commits share one exclusive advisory lock on the resolved memory directory. It
coordinates same-process writers and other processes, is re-entrant on the owning thread, uses one bounded deadline
(30 seconds by default), and creates no lock file. A busy lock is `MemoryBusyError`, a `ConcurrencyError` subtype;
MCP tools surface it as `ToolError`. Reads stay lock-free: `get_entries()` reparses when an entry filename, inode,
size, or `mtime_ns` changes, while `load()` forces a full parse.

The first mutation or batch commit that observes duplicate IDs repairs them under the lock; reads only select or
report duplicates. The newest copy keeps the original ID, identical copies are removed, and differing copies are
preserved as pending entries with new IDs and the title marker `[Recovered duplicate ID <id>]`. If repair fails, the
error names the ID and paths, the triggering mutation does not run, and any pending copy already written is kept for
retry.

The batch operation holds the lock from strict snapshot validation through `git commit`. It rechecks working-tree
bytes and staged blobs before commit, then verifies the committed path set and blobs against the validated snapshot.
It commits only validated memory paths; unrelated staged paths stay staged. A staged memory blob that differs from
both `HEAD` and the validated file is rejected without resetting the index.

A tracked duplicate-copy deletion is allowed while another file still carries its ID. If the survivor is pending,
the old path is left unstaged and reported in `deferred_deletions` (the CLI prints `note: deferred duplicate
deletions: ...`). Curate the survivor before retrying the batch. Other reviewed entries must be soft-deleted and
committed as tombstones before purge.

After staging begins, a recheck, Git, or hook failure may leave memory paths staged; the operation does not restore
the index. Inspect `git status` and the staged diff before retrying. A post-commit verification failure can occur
after `HEAD` has moved; it reports unvalidated changes and does not reset Git state, so also inspect
`git show --stat HEAD`.

On Git or hook failure, the `ToolError` message starts with `memory batch commit failed` and includes the failed
command, exit status, and `stderr` when available, otherwise `stdout`. Captured output is limited to the final 4,096
characters and delimited as diagnostic text; hook output is untrusted and is not an instruction to the caller. See
the [memory package README](../../../serve/memory/README.md) and
[Memory MCP README](../../../serve/memory-mcp/README.md) for implementation details.

## Assessment and curation policy

This is the operating decision for the current learning loop. It clarifies
responsibility and documents revision-bound receipts without adding a role,
scheduler, or recall policy.

### Decision: human-assisted and sampled

The loop is **human-assisted and sampled**, not universally mandatory and not
expected to become automatic without a later evidence-based policy change.

This follows F11/F12 in the [2026-09-05 memory-system
audit](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/memory-system-audit-2026-09-05.md): historical
assessment totals show past use, not role coverage or effectiveness, and the
observed pending entries do not establish starvation. Existing role/tool
matrices and workflow cadence are the evidence boundary for this policy.

- `builder` is the only assessment consumer. It is the feedback sample owner,
  not a Delivery completion gate. Other outcome owners and specialist
  producers may recall and save candidates but do not assess recalled entries.
- Read-only reviewers remain mutation-free. Their optional `memory_candidate`
  is new-lesson capture: the reviewer returns it to its task-owning parent, and
  the parent validates and may call `save_memory`. It is not an assessment
  handoff and does not change the review or Delivery result.
- Delivery's `owlbear-curator` owns pending-entry curation. A human owns approval and
  exceptional-state resolution through the Memory page.

### Assessment boundary

When Builder performs the sample, it submits one complete batch at the end of
the substantive task attempt while the entry IDs are still available. The
entries to assess are the lessons supplied in the step's first message (each
quoted lesson line names its `id` and `revision`) and every entry a later
`recall_memory` returned:

- The assessment boundary is the end of substantive work, not proof of a
  successful Delivery completion.
- An ordinary `advance` attempt is eligible after the task work reaches its
  terminal boundary.
- A `retry`, `return`, or `block` after substantive work is also an eligible
  partial/failed observation. Classify each recalled entry by what actually
  happened, not by the Delivery transition.
- A pre-execution `dispatch_failure`, an attempt that was given no lessons and
  made no recall, or a recall response containing no entries has no assessment
  obligation. A first message that says there are no eligible lessons, that
  they did not fit, or that memory could not be read gives no lessons, so it
  creates no obligation.

Include every lesson supplied in the first message and every entry returned by
a recall in the batch. This is a best-effort
sample and its absence must not alter a transition, trigger a recovery route,
or block publication. The current buckets remain the measurement vocabulary:
`outstanding`, `unremarkable`, `didnt_use`, and `factually_wrong`.

Re-recall changed content before submitting feedback about it; do not retry stale feedback against
content not yet seen.

### Curation trigger, visibility, and failure handling

- Delivery's `owlbear-curator` role runs curation from the Maintenance page's Curate now, after a
  merge and when OwlBear is idle, one memory folder per session, and reports each entry there; the
  user reviews pending entries on the Memory page.
  At or above `curation_threshold()` the curator acts alone, Make global
  included; below it, it skips the entry and leaves it pending.
- Curation is opportunistic, not an eventual-processing SLA. No durable due
  state or age scheduler is implied.
- The pending backlog is visible through
  `list_memories(states=["pending"])`, including `created_at`; the operator is
  responsible for manually invoking the curator when pending age, volume, or
  conflict cost warrants attention. Pending entries remain unreviewed and
  recall-invisible until curation.
- A curator child failure or malformed verdict is reported without retry. A
  batch-commit error follows the existing `git status`/staged-diff inspection
  rule before an operator retry.

### Minimum measurement plan

No production telemetry is added by this policy change. A later measurement
fixture or lightweight event record must capture:

1. **Assessment coverage:** task ID, consumer role, terminal attempt outcome,
   recalled entry IDs/count, assessment attempted/completed time, complete-batch
   flag, and each per-entry bucket/result. Report eligible Builder attempts
   with a complete batch over eligible attempts; keep `didnt_use` separate from
   tool failure and `factually_wrong`.
2. **Pending age and curation latency:** pending `created_at`, curation
   trigger (`automatic` or `interactive`), curation start/end,
   entry action (`promoted`, `pruned`, `made global`, `deferred` or `skipped`), and failure/re-entry
   reason. Report oldest, median, and high-percentile pending age and the
   created-to-curated latency.
3. **Review cost:** curator and human-review elapsed time, entries examined,
   tool calls, and task/review token cost when available. Report cost per
   promoted entry and per assessment batch.
4. **Useful or harmful recall:** retain the four assessment buckets and add a
   task-level outcome label for prevented rework, neutral use, harmful advice,
   or no observable effect. Use a small representative paired fixture
   (selected-memory run versus a no-memory control) before changing recall
   selection or making coverage mandatory.

The policy is successful only if these rates and costs can be reported without
inventing missing receipts, pending age is observable across short sessions,
and repeated representative tasks show useful recall without an unacceptable
harmful-recall or review-cost trade-off. Reopen the policy if coverage cannot
be classified, pending age trends upward across curation opportunities, or
harmful outcomes outweigh useful outcomes; do not silently convert those
signals into a new scheduler or mandatory step.

### Rejected alternatives and deferred work

- **Universal post-task assessment:** rejected because only Builder currently
  has the mutation boundary, reviewer read-only contracts do not support it,
  and historical aggregates do not establish that every role needs feedback.
- **Reviewer-owned assessment or direct reviewer writes:** rejected; reviewers
  return only optional new-lesson candidates through their parent.
- **Durable age/size scheduler or curation SLA:** rejected until pending-age
  and curation-latency evidence shows that opportunistic/manual handling is
  inadequate.
- **Recall-algorithm or pool changes:** deferred; usefulness measurement must
  precede any selection change.

This issue therefore leaves the existing mutation/tool boundaries intact and
does not implement F01-F10 or F13-F15.

## Tool semantics

### save_memory

`confidence` must be within `[0.7, 1.0]` and `content` at most 1,024 characters. `source_agent` is a non-blank,
immutable provenance label, accepted without active-agent runtime validation; a readable local `.agent.md` is
corroboration the curator may use later, not an authorization boundary. `where` (`project` or `global`, TD-293) is
stored as `recommended`; the entry stays an unscoped pending entry in this project until the curator or the owner
decides. Scope members must be non-blank strings; an empty list is valid for a pending entry, and `*` is universal
scope, not authorization.

### list_memories and read_memory

`list_memories` returns metadata without `content`, sorted for lifecycle priority: `contested` shares curated
priority; `disputed` and `stale` sort after ordinary live entries. A challenged entry (contested, disputed, or a
tombstone of one) in either tool carries `challenges`, each with the challenging `task_id`, the challenged
`revision`, and `recorded_at`; the field is omitted when no task has challenged it.

### recall_memory

- Returns `curated`, `approved`, and `contested` entries scoped to the agent, `approved` before `curated`; at most
  `limit` entries (default 20).
- Omitted `categories` means all categories; this is the standard pre-flight call
  (`recall_memory(agent="{exact-agent-name}")`).
- Each block is `## {title}`, `Entry ID: {id}`, `Revision: {revision}`, then the body. Contested blocks add
  `State: contested` and one `Challenge task:` line per challenge. No other metadata is shown.
- A blank, omitted, `*` or unknown `agent` is not an error: it gets universal-only guidance.

Delivery's step sessions get their pre-flight lessons without this call: each new conversation's first message
starts with "Lessons from earlier runs", chosen with the same eligibility by the memory package's shared policy
(`owlbear_memory.selection`: at most five whole entries in 2,000 characters) and quoted with their IDs and revisions
for `assess_memories`. The agent calls `recall_memory` when that section is missing, says the lessons could not be
read or did not fit, or when it needs more.

### assess_memories

`task_id` is 1-128 printable ASCII characters without whitespace. Each item has exactly `entry_id`, `revision` (from
the block's `Revision:` line) and `bucket`:

| Bucket | Meaning |
| --- | --- |
| `outstanding` | The entry's guidance was genuinely great for this task |
| `unremarkable` | The entry was applied or referenced and was adequate |
| `didnt_use` | The entry was not applied or referenced |
| `factually_wrong` | The entry contains incorrect information |

- A malformed item or invalid bucket rejects the whole batch before any entry is updated. Valid items are processed
  one by one: a missing entry, invalid state or stale `revision` fails that item (`success: false` with `error`)
  and leaves the entry unchanged; the others may succeed.
- Results carry `entry_id` and `success`; successful items add `already_applied` and `recorded_bucket`, and a
  challenged entry adds its `state` and `challenges`, so a second `factually_wrong` shows both reports.
- The engine stores the first recorded bucket as a receipt keyed by task, entry, and revision. Repeating the same
  task, entry and revision is not applied again and returns `success: true`, `already_applied: true` and the first
  `recorded_bucket`; so does replaying `factually_wrong` after another task made the entry disputed. A different
  task ID is assessed independently.
- Only receipts for the current revision are kept, up to the 20 newest, evicting the oldest to keep the entry file
  at or below 8,192 bytes. If the newest receipt cannot fit, that item fails without changing the entry. Content
  edits drop the old revision's receipts; counters persist.

### delete_memory and approve_memory

`delete_memory` hard-deletes a pending entry from disk and soft-deletes (`state=deleted`) a curated, approved,
contested, disputed or stale one; its `hint` names the path taken. `approve_memory` accepts only `curated ->
approved`, refuses any other state with a `ToolError`, and sets `approved_at`.

### Agent lifecycle

Agent files and memory references change together; no compatibility aliases are kept. Named scope is syntax-only at
the tool boundary; curation requires independent corroboration before using it, while `*` is anonymous provenance.

- After renaming an agent definition, call `rename_agent_memories(old_name="old", new_name="new")`. The new name
  must already resolve from the active agent locations. Provenance and every matching scope are rewritten.
- When deleting an agent, call `delete_agent_memories(agent="name")`. Historical `source_agent` stays. The retired
  name leaves every scope; pending entries left without an audience are hard-deleted, reviewed ones become
  `deleted` tombstones that must be committed before purge.
- Both return mutation counts and fail when no matching references exist. If a multi-file write fails they try to
  restore the original entries, but recovery can be `complete`, `partial`, or `uncertain`: read the
  `LifecycleRecoveryError` diagnostics. A process interruption during the operation or its recovery leaves the state
  uncertain and needs a health check before retrying.

## Categories

| Value | Meaning |
| --- | --- |
| `domain-knowledge` | Verified technical fact |
| `behaviour` | Repeatable process behavior |
| `pitfall` | Failure mode and prevention |
| `process` | Workflow execution pattern |
| `tool-usage` | Tool-specific usage insight |
| `goal` | User or system objective constraint |
| `personality` | Operator interaction preference |
| `preference` | Stable choice preference |
| `env-context` | Situational or environment constraint |

For post-task reflection: problems faced and workarounds are `domain-knowledge`, discovered patterns are
`behaviour`, time sinks and quality gaps are `env-context`.

## Configuration

The store is the project's folder in the shared data repository (`<folder>/memory`), Global memory beside it at the
repository's `memory`, read and never written; Delivery's steps name both with `OWLBEAR_MEMORY_DIR` and
`OWLBEAR_MEMORY_GLOBAL_DIR`. A workspace no folder claims keeps `.owlbear/memory`. Active agent identities are
discovered from workspace agent locations.

## Errors

Every tool raises `ToolError`, surfaced as an MCP error, for an unknown `entry_id`, a wrong source state, a read of
a soft-deleted entry, a validation failure (confidence out of range, empty title, invalid category), a stale
`revision`, or a busy lock. Responses carry a `hint` with what happened and the next step.
