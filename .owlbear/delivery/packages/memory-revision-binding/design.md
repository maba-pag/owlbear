# Memory Revision Binding Design

> Status: candidate architecture; admission gates pending

## Current Ownership (observed, dev 48f263325; memory sources unchanged at 4990469c1)

- `serve/memory/src/owlbear_memory/engine.py`: `approve`, `resolve`, `edit`, `delete` require `expected_updated_at`; `record_assessment` and `record_factually_wrong` accept optional `expected_updated_at`; `_validate_occ` compares `updated_at` and raises `ConcurrencyError`. Every mutation, including counter increments, sets a new `updated_at`. All run under an in-process `RLock` only. `rename_agent` and `delete_agent` rewrite `scope_agents` (and `source_agent`) by copying existing metadata and writing through `_write_agent_lifecycle_changes`.
- `serve/memory/src/owlbear_memory/models.py`: `MemoryEntry` (extra=forbid) with `contested_by_task: str | None`; `title` has no length limit.
- `serve/memory/src/owlbear_memory/storage.py`: `write_entry` re-validates the entry, serializes explicit UTF-8 frontmatter including `contested_by_task`, enforces a strict round-trip and an 8192-byte file cap, and replaces atomically.
- `serve/memory-mcp/src/owlbear_memory_mcp/tools.py`: `_approve_entry`, `_update_entry`, `_delete_entry`, `assess_memories` each load the current entry and forward `current.updated_at`; `_entry_to_dict` omits `contested_by_task`; `_recall_block` emits title, `Entry ID`, contested marker with `Challenge task`, body.
- `serve/memory-mcp/src/owlbear_memory_mcp/server.py`: tool registration; `approve_memory(entry_id)`, `curate_memory(entry_id, ...)`, `delete_memory(entry_id)`, `assess_memories(assessments: list[dict[str,str]], task_id)`. The MCP SDK validates registered argument annotations before invocation.
- `serve/cockpit/src/owlbear_cockpit/routes/memory.py`: `expected_updated_at` OCC on approve/resolve/edit/delete; `MemoryEntryResponse` built from `entry.model_dump()` including `contested_by_task`; web `src/api/memories.ts` type and `src/pages/MemoryTab.tsx` "Contested task" field; e2e support stacks write `contested_by_task` frontmatter.
- Maintained Cockpit e2e consumers (re-challenge 2026-10-07): `e2e/support/prove-memory-lifecycle-mcp.py` calls `curate_memory` over MCP stdio with only `entry_id` and requires an error naming each exceptional state; `e2e/memory-lifecycle-assembled.spec.ts` locates the `Contested task` label; `e2e/support/start-memory-lifecycle-stack.mjs`, `start-memory-purge-stack.mjs` and `e2e/memory-conflict.spec.ts` write or mock `contested_by_task`. They run through `npm run test:e2e:memory-lifecycle`, `npm run test:e2e:memory-purge` and the compat project.
- Maintained Python test consumers (re-challenge 2026-10-07): `tests/test_memory_agent_identity.py` and `tests/test_memory_scope_invariants.py` call `curate_memory` without a revision, and `test_memory_agent_identity.py` passes a positional timestamp to `record_factually_wrong`; `tests/test_confirmation_cycle.py` and `tests/test_memory_voting_integration.py` call `record_factually_wrong`/`record_assessment` and assert `contested_by_task`; `tests/test_memory_state_machine.py`, `tests/test_recall_memory.py` and `tests/test_cockpit_memory_routes.py` reference `contested_by_task`. Each is adapted in the outcome whose signature or field change breaks it and is named in that outcome's focused proof.
- Live MCP boundary tests exist: `serve/memory-mcp/tests/test_server.py` uses `mcp.Client(memory_mcp)`. A second engine's atomic replace changes the directory mtime the MCP engine's cache checks, so sequential cross-engine changes are visible without sibling cache work (challenger-confirmed).
- Live store: no entry is currently contested or disputed and every `contested_by_task` is null.

## Revision Token (D1)

- `MemoryEntry.revision` is a read-only Python `@property` (not a pydantic field, so it is never dumped or stored): first 16 lowercase hex characters of SHA-256 over `json.dumps({title, content, categories, confidence, scope_agents}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`. List order is significant.
- Engine `_validate_revision(entry, expected_revision)` raises `ConcurrencyError` naming the entry, expected and current revision.
- `approve`, `edit`, `delete` keep the positional `expected_updated_at` for Cockpit and gain keyword `expected_revision`; exactly one token must be supplied, otherwise `ValidationError`. `resolve` stays Cockpit-only with `expected_updated_at`.

## Assessments And Receipts (D2)

- New models: `AssessmentReceipt{task_id, revision, bucket}` and `AssessmentResult{entry, already_applied, recorded_bucket}`.
- `MemoryEntry.assessment_receipts: list[AssessmentReceipt]` (default empty) persisted in frontmatter.
- `record_assessment(entry_id, bucket, *, task_id, expected_revision)` and `record_factually_wrong(entry_id, task_id, *, expected_revision)` both return `AssessmentResult`. Order inside the lock: load, revision check, receipt/challenge lookup for `(task_id, revision)` returning `already_applied` with the recorded bucket, then existing state guards and transitions, then append the receipt and write.
- Current-revision invariant on every write path: one shared step applied before serialization (covering `edit`, assessments, challenges, `approve`, `resolve`, `delete`, `try_stale_transition`, `rename_agent`, and `delete_agent`) drops receipts whose revision differs from the entry's current revision and keeps at most the 20 most recent.
- Capacity rule: if the serialized entry would exceed 8192 bytes, evict the oldest receipts first. The newest receipt is never evicted; if the entry cannot be written with it, the assessment is refused with an error and nothing is applied (counters, state, and receipts unchanged).
- Task ID contract at the MCP boundary: 1-128 printable ASCII characters without whitespace, so 20 receipts occupy at most about 4 KB and fit beside maximum-length ASCII content and a typical title. Probe `.owlbear/scratch/memory_receipt_budget.py` (re-run 2026-10-07) serializes 20 such receipts, two challenges, a 120-character title and 1024 content characters at 6923 bytes.
- Counters are not reset by edits (preserved behavior, documented).

