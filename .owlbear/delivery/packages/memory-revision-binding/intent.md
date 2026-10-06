# Memory Revision Binding

> Status: candidate Design authority; admission gates pending

## Problem

Memory decisions and feedback are applied to whatever entry bytes are current at write time, not to the bytes the deciding agent or human actually read (observed on `dev` 48f263325):

- MCP `approve_memory`, `curate_memory`, and `delete_memory` take only `entry_id`. `tools.py` re-reads the entry and forwards its *current* `updated_at` as the engine OCC token, so the engine check can never fail for a stale caller (GitHub #249; audit probe P05 approved changed content).
- `assess_memories` re-reads the current entry and forwards its current `updated_at`; feedback recalled against an earlier revision is applied to the replacement (#244; P15 moved a corrected, re-approved entry to `disputed`).
- Ordinary assessments are not idempotent: an uncertain response retried with the same task increments counters twice (#244; P04).
- `record_factually_wrong` stores only one `contested_by_task`; a second challenge moves the entry to `disputed` and clears that field, losing the first reporter (#244; P13). The MCP `read_memory`/`list_memories` projection omits challenge data entirely.

## Actors

- `memory-curator` agent: curates and deletes via MCP (trusted but fallible).
- `builder` agent: the only assessment consumer; recalls, then submits `assess_memories` (trusted but fallible).
- Human operator: approves via the `memory-audit` prompt (MCP `approve_memory`) and resolves/edits via Cockpit (trusted).

## Product Promise

- A curator or reviewer approve/curate/delete applies only to the revision they inspected; an intervening content or scope change produces a clear concurrency refusal telling them to re-read, and leaves the entry unchanged.
- A normal read-then-mutate sequence still succeeds.
- Feedback applies only to the revision that was evaluated; feedback naming a replaced revision does not change the replacement's state or counters.
- Retrying the same assessment (same task, entry, revision) does not double-count and returns a deterministic already-applied result.
- A disputed entry retains both reporting task IDs and the revision each challenged, visible in MCP and Cockpit review projections until it is resolved; deletion keeps them on the tombstone.
- Per-entry partial batch results in `assess_memories` remain.
- Tool schemas, examples, and agent-facing handbooks match the registered contract.

## Normal Workflows

1. Curation: `memory-curator` calls `list_memories`/`read_memory`, receives `revision`, then calls `curate_memory` or `delete_memory` with that `revision`. Human approval through `memory-audit` reads the entry, shows it, and calls `approve_memory` with the shown `revision`.
2. Feedback: Builder calls `recall_memory`, whose blocks carry `Entry ID` and `Revision`; at the end of substantive work it submits one `assess_memories` batch with `{entry_id, revision, bucket}` per recalled entry.
3. Dispute: two different tasks report `factually_wrong` for the current revision; the operator opens Cockpit (or `read_memory`) and sees both task IDs and challenged revisions, then resolves, edits, or deletes.

## Operating Context (inferred)

- Actors and trust: agents above are trusted but fallible; human operator trusted. Single local laptop.
- Exposure: none added; MCP stdio and Cockpit on `127.0.0.1`. Memory content is agent-authored.
- Stakes: wrong or misattributed guidance propagating into future agent work; local and reversible through Git history; no secrets or money.
- Guarded: stale-read decisions, stale-revision feedback, duplicate retries, lost dispute evidence.
- Not guarded: forged revision tokens or task IDs (callers are trusted; the revision is a change detector, not a security token); cross-process read-check-write serialization (owned by `memory-writer-safety`, #238/#241/#240); general event sourcing or audit log.

## Scope

- Memory engine revision semantics for approve/edit/delete/assessment/challenge and agent lifecycle writes (`serve/memory`).
- Memory MCP tool signatures, schemas, projections, recall output (`serve/memory-mcp`).
- Cockpit memory response projection of revision and challenge evidence (backend model and Memory tab display) and its maintained e2e consumers (`prove-memory-lifecycle-mcp.py`, `memory-lifecycle-assembled.spec.ts`, `memory-conflict.spec.ts`, and the lifecycle and purge stack fixtures).
- Agent-facing contracts: `share/skills/h-mcp-memory`, `h-memory-structure`, `w-mem-curation`, `share/prompts/memory-audit.prompt.md`, `share/agents/memory-curator.agent.md`, `serve/memory/README.md`, `serve/memory-mcp/README.md`.
- Focused tests, including stale-revision refusal exercised through the live MCP server (`mcp.Client`), not only the engine, and the existing workspace tests that call the changed tools, engine methods or fields.

## Accepted Exclusions

- Cross-process lock, Git batch snapshot validation, cache freshness and duplicate-ID cleanup: owned by `memory-writer-safety` (#238, #241, #240).
- Cockpit's existing `expected_updated_at` request-token contract is unchanged (#249).
- No general transaction system, event sourcing, full audit log, new reviewer agent, or new human approval UI.
- Contested recall marker already exists on `dev`; no retrieval-ranking change.
- Attributing feedback to an older revision (D1 consequence: stale feedback is refused instead).
- Duplicate detection beyond the bounded receipt window (D2).
- Challenge evidence after resolution is kept only in Git history, not in projections (D3).

## Preserved Behavior

- Lifecycle state machine transitions and their guards; `disputed` still refuses further challenges.
- Cockpit approve/resolve/edit/delete with `expected_updated_at`.
- Per-entry success/failure results for valid assessment batches; malformed batches rejected whole.
- Recall selection pools and ordering.
- Assessment counters persist across content edits (documented, not reset).

## Decisions

- D1 (user-confirmed 2026-10-06): Option A, computed content hash. `revision` is a short SHA-256 over the curator-editable fields (title, content, categories, confidence, scope_agents); it is not persisted; counters, state, receipts, challenges, and timestamps do not change it. Recall, `read_memory`, and `list_memories` emit it; recall gains one `Revision:` line per block. Rejected: B persisted integer (migration, misses hand edits); C reuse `updated_at` (counter bumps cause false conflicts and Builder collisions).
- D1 consequence: feedback naming a replaced revision is refused per entry (`success: false`, concurrency error naming the current revision); it is not attributed.
- D2 (user-confirmed 2026-10-06): Option A, bounded receipt window in the entry file. Receipts `{task_id, revision, bucket}` for the current revision only, most recent 20; one assessment per task/entry/revision regardless of bucket (first answer wins); a repeat returns `success: true, already_applied: true` with the recorded bucket. Rejected: B separate ledger (new store overlapping `memory-writer-safety`); C unbounded set (breaks 8 KB cap).
- D2 refinement (designer-recorded after challenge 2026-10-06): the current-revision rule applies on every write path, including agent rename and removal; the newest receipt is always kept, older receipts are evicted oldest-first only to stay within the 8192-byte cap, and an assessment whose receipt cannot be stored is refused without effect; MCP `task_id` is 1-128 printable ASCII characters without whitespace.
- D3 (user-confirmed 2026-10-06): Option A, per-cycle challenge list `challenges: [{task_id, revision, recorded_at}]` replacing `contested_by_task`; at most two records; kept on delete and on Cockpit edits; cleared by `resolve`. Rejected: B persistent history across resolutions.
- Consumer scope (designer-recorded after re-challenge 2026-10-07): maintained Cockpit e2e and workspace test consumers of the changed MCP arguments, engine signatures and challenge fields are adapted in the outcome that changes them and proven by that outcome's focused checks and existing Playwright projects; no new e2e project is added.
- Sequencing (designer-recorded from the user's request "after or alongside without overlapping"): no Delivery dependency on `memory-writer-safety`. This change adds no lock and changes no Git batching or cache code; the revision check runs inside the engine's existing critical section. Whichever change lands second rebases on shared `engine.py` methods.

## Success

A curator reads an entry, another writer changes its content, and the curator's MCP approve/curate/delete with the old revision is refused without effect; a Builder's feedback for a replaced revision is refused without effect; a retried assessment counts once; two factual challenges leave both task IDs and challenged revisions visible in MCP and Cockpit.

## Technically Done But Wrong

- MCP tools accept a revision argument but still forward the current entry's token.
- Stale-revision refusal proven only against the engine, not the registered MCP tools.
- Any assessment counter bump or state transition changing the revision or invalidating an unchanged content review or a concurrent Builder's feedback.
- Duplicate protection that silently drops a genuinely different task's feedback.
- Second challenge still overwriting or clearing the first.
- Cockpit token contract changed or Cockpit tests rewritten to a new token.
- Adding a lock or touching Git batching (sibling change scope).
- Receipts growing until a write fails the 8 KB file cap, or an assessment counted without its receipt being stored.
- Old-revision receipts surviving a scope change made by agent rename or removal.
- Focused suites green while the maintained Cockpit memory e2e projects or other existing workspace tests fail on the old MCP arguments, engine signatures or the removed contested field.

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: "GitHub issue 249 requested outcome"
statement: MCP approve_memory, curate_memory and delete_memory apply only when the caller-supplied revision equals the entry's current revision; otherwise they refuse with a concurrency error that names expected and current revision and tells the caller to re-read before retrying, and the entry is unchanged.
```

```yaml target-contract
kind: commitment
id: COM-002
class: dealbreaker
provenance: "GitHub issue 244 requested outcome"
statement: Each assessment item names the revision that was evaluated; an item whose revision is not the entry's current revision is refused for that entry without changing its state, counters, score, receipts or challenges, while other items in the batch are processed.
```

```yaml target-contract
kind: commitment
id: COM-003
class: dealbreaker
provenance: "GitHub issue 244 requested outcome"
statement: A repeated assessment with the same task, entry and revision is not applied again and returns a deterministic already-applied result naming the recorded bucket; an assessment is never counted unless its receipt is stored with it.
```

```yaml target-contract
kind: commitment
id: COM-004
class: dealbreaker
provenance: "GitHub issue 244 requested outcome"
statement: Factual challenges retain every reporting task ID of the current dispute cycle and the revision each challenged; both are visible in the MCP read and list projections and the Cockpit memory projection until resolve, and remain on a deleted tombstone.
```

```yaml target-contract
kind: commitment
id: COM-005
class: agreed-path
provenance: "user decision D1 (2026-10-06)"
statement: The revision is a computed, unpersisted SHA-256-derived lowercase hex token over title, content, categories, confidence and scope_agents; state, counters, receipts, challenges and timestamps do not change it; recall_memory, read_memory and list_memories emit it, recall as one Revision line per block.
```

```yaml target-contract
kind: commitment
id: COM-006
class: agreed-path
provenance: "user decision D2 (2026-10-06) with designer refinement after challenge"
statement: Assessment receipts are stored in the entry file for the current revision only on every write path, at most the 20 most recent, evicting oldest first when needed to stay within the 8192-byte file cap while always keeping the newest; one assessment counts per task, entry and revision regardless of bucket, and the first recorded bucket wins.
```

```yaml target-contract
kind: commitment
id: COM-007
class: agreed-path
provenance: "user decision D3 (2026-10-06)"
statement: Challenge evidence is a per-cycle list of task ID, revision and recorded time that replaces contested_by_task, holds at most two records, survives Cockpit edits and deletion, and is cleared by resolve.
```

```yaml target-contract
kind: commitment
id: COM-008
class: protected-request
provenance: "GitHub issues 249 and 244 exclusions; user sequencing request for memory-writer-safety"
statement: Cockpit's expected_updated_at request contract, the lifecycle state machine, recall selection and ordering, per-entry partial batch results with whole-batch rejection of malformed input, and assessment counters persisting across edits are unchanged; this change adds no cross-process lock and changes no Git batching, cache freshness or duplicate-ID handling.
```

```yaml target-contract
kind: commitment
id: COM-009
class: protected-request
provenance: "user request (2026-10-06)"
statement: Stale-revision refusal for curator mutations and assessments is proven through the registered MCP tools on a live in-process server, not only through the engine.
```

```yaml target-contract
kind: commitment
id: COM-010
class: implementation-discretion
provenance: "designer"
statement: Exact field names, revision length, error wording, engine method signatures, and where the shared current-revision receipt step lives are implementation choices within the stated contract.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Curator mutations bound to the inspected revision
promise: A curator or human reviewer approving, curating or deleting a memory through MCP acts only on the revision they read; a changed entry refuses with a re-read instruction and stays unchanged.
dependencies: []
commitments: [COM-001, COM-005, COM-008, COM-009, COM-010]
acceptance:
  - "AC-001: Given an entry, read_memory and list_memories return a revision of 16 lowercase hex characters that is identical across reads and engine reloads while title, content, categories, confidence and scope_agents are unchanged, is unchanged by approve and assessment counter or timestamp changes, and differs after any of those five fields changes."
  - "AC-002: Given an entry read through the live MCP server via mcp.Client and then changed in content through a second MemoryEngine on the same directory, approve_memory, curate_memory and delete_memory each called with the old revision return a tool error stating the entry changed since it was read, naming the expected and current revision and instructing to re-read before retrying, and the entry file bytes are unchanged."
  - "AC-003: Given a revision freshly read through the live MCP server, approve_memory on a curated entry, curate_memory promoting a pending entry with scope and editing an approved entry, and delete_memory hard-deleting a pending entry and soft-deleting a curated entry all succeed."
  - "AC-004: Through the live MCP server, approve_memory, curate_memory and delete_memory called without revision or with a revision that is not 16 lowercase hex characters return an error and leave the entry unchanged."
  - "AC-005: Cockpit approve, resolve, edit and delete routes keep their expected_updated_at request schemas, and the existing OCC tests in tests/test_cockpit_memory_routes.py pass."
  - "AC-006: share/skills/h-mcp-memory/SKILL.md, share/skills/w-mem-curation/SKILL.md, share/prompts/memory-audit.prompt.md, share/agents/memory-curator.agent.md and serve/memory-mcp/README.md document revision as a required argument of approve_memory, curate_memory and delete_memory, where it comes from, the fields it covers and the stale refusal, with examples matching the registered schema; serve/memory/README.md documents that Cockpit uses updated_at while MCP uses revision against the same engine."
  - "AC-007: uv run pytest serve/memory-mcp/tests tests/test_memory_engine.py tests/test_memory_state_machine.py tests/test_memory_agent_identity.py tests/test_memory_scope_invariants.py tests/test_cockpit_memory_routes.py tests/test_agent_ecosystem_validation.py and uv run ruff check on the changed Python files pass."
  - "AC-024: serve/cockpit/web/e2e/support/prove-memory-lifecycle-mcp.py reads each exceptional-state entry's revision through read_memory over MCP stdio and passes it to curate_memory, still requiring an error naming the state and unchanged fixture bytes, and npm run test:e2e:memory-lifecycle in serve/cockpit/web passes."
```

```yaml target-contract
kind: outcome
id: OUT-002
title: Revision-bound, retry-safe assessments
promise: Builder feedback applies only to the memory revision it recalled, and retrying an uncertain assessment never double-counts.
dependencies: [OUT-001]
commitments: [COM-002, COM-003, COM-005, COM-006, COM-008, COM-009, COM-010]
acceptance:
  - "AC-008: recall_memory output places a Revision line with the entry's current revision directly after each Entry ID line, and the selected entries and their order are unchanged from the pre-change selection for the same store."
  - "AC-009: Given an entry recalled through the live MCP server and then edited and approved through a second MemoryEngine, assess_memories with the recalled revision returns success false for that item with an error stating the entry changed since recall and naming the current revision; its state, counters, score and receipts are unchanged, and another valid item in the same batch is applied."
  - "AC-010: Through the live MCP server, submitting the same task_id, entry and revision first with outstanding and then with unremarkable increments outstanding_count exactly once, and the second result is success true with already_applied true and recorded bucket outstanding; a different task_id on the same revision is applied normally."
  - "AC-011: Through the live MCP server, an assessment batch containing an item without revision, with a revision that is not 16 lowercase hex characters, or with an unknown key, or a task_id that is empty, longer than 128 characters, or contains whitespace or non-ASCII characters, is rejected as a whole and no entry changes."
  - "AC-012: Receipts survive a new MemoryEngine on the same directory and duplicate detection still returns already_applied; at most 20 receipts are kept and only for the current revision; an entry with 1024 ASCII content characters, a 120-character ASCII title and 20 receipts with 128-character task IDs serializes within 8192 bytes; when an entry is too large to keep all receipts, oldest receipts are evicted and the newest is kept; when the newest receipt cannot be stored, the assessment returns success false and counters, state and receipts are unchanged."
  - "AC-013: Given an assessment that moved an entry to stale, resubmitting it with the same task, entry and revision returns already_applied instead of a transition error."
  - "AC-014: share/skills/h-mcp-memory/SKILL.md, share/skills/h-memory-structure/SKILL.md, serve/memory/README.md and serve/memory-mcp/README.md document the item shape entry_id, revision, bucket and the task_id format; the recall Revision line; the already_applied result, receipt window and capacity limits; that stale feedback is refused and must not be re-submitted against unseen content; and that counters persist across content edits while receipts do not."
  - "AC-015: uv run pytest serve/memory-mcp/tests tests/test_assess_memories.py tests/test_recall_memory.py tests/test_memory_voting_integration.py tests/test_confirmation_cycle.py tests/test_memory_agent_identity.py tests/test_memory_engine.py tests/test_agent_ecosystem_validation.py and uv run ruff check on the changed Python files pass."
  - "AC-023: Given an entry with receipts, edit, rename_agent_memories and delete_agent_memories changes that alter its scope_agents or content leave no stored receipt whose revision differs from the entry's new revision, while approve, resolve, delete and stale transitions that leave the revision unchanged keep its receipts."
```

```yaml target-contract
kind: outcome
id: OUT-003
title: Dispute evidence retained and visible
promise: When two tasks report a memory as factually wrong, the operator sees both reporters and the revision each challenged in MCP and Cockpit before resolving or deleting it.
dependencies: [OUT-002]
commitments: [COM-004, COM-007, COM-008, COM-009, COM-010]
acceptance:
  - "AC-016: Through the live MCP server, factually_wrong from task A and then task B on the current revision leaves the entry disputed, and read_memory and list_memories return challenges listing task A then task B, each with its revision and recorded time."
  - "AC-017: The same task reporting factually_wrong twice for the same revision returns already_applied and the entry stays contested with one challenge; resubmitting task B's challenge after the entry became disputed returns already_applied instead of a transition error."
  - "AC-018: A Cockpit edit of a contested entry keeps its challenges with the original revision while the entry revision changes; deleting a disputed entry keeps its challenges on the tombstone; Cockpit resolve returns the entry to approved with no challenges."
  - "AC-019: Challenges survive a new MemoryEngine on the same directory; a stored file with contested_by_task null loads with no challenges and is written back without that key; a stored file with a non-null contested_by_task loads as one challenge with that task ID and the entry's computed revision; contested_by_task no longer appears in the memory model, storage serialization, MCP projections or Cockpit API."
  - "AC-020: A contested recall block shows the contested state marker and one Challenge task line per recorded challenge."
  - "AC-021: Cockpit GET /api/memories returns revision and challenges for each entry, and the Memory tab shows each challenge's task ID, revision and recorded time for contested and disputed entries in place of the single Contested task field, covered by MemoryTab Vitest tests including a two-challenge entry."
  - "AC-022: uv run pytest serve/memory-mcp/tests tests/test_confirmation_cycle.py tests/test_memory_voting_integration.py tests/test_memory_agent_identity.py tests/test_memory_state_machine.py tests/test_recall_memory.py tests/test_cockpit_memory_routes.py tests/test_memory_primitives.py, uv run ruff check on the changed Python files, and in serve/cockpit/web npx vitest run src/pages/MemoryTab, npx tsc -b and Biome check scoped to the changed files pass."
  - "AC-025: The memory lifecycle and purge stack fixtures and memory-conflict.spec.ts use challenges instead of contested_by_task; memory-lifecycle-assembled.spec.ts asserts the contested entry's challenge task ID through the challenge list instead of the Contested task label; npm run test:e2e:memory-lifecycle and npm run test:e2e:memory-purge in serve/cockpit/web pass."
```
