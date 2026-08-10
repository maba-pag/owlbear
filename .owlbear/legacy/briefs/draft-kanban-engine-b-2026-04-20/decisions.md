# Decisions — Brief B (Kanban Engine API + MCP Adapter + Cockpit Engine Surface)

## M1 — Scope and Aperture

### D1 — Investment Tier
**Studio.** Multi-consumer refactor with ~30-AC paper integration against Brief A and 7+ reality conflicts. Full panel + Explore-led code audit.

### D2 — Brief Scope
**Engine API spec + MCP adapter mapping + Cockpit-only engine surface.**
- Engine API: signatures, semantics, validation rules, projections, error taxonomy
- MCP adapter mapping: per-Brief-A-tool engine-call sequence
- Cockpit surface: admin release, stuck-session inspection, claim sweep
- NO stubs, NO implementation. Bottom-up build follows after Briefs A/B/C aligned.

### D3 — Aperture
**Wide.** No backwards compat, no legacy code, break things, quality over everything. Brief B may redesign any engine surface found wanting at M3.

### D4 — AC21 Handling
Edit Brief A directly to remove AC21 as part of M5/M6 finalization.

### D5 — Paper Integration Format
Per-AC table pinned to post-AC21-removal Brief A snapshot.

## M2 — Outcomes (locked; see context.md for full O1–O7 statements)

### D6 — Storage-Agnostic Engine API
O7 locked. Engine API refers to models and operations, not persistence details. Body is structured (`list[Section]`); sessions are a derived read model over the board-level activity stream; locking is described as operation-level semantics; TZ governs runtime not storage.

### D7 — Body Model (Choice A2)
**`body: list[Section]` where `Section = {heading: str | None, level: int, content: str}`.** Brief A's `show_task(section=...)` becomes a filter on this structured field. Markdown is one wire-layer render.

### D8 — Wave + agent_map Ownership (Choice B1) — SUPERSEDED-IN-PART by D42, D58
**Engine owns wave composition AND agent_map.** Introduces `agent_map: dict[str, str]` field on BoardConfig (status → agent). New engine method: ~~`pick_waves(wave_size, max_waves) → list[Wave]`~~ **renamed to `pick_tasks` per Brief A and D42** with intra-wave dep guarantee. Orchestrator wave logic (if any) retires. **Dispatchability filters extended by D58 (`blocked==true` excluded).** The original D8 method name is retired; the agent_map ownership and intra-wave dep guarantee remain in force.

### D9 — Role Views (Choice C2) — D59 extension RETIRED
**Type-level capability contract.** `KanbanEngine` full surface; `AgentEngineView` and `CockpitEngineView` thin facades exposing method subsets. Accessed via `engine.agent_view()` / `engine.cockpit_view()`. Cockpit mutation routes rewire to use `CockpitEngineView` exclusively (in Brief B scope). **D59 (third `OrchestratorView` role view) is retired during M5 cleanup as over-engineering — `pick_tasks` lives on `AgentEngineView`. Role isolation for the dispatcher capability is documentary (skill + tool docstring), not type-enforced. D61 (naming lock) is consequently vacated.**

### D10 — Board-level Activity Stream in Engine/Admin Semantics (Choice D2, revised)
**`activity.jsonl` is a first-class board-level runtime activity stream inside engine/admin semantics.** `list_sessions(filter=...)` becomes a derived cockpit/admin read model over that stream, and raw activity is exposed separately for cockpit/admin history use. Agent-facing MCP surfaces still do not expose raw activity.

## M3 — Reality-Conflict Dispositions (with code citations)

### D11 — Claim Identity (Conflict 1, user-confirmed invariant)
**Claim is a boolean-with-timestamp, not an ownership token.**

- `claimed_at: str | None` only. No `claimed_by`, no session token.
- `claimed_at` present → claim active.
- `claimed_at + timeout < now` → claim expired; engine auto-releases on next touch.
- `start_work` on active claim → fails unconditionally. No same-agent idempotency.
- `release`/`end_work` require no caller identity check.
- Orchestrator is responsible for releasing before dispatching a retry after agent crash.
- Harness invariant: the orchestrator is not independently liveness-aware from the worker. A stuck worker also stalls the orchestrator, so the system does not admit a "late zombie end_work after successful re-dispatch" path. Brief B therefore treats that scenario as out of scope rather than adding an agent-side OCC token.
- ~~`KanbanEngine.agent_name` becomes vestigial (only used by activity log writes, which are audit-only per D10). Not removed in Brief B to keep scope tight; open as a follow-up.~~ **SUPERSEDED by D33:** `agent_name` constructor parameter is removed in Brief B (D43 confirms D33 stands; D10 retired the activity log entirely).

### D12 — Wave Composition (Conflict 3) — per D8
Engine-owned. Specified in Brief B §Engine API.