## Challenge Evidence (D3)

- `ChallengeRecord{task_id, revision, recorded_at}`; `MemoryEntry.challenges: list[ChallengeRecord]` (max 2) replaces `contested_by_task`.
- `record_factually_wrong`: approved/curated -> contested with one record; contested and a new task -> disputed with the second record appended; a task already in `challenges` -> `already_applied` (lookup precedes the disputed-state guard).
- `resolve` clears `challenges`; `edit` and `delete` keep them.
- Load migration (model `before` validator, alongside the existing legacy `approval_state` drop): `contested_by_task: null` is dropped; a non-null value becomes one `ChallengeRecord` with that task, the entry's computed revision, and `recorded_at = updated_at`. Storage no longer serializes the key, so the next write removes it.

## MCP Interface

- `server.py`: `approve_memory(entry_id, revision)`, `curate_memory(entry_id, revision, ...)`, `delete_memory(entry_id, revision)` with `revision: Annotated[str, Field(pattern=r"^[0-9a-f]{16}$")]` required. `assess_memories(assessments: list[AssessmentItem], task_id: Annotated[str, Field(pattern=r"^[\x21-\x7e]{1,128}$")])` where `AssessmentItem` is a strict model `{entry_id, revision (same 16-hex pattern), bucket: Literal[...]}` with extra keys forbidden.
- `tools.py`: forward the caller's revision; never substitute the current entry's token. `ConcurrencyError` becomes `ToolError` with the re-read instruction. Per-item results add `already_applied` and `recorded_bucket` on success; stale items return `success: false` with an error stating the entry changed since recall and that the feedback was not applied.
- Projections: `_entry_to_dict` adds `revision` and `challenges`; list metadata includes both. Receipts are not projected.
- Recall: `Revision: \`<revision>\`` after `Entry ID`; contested blocks list one `Challenge task:` line per record.

## Cockpit

- `MemoryEntryResponse` replaces `contested_by_task` with `challenges` and adds `revision`; `_to_response` sets `revision` explicitly from the property because `model_dump()` does not include it. Request models unchanged.
- Web: `memories.ts` type update; `MemoryTab.tsx` renders a challenge list (task, revision, recorded time) for contested and disputed entries; e2e support fixtures switch to `challenges`.
- E2E consumers: OUT-001 changes `prove-memory-lifecycle-mcp.py` to `read_memory` each exceptional entry over the same stdio session and pass its `revision` to `curate_memory`; the state guard still rejects with the state name, and the snapshot check still requires unchanged bytes. OUT-003 switches the lifecycle and purge stack fixtures and the `memory-conflict.spec.ts` mock to `challenges`, and the assembled lifecycle spec asserts the contested task ID inside the new challenge list.

## Sequencing With memory-writer-safety

No Delivery dependency. This change adds no lock and leaves `git.py`, `MtimeScanCache`, and duplicate handling untouched. Its checks run inside the engine's current `RLock`; when `memory-writer-safety` introduces cross-process serialization, the same checks run inside that critical section unchanged. Both edit the same engine mutation methods, so the later change rebases.

## Alternatives And Tradeoffs

- Recorded under D1-D3 in intent. A single `updated_at` token was rejected because counter writes would invalidate unchanged content reviews and concurrent Builders.

## Known Weaknesses

- Until `memory-writer-safety` lands, two processes can still interleave between check and write; this change makes stale callers detectable, not the store serializable.
- Receipt window is bounded: a duplicate arriving after 20 other tasks assessed the same revision, or after capacity eviction on an unusually large entry, is applied again. Only the newest receipt is guaranteed.
- An entry already too close to the 8192-byte cap to hold one receipt refuses assessments until a curator shortens it.
- The 64-bit truncated hash is a change detector, not a security token; an edit that restores identical bytes yields the same revision (intended).
- Resolved challenge evidence remains only in Git history.
- Legacy non-null `contested_by_task` migration assigns the current revision, which may differ from the originally challenged one if it was edited in between; no such entry exists in the live store.

## Proof Approach

- Live MCP tests in `serve/memory-mcp/tests/test_server.py` via `mcp.Client(memory_mcp)` with a temporary `.owlbear/memory`, changing entries through a second `MemoryEngine` between read and mutation.
- Tool-level and engine tests in `serve/memory-mcp/tests/test_tools.py`, `tests/test_assess_memories.py`, `tests/test_confirmation_cycle.py`, `tests/test_memory_voting_integration.py` (deterministic recall fixture for AC-008), `tests/test_recall_memory.py`, `tests/test_memory_engine.py`, `tests/test_memory_state_machine.py`, `tests/test_memory_primitives.py`, `tests/test_memory_agent_identity.py`, `tests/test_memory_scope_invariants.py`, `tests/test_cockpit_memory_routes.py`.
- Cockpit web: `MemoryTab` Vitest, `npx tsc -b`, scoped Biome.
- Assembled Cockpit e2e: `npm run test:e2e:memory-lifecycle` (OUT-001 and OUT-003) and `npm run test:e2e:memory-purge` (OUT-003) in `serve/cockpit/web`.
