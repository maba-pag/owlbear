# Memory System End-to-End Audit

> **Owning task:** User-requested full-system audit; no Delivery change admitted.
> **Date:** 2026-09-06
> **Question:** Can OwlBear capture, preserve, retrieve, improve, govern, and retire useful institutional memory reliably, including when operations fail?
> **Status:** Complete, with verification limits stated below. Findings are proposals for later planning, not implementation authority.

**Verdict:** OwlBear is a usable local institutional-memory system with a sound separation of capture, curation, human approval, and retrieval. It has concrete concurrency, review-revision, persistence-policy, and UI recovery defects; it has not demonstrated a reliably closed automatic learning loop. Those are different conclusions: the system is neither fundamentally broken nor proven failure-tolerant. Keep the engine/MCP/Cockpit separation and fix the specific defects before adding agents, storage machinery, or more review ceremony.

## 1. Context and Question

This report audits the transport-free memory engine, filesystem persistence, MCP tools, agent and skill loading, Cockpit API and UI, tests, and operational recovery. Implementation files and live memories remain unchanged. Findings are inputs for later decisions and action plans, not admitted work.

The apparent product intent is to turn specific agent lessons into durable institutional guidance: producers save pending candidates; a curator validates, deduplicates, and scopes them; users approve higher-trust entries; agents recall relevant guidance and assess its usefulness; exceptional states drive review or retirement. The audit tests this interpretation against current sources rather than treating historical design notes as current authority.

Reliability means more than a successful tool call: acknowledged writes should remain readable, competing writers should not silently lose changes, human approval should bind the reviewed content, and failures should be visible. Retry-safe feedback and eventual automatic curation are useful capabilities, but they are not promises the current interfaces universally make. Priority accounts for operating conditions and recovery cost, not only whether a synthetic probe can demonstrate a behavior.

### Method and Evidence Labels

- `Observed`: directly inspected current source or executable result.
- `Documented`: an explicit intended contract, not independent runtime proof.
- `Inferred`: a consequence or recommendation supported by evidence, with limits stated.
- Confidence is high, medium, or low. Priority separates concrete defects from optional product improvements.
- All executable probes must use isolated temporary data, not the workspace's live memory store.

### Scope Boundary

This is research, not an implementation or live-memory curation session. Existing unrelated work is outside its ownership. The review assesses a laptop-resident, human-operated system; multi-tenant authorization, continuous availability, and database-grade power-loss recovery are not assumed product requirements.

## 2. Sources Studied

