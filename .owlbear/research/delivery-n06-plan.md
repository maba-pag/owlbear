# Delivery N06 — Prepared Interaction Core and Private Local Input

> **Package:** N06 of the
> [execution plan](delivery-redesign-execution-plan.md#n06--prepared-interaction-core-and-private-local-input).
> **Planned on:** `origin/dev` `ac3bf23f9` (N01, N02-A, N02-B and N09-A1 merged; N03-A…C, N04, N05-B,
> N09-A2 not merged; N04-P in progress in another lane). Python 3.14 from the lane `.venv`; FastAPI 0.142.2,
> Starlette 1.7.0, uvicorn 0.54.0, Pydantic 2.13.5, Playwright 1.63.0 with Chromium 153 (`uv.lock`).
> Live Delivery state was not read; no live record is needed by this plan. Rebased on `origin/dev` `634a77be7`:
> it adds only N05-A (`delivery-github`, `publication_provider.py`, forbidden-effect gates); no file or locator
> cited here changed.
> **Status:** draft for the plan gate. Product code is unchanged by this phase.
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
  stdin, holds them only in memory, and ends the session on confirmation, **Not now**, expiry or Cockpit exit.
  Delivery receives an opaque input reference, never a value.
- The user's confirmation is recorded only through Cockpit HTTP behind a loopback request guard and a per-panel
  session nonce. It resolves the linked Decision Request with `provenance: user-confirmed`, which is exactly N03's
  scoped confirmation. Machine observations from the handler are recorded separately on the interaction.
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
| R6 | Human confirmation recorded separately from machine observation, using N03 provenance; a click cannot assert machine success and a machine cannot fabricate a confirmation | §9.3 step 7; §9.1 Evidence split; [N03 plan](delivery-n03-plan.md) I6, §1.5 |
| R7 | Cockpit offers **Help with this step**, **Not now**, **Explain existing evidence** and **Check not available here** | Execution plan §5 N06; §4.2 (`:860`); §9.2 (`:1172`); §9.4 (`:1191`); V17 |
| R8 | Assisted check with unavailable handler or tool, or no agent host: agent or host-needed state, never **Needs your evidence**, no fake launch | V17 (`:1552`) |
| R9 | Private URL or credential-like input rejected; expired session; cancelled sign-in; no secret in transcript, log or receipt; only owned resources cleaned; cancel is not pass | V22 (`:1557`); execution plan §5 N06-B |
| R10 | Binding to the candidate and its resources; a changed candidate makes the result stale, never attached to the new candidate | §9.1 (`:1154`); execution plan §5 N06 "P must settle" |
| R11 | Every new readiness reason, action or status ships with its `workItems.ts` mirror, rendering, component test and parity assertion; every new frontier-writing operation joins the mutability policy | Execution plan §1.4 |
| R12 | Every changed persisted family registers a version owner; migrations run through the N02 core; LC full form | Execution plan §1.3; [N02 plan](delivery-n02-plan.md) I2, I3, D3 |
| R13 | Pause prevents new interaction sessions and drains open ones | Programme §4.2 Pause; [N09 plan](delivery-n09-plan.md) §1.11 K1–K3 |
| R14 | Support baseline: Python 3.14; Chromium-only Cockpit; macOS and Ubuntu; handler launch portable | Execution plan §1.1 |
| R15 | N06 defines the interface N07's B1 runner builds on; no B1 code in N06 | Execution plan §5 N06, N07; §3 traceability (`:449`) |

### 1.3 Invariants

- **I1 No private value at rest.** Private input values exist only in Cockpit process memory for the open session
  and in the handler's stdin pipe. They are never written to Delivery state, the remote snapshot, MCP or HTTP
  responses, logs, URLs, process arguments or environment variables (P5), or to any file.
- **I2 Registry-only execution.** The handler argv, environment allowlist, working directory and probe come from
  the registry entry. Allowed placeholders are engine-derived (`{candidate_worktree}`, `{python}`); request text,
  input values and agent text are never interpolated.
- **I3 One human channel.** `open`, `start`, `confirm` and `postpone` exist only on Cockpit HTTP behind the loopback
  guard (D5) and the session nonce. MCP exposes interactions read-only. `answer` refuses any request linked to an
  interaction, on every transport.
- **I4 Cancel is not pass.** Not now, decline, expiry, session loss and handler failure never resolve the linked
  request. Only `confirm` resolves it, with `observed` or `not-observed`; only `observed` can support a satisfying
  N03 `manual-procedure` result, and no outcome can confirm an N03 waiver (§1.4).
- **I5 Exact candidate.** An interaction is bound to `candidate_head` (the block's `resume_commit`, which must equal
  the branch head), the contract's current acceptance versions and the handler digest. Any change makes it
  `stale`; `confirm` and `complete` refuse a stale interaction.
- **I6 Session custody excludes writers.** An unexpired interaction session is a Change custody owner: it refuses to
  open while any writer, claim, Finalizer attempt, continuation action, publication lease or recovery fence exists,
  and every such acquisition refuses while it is open (programme §5.2).
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
| Recognition | Block settlement parses `applies_to.procedure` with `interaction_registry.parse_procedure`. A prefix match that does not resolve to a registry entry, options that differ from the handler's two fixed outcome options, criteria that are not current, or a block without `resume_commit` equal to the branch head (`runtime_settlement.py:405`) refuses the block with `interaction-request-invalid`; nothing is written |
| Reserved `none` | `interaction-handler:none@1` declares a human-only check that no registered handler can perform. It creates an interaction in `unavailable` / `no-registered-handler` (V17) instead of a generic Action Request |
| Engine record | Settlement writes `DeliveryInteraction` ([1.6](#16-persisted-records)) in the same transaction as the block |
| Resolution | Only `confirm` resolves the request (`selected_option_id` = outcome, `provenance: user-confirmed`). `answer` (`portfolio_application.py:1340`) refuses linked requests with `ERR_DELIVERY_INTERACTION_CONFIRMATION_ROUTE` |
| Evidence | The Builder, reacquired for the same task, records N03 schema-2 observations: one `manual-procedure` with `human-confirmed` provenance and `confirmation: {kind: request-resolution, request_id}` (N03 I6), and copies of the interaction's machine observations with `procedure_registration_digest` = handler digest. Locator `request:<request_id>` (an existing N03 scheme) |
| Private input | Never enters a request. Request answers are persisted and published (`DeliveryRequestResolution.response_text`, `runtime_models.py:821-837`) |
| Waiver (N03 U1 (b)) | An interaction-linked request is never a waiver confirmation. Under N03 U1 (b) a `waived` observation with a resolved `user-confirmed` request satisfies finalization, so a `not-observed` confirmation would otherwise turn a failed check into a pass. A `waived` observation whose `confirmation` cites an interaction-linked request is refused (`interaction-request-not-waiver`); a waiver uses its own N03 request |
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

**Input validation** (`owlbear_delivery.interaction_inputs`, leaf): `url` accepts `https` only by default, rejects
userinfo, rejects query keys matching `token|access_token|code|session|sig|signature|password|pwd|key|apikey|auth|
sso|saml` (case-insensitive), at most 2048 characters, host by the descriptor's static `host_policy`
(`any-host`, `suffix-allowlist(...)` or `handler-validated`, the last reported back by the handler as a bounded
`destination-not-admitted` code). `text` is length- and pattern-bounded; `choice` is an enum. Models use
`SecretStr`, `hide_input_in_errors=True`, and errors are rendered only with `include_input=False` (P4b).

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
`holder{pid, port, started_at}` (the Cockpit instance), `candidate_head`, `opened_at`, `expires_at`, `state`
(`awaiting-input`, `starting`, `awaiting-human`, `finishing`), `input_ref` (128-bit random, never derived from a
value), `inputs_provided` (descriptor names only). No digest, hash or prefix of any private value is stored,
because low-entropy values such as internal URLs could be recovered from one.

### 1.7 Interfaces and error cases

| Interface | Owner | Behavior |
| --- | --- | --- |
| Block settlement with an interaction-linked request | `runtime_settlement.py` (request-bearing block, `:250`, `:473-528`) | Creates the interaction (`needs-session`, or `unavailable` for `none`) in the block's transaction; refusal `interaction-request-invalid` with a bounded field code |
| Readiness | `application_readiness.py`, `work_items.py` | New `DeliveryReadinessReason` values: `interaction-ready` (next actor you, action `help-with-step`), `interaction-in-progress` (session open), `interaction-unavailable`, `interaction-postponed` (action `help-with-step`), `interaction-preparation-failed` and `interaction-stale` (next actor agent). New `WorkItemActionKind.HELP_WITH_STEP`. Progress: ready, in progress, unavailable and postponed → `needs-sign-in` when `human_step` is sign-in, else `needs-decision`; `starting` session → `preparing`; agent reasons → `waiting-for-chat` (M12/M13 of the N09 table). Selection order: programme §5.4 rows 8–9 |
| Continuation | `application_acquisition.py:263` | An interaction reason returns `human` (ready, in progress, unavailable, postponed) with no launch; `interaction-preparation-failed` and `interaction-stale` reacquire the same Builder task as a counted retry with failure code `interaction-preparation-failed` or `interaction-stale` (D03 retry ledger). An open session makes every other acquisition `busy` |
| `open_interaction_session(change_id, interaction_id, holder, expected_frontier_digest)` | new `application_interactions.py` mixin | Pause-gated custody start (N09-A2 K3): commits the coordination lease with the frontier as an exact no-op participant. Refuses `ERR_DELIVERY_INTERACTION_NOT_READY` (status), `_UNAVAILABLE` (static probe), `_STALE`, `_SESSION_BUSY` (another unexpired session or any writer custody), `ERR_DELIVERY_CHANGE_PAUSE_REQUESTED`. A `postponed` interaction reopens through this call |
| `update_interaction_session(..., session_id, state, input_ref=None, inputs_provided=())` | same | Session-id CAS; refuses expired or foreign sessions |
| `confirm_interaction(..., session_id, outcome, expected_frontier_digest)` | same | Re-checks I5; resolves the linked request (`user-confirmed`); interaction `resolved`. Identical replay returns the stored resolution; a different outcome conflicts (`_CONFIRMATION_CONFLICT`) |
| `complete_interaction(..., session_id, observations)` | same | Validates kinds, labels and bounds against the registry; status `completed`; releases the lease; clears the block. Replay with identical observations returns the stored record |
| `postpone_interaction(..., session_id \| None, reason)` | same | User Not now, expiry, session loss, pause drain: status `postponed` with reason; releases the lease; request stays unresolved |
| `fail_interaction_session(..., session_id, failure_code)` | same | `preparation-failed` (repairable code) or `unavailable` (environment code); releases the lease |
| `answer` | `portfolio_application.py:1340` | Refuses interaction-linked requests: `ERR_DELIVERY_INTERACTION_CONFIRMATION_ROUTE` |
| `submit_result` / `publish_result` admissibility | `delivery_runtime.py` facade; N03 `evidence.py` | Adds: an observation whose `procedure_registration_digest` equals a handler digest needs a `completed` interaction in the same outcome with that digest, `candidate_head == exact_commit`, and an equal machine observation (kind, result, platform, labels, target class); a `human-confirmed` observation citing an interaction-linked request needs `outcome = observed` and a non-stale completed interaction; a `waived` observation may not cite an interaction-linked request (§1.4). Reasons `interaction-evidence-unmatched`, `interaction-not-completed`, `interaction-stale`, `interaction-request-not-waiver` join N03's bounded `gaps` |
| Projection | `work_items.py`, `application_models.py`, MCP `target_models.py`, Cockpit `target_models.py` | `DeliveryInteractionView{interaction_id, status, status_reason, handler purpose, why_human, user_step, human_step, confirmation_question, inputs (name, label, kind, required; never values), acceptance refs, candidate_head, session (state, expires_at, inputs_provided, input_ref; holder only as "this Cockpit" or "another Cockpit"), observations}` on `WorkItemDetailView`, `get_change` and the build context |
| Cockpit HTTP (N06-B) | new `owlbear_cockpit/routes/interactions.py`, `interaction_sessions.py` | `POST /api/changes/{c}/interactions/{i}/session` (Help; lease; returns descriptors, `launch_summary` and the nonce in the JSON body; launches nothing), `POST …/start` (Start check; inputs, possibly none; launches), `GET …/session`, `POST …/confirm`, `POST …/postpone`. Nonce header `X-OwlBear-Interaction-Session`, compared with `secrets.compare_digest`. Error envelope `{code, detail, authority: "delivery", retry_safe}` with bounded field codes, never input values |
| Loopback request guard (N06-B) | new `owlbear_cockpit/request_guard.py`, installed by `run()` (`main.py:311`) | Every request: `Host` ∈ {`127.0.0.1:<port>`, `localhost:<port>`} else 403 `COCKPIT_HOST_REJECTED`. Unsafe methods: a present `Origin` must equal `http://127.0.0.1:<port>` or `http://localhost:<port>`, and a present `Sec-Fetch-Site` must be `same-origin` or `none`, else 403 `COCKPIT_ORIGIN_REJECTED`. Header-less local clients pass (P8) |
| Handler protocol v1 (N06-B) | new `owlbear_delivery/interaction_protocol.py` | JSON Lines, ≤ 16 KiB per line, ≤ 256 lines. Cockpit → handler: `start{protocol: 1, interaction_id, candidate_head, inputs}`, `human-step-complete{outcome}`, `cancel{}`. Handler → Cockpit: `ready`, `awaiting-human`, `observation{kind, result, platform, labels, target_class}`, `finished`, `failed{code}`. stdin EOF means cancel: clean up and exit (P7). Unknown messages, oversize lines or values echoed back end the session as `handler-failed` |
| Handler launch (N06-B) | `owlbear_cockpit/interaction_sessions.py` | `subprocess.Popen(argv, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=allowlist, cwd=…, start_new_session=True)`; inputs only in `start`; stderr kept in a 4 KiB memory ring, never logged or returned; deadlines per registry; cancel sends `cancel`, closes stdin, then `killpg` after the cleanup deadline (P7) |

Errors keep the existing envelopes: core `DeliveryInteractionError(DeliveryRuntimeConflictError)` with
`ERR_DELIVERY_INTERACTION_*` codes mapped by MCP `_raise` (`target_server.py:1243-1250`) and Cockpit `_http_error`
(`target_work.py:819-835`).

### 1.8 Session lifecycle

| From | Event (channel) | To | Effects |
| --- | --- | --- | --- |
| — | Builder block with linked request (MCP settlement) | `needs-session` or `unavailable` | Block, request, interaction in one transaction |
| `needs-session`, `postponed` | Help with this step (Cockpit `open`) | session `awaiting-input` | Lease; nonce in memory; panel shows `launch_summary` and inputs; nothing launched |
| session `awaiting-input` | Start check (Cockpit `start`) | session `starting` | Validate; spawn; `start` message on stdin; `input_ref`; Cockpit drops its copy |
| session `starting` | handler `awaiting-human` | session `awaiting-human` | Panel shows the confirmation question |
| session `awaiting-human` | `confirm` | `resolved`; session `finishing` | Request resolved; `human-step-complete` sent |
| session `finishing` | handler `finished` | `completed` | Observations; lease released; block cleared |
| any session state | Not now (`postpone`) | `postponed` / `user-postponed` | `cancel`, killpg after deadline; lease released |
| any session state | `expires_at` passes (Cockpit timer) | `postponed` / `session-expired` | As cancel |
| any session state | handler `failed`, exit or protocol violation | `preparation-failed` or `unavailable` | As cancel; repairable vs environment by registry |
| any session state | Cockpit exits | `postponed` / `session-lost` (best effort at shutdown) | Handler sees EOF and exits (P7); otherwise the lease expires |
| `resolved` (session `finishing`) | lease expires or Cockpit exits before `finished` | `preparation-failed` / `session-lost` | Block clears as a counted same-task Builder retry; the resolution cannot support a result |
| any | head, contract or handler change | `stale` | Refuse confirm and complete; Builder retry |
| any | operator clears the block | `stale` / `block-cleared` | Session cancelled |
| `needs-session` | pause request | unchanged; `open` refused | Open sessions drain (K2) |

Per [U1](#u1--retention-and-privacy-policy-for-private-inputs-and-interaction-evidence) (a): session TTL
15 minutes by default, hard maximum 60 minutes, set per handler within the maximum.

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
OS keychain storage; a separate loopback form server, runner process or Unix-socket channel (D1); confirmation
through chat or MCP (D4); Windows.

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
- **D4 Human channel by transport.** The MCP `answer` tool accepts caller-set `provenance: user-confirmed`
  (`target_server.py:442-448`; Cockpit `AnswerRequestBody` defaults it, `target_models.py:381`), so `answer` cannot
  separate a user's confirmation from an agent call. N06 gives confirmation its own Cockpit-only route and makes
  `answer` refuse linked requests. This is structural, not cryptographic: the trust boundary stays the local user
  (N03 R12).
- **D5 Loopback request guard for all of Cockpit** (P2, P8). Cockpit has no middleware (`main.py:57-62`). From any
  page on another loopback port, Chromium executes body-less cross-origin POSTs such as
  `POST /api/changes/{id}/publication/ready` (`target_work.py:638-640`), sending `Sec-Fetch-Site: same-site`; a
  DNS-rebinding host reaches handlers with its own `Host`. FastAPI's default strict content type blocks forged JSON
  bodies (P2; `fastapi/routing.py:448-461`). The interaction routes need the guard, and a per-route guard would
  leave forgeable siblings in the same app, so it is installed once in `run()`. Same-origin pages and header-less
  local clients are unaffected (P8); `TestClient`-based suites that do not install it are unchanged.
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

- **Prerequisites:** N06-P, N03-C; added by this plan: N09-A2 (coordination v2, pause K-inventory).
- **Editable paths:**
  - new `serve/delivery/src/owlbear_delivery/interaction_registry.py`, `application_interactions.py`
  - `runtime_models.py`: `DeliveryInteraction`, `DeliveryInteractionObservation`, `DeliveryFrontier.interactions`
    and version widening; `DeliveryInteractionError`
  - `runtime_settlement.py`: request-bearing block settlement (interaction creation, validation)
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
    `open` from another holder → `_SESSION_BUSY`; after `expires_at` a new `open` succeeds and the old interaction
    reads `postponed` / `session-expired`.
  - `update` (input_ref, names) → `confirm(observed)` resolves the request with `user-confirmed`; identical replay
    returns it; `complete` with registry-valid observations → `completed`, lease released, block cleared; the same
    Builder task is reacquired with the interaction in its build context.
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
    no lease and no change or the whole open. Crash after `confirm` before `complete` → once `expires_at` passes,
    the interaction becomes `preparation-failed` / `session-lost` and the block clears as a counted same-task
    Builder retry; the resolved request cannot support a result (`interaction-not-completed`); no completion or
    machine observation is fabricated.
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
    `main.py` (`run()` installs the guard, the session manager and its shutdown); `target_models.py` (bodies with
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
    synthetic handler; the handler receives the value on stdin only and reports `awaiting-human`;
    `confirm(observed)` → `finished` → `completed`; the handler exits; no child or grandchild remains.
  - An inputless handler launches only at `start` with an empty input set; a `choice` input is accepted.
  - Same-origin requests with `Origin: http://127.0.0.1:<port>` pass; header-less local clients pass.
- **Negative scenarios (V22):**
  - URL with userinfo, a credential-like query key, a non-`https` scheme, over 2048 characters, or a host outside
    `suffix-allowlist` → 422 with a bounded field code; no handler spawned; lease unchanged; the response never
    contains the sentinel.
  - Sentinel absence, asserted on every captured byte: HTTP responses (success and error), Cockpit logs (`caplog`),
    the real process's stdout and stderr including uvicorn's access log, MCP `get_change` and
    `show_work_item_view` JSON, frontier, coordination and snapshot bytes, the handler's argv and environment
    (recorded by the spawner in tests), and a forced spawn failure whose input carries the sentinel.
  - Expired session: `start` after `expires_at` → `_EXPIRED`; with a short test TTL the Cockpit timer cancels the
    handler, killpg leaves no survivor, status `postponed` / `session-expired`, request unresolved.
  - Cancelled sign-in: handler `failed{user-cancelled}` and user **Not now** → request unresolved; a Builder result
    citing it as satisfying is refused; cancel is not pass.
  - Guard: cross-origin `Origin`, `Sec-Fetch-Site: same-site` or `cross-site`, or a foreign `Host` → 403; nothing
    changes. Missing, wrong or closed-session nonce → 409; a second `start` in one session → refused.
  - Protocol: oversize line, unknown message, a message echoing the input, non-zero exit before `awaiting-human`,
    start or cleanup deadline exceeded → `preparation-failed` or `unavailable` by registry code; lease released.
  - Cockpit `SIGKILL` during `awaiting-human` (real processes): the handler exits on EOF; after `expires_at` a new
    Cockpit reopens; the request stays unresolved.
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
  the confirmation question appears; **Observed** → completed; the card returns to **Waiting for chat to resume**.
  **Explain existing evidence** lists the scoped criteria. A `none` interaction shows **Check not available here**
  with its reason and no Help control.
- **Negative scenarios:** a credential URL shows the bounded error and keeps the session; **Not now** returns the
  card to postponed with Help available; a short-TTL session expires with the privacy-expiry text; a page served
  from a second loopback port cannot open, confirm or post input (403); after a Cockpit restart the panel reports a
  lost session; the URL bar never contains an input or nonce; TypeScript and Python unions disagree → parity fails.
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
| F1 | Execution plan §5 N06 assumes an origin-checked form host is available; Cockpit has no request guard | `main.py:57-62`; P2: body-less cross-port POST executed, rebinding `Host` accepted | D5 adds the guard for all of Cockpit in N06-B; until then live Cockpit's body-less POST routes (for example `target_work.py:638-640`) are forgeable from other loopback pages |
| F2 | Programme §5.3 proposes extending `answer` with typed interaction outcomes | MCP `answer` accepts caller-set `provenance: user-confirmed` (`target_server.py:442-448`); HTTP defaults it (`target_models.py:381`) | D4: a Cockpit-only confirm route; `answer` refuses linked requests |
| F3 | Programme §9.3 step 1 has the agent launch the check session | The continuation controller has no terminal tool (`orchestrator.agent.md:8`) | D1, D7: Cockpit launches at **Start check** (programme §4.2 allows preparation without a running agent) |
| F4 | N03 §1.9 expects N06 to add `confirmation.kind = interaction` and an `interaction:` locator scheme | Not needed under D2 | D3; N03 G5 closes without an N03 schema change |
| F5 | §9.3 forbids values in access logs; the default uvicorn access log records query strings | `main.py:372`; P2 | Values and nonces never in URLs (I1); asserted in N06-B |

## 4. Progress

| Phase | PR | Exact head | Proof | Challenges | Status |
| --- | --- | --- | --- | --- | --- |
| N06-P | #359 | — | Probes P1–P9 | — | in review |
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
| G6 | Handler EOF, process-group kill and spawn redaction behave the same on Ubuntu | P5 and P7 ran on macOS only | POSIX semantics | N06-B tests on the Ubuntu CI workers | N06-B merge |
| G7 | Chromium's public-to-local network restrictions | P2 and P8 used a loopback attacker origin | The guard does not depend on them | — | Nothing |
| G8 | Launching candidate code from a pinned Cockpit release | N02-D and N07 are not designed against each other yet | D1, §1.10 item 5 | N07-P | N07-A |
| G9 | Edge profile custody and cross-Change contention | N07 scope | §1.10 item 3 | N07 | N07-A |
| G10 | Interaction-backed evidence after a requirement revision | Applicability is N04 | N03 survival rules | N04-B, N07-B | Nothing in N06 |
| G11 | LC exercises interaction records | Live state has none | Disposable fixtures in N06-A | N06-A fixtures; N10-M | Nothing (recorded per phase) |
| G12 | No legitimate client calls Cockpit with a cross-origin `Origin` or a non-loopback `Host` | Static search only at implementation | P8 header-less clients pass | N06-B (grep of callers; E2E stack runs guarded) | N06-B merge |
| G13 | Python cannot erase a value from memory after use | Interpreter limitation | References dropped at handoff; process ends with the session | — | Nothing (documented limit) |
