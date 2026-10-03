# Delivery N06 — Prepared Interaction Core and Private Local Input

> **Package:** N06 of the
> [execution plan](delivery-redesign-execution-plan.md#n06--prepared-interaction-core-and-private-local-input).
> **Planned on:** `origin/dev` `ac3bf23f9` (N01, N02-A, N02-B and N09-A1 merged; N03-A…C, N04, N05-B,
> N09-A2 not merged; N04-P in progress in another lane). Python 3.14 from the lane `.venv`; FastAPI 0.142.2,
> Starlette 1.7.0, uvicorn 0.54.0, Pydantic 2.13.5, Playwright 1.63.0 with Chromium 153 (`uv.lock`).
> Live Delivery state was not read; no live record is needed by this plan. Rebased on `origin/dev` `634a77be7`:
> it adds only N05-A (`delivery-github`, `publication_provider.py`, forbidden-effect gates); no file or locator
> cited here changed.
> **Status:** draft for the plan gate, revised after Sol plan round 1 ([3.6](#36-plan-gate-dispositions)). Product
> code is unchanged by this phase. User-only confirmation is N03's boundary (PR #360, in revision); N06 consumes it
> and works under either answer of N03 U2 ([1.13](#113-confirmation-channel-under-n03-u2)).
> [U1](#u1--retention-and-privacy-policy-for-private-inputs-and-interaction-evidence) is a recorded engineering
> decision of 2026-10-03. N03 U1 was answered (b) by the user on 2026-10-03 (user waivers satisfy finalization);
> §1.4 keeps interaction requests out of that route.

## 1. Contract

### 1.1 Result

- A **prepared interaction** is a typed engine record bound to one Change, outcome, task, Builder block, Decision
  Request, acceptance scope, registered handler and exact candidate head. Handlers come only from a code registry;
  no request field is ever executed or interpolated into a command.
- The Builder creates the need on its existing request-bearing block route. The engine shows **Needs you** only when
  the handler is registered, its static probe passes on this host, and no writer custody exists. Otherwise the
  Change shows agent work (`waiting-for-chat`) or **Check not available here** with the exact reason (V17).
- Cockpit owns the session. **Help with this step** opens a Cockpit panel that says what will be launched; **Start
  check** launches the registered handler as a child process, passes private inputs only through the child's
  stdin, holds them only in memory, and ends the session on completion, **Not now**, expiry or Cockpit exit.
  Custody ends only once the handler's processes are verified gone (D13). Delivery receives an opaque input
  reference, never a value.
- The user's confirmation counts only through N03's user-only confirmation boundary, the single definition N06
  consumes ([1.13](#113-confirmation-channel-under-n03-u2)). It resolves the linked Decision Request with
  `observed` or `not-observed` as N03's scoped confirmation. Caller- or worker-supplied provenance never counts.
  Machine observations from the handler are recorded separately on the interaction.
- Secrets and private values never appear in chat transcripts, MCP results, logs, receipts, remote snapshots or
  URLs. Cancel, decline and expiry never count as a pass.
- A synthetic handler proves the flow end to end in real Chromium against the built Cockpit bundle.

### 1.2 Requirements

| ID | Requirement | Source |
| --- | --- | --- |
| R1 | Typed prepared-interaction contract with every programme §9.1 field (mapping in [1.5](#15-prepared-interaction-contract)) | Programme §9.1 (`change-continuation-delivery-redesign.md:1135-1154`); P15; WP5 step 1 |
| R2 | Handlers come from a code registry, never shell text from a request | Execution plan §5 N06; §9.1 Handler row; WP5 step 1 |
| R3 | Preparation is agent work; **Needs you** only once the step is actionable | Execution plan §5 N06; §9.1 (`:1152`); WP5 step 2; U3 (`:769`) |
| R4 | Local input through a Cockpit (or loopback) form with origin checks and a one-time or session-bound token; an opaque input reference; expiry and cancel | §9.3 steps 1–4, 6 (`:1179-1185`); P16; V22 |
| R5 | No secrets in transcripts, logs, receipts or URLs; credential-bearing URLs rejected; destinations cannot be widened by form input | §9.3 steps 2–3, 5; V22; execution plan §5 N06 |
| R6 | Human confirmation recorded separately from machine observation, only through N03's user-only confirmation boundary; a click cannot assert machine success and neither a machine, a worker nor a caller can fabricate a confirmation | §9.3 step 7; §9.1 Evidence split; [N03 plan](delivery-n03-plan.md) I6, §1.5 and its user-only boundary (PR #360) |
| R7 | Cockpit offers **Help with this step**, **Not now**, **Explain existing evidence** and **Check not available here** | Execution plan §5 N06; §4.2 (`:860`); §9.2 (`:1172`); §9.4 (`:1191`); V17 |
| R8 | Assisted check with unavailable handler or tool, or no agent host: agent or host-needed state, never **Needs your evidence**, no fake launch | V17 (`:1552`) |
| R9 | Private URL or credential-like input (query, fragment, encoded component) rejected; expired session; cancelled sign-in; no secret in transcript, log or receipt; only owned resources cleaned; cancel is not pass | V22 (`:1557`); execution plan §5 N06-B |
| R10 | Binding to the candidate and its resources; a changed candidate makes the result stale, never attached to the new candidate | §9.1 (`:1154`); execution plan §5 N06 "P must settle" |
| R11 | Every new readiness reason, action or status ships with its `workItems.ts` mirror, rendering, component test and parity assertion; every new frontier-writing operation joins the mutability policy | Execution plan §1.4 |
| R12 | Every changed persisted family registers a version owner; migrations run through the N02 core; LC full form | Execution plan §1.3; [N02 plan](delivery-n02-plan.md) I2, I3, D3 |
| R13 | Pause prevents new interaction sessions and drains open ones | Programme §4.2 Pause; [N09 plan](delivery-n09-plan.md) §1.11 K1–K3 |
| R14 | Support baseline: Python 3.14; Chromium-only Cockpit; macOS and Ubuntu; handler launch portable | Execution plan §1.1 |
| R15 | N06 defines the interface N07's B1 runner builds on; no B1 code in N06 | Execution plan §5 N06, N07; §3 traceability (`:449`) |
| R16 | Session custody ends only after the handler's owned processes are verified gone; restart-safe process identity; containment when closure is unknown | Programme §5.2; V22 (owned cleanup); [N08 plan](delivery-n08-plan.md) D12 |

### 1.3 Invariants

- **I1 No private value at rest.** Private input values exist only in Cockpit process memory for the open session
  and in the handler's stdin pipe. They are never written to Delivery state, the remote snapshot, MCP or HTTP
  responses, logs, URLs, process arguments or environment variables (P5), or to any file.
- **I2 Registry-only execution.** The handler argv, environment allowlist, working directory and probe come from
  the registry entry. Allowed placeholders are engine-derived (`{candidate_worktree}`, `{python}`); request text,
  input values and agent text are never interpolated.
- **I3 One confirmation boundary.** A resolution counts as a user confirmation only when N03's boundary recorded it
  (§1.13). `open`, `start`, `postpone` and `stop` are Cockpit HTTP operations behind the guard (D5) and the session
  nonce; none is a confirmation, and the nonce binds a panel to a session, not to a user. Worker-supplied
  resolutions, MCP `answer` arguments and Cockpit `answer` bodies never resolve an interaction-linked request.
  MCP exposes interactions read-only apart from N03's boundary tool.
- **I4 Cancel is not pass.** Not now, decline, expiry, session loss and handler failure never resolve the linked
  request. Only a boundary confirmation resolves it, with `observed` or `not-observed`; only `observed` can support
  a satisfying N03 `manual-procedure` result, and no outcome can confirm an N03 waiver (§1.4).
- **I5 Exact candidate.** An interaction is bound to `candidate_head` (the block's `resume_commit`, which must equal
  the branch head), the contract's current acceptance versions and the handler digest. Any change makes it
  `stale`; `confirm` and `complete` refuse a stale interaction.
- **I6 Session custody excludes writers.** An unexpired interaction session is a Change custody owner: it refuses to
  open while any writer, claim, Finalizer attempt, continuation action, publication lease or recovery fence exists,
  and every such acquisition refuses while it is open (programme §5.2). Custody ends only when the handler's
  processes are verified gone (D13); expiry, completion or Cockpit exit alone never release it.
- **I7 Bounded, non-sensitive portable records.** Interaction records and machine observations contain only
  registry-declared identifiers, enums, digests, heads, times and bounded counts. No handler-authored free text.
- **I8 Version widening.** Families widen their version literal; old instances validate unchanged and are
  constrained to old content; no stored byte or identity changes (N03 I1, I2).
- **I9 Gate first.** N02 I1 and I5 unchanged; N06-A adds one format-marker step and the widened versions.

### 1.4 Relation to `DeliveryRequest` (programme "P must settle")

An interaction is attached to one Decision Request. Nothing new is added to `DeliveryRequest` or `DeliveryBlock`.

| Element | Rule |
| --- | --- |
| Creation route | The Builder blocks on the existing request-bearing route (`BlockDelivery.request`, `runtime_models.py:1539-1551`; settlement `runtime_settlement.py:250`). The request is a Decision Request whose N03 `applies_to` names the acceptance criteria and `procedure = "interaction-handler:<handler_id>@<version>"` |
| Recognition | Block settlement parses `applies_to.procedure` with `interaction_registry.parse_procedure`. A prefix match that does not resolve to a registry entry, options that differ from the handler's two fixed outcome options, a summary other than the registry `confirmation_question`, a request that already carries a `resolution`, criteria that are not current, or a block without `resume_commit` equal to the branch head (`runtime_settlement.py:405`) refuses the block with `interaction-request-invalid`; nothing is written |
| Reserved `none` | `interaction-handler:none@1` declares a human-only check that no registered handler can perform. It creates an interaction in `unavailable` / `no-registered-handler` (V17) instead of a generic Action Request |
| Engine record | Settlement writes `DeliveryInteraction` ([1.6](#16-persisted-records)) in the same transaction as the block |
| Resolution | Only N03's boundary resolves the request (§1.13), with `selected_option_id` = outcome, and only through `confirm_interaction`'s checks. Every other resolution of a linked request (MCP or Cockpit `answer` arguments, `portfolio_application.py:1340`; a worker-supplied `resolution`) is refused with `ERR_DELIVERY_INTERACTION_CONFIRMATION_ROUTE` or `interaction-request-invalid` |
| Fabrication routes | Both Builder block routes store the worker's `DeliveryRequest` verbatim, `resolution` included (`runtime_reads.py:710-731`, `runtime_settlement.py:524-558`), and MCP `answer` passes caller-set `provenance` (`target_server.py:442-460`). N03's boundary makes neither count for any request, interaction-linked or ordinary, waiver requests included (G14). N06-A also refuses a pre-resolved linked request at block time and pins both routes for both request kinds with assembled tests (§3.2) |
| Evidence | The Builder, reacquired for the same task, records N03 schema-2 observations: one `manual-procedure` with `human-confirmed` provenance and `confirmation: {kind: request-resolution, request_id}` (N03 I6), and copies of the interaction's machine observations with `procedure_registration_digest` = handler digest. Locator `request:<request_id>` (an existing N03 scheme) |
| Private input | Never enters a request. Request answers are persisted and published (`DeliveryRequestResolution.response_text`, `runtime_models.py:821-837`) |
| Waiver (N03 U1 (b)) | An interaction-linked request is never a waiver confirmation. Under N03 U1 (b) a `waived` observation with a resolved user-confirmed request satisfies finalization, so a genuine `not-observed` confirmation would otherwise turn a failed check into a pass. A `waived` observation whose `confirmation` cites an interaction-linked request is refused (`interaction-request-not-waiver`); a waiver uses its own N03 request, confirmed through the same boundary. This is a semantic rule; protection against fabricated confirmations is the boundary (row above) |
| Action Requests | Unchanged for non-interactive human operations. Skill text forbids asking for URLs, hostnames, credentials or tokens in any request answer |

### 1.5 Prepared-interaction contract

Programme §9.1 fields and where each lives:

| §9.1 field | N06 representation |
| --- | --- |
| Identity/version | `interaction_id` (engine digest), `change_id`, `outcome_id`, `task_id`, `request_id`, `block_id`, `candidate_head`, acceptance refs with versions, handler `id@version` and `digest`; the frontier digest versions every write |
| Purpose | Registry `purpose` (one sentence) |
| Why human | Registry `why_human` (one sentence) |
| Handler | Registry entry: `handler_id`, `version`, `argv`, `env_allowlist`, `cwd`, `probe`, `timeouts`, `digest` = sha256 of the canonical entry |
| Preparation | Agent: the Builder prepares candidate, build and harness before blocking. Engine: static probe (platform, executables on `PATH`, candidate worktree present) before **Needs you**. Cockpit: lease at **Help with this step**; launch only at **Start check**, after the panel showed `launch_summary` (§9.1 authorization before an external effect) |
| Input descriptors | `InteractionInput{name, label, kind: url\|text\|choice, required, validation, sensitivity: private\|public}`; `public` only for `choice` |
| User step | Registry `user_step` (one instruction) and `human_step: sign-in\|confirmation` |
| Evidence split | Machine: handler `observation` messages, registry-declared kinds, recorded by `complete`. Human: the request resolution recorded by `confirm` |
| Alternatives | **Not now** (`postpone`), **Explain existing evidence** (N03-C projection of the scoped criteria), **Check not available here**, **Change requirements** (N04 control, when present). Declining never means success |
| Resume | `complete` releases custody and clears the block; continuation reacquires the same Builder task with the interaction in its context |

**Registry** (`owlbear_delivery.interaction_registry`, leaf; imports Pydantic and the stdlib only):

- `InteractionHandlerDescriptor` fields: `handler_id`, `version`, `purpose`, `why_human`, `launch_summary` (what
  starting the check launches or accesses), `human_step`, `user_step`, `confirmation_question`,
  `outcome_options` (fixed `observed`, `not-observed` with labels), `inputs`,
  `observation_kinds` and `label_allowlist`, `target_classes`, `platforms` (`macos`, `linux`), `resources`
  (names only; custody owned by the declaring package), `argv`, `env_allowlist`, `cwd` (`candidate-worktree` or
  `temporary`), `probe` (`executables`, `platforms`, `candidate_paths`), `timeouts` (`start`, `human_step`,
  `cleanup`), `failure_codes` (code → `repairable` or `environment`).
- Registration validation refuses: an input named or labelled like a credential (`password`, `passcode`, `otp`,
  `mfa`, `secret`, `token`, `cookie`, case-insensitive); a `public` non-choice input; a placeholder other than the
  allowed ones; a label outside the `N03` label pattern; a duplicate `handler_id@version`.
- `DEFAULT_INTERACTION_HANDLERS` holds only the reserved `none` entry in N06. N07 adds B1. Tests inject a synthetic
  registry through composition (`load_delivery_application(..., interaction_handlers=...)`, Cockpit `run(...)`).

**Input validation** (`owlbear_delivery.interaction_inputs`, leaf): `url` is parsed with `urllib.parse.urlsplit`,
never by pattern over the raw string, and refused if the parse is not a lossless round trip. It accepts `https`
only by default; rejects userinfo; rejects any fragment (`#…`, including an empty one) unless the descriptor
declares `fragment: allowed`, which N06 never registers; rejects query keys matching
`token|access_token|id_token|code|session|sig|signature|password|pwd|key|apikey|auth|sso|saml` (case-insensitive)
after `parse_qsl` percent-decoding, and keys or values that still contain `%` after one decoding (double encoding);
at most 2048 characters; host by the descriptor's static `host_policy`
(`any-host`, `suffix-allowlist(...)` or `handler-validated`, the last reported back by the handler as a bounded
`destination-not-admitted` code), compared after IDNA normalization. `text` is length- and pattern-bounded;
`choice` is an enum. Models use `SecretStr`, `hide_input_in_errors=True`, and errors are rendered only with
`include_input=False` (P4b).

### 1.6 Persisted records

| Family (N02 ID) | Change | Before → after | Old records | Portable |
| --- | --- | --- | --- | --- |
| `frontier` | Top-level `interactions: tuple[DeliveryInteraction, ...]` (≤ 64, omitted when empty) | N03's 19 → widen 19, 20 | 19 (and N03's `readable-legacy` 18) parse unchanged; a validator rejects `interactions` below 20 | Yes |
| `snapshot` (remote) | Embeds the frontier | N03's 3 → widen 3, 4 | Native parse | — |
| handoff change-intent receipts | Embed whole frontiers | N03's 2 → widen 2, 3 (normalized delta per N03 §1.7) | Unchanged | — |
| `coordination` | `interaction_session: ChangeInteractionSession \| None` (omitted when None) | N09-A2's 2 → widen 2, 3 | Unchanged; validator rejects the field below 3 | No (host-local) |
| `format` marker | `format-N-to-N+1` marker-only migration | N assigned at merge (G3) | — | — |
| binding-embedding receipts, `DeliveryRequest`, `DeliveryBlock`, observations, `result_receipt` | Unchanged | — | — | — |

`DeliveryInteraction` (schema 1, nested in the frontier family; registered in `NESTED_MODELS`):

| Field | Meaning |
| --- | --- |
| `interaction_id` | `_receipt_digest` over `change_id`, `outcome_id`, `task_id`, `block_id`, `request_id`, `procedure`, `candidate_head`, `created_at` |
| `handler_id`, `handler_version`, `handler_digest` | Registry identity; `None` for `none` |
| `procedure`, `acceptance` | Copied from `applies_to` |
| `candidate_head` | The block's `resume_commit` |
| `status` | `needs-session`, `unavailable`, `postponed`, `resolved`, `completed`, `stale`, `preparation-failed` |
| `status_reason` | Enum: `no-registered-handler`, `handler-not-registered-here`, `platform-unsupported`, `tool-missing`, `candidate-missing`, `user-postponed`, `session-expired`, `session-lost`, `handler-failed`, `head-changed`, `contract-changed`, `handler-changed`, `block-cleared`, `paused`, or a registry `failure_codes` key |
| `outcome` | `observed`, `not-observed` or None (mirrors the authoritative request resolution) |
| `observations` | ≤ 16 `DeliveryInteractionObservation{kind, result: passed\|failed, observed_at, platform, labels, target_class}`; kinds and labels from the registry |
| `created_at`, `updated_at`, `completed_at` | Times |

`ChangeInteractionSession` (coordination, host-local custody): `interaction_id`, `session_id` (128-bit random),
`holder{pid, port, started_at}` (the Cockpit instance), `handler{pid, pgid, create_time, argv_digest}` (set at
spawn; `create_time` from `psutil`, as N08 D12), `candidate_head`, `opened_at`, `expires_at`, `state`
(`awaiting-input`, `starting`, `awaiting-human`, `finishing`, `closing`, `contained`), `input_ref` (128-bit random,
never derived from a value), `inputs_provided` (descriptor names only). No digest, hash or prefix of any private
value is stored, because low-entropy values such as internal URLs could be recovered from one. `argv_digest`
covers the registry argv only, which never carries a value (I2).

### 1.7 Interfaces and error cases

| Interface | Owner | Behavior |
| --- | --- | --- |
| Block settlement with an interaction-linked request | `runtime_settlement.py` (request-bearing block, `:250`, `:473-528`) | Creates the interaction (`needs-session`, or `unavailable` for `none`) in the block's transaction; refusal `interaction-request-invalid` with a bounded field code |
| Readiness | `application_readiness.py`, `work_items.py` | New `DeliveryReadinessReason` values: `interaction-ready` (next actor you, action `help-with-step`), `interaction-in-progress` (session open), `interaction-unavailable`, `interaction-postponed` (action `help-with-step`), `interaction-handler-unverified` (session `contained`; next actor you; action `help-with-step` re-runs the exclusion check), `interaction-preparation-failed` and `interaction-stale` (next actor agent). New `WorkItemActionKind.HELP_WITH_STEP`. Progress: ready, in progress, unavailable and postponed → `needs-sign-in` when `human_step` is sign-in, else `needs-decision`; `starting` session → `preparing`; agent reasons → `waiting-for-chat` (M12/M13 of the N09 table). Selection order: programme §5.4 rows 8–9 |
| Continuation | `application_acquisition.py:263` | An interaction reason returns `human` (ready, in progress, unavailable, postponed) with no launch; `interaction-preparation-failed` and `interaction-stale` reacquire the same Builder task as a counted retry with failure code `interaction-preparation-failed` or `interaction-stale` (D03 retry ledger). A session in any state, `closing` and `contained` included, makes every other acquisition `busy` |
| `open_interaction_session(change_id, interaction_id, holder, expected_frontier_digest)` | new `application_interactions.py` mixin | Pause-gated custody start (N09-A2 K3): commits the coordination lease with the frontier as an exact no-op participant. Refuses `ERR_DELIVERY_INTERACTION_NOT_READY` (status), `_UNAVAILABLE` (static probe), `_STALE`, `_SESSION_BUSY` (another unexpired session or any writer custody), `ERR_DELIVERY_CHANGE_PAUSE_REQUESTED`. A `postponed` interaction reopens through this call |
| `update_interaction_session(..., session_id, state, input_ref=None, inputs_provided=(), handler=None)` | same | Session-id CAS; refuses foreign sessions; refuses `starting` without a handler identity; an expired session accepts only the moves to `closing` and `contained` |
| `confirm_interaction(..., session_id, outcome, confirmation, expected_frontier_digest)` | same | Called only by N03's boundary adapter with that boundary's confirmation record (§1.13); refuses without one. Re-checks I5 and that the session is `awaiting-human`; resolves the linked request; interaction `resolved`. Identical replay returns the stored resolution; a different outcome conflicts (`_CONFIRMATION_CONFLICT`) |
| `complete_interaction(..., session_id, observations)` | same | Validates kinds, labels and bounds against the registry; status `completed`; session `closing`; clears the block. Replay with identical observations returns the stored record |
| `postpone_interaction(..., session_id \| None, reason)` | same | User Not now, expiry, session loss, pause drain: status `postponed` with reason; session `closing`; request stays unresolved |
| `fail_interaction_session(..., session_id, failure_code)` | same | `preparation-failed` (repairable code) or `unavailable` (environment code); session `closing` |
| `release_interaction_session(..., session_id, exclusion)` | same | Releases the lease only with an exclusion proof (D13): no live process matches the recorded handler `pid` + `create_time`, and no live process is in its `pgid`. Otherwise `ERR_DELIVERY_INTERACTION_HANDLER_ALIVE`; the lease stays |
| `contain_interaction_session(..., session_id, reason)` | same | Closure unknown (identity unreadable, `psutil` failure, kill refused): session `contained`; lease kept; Change shows attention `interaction-handler-unverified` with the recorded pid; the user or a later Cockpit re-runs the exclusion check; never auto-released by time |
| `answer` | `portfolio_application.py:1340`; MCP and Cockpit callers | Refuses interaction-linked requests: `ERR_DELIVERY_INTERACTION_CONFIRMATION_ROUTE`. For every other request, N03's boundary decides whether a resolution counts as user-confirmed |
| Builder block routes | `runtime_reads.py:710-731`, `runtime_settlement.py:524-558` | A linked request carrying a `resolution` is refused `interaction-request-invalid`; ordinary requests follow N03's boundary |
| `submit_result` / `publish_result` admissibility | `delivery_runtime.py` facade; N03 `evidence.py` | Adds: an observation whose `procedure_registration_digest` equals a handler digest needs a `completed` interaction in the same outcome with that digest, `candidate_head == exact_commit`, and an equal machine observation (kind, result, platform, labels, target class); a `human-confirmed` observation citing an interaction-linked request needs `outcome = observed` and a non-stale completed interaction; a `waived` observation may not cite an interaction-linked request (§1.4). Reasons `interaction-evidence-unmatched`, `interaction-not-completed`, `interaction-stale`, `interaction-request-not-waiver` join N03's bounded `gaps` |
| Projection | `work_items.py`, `application_models.py`, MCP `target_models.py`, Cockpit `target_models.py` | `DeliveryInteractionView{interaction_id, status, status_reason, handler purpose, why_human, user_step, human_step, confirmation_question, inputs (name, label, kind, required; never values), acceptance refs, candidate_head, session (state, expires_at, inputs_provided, input_ref; holder only as "this Cockpit" or "another Cockpit"), observations}` on `WorkItemDetailView`, `get_change` and the build context |
| Cockpit HTTP (N06-B) | new `owlbear_cockpit/routes/interactions.py`, `interaction_sessions.py` | `POST /api/changes/{c}/interactions/{i}/session` (Help; lease; returns descriptors, `launch_summary` and the nonce in the JSON body; launches nothing), `POST …/start` (Start check; inputs, possibly none; launches), `GET …/session`, `POST …/postpone`, and the confirmation step of §1.13. Nonce header `X-OwlBear-Interaction-Session`, compared with `secrets.compare_digest`. The nonce is a panel-to-session binding, never user authorization. Error envelope `{code, detail, authority: "delivery", retry_safe}` with bounded field codes, never input values |
| Loopback request guard (N06-B) | new `owlbear_cockpit/request_guard.py`, installed by `run()` (`main.py:311`) | Every request: `Host` ∈ {`127.0.0.1:<port>`, `localhost:<port>`} else 403 `COCKPIT_HOST_REJECTED`. Unsafe methods: a present `Origin` must equal `http://127.0.0.1:<port>` or `http://localhost:<port>`, and a present `Sec-Fetch-Site` must be `same-origin` or `none`, else 403 `COCKPIT_ORIGIN_REJECTED`. Header-less local clients pass (P8), so the guard is a cross-site defense only, never a user-presence check. Under N03 U2 (a) the confirmation route additionally needs the boundary's session cookie (§1.13) |
| Cockpit access log (N06-B) | `run()` (`main.py:372`) | `uvicorn.run(..., access_log=False)` plus a Cockpit access logger emitted by the outer ASGI wrapper that logs method, route template (or `unmatched`), status and duration only, never the raw path, query string or headers; installed before the guard so rejected requests are logged the same way. uvicorn's error logger stays on; its malformed-request warnings carry no request target (verified in N06-B) |
| Handler protocol v1 (N06-B) | new `owlbear_delivery/interaction_protocol.py` | JSON Lines, ≤ 16 KiB per line, ≤ 256 lines. Cockpit → handler: `start{protocol: 1, interaction_id, candidate_head, inputs}`, `human-step-complete{outcome}`, `cancel{}`. Handler → Cockpit: `ready`, `awaiting-human`, `observation{kind, result, platform, labels, target_class}`, `finished`, `failed{code}`. stdin EOF means cancel: clean up and exit (P7). Unknown messages, oversize lines or values echoed back end the session as `handler-failed` |
| Handler launch (N06-B) | `owlbear_cockpit/interaction_sessions.py` | `subprocess.Popen(argv, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=allowlist, cwd=…, start_new_session=True)`; the handler identity (pid, pgid = pid, `psutil` create time) is committed to the session before the `start` message is written, and a spawn whose identity cannot be committed is killed before any input is sent; inputs only in `start`; stderr kept in a 4 KiB memory ring, never logged or returned; deadlines per registry; close sends `cancel` (or `human-step-complete`), closes stdin, waits the cleanup deadline, then `killpg(SIGKILL)` and runs the exclusion check (D13) |

Errors keep the existing envelopes: core `DeliveryInteractionError(DeliveryRuntimeConflictError)` with
`ERR_DELIVERY_INTERACTION_*` codes mapped by MCP `_raise` (`target_server.py:1243-1250`) and Cockpit `_http_error`
(`target_work.py:819-835`).

### 1.8 Session lifecycle

| From | Event (channel) | To | Effects |
| --- | --- | --- | --- |
| — | Builder block with linked request (MCP settlement) | `needs-session` or `unavailable` | Block, request, interaction in one transaction |
| `needs-session`, `postponed` | Help with this step (Cockpit `open`) | session `awaiting-input` | Lease; nonce in memory; panel shows `launch_summary` and inputs; nothing launched |
| session `awaiting-input` | Start check (Cockpit `start`) | session `starting` | Validate; spawn; handler identity committed; `start` message on stdin; `input_ref`; Cockpit drops its reference |
| session `starting` | handler `awaiting-human` | session `awaiting-human` | Panel shows the confirmation question |
| session `awaiting-human` | boundary confirmation (§1.13) | `resolved`; session `finishing` | Request resolved; `human-step-complete` sent |
| session `finishing` | handler `finished` | `completed`; session `closing` | Observations; block cleared |
| any open session state | Not now (`postpone`) | `postponed` / `user-postponed`; session `closing` | `cancel` |
| any open session state | `expires_at` passes (Cockpit timer) | `postponed` / `session-expired`; session `closing` | `cancel` |
| any open session state | handler `failed`, exit or protocol violation | `preparation-failed` or `unavailable`; session `closing` | By registry code |
| session `closing` | exclusion verified (D13) | lease released | Only now may another session or writer acquire the Change |
| session `closing` | cleanup deadline passes | still `closing` | `killpg(SIGKILL)`; exclusion check again |
| session `closing` | exclusion cannot be verified | session `contained` | Lease kept; attention `interaction-handler-unverified` |
| any session state | Cockpit exits (clean) | as Not now or `session-lost`; session `closing` | Shutdown hook runs close and the exclusion check before exit; if it cannot finish, the lease stays |
| any session state | Cockpit dies (SIGKILL) | unchanged until a Cockpit starts | Handler sees EOF (P7), but nothing is released by time: the next Cockpit start, or `open` on that Change, finds the holder dead (pid + `started_at`), kills the recorded group, runs the exclusion check and moves the session to `closing` → released, or to `contained`. Interaction becomes `postponed` / `session-lost`, or `preparation-failed` / `session-lost` if it was `resolved` |
| `resolved` (session `finishing`) | session lost before `finished` | `preparation-failed` / `session-lost` | Block clears as a counted same-task Builder retry after release; the resolution cannot support a result |
| any | head, contract or handler change | `stale` | Refuse confirm and complete; Builder retry |
| any | operator clears the block | `stale` / `block-cleared` | Session cancelled |
| `needs-session` | pause request | unchanged; `open` refused | Open sessions drain (K2) |

Per [U1](#u1--retention-and-privacy-policy-for-private-inputs-and-interaction-evidence) (a): session TTL
15 minutes by default, hard maximum 60 minutes, set per handler within the maximum. The TTL bounds the human step
and private-input lifetime; it never bounds custody, which ends only at exclusion (D13).

### 1.9 Existing owners to reuse

`BlockDelivery` and request-bearing settlement (`runtime_settlement.py:250`, `:405`); N03 `applies_to`,
`DeliveryAcceptanceRef`, evaluator and projection; `_receipt_digest` (`runtime_models.py:1719`); `RuntimeTransaction`
with an exact no-op participant (`acquire_continuation_action` pattern, N09 §1.11); N09-A2's pause request and K2/K3
inventory; D03 retry ledger and same-task reacquisition; `ChangeContinuationAction.host_id/session_id`
(`workspace_models.py:551-571`) as the holder pattern; the N02 registry, gate, `delivery-migrate` and `delivery-lc`;
Cockpit's error envelope and `handle_target_validation_error` (`target_work.py:845-858`), which already returns a
fixed body for `/api/changes`; the instance record pattern (`main.py:211-216`); `Client(assemble_target_server(...))`,
the HTTP test client and the maintained E2E stack (`e2e/support/start-work-portfolio-stack.mjs`).

### 1.10 Contracts for successors

**N07 (B1 assisted-check runner)** builds on exactly these N06 surfaces:

1. One `InteractionHandlerDescriptor` for B1 added to `DEFAULT_INTERACTION_HANDLERS`: `argv` runs the candidate's
   handler inside `{candidate_worktree}`; `human_step: sign-in`; one `url` input, `private`, with a `host_policy`;
   `target_classes` (for example `sharepoint`, `confluence`); `platforms: (macos,)`; `resources: (edge-profile,)`;
   observation kinds for launch, restart and owned cleanup; failure codes classified repairable or environment.
2. The candidate-side handler implements protocol v1 from its own source, reads inputs only from `start`, never
   echoes them, treats stdin EOF as cancel, and reports only registry-declared kinds and labels.
3. Profile custody and cross-Change contention for `edge-profile` are N07's: the N06 lease ends when the session
   ends and does not prove the browser or profile was released.
4. N07-B's evidence reassessment uses N04 applicability over interaction-backed observations; N06 adds no
   applicability rule.
5. N02 U1 and U2 were answered (a): this repository's live controller, Cockpit included, is pinned and upgraded
   through `/upgrade-delivery`, so Cockpit runs the pinned release. Whether candidate code launched from it
   needs a launcher change is N07's question (G8).

**N09-B** lists **Help with this step** and the interaction reasons in its capability inventory and keeps
`/continue-change`'s `human` yield for them. **N04** maps interaction-backed observations like other `manual-procedure`
and `command` evidence; an activation makes open interactions `stale`. **N08-B** does not mount interaction routes in
degraded mode. **N10** covers V17 and V22 in the cumulative matrix; the real B1 device run is N10-H.

### 1.11 Exclusions

B1 handler, synthetic sites and Edge profile custody (N07); evidence applicability after revision (N04); the
**Change requirements** control (N04); prompt retirement (N09-B); generic interactive-browser tools and B5's policy;
OS keychain storage; a separate loopback form server, runner process or Unix-socket channel (D1); defining a
user-only confirmation mechanism (N03's boundary, §1.13); confirmation through chat text; Windows.

### 1.12 Decisions

Agent-settled with probe evidence:

- **D1 Cockpit owns the session** (P2, P3, P7, P8). Cockpit already is the user's trusted local UI, its SPA may only
  call its own origin (CSP `connect-src 'self'`, `vite.config.ts:10-24`), and programme §4.2 allows preparation that
  needs no running agent. One process holds the form, the in-memory values and the handler pipe, so no secret
  crosses a process boundary except the handler's stdin. The §9.2 controls map directly: **Start check**,
  **Not now**, **Explain existing evidence**. Rejected: a runner-hosted loopback form (a second origin;
  a launch token in a URL fragment; cookies set by any `127.0.0.1` port are sent to every other port, P2); a runner
  reached over a Unix socket (works, P3, but adds a bearer file, a per-user session directory that must be
  ownership-checked on shared `/tmp`, and a second copy of each value); an agent-launched runner (the continuation
  controller has no terminal tool, `orchestrator.agent.md:8`, and a worker would have to stay alive across the human
  step, which no host probe has shown).
- **D2 Interaction attached to a Decision Request** ([1.4](#14-relation-to-deliveryrequest-programme-p-must-settle)).
  Reuses the Builder block route, retained scoped confirmations and N03's evaluator; no request or block schema
  change; no binding-embedding receipt widens.
- **D3 No nested evidence schema change.** N03 §1.9 anticipated `confirmation.kind = interaction` and an
  `interaction:` locator scheme. With D2 the confirmation is N03's request resolution and the locator is
  `request:<id>`; the extra binding to candidate and handler is an admissibility rule (§1.7). N03's G5 closes here.
- **D4 Confirmation through N03's boundary only.** The MCP `answer` tool accepts caller-set
  `provenance: user-confirmed` (`target_server.py:442-460`; Cockpit `AnswerRequestBody` defaults it,
  `target_models.py:381`), and both Builder block routes store a worker-supplied `resolution` verbatim
  (`runtime_reads.py:710-731`, `runtime_settlement.py:524-558`). None of these can separate a user's confirmation
  from an agent call, for linked or ordinary requests. N06 therefore defines no confirmation channel of its own:
  `confirm_interaction` accepts only N03's boundary record (§1.13), `answer` refuses linked requests, block
  settlement refuses pre-resolved linked requests, and N03's boundary governs every other request, waivers
  included. Round 1 of this plan made a Cockpit-only route the boundary; that was wrong (P10).
- **D5 Loopback request guard for all of Cockpit** (P2, P8). Cockpit has no middleware (`main.py:57-62`). From any
  page on another loopback port, Chromium executes body-less cross-origin POSTs such as
  `POST /api/changes/{id}/publication/ready` (`target_work.py:638-640`), sending `Sec-Fetch-Site: same-site`; a
  DNS-rebinding host reaches handlers with its own `Host`. FastAPI's default strict content type blocks forged JSON
  bodies (P2; `fastapi/routing.py:448-461`). The interaction routes need the guard, and a per-route guard would
  leave forgeable siblings in the same app, so it is installed once in `run()`. Same-origin pages and header-less
  local clients are unaffected (P8); `TestClient`-based suites that do not install it are unchanged. The guard
  defends against other web origins only. Any local process can omit `Origin` and read the nonce from `open`, so
  neither the guard nor the nonce shows that a user acted (P10). The guard protects only Cockpits started from a
  release that contains it: the frozen live controller keeps its unguarded Cockpit until an authorized
  `/upgrade-delivery` (N02 U1 (a)), and F1 stays open on it until then.
- **D6 Layout** ([1.6](#16-persisted-records)). Portable, non-sensitive interaction records in the frontier;
  host-bound custody in coordination; widening, no rewrite (N03 D3).
- **D7 Preparation split.** Agent preparation is the Builder's work before it blocks and its repair after
  `preparation-failed`. The engine's static probe gates **Needs you**. Cockpit launches only at **Start check**,
  after the panel stated what will be launched: the authorization §9.1 requires before an external effect.
- **D8 Stale over reattach.** A changed candidate never inherits an interaction (I5); the Builder re-verifies.
- **D9 Inputs through stdin only** (P5: a child's argv and environment are readable by the same user; stdin is not).
- **D10 Empty product registry in N06.** Only the reserved `none` ships; synthetic handlers live in tests, so no
  product Change can cite synthetic evidence.
- **D11 No handler free text in portable records** (I7): portable state is published to the configured remote.
- **D12 Execution-plan deltas** ([3.5](#35-execution-plan-deltas-and-false-premises)): one added prerequisite, no
  re-split.
- **D13 Custody until exclusion.** Expiry, completion and Cockpit exit start closing; only a verified exclusion
  releases the lease. The session records the handler's `pid`, `pgid` and `psutil` create time before any input is
  sent (restart-safe identity, as N08 D12). Exclusion holds when no live process has the recorded pid with that
  create time and no live process with a create time at or after it is in the recorded group. Group members are
  killed with `killpg(SIGKILL)` only while that identity check holds, so a reused pid is never signalled. If the
  check cannot run or a member survives the kill, the session is `contained`: the lease stays, the Change shows
  `interaction-handler-unverified`, and no timer releases it. A dead Cockpit's session is recovered by the next
  Cockpit start or `open` (holder pid + `started_at` no longer live), never by elapsed time. Residual: a handler
  that leaves its process group (`setsid`, double fork) escapes this check; registry handlers are repository code,
  and N07 owns Edge profile custody (§1.10 item 3).

#### U1 — Retention and privacy policy for private inputs and interaction evidence

**Decided 2026-10-03: inputs (a), evidence (a).** Settled as an engineering decision: the user ruled that it has
one defensible answer and needs no user decision; it was listed to the user on 2026-10-03 without objection. The
execution plan (§7) had reserved this decision for N06.

- **Status quo:** no interaction exists. Request answers (`response_text`) are persisted in the frontier and
  published to the remote state branch; a user who types a URL into an Action Request publishes it.
- **Problem:** the programme fixes that secrets go only to the real site and that inputs expire, but not how long a
  private input may live, whether it may be reused across sessions, or which interaction facts are kept as
  evidence.
- **Options for private inputs:** (a) memory only in Cockpit and the handler; discarded at confirmation, Not now,
  expiry, handler exit or Cockpit exit; session TTL 15 minutes by default, 60 at most; a restart requires re-entry,
  explained as privacy expiry. (b) As (a), plus an opt-in encrypted cache in the OS keychain for reuse within N
  days (fewer re-entries; adds a keychain dependency and a different Ubuntu path). (c) Persist encrypted in Delivery
  state (rejected: state is published and copied by LC).
- **Options for evidence:** (a) keep handler and procedure identity, candidate head, acceptance refs, target class,
  platform and registry labels, bounded machine statuses, the user's selected outcome and times; no URL, hostname,
  page content, screenshot, cookie or value digest; retained and published like other Change evidence. (b) As (a),
  plus a keyed hash of the target with a host-local key, to show "same target as before" across sessions.
  (c) Additionally keep raw targets locally, unpublished.
- **Rationale for inputs (a) and evidence (a):** they meet §9.3 without new storage, keep Ubuntu and macOS
  identical, and leave nothing to leak through the remote state branch or an LC copy.
- **Limit of "memory only":** Cockpit drops its references at handoff and the handler ends with the session. That
  is reference disposal, not erasure: CPython strings are immutable, so the bytes stay in freed heap until reused,
  and they can reach swap or a core dump. N06 does not claim zeroization (G13).

### 1.13 Confirmation channel under N03 U2

N03 owns the single definition of a user-only confirmation (PR #360, being amended): the Delivery MCP server asks
the user through MCP elicitation (`elicitation/create`) inside the tool call; caller-supplied provenance never
counts; a declined or cancelled elicitation records nothing; a client without elicitation support gets a typed
refusal. N03 applies it to waivers and human-confirmed evidence. Its U2 (open user decision) is whether a Cockpit
click also counts. N06 defines no mechanism; it binds the boundary to an interaction:

- **Common to both answers.** The boundary's question is the registry `confirmation_question`, its two options are
  the registry outcomes, and its target is the exact interaction, session and `candidate_head`. The boundary
  adapter calls `confirm_interaction` with the boundary's record; N06 then re-checks I5 and `awaiting-human`.
  Decline, cancel, refusal or timeout records nothing and leaves the session `awaiting-human` until **Not now** or
  expiry. Every other path to a resolution of a linked request is refused (§1.4, §1.7).
- **Under U2 (b), only elicitation counts** (lead recommendation). Cockpit has no confirm route. When the handler
  reports `awaiting-human`, the panel tells the user to answer the confirmation in VS Code chat; the
  interaction projection marks the step `awaiting-confirmation` and `/continue-change` yields `human` with an
  instruction to call N03's boundary tool for this interaction. The Cockpit panel shows progress and **Not now**
  only. Cockpit start, inputs and handler launch are unchanged; they are not confirmations.
- **Under U2 (a), Cockpit clicks count** with N03's defense: `POST …/confirm` additionally requires an exact
  `Origin` (no header-less pass) and N03's `HttpOnly; SameSite=Strict` session cookie set by Cockpit's own page,
  plus the nonce. Residual risks, recorded with the decision: an agent driving a browser tool against Cockpit
  clicks as the user; another loopback port is same-site, so the cookie is sent cross-port (P2) and only the exact
  `Origin` check stops that; a same-user process can read the browser cookie store. The elicitation path of (b)
  also stays available.
- **What changes between (a) and (b):** only the confirm step. Under (b): no `…/confirm` route, the panel's
  confirmation buttons become chat guidance, the orchestrator skill gains the elicitation hand-off, and N06-C's
  E2E confirms through a stub MCP client that answers elicitation. Under (a): the route exists with cookie and
  exact-Origin checks, and N06-C clicks **Observed** in Chromium. Readiness, custody, inputs, launch, D13,
  evidence admissibility and V22 are identical.
- **Until U2 is answered:** N06-A builds `confirm_interaction` against N03's boundary record type and tests it with
  an elicitation-backed MCP client; N06-B does not ship a confirm route (G14).

## 2. Feasibility Probes

Ran in the lane worktree on `ac3bf23f9` with `uv run --no-sync`; disposable servers and temporary directories only;
no Delivery state touched. Scripts and outputs: `.owlbear/scratch/n06p/` (unversioned).

| ID | Executed | Result | Premise settled |
| --- | --- | --- | --- |
| P1 | Source reads on `ac3bf23f9` (locators in §1) | `DeliveryRequest` has no handler, candidate or input fields (`runtime_models.py:839-858`); answers persist free text (`:821-837`); `BlockDelivery` carries one optional request (`:1539-1551`); readiness has no interaction reason (`work_items.py:275-312`); `preparing` and `needs-sign-in` are reserved and never emitted (`:314-327`, `derive_delivery_progress` `:593`; N09 §1.4); continuation capabilities are `planner`, `builder`, `finalizer`, `engine` (`application_models.py:285`); Cockpit binds `127.0.0.1` (`main.py:50`) with no middleware (`:57-62`); the orchestrator has no terminal tool (`orchestrator.agent.md:8`); no existing code or skill mentions assisted checks, **Help with this step** or private input (recursive grep, 0 hits) | D1, D2, D4; N06 starts from no assistance code |
| P2 | `p2_browser.py`: two FastAPI apps on loopback ports, real Chromium 153 (Playwright 1.63), `--host-resolver-rules` for rebinding | Cross-port no-cors body-less POST executed (`Origin` = attacker origin, `Sec-Fetch-Site: same-site`); no-cors Blob and `text/plain` JSON did not reach the JSON route; a CORS JSON POST failed preflight; an `HttpOnly; SameSite=Strict` cookie set by port A was sent to port B; `Host: rebind.test:<port>` reached the handler same-origin; uvicorn's access log recorded `?token=QUERYSECRET` but not the fragment | D5; no values or tokens in URLs; no cookie-based session (cookies are not port-isolated); Origin must be compared exactly, not by `Sec-Fetch-Site` |
| P3 | `p3_p6_local.py` P3: Unix socket under the per-user temp dir | 133-byte path fails (`AF_UNIX path too long`), 85-byte path binds; 0700 directory and 0600 socket; bearer exchange works | The runner-over-socket alternative is feasible but heavier (rejected in D1) |
| P4 | P4 and `p4b_redaction.py`: Pydantic 2.13 redaction | `SecretStr` dumps as `**********` and its repr hides the value; `hide_input_in_errors=True` hides the value in `str(exc)` but `exc.json()` and `exc.errors()` still include it unless `include_input=False` | Input models use `SecretStr`, `hide_input_in_errors`, and render errors only with `include_input=False` |
| P5 | P5: child process visibility via `ps` | A child's argv and environment are visible to the same user (`ps -o command=`, `ps eww`); data written to its stdin is not | D9 |
| P6 | P6: `state_formats.scan_capability` on a temp workspace with `runtime/changes/change-a/interactions/i1.json` | Classified `unrecognized`; `require_capability` passes (`state_formats.py:941-942`, `:622-626`; also `test_state_formats.py:686`) | A new layout alone is not refused by an older gated controller, so N06-A's format-marker step is required for downgrade refusal (N02 D3) |
| P7 | `p7_p8_handler_guard.py` P7: parent → child JSON over stdin, then `SIGKILL` of the parent; `killpg` of a new-session group with a grandchild | Child's first message carried input names only; after the parent's death the child read EOF immediately; `killpg` left no survivor | Handler protocol EOF = cancel; group kill ends grandchildren (macOS; Ubuntu in G6) |
| P8 | P8: prototype guard middleware, same Chromium setup | Same-origin page 200; cross-port forged POST blocked; rebinding host 403; header-less local `httpx` POST 200 | D5 guard is feasible and does not break local clients |
| P9 | `pytest serve/delivery/tests/test_state_formats.py` (one file) | 85 passed in 4.13 s; hygiene (`:179`), fingerprint (`:274`) and unrecognized-record (`:686`) tests present | New nested and coordination models must be registered; the fingerprint test catches an unversioned schema change |
| P10 | Round-1 gate source reads on `1600efa60` (source equal to `634a77be7`) | Both Builder block routes copy the worker's `DeliveryRequest`, `resolution` included (`runtime_reads.py:710-731`, `runtime_settlement.py:524-558`); `DeliveryRequestResolution.provenance` is a caller-set literal (`runtime_models.py:821-837`); MCP `answer` forwards it (`target_server.py:442-460`); `run()` calls `uvicorn.run(app, host=_HOST, port=port)` with the default access log (`main.py:372`); the session-open response carries the nonce and the guard admits header-less clients (this plan); `psutil` 7.2.2 and `mcp` 2.2.0 are locked; no `elicit` call exists in `serve/` | Gate findings 1, 2, 3 and 5 hold; confirmation moves to N03's boundary (D4, §1.13); D13; access log off (§1.7) |

## 3. Phases

### 3.1 Shared rules

- **Layout.** Re-resolve every symbol with `grep` at phase start; N03-A…C, N04-A and N09-A2 will have moved or
  extended several owners named here.
- **Versions.** N03-A, N04-A, N05-B, N09-A2 and N06-A each register version steps. The second of any two to merge
  renumbers its steps and migration and reruns LC full form (N05 F6; G3).
- **Ownership** (execution plan §1.6). Opus keeps models, versions, migration registration, custody, the guard,
  handler launch, redaction and every V22 test oracle. Luna may take frontend mirrors and rendering, parity
  assertions, fixture conversion and skill text after Opus fixes the contract.
- **Assembled proof** uses the default loader, `Client(assemble_target_server(...))`, the Cockpit HTTP client with the
  guard installed, real child processes for handlers, and the maintained E2E stack.
- **Exports.** A phase that changes `owlbear_delivery.__all__` updates
  `serve/delivery/tests/fixtures/module_surface.json` and the N02 fingerprint fixture in the same PR.
- **Sentinel.** Every V22 test uses one unique sentinel value per test and searches all captured bytes for it.

### 3.2 N06-A — Interaction lifecycle, registry, readiness gate and binding

- **Prerequisites:** N06-P, N03-C and N03's user-only boundary as amended by PR #360 (G14); added by this plan:
  N09-A2 (coordination v2, pause K-inventory).
- **Editable paths:**
  - new `serve/delivery/src/owlbear_delivery/interaction_registry.py`, `application_interactions.py`
  - `runtime_models.py`: `DeliveryInteraction`, `DeliveryInteractionObservation`, `DeliveryFrontier.interactions`
    and version widening; `DeliveryInteractionError`
  - `runtime_settlement.py`, `runtime_reads.py`: both request-bearing block routes (interaction creation,
    validation, refusal of a pre-resolved linked request)
  - `delivery_runtime.py` facade: frontier writers for interaction status, `publish_result` admissibility (§1.7);
    N03 `evidence.py` gap reasons
  - `workspace_models.py`: `ChangeInteractionSession`, `ChangeCoordination.interaction_session`, version widening;
    `workspace_coordination.py`: lease open/update/release with the no-op frontier participant and the K3 check
  - `application_models.py`: views, `DeliveryContinuationReason` additions; `application_acquisition.py`: `human`
    results, busy under an open session, Builder retry for preparation failure and stale;
    `application_readiness.py`, `work_items.py`: reasons, `HELP_WITH_STEP`, progress rows, static probe
  - `portfolio_application.py`: `answer` refusal; `delivery_application_loader.py`: `interaction_handlers` composition
    parameter and N03 §1.7 normalized comparisons for the new frontier field
  - `delivery_state.py`: snapshot version; `runtime_receipts.py`: handoff change-intent widening
  - `state_formats.py`, `state_migration.py`: §1.6 entries, `NESTED_MODELS`, marker step
  - `owlbear_delivery/__init__.py`; `serve/delivery/tests/fixtures/module_surface.json`; N02 fingerprint and golden
    fixtures
  - `serve/delivery-mcp/src/owlbear_delivery_mcp/target_models.py`, `target_server.py`: views, error codes; no new
    tool
  - `serve/tools/src/owlbear_tools/delivery_diagnostics.py`: version mirror
  - frontend companions: `serve/cockpit/web/src/api/workItems.ts`, `components/workItemPresentation.ts`,
    `WorkItemDetail.tsx` (interaction-linked requests show status and reason without answer controls),
    `WorkPortfolioPage.tsx`; component test; `serve/cockpit/src/owlbear_cockpit/target_models.py`
  - tests: new `serve/delivery/tests/test_interaction_registry.py`, `test_interactions.py`; `test_state_formats.py`,
    `test_state_migration.py`, `test_delivery_runtime.py`, `test_work_items.py`;
    `serve/delivery-mcp/tests/test_target_server.py`;
    `serve/tools/tests/test_delivery_diagnostics.py`; `tests/test_cockpit_boundary.py` (reason, progress and action
    parity); `tests/test_delivery_worktree_authority.py` (new frontier writers; lease in the K-inventory);
    `tests/test_agent_ecosystem_validation.py`
  - skill and agent text: `share/skills/w-packet-building/SKILL.md` (block with an interaction-linked request; copy
    machine observations; never collect values in requests), `share/skills/h-decision-requests/SKILL.md` (no URLs,
    hostnames, credentials or tokens in request answers), `share/skills/w-orchestration/SKILL.md` (yield on
    interaction reasons with the Cockpit instruction; never confirm), `share/agents/repairer.agent.md` (never answer
    linked requests)
  - this plan's N06-A row; execution plan status row
- **Positive scenarios:**
  - A Builder block whose Decision Request names `interaction-handler:synthetic-acknowledgement@1` (test registry)
    creates the request, block and `needs-session` interaction in one transaction; readiness `interaction-ready`,
    next actor you, action `help-with-step`, progress `needs-decision`; `acquire_change_action` returns `human` with
    no launch; MCP `get_change` shows the view with input names and no value field.
  - `interaction-handler:none@1` → `unavailable` / `no-registered-handler`; readiness `interaction-unavailable`;
    continuation `human`, no launch (V17).
  - `open` → lease; Builder, Planner, Finalizer and engine-action acquisition on that Change return `busy`; a second
    `open` from another holder → `_SESSION_BUSY`; after `expires_at` the session moves to `closing`, the old
    interaction reads `postponed` / `session-expired`, and a new `open` succeeds only after
    `release_interaction_session` with an exclusion proof.
  - `update` (input_ref, names, handler identity) → `confirm_interaction(observed)` from an elicitation-backed MCP
    test client through N03's boundary resolves the request; identical replay returns it; `complete` with
    registry-valid observations → `completed`, session `closing`; `release` with an exclusion proof frees the
    lease and clears the block; the same Builder task is reacquired with the interaction in its build context.
  - The Builder submits a `manual-procedure` `human-confirmed` observation citing the request plus copied machine
    observations at `exact_commit = candidate_head`; the result promotes and N03's evaluator shows the criterion
    `covered`.
  - Pause request while `needs-session` → `open` refused; with an open session → `update`, `confirm`, `complete` and
    `postpone` succeed and the pause converts after release (N09 K2).
  - Format: frontier 20 with interactions and coordination 3 with a session round-trip byte-identically; every
    golden record of earlier versions round-trips unchanged; `delivery-migrate` marker step on a disposable portfolio
    with a passive Builder handoff and an N03-format Change changes only the marker.
- **Negative scenarios:**
  - Block refused with `interaction-request-invalid`, nothing written: unknown handler, options not equal to the
    handler's, criterion not current, missing or non-head `resume_commit`, more than 64 interactions.
  - Registry refuses a credential-named input, a `public` url input, an unknown placeholder, an unregistered label.
  - `answer` on a linked request (MCP and application) → `_CONFIRMATION_ROUTE`; frontier bytes unchanged.
  - Fabrication, assembled (`Client(assemble_target_server(...))`, default loader, real worktree), each for an
    interaction-linked request and for an ordinary scoped waiver request, through both block routes
    (`transition_delivery` block and Builder `settle_worker_invocation`): (1) the worker supplies a request already
    resolved `user-confirmed`; (2) the agent calls MCP `answer` with `provenance: user-confirmed`. Route 1 on a
    linked request → `interaction-request-invalid`, nothing written. In every other case N03's boundary leaves the
    request unconfirmed. Then a Builder result with a `human-confirmed` observation or a `waived` record citing it
    is refused, finalization refuses, and no criterion reads `covered` or `waived`.
  - `confirm_interaction` without a boundary record, with a record for another interaction, session or head, or
    while the session is not `awaiting-human` → refused; a declined or cancelled elicitation records nothing.
  - `confirm` after the branch head, an acceptance version or the handler digest changed → `_STALE`; status
    `stale`; readiness `interaction-stale` → same-task Builder retry with failure code `interaction-stale`.
  - `confirm(not-observed)`; `postpone`; expiry; `fail` → request unresolved or `not-observed`; a Builder result citing
    it as satisfying → refused (`confirmation-unresolved` or `interaction-not-completed`); finalization refuses.
  - A result with a machine observation carrying a handler digest but no matching completed interaction, a
    different kind, label or result, or another commit → `interaction-evidence-unmatched`.
  - `confirm` with a different outcome after an accepted one → `_CONFIRMATION_CONFLICT`.
  - A `waived` observation whose confirmation cites an interaction-linked request, resolved `observed` or
    `not-observed` → refused `interaction-request-not-waiver`; finalization refuses; frontier bytes unchanged.
  - Crash injection (N02-B harness) between the lease and the frontier participant of `open` → restart sees either
    no lease and no change or the whole open. Crash after `confirm` before `complete` → the session stays leased
    past `expires_at`; the next `open` or Cockpit start finds the holder dead, verifies exclusion of the recorded
    handler, and only then the interaction becomes `preparation-failed` / `session-lost` and the block clears as a
    counted same-task Builder retry; the resolved request cannot support a result (`interaction-not-completed`); no
    completion or machine observation is fabricated.
  - Custody: `release_interaction_session` while a process with the recorded pid and create time is live →
    `_HANDLER_ALIVE`, lease kept; a recorded pid now held by a process with another create time counts as gone and
    is never signalled; an unreadable identity → `contained`, readiness `interaction-handler-unverified`, every
    acquisition `busy`, and no elapsed time releases it.
  - Corruption (V20): an interaction field inside a frontier 19, a session inside coordination 2, an observation
    kind outside the registry → rejected at parse; the Change is unavailable; never rehashed.
  - Downgrade: the predecessor release refuses the new marker, frontier 20, coordination 3 and snapshot 4 with typed
    version diagnostics and unchanged tree hashes.
  - Privacy: a sentinel placed in every descriptor-facing string a test can control never appears in frontier,
    coordination or snapshot bytes (none of those strings is a value; the test pins I7).
- **Inner loop:** `uv run pytest serve/delivery/tests/test_interaction_registry.py -q`, then
  `uv run pytest serve/delivery/tests/test_interactions.py -q`.
- **Closeout:** `uv run test --changed`; scoped `uv run ruff check` and `ruff format --check`;
  `uv run pytest tests/test_cockpit_boundary.py tests/test_delivery_worktree_authority.py -q`;
  `uv run pytest tests/test_agent_ecosystem_validation.py tests/test_package_boundary.py -q`;
  `npm test`; `npm run build`; Biome on changed frontend files.
- **LC:** full form with `delivery-lc`: unmigrated copy refused; migrated copy lists and reads every Change as
  available with no interaction; the predecessor refuses it; a synthetic newer format is refused; live hashes
  unchanged.
- **Size / risk:** L / high. Four widened families, a marker step, custody and settlement changes and a new
  admissibility rule; the risk is a custody hole between session and writers, which the K-inventory test and the
  `busy` scenarios pin.

### 3.3 N06-B — Secure local input, handler launch and V22

- **Prerequisites:** N06-A.
- **Editable paths:**
  - new `serve/delivery/src/owlbear_delivery/interaction_inputs.py`, `interaction_protocol.py`
  - new `serve/cockpit/src/owlbear_cockpit/request_guard.py`, `interaction_sessions.py`, `routes/interactions.py`;
    `main.py` (`run()` installs the guard, the access logger with `access_log=False`, the session manager, its
    startup recovery of dead-holder sessions and its shutdown); `target_models.py` (bodies with
    `SecretStr` and `hide_input_in_errors`); `routes/target_work.py` (shared error mapping only)
  - `owlbear_delivery/__init__.py` and `module_surface.json` if exports change
  - tests: new `serve/cockpit/tests/test_request_guard.py`, `test_interaction_sessions.py`,
    `serve/cockpit/tests/support/synthetic_interaction_handler.py`, `synthetic_registry.py`;
    new `serve/delivery/tests/test_interaction_inputs.py`, `test_interaction_protocol.py`;
    `tests/test_cockpit_launch.py` (guard installed by `run()`)
  - this plan's N06-B row; execution plan status row
- **Positive scenarios:**
  - Real Cockpit process (`run()` on a disposable portfolio, synthetic registry, isolated port): `open` returns
    descriptors, `launch_summary` and a nonce and launches nothing; `start` with a valid `https` URL spawns the
    synthetic handler; the handler receives the value on stdin only and reports `awaiting-human`; the boundary
    confirmation (§1.13; an elicitation-backed MCP test client until U2 is answered) records `observed` →
    `finished` → `completed`; the handler exits; the exclusion check passes and the lease is released; no child or
    grandchild remains.
  - An inputless handler launches only at `start` with an empty input set; a `choice` input is accepted.
  - Same-origin requests with `Origin: http://127.0.0.1:<port>` pass; header-less local clients pass on
    non-confirming routes. G12: the maintained clients (the built SPA, `cockpit list`, `test_cockpit_launch.py`,
    the E2E stacks) run against the guarded app assembled by `run()`, not against an unguarded `TestClient`.
- **Negative scenarios (V22):**
  - URL with userinfo, a credential-like query key (plain, `%61ccess_token`, or double-encoded `%2561…`), any
    fragment (`https://approved.example/#access_token=…`, a bare `#`, `#%61ccess_token=…`), a non-`https` scheme,
    a non-round-tripping parse, over 2048 characters, or a host outside
    `suffix-allowlist` (also after IDNA normalization) → 422 with a bounded field code; no handler spawned; lease
    unchanged; the response never contains the sentinel.
  - Sentinel absence, asserted on every captured byte: HTTP responses (success and error), Cockpit logs (`caplog`),
    the real `run()` process's stdout and stderr, MCP `get_change` and `show_work_item_view` JSON, frontier,
    coordination and snapshot bytes, the handler's argv and environment (recorded by the spawner in tests), and a
    forced spawn failure whose input carries the sentinel.
  - Access log through the real `run()` wiring: the sentinel in a query string on an accepted route (200), on a
    guard-rejected request (403), on an unknown route (404), on a 422, and in a malformed request line sent over a
    raw socket never appears in stdout or stderr; the access line shows the route template or `unmatched`.
  - Local HTTP cannot confirm: a header-less local client with the nonce from `open` calls every Cockpit route;
    none resolves the request. Under U2 (b) no confirm route exists (404); under U2 (a) `…/confirm` without the
    boundary cookie or exact `Origin` → 403 and the request stays unresolved.
  - Expired session: `start` after `expires_at` → `_EXPIRED`; with a short test TTL the Cockpit timer cancels the
    handler, killpg leaves no survivor, the exclusion check passes before release, status `postponed` /
    `session-expired`, request unresolved.
  - Cancelled sign-in: handler `failed{user-cancelled}` and user **Not now** → request unresolved; a Builder result
    citing it as satisfying is refused; cancel is not pass.
  - Guard: cross-origin `Origin`, `Sec-Fetch-Site: same-site` or `cross-site`, or a foreign `Host` → 403; nothing
    changes. Missing, wrong or closed-session nonce → 409; a second `start` in one session → refused.
  - Protocol: oversize line, unknown message, a message echoing the input, non-zero exit before `awaiting-human`,
    start or cleanup deadline exceeded → `preparation-failed` or `unavailable` by registry code; lease released.
  - Cockpit `SIGKILL` during `awaiting-human` (real processes): the lease survives `expires_at`; a second
    Cockpit's `open` before the restart check → `_SESSION_BUSY`; the restarted Cockpit finds the holder dead,
    verifies exclusion and only then reopens; the request stays unresolved.
  - Uncooperative handlers (real processes, macOS and the Ubuntu CI workers): one ignores stdin EOF, one stalls
    after the confirmation without `finished`, one spawns a grandchild in its group. Cockpit `SIGKILL` or expiry
    → lease kept while any is alive; after `killpg` and the exclusion check, released with no survivor. With
    `psutil` forced to fail → `contained`, lease kept, every acquisition `busy`, no release by time. A recorded pid
    reused by an unrelated process (create time differs) is never signalled.
- **Inner loop:** `uv run pytest serve/cockpit/tests/test_request_guard.py -q`, then
  `uv run pytest serve/cockpit/tests/test_interaction_sessions.py -q`.
- **Closeout:** `uv run test --changed`; scoped Ruff;
  `uv run pytest tests/test_cockpit_work_items.py tests/test_cockpit_launch.py tests/test_package_boundary.py -q`;
  `npm run test:e2e:work` (the guard runs in the real stack).
- **LC:** load form (startup gains the guard and session manager; no format change): the live copy loads and lists
  through a guarded Cockpit with unchanged hashes.
- **Size / risk:** M / high. The security boundary of the package.

### 3.4 N06-C — Presentation, MCP/HTTP projection and synthetic E2E

- **Prerequisites:** N06-B.
- **Editable paths:**
  - `serve/cockpit/web/src/api/workItems.ts` (interaction view, session calls), new
    `src/components/InteractionPanel.tsx` (**Help with this step**, launch summary, **Start check** with the input
    form from descriptors and no value echo, waiting text, confirmation question, **Not now**, **Explain existing
    evidence** filtered from N03-C's projection, **Check not available here** with the reason),
    `WorkItemDetail.tsx`, `workItemPresentation.ts`, `WorkPortfolioPage.tsx`; component tests
  - `serve/cockpit/web/e2e/interaction.spec.ts`, new `e2e/support/start-interaction-stack.mjs` and
    `e2e/support/interaction-cockpit.py` (calls `owlbear_cockpit.main.run` with the synthetic registry), seed additions
  - `work_items.py`, `application_models.py`, MCP `target_models.py`: view fields not added in A, if any
  - `tests/test_cockpit_boundary.py`; `setup/operating-owlbear.md` (Help with this step, privacy expiry, cancel);
    `share/skills/w-orchestration/SKILL.md` wording if the view changed
  - this plan's N06-C row and package closeout; execution plan status row
- **Positive scenarios (real Chromium, built bundle):** the card shows **Needs your decision** and **Help with this
  step**; the panel shows purpose, why human, what **Start check** launches and one instruction; nothing runs before
  **Start check**; a valid URL is accepted and the field is cleared;
  the confirmation question appears; the boundary confirmation records **Observed** (U2 (a): a click in the panel;
  U2 (b): the panel points to chat and a stub MCP client answers the elicitation) → completed; the card returns to
  **Waiting for chat to resume**.
  **Explain existing evidence** lists the scoped criteria. A `none` interaction shows **Check not available here**
  with its reason and no Help control.
- **Negative scenarios:** a credential URL shows the bounded error and keeps the session; **Not now** returns the
  card to postponed with Help available; a short-TTL session expires with the privacy-expiry text; a page served
  from a second loopback port cannot open, start, post input or confirm (403); after a Cockpit restart the panel
  reports a lost session only after the exclusion check, or `interaction-handler-unverified`; the URL bar never
  contains an input or nonce; TypeScript and Python unions disagree → parity fails.
- **Host rehearsal:** on a disposable portfolio in a real VS Code window, a Builder blocks with an interaction-linked
  request through Copilot, the user completes the synthetic check in Cockpit, and `/continue-change` reacquires the
  same task and submits the result. Evidence on the PR (G5).
- **Inner loop:** `npm --prefix serve/cockpit/web test -- InteractionPanel`; then
  `npm --prefix serve/cockpit/web run test:e2e:work -- interaction`.
- **Closeout:** `uv run test --changed`; `npm test`; `npm run build`; Biome on changed files; `npm run test:e2e:work`;
  package closeout: full `uv run test` once and a cumulative Sol challenge of the N06 diff against this plan.
- **LC:** load form (projection over every live Change; none has interactions).
- **Size / risk:** M / medium.

### 3.5 Execution-plan deltas and false premises

Deltas to apply in the N06-P PR:

1. §4.4: N06-P row on merge.
2. No §4.2 change: N09-A2 is added as an N06-A prerequisite by this package plan (execution plan §4.2 allows a
   package plan to add prerequisites). N06-A also overlaps N04-A on core modules; the ready rule serializes them.
3. No re-split; LC lines: A full form, B and C load form.
4. §7: record N06 U1 (inputs (a), evidence (a)) as an engineering decision of 2026-10-03, listed to the user
   without objection, in place of "N06: retention and privacy policy for private inputs" under "Decided later".

Premises found false or incomplete on `ac3bf23f9`:

| ID | Premise | Evidence | Consequence |
| --- | --- | --- | --- |
| F1 | Execution plan §5 N06 assumes an origin-checked form host is available; Cockpit has no request guard | `main.py:57-62`; P2: body-less cross-port POST executed, rebinding `Host` accepted | D5 adds the guard for all of Cockpit in N06-B; until then, and on the frozen live controller until an authorized `/upgrade-delivery`, live Cockpit's body-less POST routes (for example `target_work.py:638-640`) are forgeable from other loopback pages |
| F2 | Programme §5.3 proposes extending `answer` with typed interaction outcomes | MCP `answer` accepts caller-set `provenance: user-confirmed` (`target_server.py:442-460`); HTTP defaults it (`target_models.py:381`); block routes keep worker resolutions (P10) | D4: confirmation only through N03's boundary (§1.13); `answer` refuses linked requests |
| F3 | Programme §9.3 step 1 has the agent launch the check session | The continuation controller has no terminal tool (`orchestrator.agent.md:8`) | D1, D7: Cockpit launches at **Start check** (programme §4.2 allows preparation without a running agent) |
| F4 | N03 §1.9 expects N06 to add `confirmation.kind = interaction` and an `interaction:` locator scheme | Not needed under D2 | D3; N03 G5 closes without an N03 schema change |
| F5 | §9.3 forbids values in access logs; the default uvicorn access log records query strings, and middleware cannot suppress it | `main.py:372`; P2; P10 | uvicorn access log off; a route-template access logger (§1.7); asserted through real `run()` in N06-B |

### 3.6 Plan gate dispositions

Sol plan round 1 (`revision-required`, on `1600efa60`). Premises checked against source (P10).

| Finding | Disposition | Where |
| --- | --- | --- |
| 1 HIGH: `interaction-request-not-waiver` blocks only linked confirmations; ordinary requests and worker-supplied resolutions fabricate confirmations | Accepted. Both block routes keep worker resolutions; `answer` forwards caller provenance. Fixed by delegation: N03's boundary is the only source of a user confirmation for every request; N06 adds block-time refusal of pre-resolved linked requests and assembled tests of both fabrication routes for linked and waiver requests. The waiver rule stays as a semantic rule | §1.4, §1.7, §1.13, D4, I3, §3.2 |
| 2 HIGH: Cockpit HTTP is not user-only | Accepted. The nonce and guard were never user presence. Confirmation follows N03 U2: (b) elicitation hand-off, no Cockpit confirm route; (a) N03's exact-Origin and `SameSite=Strict` cookie defense with stated residuals. Local-HTTP refusal tested | §1.7, §1.13, D5, §3.3, §3.4 |
| 3 HIGH: expiry releases custody without handler exclusion | Accepted. Custody ends only on a verified exclusion over a recorded pid, pgid and `psutil` create time; `contained` when unknown; dead-holder recovery at restart, never by time; uncooperative-handler tests on macOS and Ubuntu | I6, R16, §1.6, §1.7, §1.8, D13, §3.2, §3.3 |
| 4 MED: credential-bearing fragments admissible | Accepted. Fragments refused; structured `urlsplit` with round-trip, decoded keys, double-encoding and IDNA cases | §1.5, §3.3 |
| 5 MED: uvicorn access log logs query values despite middleware | Accepted. `access_log=False` plus a route-template logger; accepted, rejected, unmatched, 422 and malformed requests through real `run()` | §1.7, F5, §3.3 |
| Note: G12 against the guarded app | Accepted | §3.3, G12 |
| Note: frozen live controller unguarded until upgrade | Accepted | D5, F1 |
| Note: memory-only is reference disposal | Accepted | U1, G13 |

No finding was rebutted.

## 4. Progress

| Phase | PR | Exact head | Proof | Challenges | Status |
| --- | --- | --- | --- | --- | --- |
| N06-P | #359 | `1600efa60` | Probes P1–P10 | Sol plan round 1: revision-required (findings 1–5 accepted; confirmation delegated to N03's boundary, custody until exclusion, fragments, access log) → revised | in review |
| N06-A | — | — | — | — | — |
| N06-B | — | — | — | — | — |
| N06-C | — | — | — | — | — |

## 5. Verification Gaps

| ID | Claim | Why unproven | Evidence available | Owner | Blocks |
| --- | --- | --- | --- | --- | --- |
| G1 | N03's `applies_to`, retained scoped confirmations, evaluator and projection behave as N03 §1.4–1.9 states | N03-A…C are not implemented | N03 plan | N06-A (re-check at start; a divergence stops for a plan revision) | N06-A start |
| G2 | N09-A2's coordination v2, pause request and K2/K3 inventory accept one more owner kind as specified | N09-A2 is in progress | N09 plan §1.11 | N06-A | N06-A start |
| G3 | Version and marker numbering composes with N03-A, N04-A, N05-B and N09-A2 | None of them is merged | N02 D3 linear chain; N05 F6 | Second of each pair to merge | That merge |
| G4 | The panel works in the built bundle in Chromium | No frontend was built in P | P2, P8 browser behavior | N06-C (`npm run build`, `test:e2e:work`) | N06-C merge |
| G5 | A real Builder blocks with an interaction-linked request and resumes the same task after confirmation | Agent behavior; fixtures cannot prove it | Settlement and reacquisition are D03 routes | N06-C host rehearsal | N06-C merge |
| G6 | Handler EOF, process-group kill, `psutil` create time, the exclusion check and spawn redaction behave the same on Ubuntu | P5 and P7 ran on macOS only | POSIX semantics; N08 G7 | N06-B tests on the Ubuntu CI workers | N06-B merge |
| G7 | Chromium's public-to-local network restrictions | P2 and P8 used a loopback attacker origin | The guard does not depend on them | — | Nothing |
| G8 | Launching candidate code from a pinned Cockpit release | N02-D and N07 are not designed against each other yet | D1, §1.10 item 5 | N07-P | N07-A |
| G9 | Edge profile custody and cross-Change contention | N07 scope | §1.10 item 3 | N07 | N07-A |
| G10 | Interaction-backed evidence after a requirement revision | Applicability is N04 | N03 survival rules | N04-B, N07-B | Nothing in N06 |
| G11 | LC exercises interaction records | Live state has none | Disposable fixtures in N06-A | N06-A fixtures; N10-M | Nothing (recorded per phase) |
| G12 | No legitimate client calls Cockpit with a cross-origin `Origin` or a non-loopback `Host` | Static search only at implementation | P8 header-less clients pass | N06-B: every maintained client against the guarded app assembled by `run()` (§3.3); the frozen live controller is unguarded until an authorized upgrade | N06-B merge |
| G13 | Python cannot erase a value from memory after use | Immutable `str`/`bytes`; freed heap, swap and core dumps | References dropped at handoff; process ends with the session | — | Nothing (documented limit, U1) |
| G14 | N03's user-only boundary (elicitation record, refusals) and the answer to N03 U2 | PR #360 does not yet contain the boundary text (head `4839b1fc8`); U2 is an open user decision | User's description of #360; §1.13 covers both answers | N03 / user; N06-A re-checks at start; a divergence stops for a plan revision | N06-A start (record type); N06-B confirm route (U2) |
| G15 | A handler that leaves its process group is detected | `setsid` or double fork escapes pgid tracking | D13 residual; registry handlers are repository code | N07-P for B1 (Edge profile custody) | Nothing in N06 |