### D13 — Locking (Conflict 4)
**Document what exists as operation-level guarantees.**
- **Atomic ID allocation.** `create_task` guarantees unique monotonic IDs under concurrent creation. (Implementation: file lock today; any storage-level primitive acceptable for Brief C.)
- **Optimistic concurrency on edit.** `edit_task` and `move_task` accept an `updated` token; operation rejected with `ConcurrencyError` if current `updated` ≠ token. **SUPERSEDED-IN-PART by D46:** OCC parameter applies on `CockpitEngineView` writes only; `AgentEngineView` writes do not accept `expected_updated`.
- No pessimistic locking beyond atomic ID; no distributed locking.

### D14 — TZ Policy (Conflict 5)
**UTC everywhere, ISO 8601 with offset on the wire.** Aligns to existing reality. No migration cost. No per-engine TZ config.

### D15 — TDD / Clarity Gates (Conflict 6) — REVERSED at M4 — dispatcher rules SUPERSEDED-IN-PART by D42, D58
**Gates move to write-time on status-transition operations.** Validation runs in `move_task` and in `end_work` when `move_to` causes a transition. Predicate failure → `ValidationError`; task does not transition. ~~Dispatch (`pick_waves`) is unfiltered by quality gates: it returns every task that is unclaimed, non-archived, has `dep_status != "blocked"`, and matches status.~~ **Dispatch is now `pick_tasks` (D42); dispatchability filters per D42+D58 are: not claimed, not archived, `dep_status != "blocked"`, `blocked != true`. The "unfiltered by quality gates" principle stands — D15 predicates fire only at write-time, not at dispatch.** Quality is the agent's responsibility on pickup (they may `end_work(outcome="reject", move_to="<earlier>")` if the task is malformed).

**Rationale for reversal:** dispatch-time gates without state mutation are an invisible-deletion mechanism — a task that fails the gate is not blocked, not flagged, just absent from `pick_waves` with no signal to the human. The right place to enforce structural well-formedness is at the moment of state change.

**Predicate model (C-tight):** config-driven section-name requirements on `BoardConfig`. Engine inspects `body: list[Section]` (per D7); never names markdown literals. Schema sketch:

```yaml
status_predicates:
  in-progress:
    required_sections: ["acceptance criteria"]
    require_list_in_section: true
    test_section_or_non_impl_tag: ["test-writer notes"]
  review:
    required_sections: ["acceptance criteria"]
non_impl_tags: [research, docs, type:config, type:docs, test, type:test, agent, quality, type:user-action]
```

Section identity is `Section.heading` (case-insensitive, whitespace-stripped). Statuses without a `status_predicates` entry have no predicate.

**SUPERSEDED-IN-PART by D64:** the DSL key `require_list_in_section` is locked as `dict[str, bool]` (heading-name → required flag), not the boolean shown in the sketch above. The sketch above is illustrative; D64 is normative for predicate DSL shape.

**Grandfathering:** tasks already in advanced statuses are not retroactively validated. Predicate applies only when a `move_task` or `end_work` transition triggers it. Migration is incremental: the user (or agent) repairs a task only when next advancing it.

### D16 — `agent_map` (Conflict 7) — per D8
Introduced as net-new BoardConfig field.

### D17 — Archive Atomicity (user Decision 6)
**Archive operation clears claim atomically.** To be verified in current `move_task(archived)`; if gap, Brief B specifies it as engine invariant.

### D18 — Active + Lazy Expiration (user Decision 7)
**Engine consumers may call claim-only `sweep()` on init.** Cockpit currently does not — Brief B records this as a Cockpit bug to fix. Lazy expiration continues at every claim-sensitive touch (existing behavior). Corruption repair is not part of startup sweep.

### D19 — Duplicate Frontmatter IDs (user Decision 9)
**Treated as corruption. No auto-fix.** Engine surfaces `CorruptionError` at read time. `repair-duplicates` CLI follow-up is conditional on Brief C's storage choice.

### D20 — AC30 Timestamp Format (new conflict from M3)
**Change to full ISO 8601 with offset; accept inconsistent historical prefixes.** No task body rewrite. New entries get full ISO; old entries keep `[[YYYY-MM-DD]]` shape.

### D21 — Cockpit Mutation Rewire (new conflict from M3)
**In Brief B scope.** Cockpit mutation routes rewire to use `CockpitEngineView` (per D9). Structural change accepted.

## M4 — Resolutions of Open Questions and Cross-Cutting Risks

### D22 — OCC token scope (Conflict A → A3)
**Required by `CockpitEngineView` mutations; optional in `AgentEngineView` mutations.** Cockpit always has a freshly-rendered token from the read that produced the editable view; Cockpit mutations must echo it; engine raises `ConcurrencyError` if stale. MCP agents may omit the token to skip a pre-fetch round trip (typical in dispatch-driven flows where the orchestrator avoids same-task concurrent dispatch); if they pass one, the engine enforces it. Trade accepted: an MCP agent that bypasses the token can clobber a Cockpit edit silently. Mitigation: Cockpit edits update `updated` and any subsequent agent that DOES pass the token (e.g., a reviewer pre-fetching) sees a stale token and aborts.

### D23 — OCC token type (Conflict B → B1)
**Use the existing `updated` ISO-8601 timestamp string as the token.** No new field. Risk of microsecond collision is negligible on a single-laptop deployment. Cockpit already wired for this. Brief C may swap to a `revision: int` if the storage backend offers a natural revision counter (e.g., a DB row version), with the engine continuing to expose it as `updated` on the wire to keep the contract stable.