| Source | Evidence | Relevance and limits |
| --- | --- | --- |
| [Memory package](../../serve/memory/README.md) | Documented | Lifecycle, persistence, scoring, OCC, and package intent. |
| [Engine](../../serve/memory/src/owlbear_memory/engine.py), [storage](../../serve/memory/src/owlbear_memory/storage.py), [models](../../serve/memory/src/owlbear_memory/models.py) | Observed, executed | Full source inspection; synthetic round-trip, interleaving, lifecycle, and cache probes. |
| [MCP tools](../../serve/memory-mcp/src/owlbear_memory_mcp/tools.py), [server](../../serve/memory-mcp/src/owlbear_memory_mcp/server.py), [Git helper](../../serve/memory-mcp/src/owlbear_memory_mcp/git.py) | Observed, executed | Contracts, projections, recall, feedback, batching, and persistence custody. |
| [Memory API](../../serve/cockpit/src/owlbear_cockpit/routes/memory.py), [Cockpit runtime](../../serve/cockpit/src/owlbear_cockpit/main.py) | Observed, tests | HTTP mutations, health, dependencies, error contracts, and startup isolation. |
| [Memory UI](../../serve/cockpit/web/src/pages/MemoryTab.tsx), [API client](../../serve/cockpit/web/src/api/memories.ts), [polling hook](../../serve/cockpit/web/src/hooks/usePollingFetch.ts), [workspace status](../../serve/cockpit/web/src/components/WorkspaceStatus.tsx) | Observed, browser | Full memory-page inspection; real Chromium with isolated API responses. |
| [Memory handbook](../../share/skills/h-mcp-memory/SKILL.md), [entry-quality handbook](../../share/skills/h-memory-structure/SKILL.md), [curation workflow](../../share/skills/w-mem-curation/SKILL.md) | Documented, compared | Entry quality, provenance, lifecycle, operation syntax, and recovery obligations. |
| [Curator](../../share/agents/memory-curator.agent.md), [builder](../../share/agents/builder.agent.md), [orchestrator](../../share/agents/orchestrator.agent.md), [review prompt](../../share/prompts/memory-audit.prompt.md) | Observed | Full bodies and immediate loading relationships; metadata map of all 13 shared roles. |
| [Orchestration](../../share/skills/w-orchestration/SKILL.md), [building](../../share/skills/w-packet-building/SKILL.md), [reviewer protocol](../../share/skills/r-challenger-protocol/SKILL.md) | Observed | Actual trigger and feedback ownership, including reviewer candidate return. |
| [Global governance](../../share/instructions/owlbear-system.instructions.md), [loading model](../../share/README.md), [wiring map](../../share/WIRING.md), [agent structure](../../share/skills/h-agent-structure/SKILL.md) | Documented, validated | Authority, tool boundaries, loading, and context-cost expectations. |
| [Original OCC research](memory-engine-state-machine-occ.md) | Historical | Explains the original caching decision; not proof of current reliability. Other memory-topic research was inventoried, not all reread. |
| [Git commit contract](https://git-scm.com/docs/git-commit#_description) | External primary source | Explicit path arguments commit current worktree content, not an immutable earlier index snapshot. |
| [SQLite atomic commit](https://sqlite.org/atomiccommit.html) | External primary source | Transaction, locking, recovery, and crash-test comparison; not a recommendation to migrate automatically. |
| [OWASP prompt-injection guidance](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) | External guidance | Persistent poisoning threat model and separation of retrieved data from authority; not evidence of an actual attack here. |

Inspected source revision: `ee39f58d235e099fcfe6c340c61b73c3076410eb`. Claims are grounded in the cited implementation and focused checks, not in historical design notes or reviewer agreement alone.

## 3. Analysis

### Executable Evidence

Production engine and MCP implementations were exercised with synthetic entries in disposable directories under `.owlbear/scratch/`. Git-policy probes used temporary repositories, not the workspace's history. Browser probes used the actual frontend with synthetic API responses. Probe results establish behavior under stated conditions, not incident frequency or priority by themselves.

| Probe | Observed result | Interpretation |
| --- | --- | --- |
| P01 | Saving a 9,000-character title succeeded; the serialized file exceeded 8,192 bytes; a fresh read returned zero entries and one parse error. | A genuine boundary-validation defect using abnormally large metadata, not evidence that ordinary short entries fail. |
| P02 | Engine B edited content after engine A's OCC check and before A's write; both returned success, but A overwrote B's content. | Lost updates require no clock collision. Controlled two-instance interleaving establishes the compare/write race. |
| P03 | An in-place file edit left directory mtime unchanged; cached reads returned old content until `load()`. | This is missing file-change invalidation, not a claimed one-second filesystem timestamp limitation. Atomic replacement writes do change directory membership. |
| P04 | Submitting the same task/entry `outstanding` assessment twice incremented its counter to two. | Counter feedback is replayable; `task_id` is not an idempotency key for ordinary assessments. |
| P05 | Content changed after `read_memory`; later `approve_memory(entry_id)` approved the changed content. | MCP checks a fresh server-side token, not the revision the human reviewed. |
| P06 | A contested entry's content appeared in recall with no state warning; MCP full read also omitted `contested_by_task`. | Trust and challenge evidence are lost at the transport projection. |
| P07 | An unknown producer's recall instructed it that it was read-only and must not write memories. | Recall derives permission-like guidance from stored-name recognition, conflicting with open pending-candidate intake. |
| P08 | An approved entry was committed in a temporary Git repository, its sole audience retired through `delete_agent`, and `commit_batch(session_type="curation")` rejected the physical deletion. | The supported lifecycle operation and supported Git deletion guard disagree. HEAD retains the original entry; this is a blocked checkpoint, not irreversible loss. |
| P09 | With five equally scored entries and `limit=4`, pool selection excluded the only approved entry when its UUID sorted last. | Demonstrates exploration-first selection, not by itself a violation of approved-first output ordering. Whether approval must also dominate admission is a policy question. |
| P10 | Chromium received HTTP 503 from `/api/memories` and rendered "No memory entries yet" without an error. | A failed request is misrepresented as successful-empty. No claim is made that live Cockpit specifically emits 503 routinely. |
| P11 | After an edit received Cockpit's `{code, message}` HTTP 409 envelope, a second Save sent the identical stale `expected_updated_at`. | The draft survives, but refreshing the list does not reconcile its base revision. |
| P12 | Worktree content was changed immediately after `commit_batch` validation in a temporary repository; HEAD contained the replacement content. | Exact validation-to-commit snapshot race, requiring an overlapping write. The replacement in this probe was still schema-valid. |
| P13 | Two distinct factual challenges moved an entry to disputed and cleared `contested_by_task`. | Loss of challenge identity is directly observed; an entire event-history system is not the only possible correction. |
| P14 | `EditRequest` accepted `scope_agents=[""]`; `MemoryEngine.edit` promoted the pending entry to curated with that scope. | HTTP/domain validation admits an unusable audience. This was a request-model/engine probe, not a demonstration that the normal UI generates blank strings. |
| P15 | After recall, the entry was corrected and approved; two distinct tasks assessed the earlier content as factually wrong, moving the corrected content to disputed. | Feedback targets the latest entry rather than the evaluated revision. No retry or duplicate submission is necessary. |
| P16 | Two files shared an ID with different content/timestamps. Deleting and purging the selected newer entry exposed the older curated entry on a fresh load. | A supported cleanup operation can restore recall eligibility under pre-existing duplicate corruption. Health correctly detected the duplicate before mutation. |

The reported focused test runs comprise **217 and 111 passing backend/registered-test results**, a **255-pass backend validation run overlapping those scopes**, and **16 Vitest passes in 3 frontend files**. They are not summed into a count of unique tests. No executed maintained test failed; unsuccessful probe harness attempts are excluded from evidence. Agent, skill, and prompt validators exited zero, covering 13 shared roles and 19 prompts where those counts were reported.

### Operational Evidence

- Only `builder` has `assess_memories` in the 13-agent inventory. Its required workflow has no assessment step. The handbook says to include every recalled entry when assessing; this does not unambiguously require every role to assess after every task. Existing reviewer candidate returns concern new lessons, not evaluations of recalled entries.
- Periodic curation is implemented after session-local completed cycles 3, 13, 23, etc., and manual curation is available. Short sessions do not trigger it; no backlog-age or eventual-processing guarantee is specified. There is no evidence of actual starvation.
- Cockpit exposes storage-health details at `/health/memory` and in the workspace-status panel. MCP lacks an equivalent tool. The Memory page's narrower count display does not mean the system has no diagnostics.
- `/memories` redirects to `/memory`; the documented handoff works. Human-only approval is a role/tool-allowlist policy, not contradicted merely because the MCP server registers `approve_memory`.
- Desktop 1440 x 1000 and mobile 390 x 844 screenshots were inspected. The tested mobile page had no horizontal document overflow. Stacked filters used much of the first viewport; this is an ergonomic observation, not a demonstrated task failure or a full accessibility assessment.

Read-only live-store aggregates on 2026-09-05: **53 Markdown files, 53 valid IDs, zero unreadable files, zero duplicate IDs**. States: 15 approved, 6 curated, 3 pending, 1 stale, 28 deleted. Assessment totals: 16 outstanding, 16 unremarkable, 566 unused. This is evidence of actual past feedback and successful storage, not evidence of current complete role coverage, automatic curation timeliness, or learning effectiveness. No entry content is reproduced here.

### 3.1 Intended Loop and Actual Coverage

```text
Task experience -> pending candidate -> curator quality/scope -> curated guidance
                  -> human approval -> recall -> application -> feedback
                  -> dispute/revalidation or retirement -> durable history
```

Human approval means a higher-trust tier, not permission to enter recall: curated entries are already recalled. This is an explicit lifecycle choice, not a missing approval gate. The meaningful concern is whether consumers can distinguish challenged guidance and whether a human approves the exact content they reviewed.

| Capability | Present today | End-to-end assessment |
| --- | --- | --- |
| Capture | Eight save-capable producer/owner roles; unscoped pending intake; reviewer candidates returned through parents | Good separation. Non-idempotent intake is explicit; cold-start recall wrongly derives permission-like instructions from stored-name recognition. |
| Quality and scoping | Dedicated curator, meaning-based deduplication, evidence expectations, narrow scopes | Appropriate human-assisted policy. Pending uncertainty is not evidence of failed curation; actual backlog age and handling need measurement. |
| Approval | Human prompt and Cockpit controls; engine transition guards | Cockpit supplies the caller's revision token. MCP supplies its own fresh token, leaving a review-to-action gap. |
| Retrieval | Role/category filtering, 20-entry default, three selection pools | Useful bounded role guidance. No contested-state warning; task-sensitive retrieval is an optional extension, not inherently necessary for broadly applicable lessons. |
| Learning feedback | Four buckets, counters, score, two-task factual challenge, automatic non-use exclusion | Operational mechanisms exist. Old-revision feedback is a correctness gap; universal assessment coverage and effectiveness remain unproven. |
| Recovery | OCC errors, atomic single-file replacement, lenient reads, health details, Git history | Good ordinary-operation defenses. Independent writers and corrupted duplicate cleanup have specific gaps; transactional crash recovery is not established. |
| Operator work | Search/filter/edit/approve/resolve/delete/purge; shared health panel | Usable controls with real failure-display and stale-draft reconciliation defects. |
| Maintenance | Agent rename/retirement, tombstone purge, batch commit | Tools exist, but retirement and some purge/checkpoint sequences disagree on physical-deletion policy. |
| Evaluation | Extensive local contracts and assembled lifecycle/purge browser scenarios | Stronger evidence for mechanism correctness than for real task improvement or rare failure recovery. |

### 3.2 Ratings

Scale: 1 = missing; 2 = partial with consequential gaps; 3 = usable with limits; 4 = strong and meaningfully tested; 5 = demonstrated under the relevant fault and operational conditions. These are ordinal judgments, not measured reliability probabilities; do not average them into a certification.

| Dimension | Rating | Reason |
| --- | --- | --- |
| Responsibility boundaries | 4/5 | Transport-free engine reused by genuinely different adapters; existing separation earns its cost. |
| Persistence and concurrency | 2/5 | Single-instance behavior is usable, but independent writers can silently lose edits; write bounds and maintenance checkpoints also have confirmed gaps. |
| Retrieval trust and relevance | 3/5 | Role filtering and bounded selection work. Challenged guidance lacks a warning; exploration-first admission is a policy, not a demonstrated ranking defect. |
| Learning workflow | 3/5 | Capture through feedback and retirement are implemented and have historical use. This rates the human-assisted lifecycle; reliable autonomous coverage and improved task outcomes are not established. |
| Human governance | 3/5 | Consent, role separation, and Cockpit revision checks are sound. MCP review binding and dispute evidence need targeted improvements. |
| Cockpit operability | 3/5 | Functional controls and health; reproduced false-empty and stale-retry behavior. |
| Verification strategy | 3/5 | Substantial passing contract tests and targeted reproductions; limited cross-process, crash, and effectiveness evidence. Repeated test runs are not independent coverage. |

### 3.3 Ranked Finding Register

P1 = highest priority for a supported deployment with consequential silent loss. P2 = actionable correctness or operability work whose trigger or impact is narrower. P3 = lower-frequency hardening, diagnostics, or documentation. Priority is separate from confidence. Conditional findings require the stated condition; none is a claim of a live-store incident. Assessment coverage and curation cadence are discussed as policy questions, not ranked defects.

| ID | Priority | Finding | Evidence and confidence |
| --- | --- | --- | --- |
| F01 | P1, concurrent writers | Independent engines can silently lose successful writes. | Observed P02; high. |
| F02 | P2, intervening edit | MCP approval/edit/delete do not bind the revision the caller reviewed. | Observed P05; high. Cockpit already supplies that token. |
| F03 | P2, oversized metadata | Accepted serialized writes can exceed the reader's limit. | Observed P01; high. Ordinary concise entries are not shown failing. |
| F04 | P2 | Recall removes the warning that an entry has been challenged. | Observed P06; high. Pool-selection policy is a separate question. |
| F05 | P2, intervening edit or retry | Old-version feedback affects replacement content; uncertain retries cannot be reconciled by task. | Observed P04/P15; high. Non-idempotent annotation correctly describes counter behavior. |
| F06 | P2, external edit or corruption | In-place changes evade the cache; cleanup can expose an older duplicate. | Observed P03/P16; high. Health detects duplicates and normal atomic writes invalidate the cache. |
| F07 | P2, maintenance | Agent retirement and some purge sequences fail the supported Git deletion policy. | Observed P08; high. The temporary repository retained the original entry in HEAD. |
| F08 | P2, overlapping write | Commit can include bytes changed after validation. | Observed P12 plus Git contract; high. Store-wide batching itself is not a defect. |
| F09 | P2 | Cockpit can report an empty or apparently current store when loading failed. | Observed P10; high. |
| F10 | P2 | Cockpit conflict retry preserves the stale token without a usable reconciliation action. | Observed P11; high. |
| F13 | P2 | Disputed-state review loses the identifying challenge evidence. | Observed P13 and MCP projection; high. Full event history is optional. |
| F14 | P3, lifecycle write failure | Best-effort batch rollback lacks clear partial-failure recovery. | Observed source; compound failure/crash consequences inferred, medium. |
| F15 | P2 domain / P3 docs | HTTP scope validation and several documented MCP contracts disagree with intended use. | Observed P07/P14 and signatures; high. Not an approval-permission bypass. |

#### F01: Serialize the Whole Read-Check-Write Operation

[Engine locking](../../serve/memory/src/owlbear_memory/engine.py#L85) is per instance. [Edit](../../serve/memory/src/owlbear_memory/engine.py#L255) checks a cached entry, computes a replacement, and later writes it. MCP and Cockpit instantiate independent engines. Atomic rename prevents a torn file, not two valid writers overwriting each other. P02 reproduces loss without threads, clock collisions, or timestamp-resolution assumptions.

The trigger is overlapping writes to the same entry through independent instances, not simply opening two clients. Sequential atomic writes normally invalidate the other instance's cache. A deliberately serialized single-writer workflow avoids the demonstrated race; same-instance locking is a real protection. P1 applies because simultaneous MCP and Cockpit use is a supported, plausible deployment, even though incident frequency is unknown.

**Direction:** start with shared cross-process locking around fresh-read, revision check, and write, including destructive lifecycle operations. Consider a single mutation owner only if that simpler approach is inadequate. A better token alone does not solve this race. **Acceptance:** deterministically interleave two engines; one must reject the stale write or preserve both changes according to an explicit operation contract.

#### F02: Human Approval Must Mean Approval of Exact Content

[MCP approval](../../serve/memory-mcp/src/owlbear_memory_mcp/tools.py#L570) fetches the latest entry and uses its timestamp internally. The caller supplies only an ID. Curation and deletion follow the same pattern. This catches a narrow internal race but not a change between a human's read and their decision. P05 approved content the reviewer had never read. Cockpit's request-token contract is better at this boundary, though still subject to F01.

An intervening edit is required. Ordinary sequential MCP review works, and this is not a failure of every approval path or evidence that agents can bypass their tool allowlists. P2 reflects the narrower workflow trigger while preserving the significance of approving unseen content.

**Direction:** accept the reviewed revision for MCP approval, curation, and deletion and carry it through the review flow, as Cockpit already does. Use a token that identifies the relevant content/scope revision; assessment-counter changes need not invalidate a human review of unchanged guidance. **Acceptance:** change the reviewed content before the decision and reject the stale approval without changing its state.

#### F03: Make Successful Writes Round-Trip

[Storage](../../serve/memory/src/owlbear_memory/storage.py#L67) caps reads at 8,192 bytes, while [writes](../../serve/memory/src/owlbear_memory/storage.py#L133) serialize unbounded title/provenance/scope metadata without checking final size. A 1,024-character body ceiling is not a serialized-byte ceiling. P01 returned success and then disappeared from normal reads.

The 9,000-character title is adversarial input for a concise institutional-memory store, not a normal title. The file remains on disk and health can report it. This is a definite write/read contract defect worth a small fix, not evidence of widespread data loss or a need to replace storage.

**Direction:** reject an oversized final encoded representation before replacing the file, with coherent metadata bounds and an actionable error. **Acceptance:** boundary-sized ASCII and multibyte inputs round-trip or fail before persistence; a rejected edit leaves the previous file intact.

#### F04: Identify Challenged Guidance in Recall

[Recall](../../serve/memory-mcp/src/owlbear_memory_mcp/tools.py#L337) intentionally includes contested entries to permit a second task's assessment, but returns only title, ID, and body. The consumer cannot distinguish challenged guidance from other lessons. Keeping it recallable is not itself a defect; discarding its warning is an avoidable trust-context gap. No actual harmful use was observed.

**Direction:** add a concise contested marker and reason/reference when available. A structured envelope is an option, not a prerequisite. Preserve the decision to permit independent confirmation unless a separate product decision changes it. **Acceptance:** challenged guidance is identifiable in recalled output and remains subject to normal instruction/tool authority. Pool admission policy is assessed separately below.

#### F05: Bind Feedback to Evaluated Content

[Assessment](../../serve/memory-mcp/src/owlbear_memory_mcp/tools.py#L589) operates on the latest entry. P15 shows that two distinct tasks evaluating old content can move its corrected, approved replacement to disputed. This is a content-version correctness issue independent of whether callers retry. Content edits also retain past counters; retaining reputation across a wording fix may be reasonable, but materially changing the claim needs an explicit policy.

Ordinary counters also increment twice for the same task/entry submission (P04). The server correctly marks assessment non-idempotent, so this is not a false idempotency promise. Nevertheless, an uncertain response leaves no per-task receipt by which the caller can verify whether its contribution was applied. Blanket retry would distort feedback. The existing per-item success/failure results and initial batch-shape validation are useful and should remain.

**Direction:** distinguish a content/scope revision from the update timestamp that also changes during assessment. Supply the evaluated revision with feedback. Add a small task/entry/revision deduplication or reconciliation record if safe retries are required; do not prescribe a general event-sourcing system. **Acceptance:** feedback on replaced content is rejected or attributed to that version, and the chosen retry contract explicitly avoids duplicate application or refuses unreconcilable retries.

#### F06: Cache and Duplicate Handling Must Support Repair

[Directory caching](../../serve/memory/src/owlbear_memory/engine.py#L66) misses in-place file changes until another directory change or force-load (P03). Normal storage writes use atomic replacement and do invalidate it. This is relevant to external repair/edit tools, not proof that ordinary sequential MCP/Cockpit updates remain invisible. Either detecting those edits or explicitly requiring a force reload is a defensible supported contract.

[Duplicate loading](../../serve/memory/src/owlbear_memory/engine.py#L102) picks the newest record and retains the others. P16 confirms that deleting/purging that selected file can expose an older curated record. Duplicate corruption is a prerequisite, and health already reports it correctly. The gap is allowing an ambiguous destructive operation, not missing corruption detection.

**Direction:** make external-edit freshness explicit and prevent destructive mutation of ambiguous duplicate IDs until resolved. **Acceptance:** supported repair procedures refresh reads, and cleanup cannot silently restore an older recallable version. Returning mutable cached model objects is a separate P3 encapsulation concern: no current caller misuse was demonstrated, so defensive copying is not a prerequisite to the corruption fix.

#### F07: Close the Lifecycle Under Supported Persistence

[Agent retirement](../../serve/memory/src/owlbear_memory/engine.py#L352) physically removes entries with no remaining audience even when they were approved. [Git deletion validation](../../serve/memory-mcp/src/owlbear_memory_mcp/git.py#L130) allows physical deletion only when the HEAD snapshot is pending or deleted. P08 demonstrates the mismatch. Similarly, soft-delete followed by immediate purge can fail if the tombstone has not first reached HEAD; the UI does not coordinate that checkpoint.

This is a maintenance-path failure, not immediate corruption during ordinary recall. The rejected deletion is recoverable from HEAD. Immediate purge requires an eligible age threshold, such as explicitly choosing zero days; the default 30-day threshold reduces that exposure but does not guarantee the tombstone was committed.

**Direction:** align lifecycle deletion with Git policy, for example by retaining reviewed tombstones until checkpoint. Do not simply bypass the guard. **Acceptance:** retire a sole-scope approved entry and checkpoint through supported operations; delete/purge before and after a tombstone checkpoint has explicit tested behavior. A new receipt subsystem is not required just to fix this mismatch.

#### F08: Preserve the Validated Commit Snapshot

[Batch commit](../../serve/memory-mcp/src/owlbear_memory_mcp/git.py#L174) validates worktree records, stages non-pending records, and invokes `git commit` with explicit paths. Git reads the current worktree contents of those paths. P12 confirms that an overlapping change can reach HEAD after the helper validated different bytes. The probe changed content while preserving valid schema; it proves snapshot mismatch, not an observed malicious or malformed commit.

The helper intentionally batches all eligible changed memories and excludes unrelated non-memory paths. No exact per-session ownership contract exists, so store-wide batching is not a separate defect. Likewise, it explicitly warns that failed commits can leave memory files staged; automatically resetting the user's index would not be a safe repair.

**Direction:** coordinate validation through commit with supported writers or commit an isolated validated snapshot; reuse the writer-coordination solution from F01 where adequate. Keep the existing strict validation, bounded errors, and untrusted-hook-output labelling. **Acceptance:** an intervening change is rejected or left uncommitted, and unrelated staging survives success and failure.

#### F09: A Load Failure Is Not an Empty Store

[Memory page fetching](../../serve/cockpit/web/src/pages/MemoryTab.tsx#L313) uses `paused: true`, discards the fetch error, and resets parse-error count to zero. The hook marks the attempt finished; [empty rendering](../../serve/cockpit/web/src/pages/MemoryTab.tsx#L854) then says no entries exist. After prior success, the same path can retain stale rows without indicating stale data. Visibility changes and successful mutations can refetch, but there is no ordinary polling or explicit Memory-page retry control.

The 503 fixture exercises the generic failed-request path; actual production error frequency was not measured. A reload or visibility change can recover the page. Pausing polling is defensible; misreporting a failed attempt as empty is not.

**Direction:** distinct successful-empty and failed/stale states with an explicit retry. Preserve corruption warnings until a successful check supersedes them. Continuous polling and detailed freshness telemetry are optional. **Acceptance:** failed requests and successful empty responses render differently, and retry restores the current list.

#### F10: Conflicts Need a Draft-Preserving Resolution Path

[Draft initialization](../../serve/cockpit/web/src/pages/MemoryTab.tsx#L278) captures a revision once. [Conflict handling](../../serve/cockpit/web/src/pages/MemoryTab.tsx#L560) refreshes entries but not the draft's revision or base content. P11 resubmits the same stale token. Checking for `MEM_CONFLICT` inside message text also ignores the actual separate `code` field.

The draft is preserved on conflict. Cancel and reopen after refresh is an existing recovery path, but discards the draft; repeated Save is not one. No automatic overwrite is demonstrated, and merely refreshing the token would weaken the protection against unseen edits.

**Direction:** explain the conflict and offer a draft-preserving comparison/reapply action against the refreshed entry, or at minimum an explicit discard/reload path. Parse the actual error code. **Acceptance:** a user can resolve the conflict without an opaque retry loop; replacing the revision requires reviewing the newer content. A general-purpose merge editor is unnecessary.

#### F13: Preserve Evidence Needed for Dispute Review

[Factual challenges](../../serve/memory/src/owlbear_memory/engine.py#L385) record only the first task ID; the second challenge clears it when moving to disputed. [MCP projection](../../serve/memory-mcp/src/owlbear_memory_mcp/tools.py#L151) omits even that field. No persistent reason, evidence locator, actor, or challenged revision is recorded. Cockpit shows a task string without a source-context action; [resolution](../../serve/memory/src/owlbear_memory/engine.py#L220) promotes directly to approved. Non-use staleness is not temporal invalidation, despite the state name.

Disputed entries are correctly excluded from recall, so this is not further propagation of known-disputed advice. Its P2 impact is on the normal human-resolution workflow: the identifying evidence disappears precisely when the operator needs to evaluate two reports. Frequency is unmeasured, but it is not merely cosmetic metadata. A complete content-version audit log is a separate P3 enhancement, not the minimum fix.

**Direction:** retain both reporting task IDs and the challenged content revision, project them through MCP, and allow a bounded reason/evidence locator. Clarify that non-use staleness is not proof of falsehood. **Acceptance:** the operator can identify what was challenged and why before resolving or retiring the entry. Preserve human authority to resolve without mandating a new review agent or event store.

#### F14: Clarify Partial Lifecycle Failure Recovery

[Multi-entry lifecycle writes](../../serve/memory/src/owlbear_memory/engine.py#L544) try to restore all originals after an exception, including entries not changed by the operation. There is no cross-process exclusion or restart journal; rollback itself can fail and mask the initial error. A crash skips the handler entirely. Single-file writes fsync the file but do not demonstrate parent-directory or power-loss durability. Purge returns counts, not failed-entry details.

Ordinary successful operations and single-file atomic replacement are useful defenses. No restart-atomic batch or power-loss guarantee has been established, and no crash incident was demonstrated. P3 reflects the uncommon compound-failure path. Absence of a journal alone does not justify a database migration or a P2 defect.

**Direction:** first report the failed operation and incomplete rollback accurately, preserve both errors, and bound restoration to affected records. Add a restart journal only if crash-atomic batches become a requirement. **Acceptance:** injected write and restoration failures produce diagnosable partial state and do not claim full rollback. Parent-directory durability and independent Cockpit recovery are separate capability choices below.

#### F15: Put Invariants in the Engine and Remove Contract Drift

The [MCP handbook](../../share/skills/h-mcp-memory/SKILL.md#L88) still documents `save_memory.scope_agents`, although the callable tool does not accept it; it says blank/wildcard recall is rejected, although fallback guidance is returned; and it claims rename targets must resolve from active definitions, although the tool only checks syntax. It omits the finalizer from its access matrix. The [entry handbook](../../share/skills/h-memory-structure/SKILL.md#L18) says deletion clears approval time, while the engine preserves it.

The functional P2 issue is blank-member scope validation: the [HTTP request](../../serve/cockpit/src/owlbear_cockpit/routes/memory.py#L74) and [engine](../../serve/memory/src/owlbear_memory/engine.py#L255) accept a truthy list such as `[""]` and promote pending guidance into an unusable audience (P14). The normal UI trims newly typed values, reducing exposure, but direct API clients and stored values still cross this boundary. Whether a human may intentionally clear all scopes is a separate policy; agent and human permissions need not be identical.

P07 also shows recall telling an unrecognized producer not to write, despite intake accepting non-blank provenance. Name recognition from stored entries is not caller authorization. Conversely, registering `approve_memory` on the server does not contradict its exclusion from named agent allowlists. No such permission bypass was demonstrated.

**Direction:** validate nonblank scope members in the engine, clarify intentional human-only operations, and remove permission claims inferred solely from recognition. Correct the documentation from the live schema. **Acceptance:** both adapters reject malformed members, cold-start guidance agrees with actual intake authority, and documented examples match callable parameters. Keep ordinary documentation discrepancies P3 rather than using them to inflate the functional finding.

### 3.4 Coverage and Policy Questions

#### F11: Assessment Coverage Is Not Established

[Builder](../../share/agents/builder.agent.md#L8) is the only role with assessment access, and its [required workflow](../../share/skills/w-packet-building/SKILL.md) does not schedule it. The [handbook](../../share/skills/h-mcp-memory/SKILL.md#L154) requires a complete batch when assessing but does not clearly settle mandatory timing or participation by every role. This establishes a loading/coverage ambiguity, not proof that assessment never happens or that a mandatory step is missing.

Read-only reviewers are appropriately mutation-free. Their [candidate return](../../share/skills/r-challenger-protocol/SKILL.md#L79) captures new lessons; it has no recalled-entry ID/bucket fields and is not an existing assessment handoff. Builder-only assessment may be a deliberate sample, but it cannot establish usefulness for reviewer-only scopes. Neither blanket mandatory feedback nor guaranteed adequate sampling follows from the current contracts.

**Decision:** which consumers should contribute feedback, at what task boundary, and is sampling sufficient? Measure actual invocation/coverage before adding mandatory work. If reviewer feedback is needed, return it through the owning parent without granting reviewer mutation authority or changing the primary Delivery result.

#### F12: Curation Cadence Is Opportunistic, Not an SLA

[Orchestration](../../share/skills/w-orchestration/SKILL.md#L98) intentionally counts session-local cycles and dispatches after 3, 13, 23, etc. Manual curator invocation exists. A sequence of short sessions may perform no automatic curation, but that does not violate an explicit eventual-processing promise. The observed three pending entries do not prove an accumulating or neglected backlog.

[Periodic policy](../../share/skills/w-mem-curation/SKILL.md#L43) suppresses identity-only uncertainty in chat summaries, not from stored pending entries or manual review. Failed scheduled attempts consume a slot. Dispatch failures stop the orchestrator after the batch; internal curator failures are reported and acquisition continues. These are explicit choices whose operational cost has not been measured, not absent failure handling.

**Decision:** is manual plus opportunistic curation adequate, or should candidate age/size create a durable due state? Only the latter requires an eventual-processing trigger. Preserve the compact cadence until evidence or a product requirement justifies more scheduling machinery. Reconsider stopping unrelated Delivery work on optional-housekeeping failure if that coupling causes observed disruption.

#### Recall Admission and Review Effort

The three pools deliberately reserve exploration/challenge slots before final ordering; [voting integration tests](../../tests/test_memory_voting_integration.py#L353) protect that allocation. Approved-first output does not necessarily mean approved-first admission. P09 exposes how low limits can be entirely exploratory, but does not establish that exploration is wrong. Clarify the intended small-limit policy before changing it; evaluate task outcomes rather than presuming trust-first selection is always better.

Human approval, a first factual challenge, and independent confirmation each have plausible purposes. The two-task rule reduces the chance that one mistaken agent suppresses useful guidance, at the cost of continued exposure while contested. A warning, evidence, and revision binding are targeted improvements. A more skeptical or shorter review prompt is a usability choice unless observed cost or failure justifies it.

### 3.5 Threat Model and Optional Capabilities

These are conditional product enhancements, not additional confirmed defects, evidence of malicious stored content, or an automatic backlog. Prioritize them only where the operator's goals or measured usage justify their cost.

| Capability | Why it matters | Minimum useful next depth |
| --- | --- | --- |
| Retrieved guidance is not authority | Raw recalled Markdown can carry persistent behavioral instructions. Named provenance is self-reported, and previous reviewed entries are not independent proof of truth. UI Markdown sanitization addresses rendering, not model instruction-following. | Explicit advisory boundary in recall, trust/revision metadata, poisoned-candidate tests, and existing least-privilege tool enforcement. Avoid a regex-only promise of prompt-injection prevention. |
| Evidence and supersession | Confidence, usefulness, correctness, and applicability differ; large rewrites need different evidence from wording fixes. | Fix F05/F13 first. Add last verification/use and a simple supersedes link only if actual replacement workflows need them; no knowledge graph is necessary. |
| Task relevance and recall explanation | Roles may need broadly applicable guidance on every task, or task-specific advice; low use does not distinguish those cases. | Evaluate the current policy first. Add optional task/path context, a token budget, or selection preview if irrelevant recall consumes meaningful context. Embeddings are not the default next step. |
| Operational visibility | Healthy files do not prove useful learning; the existing health panel already answers storage-integrity questions. | Start with actual pending age and feedback coverage. Add checkpoint or conflict summaries if they answer frequent operator questions; avoid an undemanded telemetry dashboard. |
| Durable checkpoint and restore | Cockpit mutations do not checkpoint via Git; manual review commits are optional; pending entries intentionally remain outside the supported batch commit. Git history is not automatic off-device backup. | Explicit local durability tiers, checkpoint status, exact restore preview, and operator-owned backup guidance. Do not auto-push or broad-commit as a fix. |
| Privacy and deletion meaning | Tombstones and purges do not erase Git history or copies. Task-specific paths/provenance can be sensitive even without secrets. | Clear retention/erasure semantics, reject secrets before capture/checkpoint, and a separately authorized purge-history procedure when required. No evidence of exposed secrets was sought or found in this audit. |
| Learning effectiveness | Passing transition tests cannot establish that memory improves task outcomes. Most counters measure model judgments, not avoided failures. | A small representative task set comparing no-memory and selected-memory outcomes: prevented errors, harmful advice, token cost, and human review time. Expand only when those results justify it. |
| Recovery independent of Delivery | [Cockpit startup](../../serve/cockpit/src/owlbear_cockpit/main.py#L293) loads Delivery context and the built UI before Memory becomes available; MCP has no exceptional-state resolution operation. | If memory recovery must work during Delivery configuration failure, expose a bounded independent operator route. Shared application startup alone is not proof of unacceptable availability. |

No additional autonomous agent is inherently missing. The curator, read-only reviewers, write-capable owners, and human operator are sufficient roles. Clarify coverage and repair existing boundaries before adding a memory planner, separate scorer, or permanent memory daemon.

### 3.6 Where Depth Could Decrease

Measured by `wc -w`: curator agent 718 words; curation workflow 1,324; entry handbook 1,095; MCP handbook 2,090; review prompt 2,498. Total 7,725 words across this cluster, not all loaded together. Manual review explicitly loads roughly 5,683 words from the prompt plus its two handbooks before source escalation or delegation; periodic curation starts with roughly 2,042 words from agent plus workflow. The universal instruction affects every role. These are word counts, not token estimates or deletion quotas.

| Block | Classification | Why and surviving obligations |
| --- | --- | --- |
| Three recall pools, fixed reservations, linear score, lifetime non-use threshold | Keep until evaluated; do not deepen speculatively | These are modest deterministic mechanisms, not inherently overengineered. Compare with simpler trust/relevance-first selection only if evaluation reveals lower usefulness or unfair exclusion. Preserve bounded recall, exploration intent, and exceptional-state exclusions. |
| Mandatory adversarial pass, forced batch ranking, retention pressure, and continuation loop | Consider bounded/manual modes | Independent challenge and explicit continuation may be deliberate user preferences. The prompt's 2,498 words are cost evidence, not proof of wasted work. If review is too expensive, offer a bounded mode and reserve extra challenge for consequential uncertainty. Keep consent, skeptical retention, source checking, per-entry decisions, and failure handling. Move reusable procedure to one skill only if reuse warrants it. |
| Repeated retired-store, provenance, scope, and lifecycle rules | Compress exact duplicates cautiously | F15 establishes actual contract drift, making consolidation useful. Keep one full owner per rule and concise consumer pointers with reliable loading. Preserve no fallback store, no self-corroboration, targeted scope, approval boundaries, and conflict deferral. Word count alone is not a removal criterion. |
| Identity corroboration versus factual evidence | Keep distinct; strengthen factual evidence | The policy already says identity evidence does not raise truth confidence. Do not criticize it for a conflation it explicitly rejects. Fix missing challenge evidence separately; compress repeated identity instructions without weakening scope validation. |
| Memory-page metadata and stacked filters | Optional progressive disclosure | The large component and mobile filter height are ergonomic/maintenance concerns, not evidence of broken layout. Prefer concise state visibility and collapsible metadata/filters if repeated use warrants them. Extract the edit/conflict responsibility when fixing F10, not a wholesale component rewrite. Preserve labels, sanitization, confirmation, and reachable actions. |

Do not collapse seven lifecycle states just to reduce a number. Each expresses a meaningful distinction in the current workflow. Consider one review state with separate reasons only if it makes actual operator decisions simpler while preserving exclusion, confirmation, and human-resolution semantics.

### 3.7 Storage Alternatives

| Option | Benefits | Costs and boundaries | Judgment |
| --- | --- | --- | --- |
| Keep Markdown canonical; add shared locking, coherent bounds, and review/feedback revisions | Preserves inspectability, Git review, existing adapters, and small deployment | Supported writers must coordinate; external edits need an explicit freshness contract | Best first candidate for the small local store. Add recovery records only for an established batch/retry requirement. |
| Single local mutation owner | Centralizes concurrency and operation receipts without changing entry representation | Introduces service availability and lifecycle responsibility; direct file edits still need detection | Consider if independent writer coordination remains difficult; reuse an existing owner where feasible. |
| SQLite canonical storage with reviewed export | Proven transaction machinery, receipt uniqueness, history/querying | Changes clone/Git workflow, migration and backup semantics; editable export must not become a second writable truth | Reasonable if durable multi-entry transactions and event history are requirements. Not justified merely by 53 files. |

Do not implement a home-grown transactional database inside Markdown just to avoid acknowledging the trade-off. Conversely, a database does not fix stale human approval, unclear feedback coverage, poisoned guidance, or confusing UI by itself. The observed store size supplies no scale-based reason to migrate.

## 4. Recommendation, Confidence, And Limits

### Recommended Order for Later Action Plans

| Theme | Findings | Likely owner | Required outcome before closing |
| --- | --- | --- | --- |
| 1. Fix silent cross-writer loss | F01; shared coordination may also resolve F08 | Engine, storage, Git helper | Supported concurrent writers cannot silently overwrite accepted changes or commit a different validated snapshot. |
| 2. Repair bounded correctness and UI gaps | F02-F10, F13, domain part of F15 | Existing engine, adapters, Cockpit | Exact reviewed/evaluated content, coherent write/deletion contracts, conditional corruption safeguards, truthful load state, recoverable conflicts, and usable challenge evidence. Prioritize by actual operator usage within this group. |
| 3. Clarify and measure learning policy | F11-F12 and recall-policy questions | Owning workflows and operator | Explicit assessment coverage and curation expectations, plus a small outcome comparison. Do not require universal feedback or a durable scheduler without choosing those goals. |
| 4. Tighten diagnostics and documentation | F14, documentation part of F15 | Existing engine and memory handbooks | Honest partial-failure reporting and accurate callable examples; no new transaction system required by default. |
| 5. Add optional depth or simplify | Capability and depth tables | Product decision, then existing owners | A demonstrated operator need or measured benefit justifies each additional control or removal. Preserve useful existing roles, review safeguards, and storage boundaries. |

### Decisions for Optional Expansion

1. Does the existing curated-before-approval and two-task confirmation policy meet the operator's trust goal once warnings and revision binding are fixed?
2. Is assessment intentionally sampled through builders, or should other consumers contribute through safe parent handoffs? Is opportunistic/manual curation sufficient?
3. Does exploration-first admission, particularly at small limits, improve outcomes compared with a simpler selection policy?
4. Is local readable-file persistence sufficient, or are automatic checkpoints, crash-atomic batches, independent recovery, or off-device backup required? Preserve Markdown/Git unless those answers justify a storage change.
5. Which small set of representative tasks can demonstrate value relative to token and review cost?

These choices do not block fixing the reproduced defects and need not all become projects. No Delivery tasks, changes, requests, or implementation plans were created by this audit.

### Verification and Limits

- Focused backend/registered-test runs reported 217, 111, and 255 passes with overlapping scopes; focused Vitest reported 16 passes. No unique-test total, whole-suite result, or coverage percentage is claimed.
- Sixteen bounded observations are recorded above. P08/P12 exercised actual temporary Git repositories; P15/P16 distinguish old-version feedback and duplicate cleanup from retry behavior and simple duplicate detection. P02 uses a controlled two-engine interleaving, not a multiprocess stress benchmark. Probe harness failures are not product findings.
- Agent, skill, and prompt validators passed. All memory engine and MCP implementation files, the Memory page/API, curator cluster, and immediate workflow/health boundaries were inspected. All 13 shared roles were mapped from metadata; non-memory bodies outside the direct cluster were not exhaustively reviewed.
- Existing assembled Memory lifecycle and purge scenarios were inspected but not run as a full built-backend E2E gate. The Chromium probes exercised the actual frontend through a temporary Vite server with synthetic responses, not live backend mutations. Servers/browser processes were closed after each probe.
- No physical power-loss, process-kill recovery campaign, network-filesystem test, sustained scale benchmark, complete accessibility audit, remote-authentication review, or real-agent poisoning experiment was performed. Findings about those conditions are explicitly inferred risks/design gaps.
- Live inspection was aggregate-only and showed no current corruption. Historical counters prove some past feedback, not the completeness or accuracy of current learning. No live memory content was edited, approved, assessed, retired, or committed.
- Deferred-tool searches in this audit session returned several mutation/read bindings but did not expose `recall_memory`; no pre-flight recall was possible through the available binding. This session capability limit is not treated as proof that the repository server lacks recall: its implementation and registered tests exist.
- Research and source attribution are the only audit artifacts; implementation and live memory remain unchanged. Temporary screenshots/probe directories are not durable evidence dependencies; the report retains outcomes and reproduction conditions.
- Research conclusions belong here, not in institutional memory. The audit does not treat reviewer agreement as proof, infer intent from passing tests alone, or turn every missing feature into a defect.

**Bottom line:** keep the working local architecture and human-assisted workflow. Fix the narrow correctness and recovery gaps, clarify automatic-learning expectations, and measure usefulness before increasing or reducing policy complexity. The evidence supports targeted improvement, not either a clean bill of health or a wholesale redesign.