### D24 — `agent_map` completeness (Conflict D → D1)
**Fail-fast at config load.** Every status declared in `BoardConfig.statuses` must have an entry in `agent_map`. Missing entry → `ConfigError` at engine construction. Same failure mode as a missing status. No `_default` fallback. Loud and immediate beats silent miswiring.

### D25 — `last_end_outcome` field (Conflict E → E2)
**Withdrawn.** The task body's appended `end_work` notes already carry the outcome of the last attempt. Adding a structured field would create two sources of truth that can drift. The Cockpit display reads the body as-is.

### D26 — `Section` model shape (Q3)
**`Section = {heading: str | None, level: int, content: str}`.**
- `heading=None, level=0` represents the body preamble (text before any heading); allowed only as the first element.
- `level` is the heading rank (2 for `##`, 3 for `###`, etc.); preserved on round-trip.
- `content` is the section body text (markdown-formatted today; opaque to the engine).
- Code blocks containing literal `## Heading` text in `content` must NOT be parsed as nested sections (parser is code-block aware).
- Repeated headings: allowed; predicate matching uses case-insensitive whitespace-stripped equality.

### D27 — Exception taxonomy (Q4)
**Shallow class hierarchy under `KanbanError(Exception)`** with subclasses: `NotFoundError`, `ValidationError`, `ConcurrencyError`, `CorruptionError`, `ConfigError`. Each carries `code: str` (machine-readable, e.g. `ERR_NOT_FOUND`, `ERR_INVALID_STATUS`), `user_message: str` (sanitized; safe for MCP `ToolError` and Cockpit HTTP body), and optional `detail: str` (logged, not surfaced). MCP adapter maps `code` to `ToolError(user_message)`; Cockpit adapter maps subclass to HTTP status (404/422/409/500) with `user_message` as body.

### D28 — `pick_waves` algorithm (Q5)
**Greedy by `(priority_rank, status_rank, id)`, deterministic.** Process tasks in that order; for each, place into the lowest-index existing wave that contains no dep edge to this task in either direction; if no such wave exists and `len(waves) < max_waves`, create a new wave; otherwise drop. Excludes claimed tasks, archived tasks, and tasks with `dep_status="blocked"`. Default `wave_size` from `BoardConfig.wave_size` (new field, with Pydantic-validated default e.g. 4). Default `max_waves=3` per Brief A.

### D29 — `claim_timeout` format (Q7)
**Support `s`/`m`/`h`/`d` suffixes via Pydantic validator at config load.** Invalid format → `ConfigError` at engine construction. Replaces current loose lazy parsing.

### D30 — Body wire format (Q8) — amends D7
**Engine internal model is `list[Section]` (D7); engine-to-consumer wire shape is `body: str` (markdown).** `show_task(section=...)` filters internally and serializes back to markdown for the wire; on the wire only the matching sections appear. Brief A's `body: str | null` shape is honored without revision. `list[Section]` never leaks to MCP or Cockpit responses.

### D31 — `list_sessions` narrowing (Q9)
**`list_sessions(filter=...)` remains a cockpit/admin read model derived from the board-level activity stream.** Default filter `"active"` returns `state in {"running", "stuck"}` only, but closed-session filters such as `"all"`, `"blocked-or-rejected"`, and `"released"` remain supported for cockpit/admin use. `state` is a session-level cockpit/history classifier and does not replace task-level `claimed_at` / `claimed` semantics. This surface stays off the agent MCP path.

### D32 — Activity stream naming (R1)
**Keep `activity.jsonl` and formalise it as a board-level activity stream.** It is a single gitignored runtime file under `.owlbear/kanban/`, storing structured JSONL activity events for cockpit/admin history surfaces. This is product data, not a diagnostic log.

### D33 — Drop `agent_name` from constructor (R3)
**`KanbanEngine.__init__` no longer accepts `agent_name`.** Per D11 (no claim identity), the parameter has no remaining semantic. **SUPERSEDED-IN-PART by D43:** the old diagnostic-log rationale in this entry is retired; the board-level activity stream no longer depends on constructor-level claim identity. The `agent_name` removal stands solely on D11.

### D34 — AST role-view enforcement test (R5)
**Brief B AC: a CI test scans `serve/cockpit/` source for any reference to engine methods outside the `CockpitEngineView` allow-list.** Existing `tests/test_cockpit_boundary.py` extends to this pattern (it currently scans only for explicitly-denied method names; broaden to allow-list).

### D35 — Body size limits (R6)
**Two thresholds at engine input boundary on `create_task`/`edit_task`:**
- `body` size > 100 KB → operation succeeds; response `guidance` includes a warning instructing the agent to verify the size is needed and otherwise prune the body (with a hint to consult an appropriate cleanup skill).
- `body` size > 500 KB → `ValidationError(code="ERR_BODY_TOO_LARGE")`. Hard rejection.

Limits apply to the markdown wire shape on input. **SUPERSEDED-IN-PART by D47:** the authoritative measurement is UTF-8 bytes of the markdown `body: str` parameter at the engine input boundary, **before parsing**. The post-parse fairness consideration in the original wording is informational; D47 is normative.

### D36 — Sweep compare-and-clear (R8)
**`sweep()` releases an expired claim only if the captured `claimed_at` value still matches at clear-time.** Closes a race where a sweep observes an expired claim, then a fresh claim arrives before the release write. Pseudocode-free description: read claim, check expiry, on expiry attempt write conditional on the read value being unchanged; if changed, skip. Engine guarantee: sweep never destroys a fresh claim. This decision applies to claim-only sweep semantics; corruption repair and quarantine are deliberately outside `sweep()` and live on a separate explicit admin surface.

## M4-Critic Resolutions (Findings 1–11)

### D37 — Archival validation ownership (Finding 11 / J)
**Engine validates `archival_reason` and `archival_refs` at every write that touches them** (`move_task` to archive status; `edit_task` if mutation crosses an archival field). Per Brief A §7. Codes: `ERR_ARCHIVAL_REASON_INVALID`, `ERR_ARCHIVAL_REFS_REQUIRED`, `ERR_ARCHIVAL_REFS_FORBIDDEN`, `ERR_ARCHIVAL_REF_MISSING`, `ERR_ARCHIVAL_REF_SELF`, `ERR_ARCHIVAL_REF_CYCLE`. Raised as `ValidationError`.

### D38 — `dep_status` freshness model (Finding 11 / K)
**Computed on every read.** `list_tasks`, `show_task`, `pick_tasks` derive `dep_status` from current dep states at call time. Pure function, no cache, no invalidation. Cost is O(deps) per task per read; bounded at laptop scale.

### D39 — `guidance` placement (Finding 11 / L)
**`guidance: list[str]` lives on response envelopes only.** Never on the `Task` model, never persisted. Engine generates per call as part of operation results.

### D40 — Body wire contract scope (Finding 2)
**Brief B contract for body is narrow:** `create_task` / `edit_task` accept markdown `str`; engine parses internally to evaluate write-time predicates (D15) and to support `show_task(section=...)` (D26+D30). **Round-trip behavior — byte-exact vs normalized — is Brief C's contract**, not Brief B's. Brief B does not promise either way; Brief C inherits the implementation choice and its visible consequences.

### D41 — `end_work(success)` auto-advance is atomic (Finding 1)
**`end_work(outcome="success")` either advances cleanly or fails atomically.** When success auto-advances to the next status (per the configured sequence), the destination status's predicate (D15) runs. If the predicate fails: the entire `end_work` call fails with `ValidationError`; status stays at current; claim NOT released; note NOT appended. Caller must repair the body and retry, or call `end_work(outcome="reject", move_to=…)` to escape. The destination predicate is the agent's already-known job description per the agent file; no special guidance scaffolding required.

### D42 — Dispatcher returns cycles (Finding 4) — replaces D28
**`pick_tasks` (same name, redefined) returns a cycle: an ordered sequence of waves.** A wave is a set of tasks dispatched in parallel; size ≤ `wave_size` (`BoardConfig.wave_size`, new field, default 4); composition respects the four-bucket agent-type compatibility matrix (auditor / builder / light-flex / heavy-flex per existing `share/skills/w-orchestration/SKILL.md`, now codified into engine config as `BoardConfig.agent_compatibility` and `BoardConfig.agent_types`). Wave assembly logic and configuration move from the orchestrator skill into the engine dispatcher. **Exposed via MCP only to the orchestrator agent (role-gated); not exposed via Cockpit.** D28 superseded.

### D43 — Board-level activity stream in engine/admin scope (Finding 8) — amends D32
**Engine/admin owns a first-class board-level activity stream.** D32 stands: `activity.jsonl` is a structured runtime artifact, not a diagnostic side-channel. Every mutating engine operation appends an activity event; cockpit/admin surfaces query the stream directly via a dedicated activity interface and indirectly via `list_sessions(filter=...)` derived from the same stream. Storage owns on-disk persistence and compaction policy in Brief C. D33 still stands: this does not reintroduce `claimed_by` as task state.

### D44 — Drop AST role-view scanner (Finding 9) — reverses D34
**No CI test scans Cockpit code for engine imports.** Role views (D9) document and label the intended Cockpit and agent surfaces. If Cockpit code reaches around the view to import the engine class directly, that is the Cockpit team's call and their problem. The role view's existence and naming make intent obvious; an AST guard against deliberate-or-careless misuse adds maintenance overhead with no real protection. D34 reversed.

### D45 — Cockpit history views in Brief B scope via activity stream (Finding 7)
**Resolved by D43 in the opposite direction.** Cockpit history views are in scope through the board-level activity stream. Brief B must provide cockpit/admin read surfaces for raw activity and derived sessions; Brief C must persist the stream and its compaction policy. The open question is storage and query shape, not whether cockpit history exists.

### D46 — OCC token mechanics narrowed (Finding 5) — amends D22
**OCC tokens apply only to Cockpit writes.** D22's "optional on MCP" is tightened to **"not used by MCP."** `start_work` / `claim_task` / other agent-side writes have no `expected_updated` parameter; the existing claim-already-held check is the only concurrency gate on the agent path. The dispatch prompt (per F4 / D42) remains task-ID-only. Race window: a Cockpit edit between dispatch and claim shows up to the agent as the post-edit body; agent acts on current state. This relies on D11's harness invariant: retries happen only after the original worker has actually exited, not while a later `end_work` can still arrive.

### D47 — Body input limits (Finding 10) — amends D35
**Body size measured in UTF-8 bytes of the markdown `body: str` parameter at the engine input boundary**, before parsing. 100 KB warn (D35) and 500 KB hard error (D35) thresholds stand and apply to that measurement. **No caps on title, tags, or frontmatter** — over-engineering for an attack surface that does not exist on a single-user laptop tool.

### D48 — Exception taxonomy scope (Finding 6) — affirms D27
**The integrated taxonomy after approved Brief C amendments has six subclasses (`NotFoundError`, `ValidationError`, `ConcurrencyError`, `CorruptionError`, `ConfigError`, `MigrationRequiredError`).** `MigrationRequiredError` is reserved for the engine-init unmigrated-board gate introduced by Brief C C11/AM-12. Body-too-large is `ValidationError(code="ERR_BODY_TOO_LARGE")`. Storage I/O failure modes, including activity-stream append/query/compaction failures, remain out of Brief B scope (Brief C may map them into the approved taxonomy or define a lower-layer handling path).

## Paper-Integration-Critic Resolutions (Findings 1–13, second Critic round)

### D49 — Status transition policy (Finding 3)
**Engine accepts any source → destination transition.** No `BoardConfig.allowed_transitions` graph; no `ERR_TRANSITION_FORBIDDEN` code. Brief A §5.6's "unsupported transition" wording re-reads as "invalid status enum value" → `ERR_INVALID_STATUS`. Gates on transition: (a) destination predicate per D15 (`status_predicates`); (b) archival rules per D37 (when destination is `archived`). Predicate or archival failure → `ValidationError`; transition does not occur (atomic per D41). Brief A revision: re-word §5.6 to drop "unsupported transition" language.

### D50 — `create_task` no longer accepts `status` (Finding 8)
**`create_task` engine API has no `status` parameter.** New tasks created at `BoardConfig.entry_status` (new field; must reference a declared status; default `"research"`). Closes the predicate-on-create question (Finding 8) by removing the parameter that created it. Migration / admin / test scenarios use a separate path (Brief C decides; out of Brief B scope). Brief A revision: §5.4 drop `status` parameter from `create_task` signature; AC list affected (verify no AC explicitly depends on creating at non-entry status).

### D51 — `end_work(success)` forbids caller-supplied archival fields (Finding 1)
**`end_work(outcome="success")`:** caller passing `archival_reason` or `archival_refs` raises `ValidationError(code="ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_SUCCESS")`. Engine sets `archival_reason="completed"`, `archival_refs=[]` itself when the auto-advance lands at `archived`. **`end_work(outcome="reject", move_to="archived")`:** full D37 matrix applies to caller-supplied reason/refs. **`end_work(outcome="reject", move_to != "archived")`** and **`end_work(outcome="release")`** and **`end_work(outcome="block")`:** `archival_reason` / `archival_refs` must be absent → `ERR_ARCHIVAL_FIELDS_FORBIDDEN`.

### D52 — `end_work` outcome enum is 4 values (Finding 11)
**`end_work(outcome=...)` accepts: `success`, `reject`, `release`, `block`.** All four release the claim. Invalid value → `ValidationError(code="ERR_INVALID_OUTCOME")`.

- **`success`** (from any non-archive status): auto-advances one step in `BoardConfig.statuses` order. From the last non-archive status (typically `done`): auto-archives with `archival_reason="completed"`, `archival_refs=[]`. Predicate on destination per D15+D41 (atomicity: predicate failure = entire call fails, claim NOT cleared, note NOT appended). Caller may NOT pass `archival_reason`/`archival_refs`/`block_reason`/`move_to`.
- **`reject`**: requires `move_to`; archives if `move_to="archived"` (caller supplies reason/refs per D37); D15 predicate on destination; D41 atomicity; clears claim; `note` appended if set. Caller may NOT pass `block_reason`.
- **`release`**: clears claim, no status change, `note` appended if set. Caller may NOT pass `archival_reason`/`archival_refs`/`block_reason`/`move_to`.
- **`block`**: requires `block_reason: str` (non-empty) → missing or empty raises `ValidationError(code="ERR_BLOCK_REASON_REQUIRED")`. Sets `blocked=true`, `block_reason=<value>`. Optionally accepts `move_to` (forward or backward) — if set, status changes per `move_to` (predicate fires per D15; D41 atomicity); if unset, status unchanged. Clears claim. `note` appended if set. Caller may NOT pass `archival_reason`/`archival_refs`.

`fail` is dropped (orphan-claim foot-gun). Brief A revisions: §5.8 add `block` outcome + `block_reason` parameter + validation rules; §5.8 revise `success` semantics (any-status auto-advance, not done-only); update AC18 wording; new ACs for `block`. AC list edits batched at brief draft.

### D53 — `edit_task(block_reason=...)` retained (F11-edit-α)
**`edit_task` keeps the `block_reason` parameter** for the "set/clear block reason without claim mechanics" use case (admin updating a block reason on an unclaimed task; Cockpit blocking from GUI). Two paths exist intentionally: `edit_task(block_reason=...)` is a **state assertion** (any caller, any time, no claim semantics); `end_work(outcome="block")` is an **agent lifecycle exit** (claimed → blocked + released + optional move).

### D54 — Engine guidance on block + skip-transition (F11-block-guidance + F11-skip-guidance)
**Engine emits guidance per D39 in two new cases:**
- **`end_work(outcome="block")` response** includes guidance string suggesting the agent open an Action-Request or Decision-Request task to surface the blocker for review. Phrasing tunable; intent locked. Reaches every agent regardless of which `share/agents/*.agent.md` they instantiate from.
- **`move_task` or `end_work(reject, move_to=...)` response** includes guidance when the transition skips more than one position in `BoardConfig.statuses` order — e.g., `"transition skipped statuses: todo, in-progress; verify intentional"`. Soft norm; doesn't block.

### D55 — `end_work` on unclaimed task (Finding 12)
**`end_work(outcome="release")` on unclaimed task: succeeds idempotently** (pure no-op — no state written; `updated` NOT advanced; `note` NOT appended even if provided, because there is nothing to annotate). **`end_work(outcome="success"/"reject"/"block")` on unclaimed task: `ValidationError(code="ERR_NOT_CLAIMED")`.** Rationale: `release` is a "ensure not claimed" recovery primitive; it must be side-effect-free when already satisfied. Touching `updated` or appending a note when the task state does not change is misleading and breaks idempotency guarantees (a second identical call would produce different `updated` timestamps).

### D56 — `show_task(section=...)` matches by heading regardless of level (Finding 4)
**`show_task(section=...)` matches by `Section.heading`** (case-insensitive, whitespace-stripped), **regardless of `Section.level`.** All matches concatenated in document order. `body=None` + `missing_sections=[name]` if no match. Multiple matches → `guidance` includes occurrence count per D54-style emission. Predicates (D15) may filter by `Section.level` if a board needs that discrimination; this projection does not. Brief A revision: §5.2 wording "matching `##` heading content" → "matching heading content (regardless of level)".

### D57 — Error code additions to D27 taxonomy
**Adds to D27 named error codes** (plus approved Brief C startup/config additions):
- `ERR_NOT_CLAIMED` (`ValidationError`) — D55.
- `ERR_BLOCK_REASON_REQUIRED` (`ValidationError`) — D52 block validation.
- `ERR_NO_OP` (`ValidationError`) — Brief A §5.5 edit_task no-op rule (already existed implicitly).
- `ERR_BODY_EXCLUSIVE` (`ValidationError`) — Brief A §5.5 body+append_body mutual exclusion.
- `ERR_IDS_EXCLUSIVE` (`ValidationError`) — Brief A §5.1 ids exclusion rule.
- `ERR_SECTION_EMPTY` (`ValidationError`) — Brief A §5.2 empty-string section.
- `ERR_INVALID_STATUS` / `ERR_INVALID_PRIORITY` (`ValidationError`) — enum violations across tools.
- `ERR_INVALID_WAVE_PARAM` (`ValidationError`) — `pick_tasks(wave_size<1 \| max_waves<1)`.
- `ERR_PARENT_NOT_FOUND` / `ERR_DEP_NOT_FOUND` (`ValidationError`) — cross-ref validation per Brief A §7.
- `ERR_ARCHIVAL_REASON_INVALID` / `ERR_ARCHIVAL_REASON_REQUIRED` / `ERR_ARCHIVAL_FIELDS_FORBIDDEN` / `ERR_ARCHIVAL_REFS_REQUIRED` / `ERR_ARCHIVAL_REFS_FORBIDDEN` / `ERR_ARCHIVAL_REF_MISSING` / `ERR_ARCHIVAL_REF_SELF` / `ERR_ARCHIVAL_REF_CYCLE` / `ERR_COMPLETED_REQUIRES_DONE` (`ValidationError`) — D37 archival matrix.
- `ERR_TERMINAL_STATUS_INVALID` (`ConfigError`) — D65: `BoardConfig.terminal_status` not in `statuses` or not the final element.
- `ERR_INVALID_OUTCOME` / `ERR_REJECT_REQUIRES_MOVE_TO` / `ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK` / `ERR_MOVE_TO_FORBIDDEN_ON_SUCCESS` / `ERR_MOVE_TO_FORBIDDEN_ON_RELEASE` / `ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_SUCCESS` (`ValidationError`) — D52 + D51 `end_work` forbidden-parameter matrix.
- `ERR_PREDICATE_FAILED` (`ValidationError`) — D15 destination-status predicate failure on `create_task` (entry-status), `move_task`, `end_work(success/reject/block with move_to)`. Detail field carries predicate name.
- `ERR_ENTRY_STATUS_INVALID` (`ConfigError`) — `BoardConfig.entry_status` does not reference a declared status. Raised at engine init per D50.
- `ERR_INVALID_CLAIM_TIMEOUT` (`ConfigError`) — malformed `claim_timeout` duration string at config load / engine init per Brief C AM-15.
- `ERR_MIGRATION_REQUIRED` (`MigrationRequiredError`) — active board still contains unmigrated `claimed_by` fields at engine init per Brief C C11/AM-12.
- `ERR_ALREADY_CLAIMED` (`ConcurrencyError`) — `start_work` on active claim.
- `ERR_ARCHIVED_NOT_CLAIMABLE` / `ERR_BLOCKED_NOT_CLAIMABLE` (`ValidationError`) — `start_work` validation.
- `ERR_BODY_TOO_LARGE` (`ValidationError`) — D35+D47.
- `ERR_STALE` (`ConcurrencyError`) — OCC token mismatch on Cockpit writes per D22+D46.
- `ERR_NOT_FOUND` (`NotFoundError`) — `show_task` / `edit_task` / `move_task` / `start_work` / `end_work` / `release_task` on missing `id`.

Corrects normalized error-code names from the first-pass paper-integration draft. **D27 names: subclass + code; canonical code names listed here are the locked spelling. There is no `ERR_INVALID_ARCHIVAL_REASON` (the canonical spelling is `ERR_ARCHIVAL_REASON_INVALID`).**

### D58 — `pick_tasks` excludes `blocked==true` (round-4 contract repair)
**`pick_tasks` excludes tasks with `blocked==true`** in addition to the previously-locked exclusions (claimed, archived, `dep_status=="blocked"`). Rationale: a `blocked==true` task cannot be claimed (`start_work` raises `ERR_BLOCKED_NOT_CLAIMABLE` per Brief A §5.7); dispatching it would create an unclaimable wave entry and surface a contract contradiction between dispatcher and claim. Brief A §5.3 and §8 AC22 are revised to add this exclusion (see Brief A Revision List #10).

## Brief A Revision List (locked across all decisions)

When drafting brief.md (M5), Brief A receives the following edits, applied as part of M5/M6 finalization (per D4):

1. Remove AC21 ("non-claimant `end_work` → ToolError") — D11 invariant: no claim identity.
2. §5.4 `create_task` signature: drop `status` parameter — D50.
3. §5.6 `move_task`: re-word "unsupported transition" → "invalid status enum" — D49.
4. §5.8 `end_work` signature: add `block` outcome + `block_reason` parameter — D52.
5. §5.8 `end_work` validation: revise `success` semantics from `done`-only to any-status auto-advance — D52; update AC18 wording.
6. §5.8 `end_work` validation: add validation rules for `block` outcome — D52, D54.
7. §5.2 `show_task` wording: "matching `##` heading" → "matching heading (regardless of level)" — D56.
8. §7 "Cross-cutting contracts": confirm error-code names match D57.
9. AC list: add ACs for `block` outcome (validation, claim release, optional move_to, guidance emission); revise AC18 wording for any-status `success`.
10. §5.3 `pick_tasks` and §8 AC22: add `blocked==true` to dispatchability exclusions — D58 (round-4 contract repair, resolves dispatcher ↔ `start_work` contradiction).
11. §7 decisions C3 `deprecated`/`duplicate` dep effect: remove “engine treats X as dispatchable iff at least one redirect target is done or completed-archived” clause. `dep_status="redirect"` tasks are **always dispatchable**; redirect-chain resolution is agent responsibility at pickup. This is a deliberate KISS simplification (Brief B): computing transitive chain completeness at dispatch time requires unbounded depth traversal and is deferred to the agent, who has full task context when starting work.

### D59 — OrchestratorView extends D9 (round-5 decision-set repair) — RETIRED in M5 cleanup
**Status: RETIRED.** Post-M5 review concluded that adding a third role view for a single method paid architecture cost without enforcement value (single-user system, all agents can call MCP tools regardless). `pick_tasks` is exposed on `AgentEngineView`. Role isolation is documented in the orchestrator skill and the tool's docstring. The MCP adapter no longer carries a view-selection branch for `pick_tasks`.

*Original text retained below for traceability.*
**D9 is extended with a third role view: `OrchestratorView`.** Locks the dispatcher capability into the same role-view model as `AgentEngineView` and `CockpitEngineView`. `OrchestratorView` exposes exactly `pick_tasks` (per D42; the round-3 wave-assembly position is hereby elevated into the locked decision set as part of D9's extension). Accessed via `engine.orchestrator_view()`. The MCP `pick_tasks` tool is dispatched via this view only; not exposed on `AgentEngineView`, not exposed on `CockpitEngineView`. **Naming locked separately by D61.** Rationale: round-4 critic correctly identified that D9 alone defined only two views, while paper and D42 referenced three; D59 closes that gap inside the decision set.

## M5 — Open-Item Locks (Brief B contract closure per O5: no TBD past M5)

### D60 — `pick_tasks` dispatchable-task ordering algorithm
**Greedy by `(priority_rank, age, id)`, deterministic.** Engine sorts dispatchable tasks (per D42+D58 filters: not claimed, not archived, `dep_status != "blocked"`, `blocked != true`) by:
1. `priority_rank` ascending — from `BoardConfig.priorities` order (highest first).
2. `age` descending — oldest `created` timestamp first within priority.
3. `id` ascending — final tiebreak for total order.
Then processes the sorted list per D42 wave-composition rules (size + agent-compatibility + intra-wave dep-disjointness). Replaces D28's `(priority_rank, status_rank, id)` triple with the simpler `(priority_rank, age, id)`: status_rank is unnecessary because `BoardConfig.agent_map` already binds status to a single agent, so wave assembly handles status mixing via the compatibility matrix. Closes paper §7 #1.

### D61 — Role view naming locked: `OrchestratorView` — VACATED
**Status: VACATED** with D59. No `OrchestratorView` exists post-M5 cleanup; naming lock is moot.

*Original text retained below for traceability.*
**The third role view is named `OrchestratorView`.** Alternatives `DispatcherView` / `PlannerView` rejected: "orchestrator" is the consumer agent's name in the existing pipeline (`share/agents/orchestrator.agent.md`); naming the view after the consumer keeps the call site self-documenting (`engine.orchestrator_view().pick_tasks(...)`). Closes paper §7 #2.

### D62 — `BoardConfig.agent_types` shape
**`agent_types: dict[str, str]`** — maps agent name to bucket name. Bucket names are the four labels from D42's compatibility matrix: `"auditor"`, `"builder"`, `"light-flex"`, `"heavy-flex"`. Default mapping mirrors `share/skills/w-orchestration/SKILL.md` "Wave Assembly" section. Engine validates at init: every value in `agent_types` must be a key in `agent_compatibility` (D63), else `ConfigError`. Closes paper §7 #3.

### D63 — `BoardConfig.agent_compatibility` shape
**`agent_compatibility: dict[str, list[str]]`** — maps bucket name to list of compatible bucket names (mutually-parallelisable buckets within a single wave). The relation MUST be symmetric: `b1 in agent_compatibility[b2]` iff `b2 in agent_compatibility[b1]`; engine validates at init, else `ConfigError`. Default value (codifies current orchestrator skill):
```python
{
  "auditor":     ["auditor"],
  "builder":     ["builder", "light-flex"],
  "light-flex":  ["builder", "light-flex", "heavy-flex"],
  "heavy-flex":  ["light-flex", "heavy-flex"],
}
```
A bucket is always self-compatible (allows multiple instances of the same agent type in one wave). Closes paper §7 #4.

### D64 — `BoardConfig.status_predicates` DSL keys (Brief B-locked subset)
**The DSL keys locked by Brief B are exactly those in D15's sketch:**
- `required_sections: list[str]` — each named section (case-insensitive heading match per D26+D56) MUST be present in `body: list[Section]`. Failure → `ERR_PREDICATE_FAILED` with `detail="missing section: <name>"`.
- `require_list_in_section: dict[str, bool]` — named section MUST contain at least one markdown list item (`-`/`*`/`1.`). Failure → `ERR_PREDICATE_FAILED` with `detail="section <name> empty"`.
- `test_section_or_non_impl_tag: list[str]` — task MUST have at least one of the named sections OR carry a tag from `BoardConfig.non_impl_tags`. Failure → `ERR_PREDICATE_FAILED` with `detail="test section missing and no non-impl tag"`.
- `BoardConfig.non_impl_tags: list[str]` (top-level config field, default per D15 sketch) — the tag whitelist consumed by `test_section_or_non_impl_tag`.

Brief B does not lock additional operators. Brief C planning may extend the DSL with new keys (e.g., regex matchers, frontmatter requirements) as concrete decomposition tasks; each extension is a discrete decision, not a Brief B contract drift. Closes paper §7 #5.

### D65 — Terminal-status configurability (`terminal_status` field, default `"done"`)
**`BoardConfig.terminal_status: str = "done"`. Engine validates at init that `terminal_status in BoardConfig.statuses` AND `terminal_status == BoardConfig.statuses[-1]`** (i.e., it must be the last element). Failure → `ConfigError(code="ERR_TERMINAL_STATUS_INVALID")`. Default `"done"` preserves existing OwlBear convention; consumers can rename the terminal column without engine code changes.

This locks two semantics that prior decisions assumed but never stated:

1. The completed-archival gate (the "completed-requires-terminal" gate referenced in paper §2/§3 and AC5/AC6) checks `current.status == BoardConfig.terminal_status` — not a hardcoded literal.
2. D52's `end_work(outcome="success")` definition ("from the terminal status … auto-archives") is now unambiguous: `terminal_status` IS the last non-archive status, so `success` from terminal auto-archives with `archival_reason="completed"`; `success` from any earlier status advances exactly one step in `BoardConfig.statuses` order. There is no second-archival-hop semantics.

*M5 follow-up:* the original D65 locked the literal name `"done"`. Post-M5 consistency review made `terminal_status` symmetric with `entry_status` (configurable, defaulted, init-validated). The error code `ERR_TERMINAL_STATUS_INVALID` remains in D57. AC-NEW-23 (paper §4) is reworded to cover the configurable form.
