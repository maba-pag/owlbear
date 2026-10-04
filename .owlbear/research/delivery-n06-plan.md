# Delivery N06 — Prepared Interaction Core and Private Local Input

> **Package:** N06 of the
> [execution plan](delivery-redesign-execution-plan.md#n06--prepared-interaction-core-and-private-local-input).
> **Planned on:** `origin/dev` `ac3bf23f9` (N01, N02-A, N02-B and N09-A1 merged; N03-A…C, N04, N05-B,
> N09-A2 not merged; N04-P in progress in another lane). Python 3.14 from the lane `.venv`; FastAPI 0.142.2,
> Starlette 1.7.0, uvicorn 0.54.0, Pydantic 2.13.5, Playwright 1.63.0 with Chromium 153 (`uv.lock`).
> Live Delivery state was not read; no live record is needed by this plan. Rebased on `origin/dev` `634a77be7`:
> it adds only N05-A (`delivery-github`, `publication_provider.py`, forbidden-effect gates); no file or locator
> cited here changed. Round 3 merged `origin/dev` `141795676` (adds N09-A2, PR #357); round-3 locators are on that
> merge (`edab21d5a`).
> **Status:** draft for the plan gate, revised after Sol plan rounds 1–3 ([3.6](#36-plan-gate-dispositions)).
> Product code is unchanged by this phase. User-only confirmation is N03's boundary (PR #360 at `f4d09d774`: R14,
> I6, I10, D13 and its single-use rule `:486-513`); N06 dispatches interaction-linked requests through N03's scoped
> `answer`, consumes N03's consent generation (D16) and works under either answer of N03 U2
> ([1.13](#113-confirmation-channel-under-n03-u2)).
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
  check** starts a Delivery-owned launcher that runs the registered handler only after its process identity is
  recorded, passes private inputs only through the handler's stdin, holds them only in memory, and ends the
  session on completion, **Not now**, expiry or Cockpit exit. Custody ends only once no process carrying the
  session's ownership token remains (D13). Delivery receives an opaque input reference, never a value.
- The user's confirmation counts only through N03's boundary: MCP `answer` on the linked request, which asks the
  user by MCP elicitation ([1.13](#113-confirmation-channel-under-n03-u2)). Its `passed` or `failed` decision is
  shown as observed or not observed, appended to the Change confirmation ledger and bound to the interaction in
  one transaction. Caller-, worker- or Cockpit-supplied provenance never counts (a Cockpit channel exists only if
  N03 U2 is (a)). Machine observations from the handler are recorded separately on the interaction.
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
| R6 | Human confirmation recorded separately from machine observation, only as an N03 ledger confirmation captured by N03's scoped `answer` and consuming N03's consent generation; a click cannot assert machine success and neither a machine, a worker nor a caller can fabricate a confirmation | §9.3 step 7; §9.1 Evidence split; [N03 plan](delivery-n03-plan.md) R14, I6, I10, §1.5, D13, single use `:486-513` (PR #360 at `f4d09d774`) |
| R7 | Cockpit offers **Help with this step**, **Not now**, **Explain existing evidence** and **Check not available here** | Execution plan §5 N06; §4.2 (`:860`); §9.2 (`:1172`); §9.4 (`:1191`); V17 |
| R8 | Assisted check with unavailable handler or tool, or no agent host: agent or host-needed state, never **Needs your evidence**, no fake launch | V17 (`:1552`) |
| R9 | Private URL or credential-like input (any undeclared query, fragment or path structure, credential-bearing or token-like path segment, encoded component) rejected; expired session; cancelled sign-in; no secret in transcript, log or receipt; only owned resources cleaned; cancel is not pass | V22 (`:1557`); execution plan §5 N06-B |
| R10 | Binding to the candidate and its resources; a changed candidate makes the result stale, never attached to the new candidate | §9.1 (`:1154`); execution plan §5 N06 "P must settle" |
| R11 | Every new readiness reason, action or status ships with its `workItems.ts` mirror, rendering, component test and parity assertion; every new frontier-writing operation joins the mutability policy | Execution plan §1.4 |
| R12 | Every changed persisted family registers a version owner; migrations run through the N02 core; LC full form | Execution plan §1.3; [N02 plan](delivery-n02-plan.md) I2, I3, D3 |
| R13 | Pause prevents new interaction sessions and drains open ones | Programme §4.2 Pause; [N09 plan](delivery-n09-plan.md) §1.11 K1–K3 |
| R14 | Support baseline: Python 3.14; Chromium-only Cockpit; macOS and Ubuntu; handler launch portable | Execution plan §1.1 |
| R15 | N06 defines the interface N07's B1 runner builds on; no B1 code in N06 | Execution plan §5 N06, N07; §3 traceability (`:449`) |
| R16 | Session custody ends only after no Delivery-owned handler process remains; ownership recorded before any handler runs and positive before any signal; containment with a user recheck route when closure is unknown | Programme §5.2; V22 (owned cleanup); [N08 plan](delivery-n08-plan.md) D12 |
| R17 | Every interaction write survives a restart before publication, including during a retained Builder handoff; there the outcome binding changes only by a receipt the loader replays | `delivery_application_loader.py:603-607`, `:1010-1053`, `:1582-1605`, `:1755-1777`; N03 §1.7 L row |
| R18 | An interaction session coexists only with the passive handoff of its own Builder settlement; every other custody is refused both ways | `workspace_coordination.py:894`, `:1000-1001`, `:1288-1349`; `workspace_models.py:1633-1660`; programme §5.2 |

### 1.3 Invariants

- **I1 No private value at rest.** Private input values exist only in Cockpit process memory for the open session
  and in the handler's stdin pipe. They are never written to Delivery state, the remote snapshot, MCP or HTTP
  responses, logs, URLs, process arguments or environment variables (P5), or to any file.
- **I2 Registry-only execution.** The handler argv, environment allowlist, working directory and probe come from
  the registry entry. Allowed placeholders are engine-derived (`{candidate_worktree}`, `{python}`); request text,
  input values and agent text are never interpolated.
- **I3 One confirmation boundary.** A linked request is resolved only by N03's scoped `answer` (D13), which builds
  the ledger confirmation from the user's elicitation answer (or from N03-C's Cockpit channel if U2 is (a)). N06
  adds interaction checks and writes to that dispatch, never a channel. N03 already refuses a scoped request that
  arrives resolved and ignores caller `resolution` and `provenance`. `open`, `start`, `postpone` and `recheck` are
  Cockpit HTTP operations behind the guard (D5); none is a confirmation, and the nonce binds a panel to a session,
  not to a user. MCP adds no interaction tool. A linked answer consumes N03's consent generation in the transaction
  that records it; N06 adds no generation of its own (D16).
- **I4 Cancel is not pass.** Not now, decline, cancel, refusal, expiry, session loss and handler failure write no
  confirmation. A `failed` (not observed) decision is recorded but never satisfies (N03 I6); only `passed` with a
  completed, non-stale interaction supports a `human-confirmed` `manual-procedure` observation, and no interaction
  confirmation can support a waiver (§1.4).
- **I5 Exact candidate.** An interaction is bound to `candidate_head` (the block's `resume_commit`, which must equal
  the branch head), the contract's current acceptance versions and the handler digest. Any change makes it
  `stale`; the linked answer and `complete` refuse a stale interaction.
- **I6 Session custody excludes writers.** An unexpired interaction session is a Change custody owner. It opens only
  when the Change has no writer, or when its only custody is the passive handoff retained by the settlement that
  created its interaction (D15). It refuses every other writer, claim, Finalizer attempt, continuation action,
  publication lease or recovery fence, and every such acquisition, the same-task consumption of that handoff
  included, refuses while it is open (programme §5.2). Custody ends only when the exclusion check finds no
  Delivery-owned process (D13); expiry, completion or Cockpit exit alone never release it.
- **I7 Bounded, non-sensitive portable records.** Interaction records and machine observations contain only
  registry-declared identifiers, enums, digests, heads, times and bounded counts. No handler-authored free text.
- **I8 Version widening.** Families widen their version literal; old instances validate unchanged and are
  constrained to old content; no stored byte or identity changes (N03 I1, I2).
- **I9 Gate first.** N02 I1 and I5 unchanged; N06-A adds one format-marker step and the widened versions.
- **I10 Ledger and replay.** N03 I10 holds: a linked answer appends exactly one ledger entry in the transaction
  that resolves the request and the interaction, and no N06 writer touches `confirmations`. Every interaction write
  during a retained Builder handoff is bound by an interaction transition receipt in its transaction and leaves the
  outcome binding unchanged, except the receipt-backed withdrawal that starts a retry before confirmation (D14).
- **I11 Positive ownership before any signal.** A process is signalled only when it carries the session's spawn
  token or belongs to the group of a leader verified live by pid, create time and token (D13). Nothing else in the
  recorded group or session is signalled; when a process cannot be classified, the session stays `contained`.

### 1.4 Relation to `DeliveryRequest` (programme "P must settle")

An interaction is attached to one Decision Request. Nothing new is added to `DeliveryRequest` or `DeliveryBlock`.

| Element | Rule |
| --- | --- |
| Creation route | The Builder blocks on the existing request-bearing route (`BlockDelivery.request`, `runtime_models.py:1539-1551`; settlement `runtime_settlement.py:250`). The request is a Decision Request with no `options`, `summary` equal to the registry `confirmation_question`, and N03 `applies_to{kind: confirm-check, acceptance, procedure: "interaction-handler:<handler_id>@<version>"}` |
| Recognition | Block settlement parses `applies_to.procedure` with `interaction_registry.parse_procedure`. A prefix match that does not resolve to a registry entry, `applies_to.kind` other than `confirm-check`, non-empty `options`, a summary other than the registry `confirmation_question`, criteria that are not current, or a block without `resume_commit` equal to the branch head (`runtime_settlement.py:405`) refuses the block with `interaction-request-invalid`; nothing is written. A scoped request that arrives with a `resolution` is already refused by N03 (§1.5 Confirmation scope) |
| Reserved `none` | `interaction-handler:none@1` declares a human-only check that no registered handler can perform. It creates an interaction in `unavailable` / `no-registered-handler` (V17) instead of a generic Action Request |
| Engine record | Settlement writes `DeliveryInteraction` ([1.6](#16-persisted-records)) and its first transition receipt (D14) in the block's transaction |
| Resolution | MCP `answer` on the linked request through N03's D13 boundary. Its resolver asks the interaction question only while the session is `awaiting-human`; an `accept` resolves the request, appends the ledger confirmation and sets the interaction `resolved` with its `confirmation_id` in one transaction that consumes N03's consent generation, whose question carries the interaction binding (§1.7, §1.13, D16). Decision `passed` is shown as observed and `failed` as not observed. Cockpit `answer_request` keeps N03-A's `channel-unavailable` refusal for scoped requests unless U2 is (a) |
| Fabrication routes | Both Builder block routes store the worker's `DeliveryRequest` verbatim, `resolution` included (`runtime_reads.py:710-731`, `runtime_settlement.py:524-558`), and MCP `answer` passes caller-set `provenance` (`target_server.py:442-460`). After N03-A a scoped request created with a `resolution` is refused, and caller `resolution` and `provenance` confer nothing on a scoped request (N03 §1.5, D13). N06-A pins both routes for linked and ordinary scoped requests with assembled tests (§3.2) |
| Evidence | The Builder, reacquired for the same task, records N03 schema-2 observations: one `manual-procedure` with assessment `passed`, `human-confirmed` provenance, `confirmation_id` = the interaction's ledger confirmation, `procedure` = the scope's procedure and `covers` = its acceptance refs (N03 I6); and copies of the interaction's machine observations (`machine-observed`) with `procedure_registration_digest` = handler digest. Optional locator `request:<request_id>` (an existing N03 scheme) |
| Private input | Never enters a request. Request answers are persisted and published (`DeliveryRequestResolution.response_text`, `runtime_models.py:821-837`) |
| Waiver (N03 U1 (b)) | A linked request is `confirm-check`, so its decisions are `passed` or `failed`, never `waive`; N03's `confirmation_applies` already refuses a `waived` record citing it (`confirmation-not-applicable`). A waiver needs its own `waive` request answered through the same boundary. N06 adds no waiver rule |
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
| Evidence split | Machine: handler `observation` messages, registry-declared kinds, recorded by `complete`. Human: the ledger confirmation of the linked answer |
| Alternatives | **Not now** (`postpone`), **Explain existing evidence** (N03-C projection of the scoped criteria), **Check not available here**, **Change requirements** (N04 control, when present). Declining never means success |
| Resume | The linked answer resolves request and block (N03's request-resolution successor); `complete` records machine observations and leaves the binding unchanged; after release, continuation reacquires the same Builder task with the interaction in its context. Without a confirmation, a failed or stale interaction is withdrawn in the reacquisition transaction (D14) |

**Registry** (`owlbear_delivery.interaction_registry`, leaf; imports Pydantic and the stdlib only):

- `InteractionHandlerDescriptor` fields: `handler_id`, `version`, `purpose`, `why_human`, `launch_summary` (what
  starting the check launches or accesses), `human_step`, `user_step`, `confirmation_question`,
  `decision_labels` (labels for N03's `passed` and `failed`; default "Observed" and "Not observed"), `inputs`
  (a `url` input carries a `url_policy`), `observation_kinds` and `label_allowlist`, `target_classes`,
  `platforms` (`macos`, `linux`), `resources`
  (names only; custody owned by the declaring package), `argv`, `env_allowlist`, `cwd` (`candidate-worktree` or
  `temporary`), `probe` (`executables`, `platforms`, `candidate_paths`), `timeouts` (`start`, `human_step`,
  `cleanup`), `failure_codes` (code → `repairable` or `environment`).
- Registration validation refuses: an input named or labelled like a credential (`password`, `passcode`, `otp`,
  `mfa`, `secret`, `token`, `cookie`, case-insensitive); a `public` non-choice input; a placeholder other than the
  allowed ones; a label outside the `N03` label pattern; a duplicate `handler_id@version`.
- `DEFAULT_INTERACTION_HANDLERS` holds only the reserved `none` entry in N06. N07 adds B1. Tests inject a synthetic
  registry through composition (`load_delivery_application(..., interaction_handlers=...)`, Cockpit `run(...)`).

**Input validation** (`owlbear_delivery.interaction_inputs`, leaf). A `url` input is admitted only through its
descriptor's `url_policy`; N06 registers none, and N07 declares B1's:

- **Parse.** `urllib.parse.urlsplit`, never a pattern over the raw string; refused unless `urlunsplit` returns the
  input unchanged; at most 2048 characters; scheme in `schemes` (default `https` only); no userinfo; no explicit
  port unless declared; host by `host_policy` (`any-host`, `suffix-allowlist(...)` or `handler-validated`, the
  last reported back by the handler as a bounded `destination-not-admitted` code), compared after IDNA
  normalization.
- **Fragment.** Any `#`, including an empty fragment, is refused.
- **Query.** Refused unless the descriptor declares `query_keys`. The default is no query at all, so
  `?client_secret=…` or a SharePoint `?e=…` sharing key is refused without depending on a keyword list.
  Declared keys are parsed with `parse_qsl(strict_parsing=True, keep_blank_values=True)`; every key must be
  declared, appear once and match its declared value pattern; a `%` left after one decoding is refused.
- **Path.** Admitted only when it matches one of the descriptor's declared `paths`; the default admits only an
  empty path or `/`. A path template is a sequence of literal segments and named identifier slots; each slot has an
  anchored pattern and a maximum length, for example `/wiki/{space:[A-Z]{2,16}}/pages/{page:[0-9]{1,20}}`.
  Before matching, the path is split on `/` (at most 32 segments); each segment is
  percent-decoded once and must then match `[A-Za-z0-9._~-]{1,128}`, so `;`, `=`, `:`, `@`, `+`, `,`, `%`,
  whitespace, controls, `\` and an encoded `/` are refused, and so is double encoding. `.` and `..` segments, and
  empty segments other than a trailing slash, are refused. A path that no template matches is refused
  (`url-path-undeclared`): a bearer link such as `/invite/<GUID>` or `/s/ab3-x9k` fails because nothing declares
  it, not because a heuristic recognized it. Registration refuses a slot without a pattern or maximum length, and a
  template with a literal segment in the bearer-route list (`invite`, `share`, `shared`, `s`, `r`, `guest`,
  `guestaccess`, `join`, `magic`, `reset`, `confirm`, `verify`, `activate`, `login`, `signin`, `sso`, `oauth`,
  `callback`, `redirect`; case-insensitive) or the credential list below. As a second filter on slot values, a
  value equal to a credential word (`token`, `access_token`, `id_token`, `session`, `sig`, `signature`,
  `password`, `secret`, `apikey`, `api_key`, `auth`, `code`, `saml`, `jwt`, `bearer`; case-insensitive) is
  refused, as is a token-like value: one starting `eyJ` or holding a run of 32 or more `[A-Za-z0-9_]` characters.
  That a declared identifier is not a bearer capability is the handler author's claim, reviewed with the handler
  (N07 for B1).
- **Errors.** Bounded codes `url-parse`, `url-scheme`, `url-userinfo`, `url-port`, `url-host`, `url-length`,
  `url-fragment`, `url-query-not-allowed`, `url-query-key`, `url-query-value`, `url-path-undeclared`,
  `url-path-segment`, `url-path-credential`, `url-path-token-like`; never the value.

`text` is length- and pattern-bounded; `choice` is an enum. Models use `SecretStr`, `hide_input_in_errors=True`,
and errors are rendered only with `include_input=False` (P4b).

### 1.6 Persisted records

| Family (N02 ID) | Change | Before → after | Old records | Portable |
| --- | --- | --- | --- | --- |
| `frontier` | Top-level `interactions: tuple[DeliveryInteraction, ...]` (≤ 64, omitted when empty) | N03's 19 → widen 19, 20 | 19 (and N03's `readable-legacy` 18) parse unchanged; a validator rejects `interactions` below 20 | Yes |
| `snapshot` (remote) | Embeds the frontier | N03's 3 → widen 3, 4 | Native parse | — |
| handoff change-intent receipts | Embed whole frontiers | N03's 2 → widen 2, 3 (normalized delta per N03 §1.7) | Unchanged | — |
| `coordination` | `interaction_session: ChangeInteractionSession \| None` (omitted when None) | N09-A2's 2 → widen 2, 3 | Unchanged; validator rejects the field below 3 | No (host-local) |
| interaction transition receipts (new) | `_DeliveryInteractionTransitionReceipt` under the Change's runtime receipts, one per interaction write during a retained Builder handoff (D14) | New, schema 1 | None exist | No (host-local; the frontier carries the state once published) |
| `format` marker | `format-N-to-N+1` marker-only migration | N assigned at merge (G3) | — | — |
| binding-embedding receipts, `DeliveryRequest`, `DeliveryBlock`, `DeliveryUserConfirmation`, request-resolution receipts, observations, `result_receipt` | Unchanged (N03's shapes, channels and locator schemes; D3) | — | — | — |

`DeliveryInteraction` (schema 1, nested in the frontier family; registered in `NESTED_MODELS`):

| Field | Meaning |
| --- | --- |
| `interaction_id` | `_receipt_digest` over `change_id`, `outcome_id`, `task_id`, `block_id`, `request_id`, `procedure`, `candidate_head`, `created_at` |
| `handler_id`, `handler_version`, `handler_digest` | Registry identity; `None` for `none` |
| `procedure`, `acceptance` | Copied from `applies_to` |
| `candidate_head` | The block's `resume_commit` |
| `handoff_settlement_id` | The `settlement_id` of the request-bearing Builder settlement that created it, or None when the block route released the writer (D15) |
| `status` | `needs-session`, `unavailable`, `postponed`, `resolved`, `completed`, `stale`, `preparation-failed`, `withdrawn` |
| `status_reason` | Enum: `no-registered-handler`, `handler-not-registered-here`, `platform-unsupported`, `tool-missing`, `candidate-missing`, `user-postponed`, `session-expired`, `session-lost`, `handler-failed`, `head-changed`, `contract-changed`, `handler-changed`, `block-cleared`, `paused`, or a registry `failure_codes` key |
| `confirmation_id` | sha256 or None: the ledger confirmation of the linked answer. The view derives observed (`passed`) or not observed (`failed`) from its decision through N03 `resolve_confirmation`; nothing stores the outcome twice |
| `observations` | ≤ 16 `DeliveryInteractionObservation{kind, result: passed\|failed, observed_at, platform, labels, target_class}`; kinds and labels from the registry |
| `created_at`, `updated_at`, `completed_at` | Times |

`ChangeInteractionSession` (coordination, host-local custody): `interaction_id`, `handoff_settlement_id` (copied
from the interaction; D15), `session_id` (128-bit random),
`holder{pid, port, started_at}` (the Cockpit instance), `spawn{token, intent_at}` (128-bit random token committed
before any process starts; an ownership marker that authorizes nothing), `leader{pid, create_time,
cmdline_digest}` (the launcher, set after spawn and before the handler runs; pid = pgid = sid; `create_time` from
`psutil`, as N08 D12), `candidate_head`, `opened_at`, `expires_at`, `state` (`awaiting-input`, `starting`,
`awaiting-human`, `finishing`, `closing`, `contained`), `containment{reason, observed_at, processes}` (only in
`contained`; reason `scan-failed`, `identity-unreadable`, `ambiguous-member` or `kill-refused`; at most 8
`{pid, create_time, name}` with `name` ≤ 64 characters), `input_ref` (128-bit random, never derived from a value),
`inputs_provided` (descriptor names only). No digest, hash or prefix of any private value is stored, because
low-entropy values such as internal URLs could be recovered from one. `cmdline_digest` covers the launcher argv,
which carries the token and never a value (I2).

`_DeliveryInteractionTransitionReceipt` (schema 1): `change_id`, `interaction_id`, `settlement_id` and
`builder_handoff_context` (the retained handoff it belongs to; read through that context like N03's receipts),
`sequence` (from 1 per handoff), `previous_receipt_id`, `kind` (`created`, `postponed`, `resolved`, `completed`,
`failed`, `stale`, `withdrawn`), `before_frontier_digest` and `after_frontier_digest`, `after` (the whole
`DeliveryInteraction`), `confirmation_id` (only for `resolved`), `binding_before_digest` and `binding_after`
(only for `withdrawn`), `receipt_id` (`_receipt_digest` over the rest).

### 1.7 Interfaces and error cases

| Interface | Owner | Behavior |
| --- | --- | --- |
| Block settlement with an interaction-linked request | `runtime_settlement.py` (request-bearing block, `:250`, `:473-528`) | Creates the interaction (`needs-session`, or `unavailable` for `none`) and its `created` transition receipt in the block's transaction; refusal `interaction-request-invalid` with a bounded field code |
| Readiness | `application_readiness.py`, `work_items.py` | New `DeliveryReadinessReason` values: `interaction-ready` (next actor you, action `help-with-step`), `interaction-in-progress` (session open, not awaiting the user), `interaction-awaiting-confirmation` (session `awaiting-human` and the linked request unresolved; next actor you; under U2 (b) no Cockpit action, the panel gives chat guidance; under U2 (a) action `confirm-step`), `interaction-unavailable`, `interaction-postponed` (action `help-with-step`), `interaction-handler-unverified` (session `contained`; next actor you; action `check-handler-stopped`), `interaction-preparation-failed` and `interaction-stale` (next actor agent). New `WorkItemActionKind` values `HELP_WITH_STEP` and `CHECK_HANDLER_STOPPED` (and `CONFIRM_STEP` only under U2 (a)). Progress: ready, awaiting confirmation, unavailable, postponed and unverified → `needs-sign-in` when `human_step` is sign-in, else `needs-decision`; `starting` session → `preparing`; agent reasons → `waiting-for-chat` (M12/M13 of the N09 table). Selection order: programme §5.4 rows 8–9 |
| Continuation | `application_acquisition.py:263` | `interaction-awaiting-confirmation` returns `human` with `confirmation{request_id, expected_frontier_digest}`, the handle the orchestrator passes to MCP `answer` (§1.13); the other user reasons return `human` with no launch; `interaction-preparation-failed` and `interaction-stale` reacquire the same Builder task: with a retained handoff through its same-task acquisition, which withdraws the unconfirmed interaction in the same transaction (D14); without one through ordinary Builder acquisition after the same withdrawal. No retry counter changes; the 64-interaction bound (§1.4) ends a loop. A session in any state, `closing` and `contained` included, makes every Planner, Builder, Finalizer and engine acquisition `busy` |
| `open_interaction_session(change_id, interaction_id, holder, expected_frontier_digest)` | new `application_interactions.py` mixin | Pause-gated custody start (N09-A2 K3): commits the coordination lease with the frontier as an exact no-op participant. Admits a Change with no writer and no handoff, or one whose only custody is the handoff of the interaction's `handoff_settlement_id` (writer = its `original_writer` with kind `handoff`, `branch_head` = `candidate_head`; D15). Refuses `ERR_DELIVERY_INTERACTION_NOT_READY` (status), `_UNAVAILABLE` (static probe), `_STALE`, `_SESSION_BUSY` (another unexpired session, an active writer of any kind, a foreign handoff or any other custody owner), `ERR_DELIVERY_CHANGE_PAUSE_REQUESTED`. A `postponed` interaction reopens through this call |
| `update_interaction_session(..., session_id, expected_state, state, spawn=None, leader=None, input_ref=None, inputs_provided=())` | same | CAS on session id and state; refuses foreign sessions; `starting` requires a committed `spawn`; `leader` is set once, while `starting`, under a CAS on the spawn token; an expired session accepts only the moves to `closing` and `contained` |
| Linked answer dispatch | N03's `answer` adapter and resolver (`target_server.py`), `PortfolioApplication.answer`, `DeliveryRuntime.resolve_request`; N06-A adds the interaction branch | Resolver: for a request whose procedure parses as an interaction handler, it renders only while the interaction is non-stale and its session is `awaiting-human` on `candidate_head` = branch head; the form adds the registry `confirmation_question` and `user_step`, `interaction_id`, `session_id`, `candidate_head`, and `decision_labels` as titles of N03's `passed` and `failed`. Otherwise it returns a plain refusal value and nothing is asked: `ERR_DELIVERY_INTERACTION_NOT_AWAITING_CONFIRMATION` or `_STALE`. Apply: one `RuntimeTransaction` under N03's `expected_frontier_digest` CAS writes the request resolution, appends the ledger confirmation, sets the interaction `resolved` with that `confirmation_id`, writes N03's schema-2 request-resolution receipt and the `resolved` transition receipt (D14), and holds an exact no-op coordination participant that requires the rendered session id and state `awaiting-human`. This transaction consumes N03's consent generation (D16). Any mismatch writes nothing. Replay follows N03: a retry of the consumed generation returns the stored resolution and writes no second ledger entry, interaction write or receipt; a later answer finds the request resolved |
| `complete_interaction(..., session_id, observations)` | same | Validates kinds, labels and bounds against the registry; requires `resolved`; status `completed`; session `closing`; transition receipt; the binding is unchanged, since the answer already resolved request and block (D14). Replay with identical observations returns the stored record |
| `postpone_interaction(..., session_id \| None, reason)` | same | User Not now, expiry, session loss, pause drain: status `postponed` with reason; session `closing`; request stays unresolved; transition receipt |
| `fail_interaction_session(..., session_id, failure_code)` | same | `preparation-failed` (repairable code) or `unavailable` (environment code); session `closing`; transition receipt |
| `release_interaction_session(..., session_id)` | same | Runs the exclusion check itself through `interaction_custody` (D13); no caller-supplied proof. Releases only when it holds; a live owned process → `ERR_DELIVERY_INTERACTION_HANDLER_ALIVE`, lease kept; unknown → `contained` |
| `contain_interaction_session(..., session_id, containment)` | same | Closure unknown (scan failure, unreadable identity, ambiguous member, kill refused): session `contained` with its `containment` record; lease kept; Change attention `interaction-handler-unverified`; never released by time |
| `recheck_interaction_session(change_id, interaction_id, expected_session_id, expected_state)` | same | The user's recovery route for `closing` and `contained`, and for any state whose holder is dead (pid + `started_at`). Exact fence on session id and state. Runs the authorized kills and the exclusion check (D13), then releases, or stays `contained` with a fresh `containment`; an open session of a live holder → `_SESSION_BUSY`. Needs no nonce, opens no session, is not pause-gated (a drain step, K2) and never releases by elapsed time. Callable by the holding Cockpit or any later one |
| `interaction_custody` | new `owlbear_delivery/interaction_custody.py` (leaf; `psutil`) | `classify(session) -> InteractionExclusion{state: excluded \| alive \| unknown, owned, ambiguous}` and `kill_owned(session)` over every current-user process, the caller's descendants included, read by its own `psutil_same_user_processes()`; `worker_stall.psutil_user_processes` is not reused and keeps its semantics (D13). A process-table protocol lets N06-A tests inject tables |
| Same-task handoff consumption | `workspace_coordination.py:1318-1349`, `application_acquisition.py` `_validate_builder_handoff_source`; loader | Refuses while `interaction_session` is present in any state (D15). For an unconfirmed `preparation-failed` or `stale` interaction it carries the `withdrawn` receipt and binding change (D14) |
| `answer` | `portfolio_application.py:1340`; MCP and Cockpit callers | Linked requests: the dispatch above, with every N03 refusal (`ERR_DELIVERY_CONFIRMATION`). Every scoped request: N03's boundary. Cockpit `answer_request` keeps N03-A's `channel-unavailable` refusal for scoped requests unless U2 is (a) |
| Builder block routes | `runtime_reads.py:710-731`, `runtime_settlement.py:524-558` | A linked request outside §1.4 (kind, options, summary, procedure, criteria, `resume_commit`) is refused `interaction-request-invalid`; a `resolution` on any scoped request is N03's refusal |
| `submit_result` / `publish_result` admissibility | `delivery_runtime.py` facade; N03 `evidence.py` | Adds: an observation whose `procedure_registration_digest` equals a handler digest needs a `completed` interaction in the same outcome with that digest, `candidate_head == exact_commit`, and an equal machine observation (kind, result, platform, labels, target class); a `human-confirmed` observation whose `confirmation_id` is an interaction's needs that interaction `completed` and non-stale with `candidate_head == exact_commit` (N03 I6 already requires decision `passed`). Reasons `interaction-evidence-unmatched`, `interaction-not-completed`, `interaction-stale` join N03's bounded `gaps` |
| Projection | `work_items.py`, `application_models.py`, MCP `target_models.py`, Cockpit `target_models.py` | `DeliveryInteractionView{interaction_id, status, status_reason, handler purpose, why_human, user_step, human_step, confirmation_question, inputs (name, label, kind, required; never values), acceptance refs, candidate_head, confirmation (request_id, decision label) when resolved, session (state, expires_at, inputs_provided, input_ref, containment; holder only as "this Cockpit" or "another Cockpit"), observations}` on `WorkItemDetailView`, `get_change` and the build context |
| Cockpit HTTP (N06-B) | new `owlbear_cockpit/routes/interactions.py`, `interaction_sessions.py` | `POST /api/changes/{c}/interactions/{i}/session` (Help; lease; returns descriptors, `launch_summary` and the nonce in the JSON body; launches nothing), `POST …/start` (Start check; inputs, possibly none; launches), `GET …/session`, `POST …/postpone`, `POST …/session/recheck` (body `{session_id, state}`; no nonce). No confirm route unless U2 is (a) (N06-C, §1.13). Nonce header `X-OwlBear-Interaction-Session`, compared with `secrets.compare_digest`. The nonce is a panel-to-session binding, never user authorization. Error envelope `{code, detail, authority: "delivery", retry_safe}` with bounded field codes, never input values |
| Loopback request guard (N06-B) | new `owlbear_cockpit/request_guard.py`, installed by `run()` (`main.py:311`) | Every request: `Host` ∈ {`127.0.0.1:<port>`, `localhost:<port>`} else 403 `COCKPIT_HOST_REJECTED`. Unsafe methods: a present `Origin` must equal `http://127.0.0.1:<port>` or `http://localhost:<port>`, and a present `Sec-Fetch-Site` must be `same-origin` or `none`, else 403 `COCKPIT_ORIGIN_REJECTED`. Header-less local clients pass (P8), so the guard is a cross-site defense only, never a user-presence check. Under U2 (a) N06-C's confirm route also needs N03-C's exact `Origin` and cookie checks (§1.13) |
| Cockpit access log (N06-B) | `run()` (`main.py:372`) | `uvicorn.run(..., access_log=False)` plus a Cockpit access logger emitted by the outer ASGI wrapper that logs method, route template (or `unmatched`), status and duration only, never the raw path, query string or headers; installed before the guard so rejected requests are logged the same way. uvicorn's error logger stays on; its malformed-request warnings carry no request target (verified in N06-B) |
| Handler protocol v1 (N06-B) | new `owlbear_delivery/interaction_protocol.py` | JSON Lines, ≤ 16 KiB per line, ≤ 256 lines. Cockpit → handler: `start{protocol: 1, interaction_id, candidate_head, inputs}`, `human-step-complete{outcome}` (`observed` or `not-observed`, from the ledger decision `passed` or `failed`), `cancel{}`. Handler → Cockpit: `ready`, `awaiting-human`, `observation{kind, result, platform, labels, target_class}`, `finished`, `failed{code}`. stdin EOF means cancel: clean up and exit (P7). Unknown messages, oversize lines or values echoed back end the session as `handler-failed` |
| Handler launch (N06-B) | `owlbear_cockpit/interaction_sessions.py`, new `owlbear_cockpit/interaction_launcher.py` | After `spawn` is committed: `subprocess.Popen([python, -m, owlbear_cockpit.interaction_launcher, --token=<t>], stdin=PIPE, stdout=PIPE, stderr=PIPE, env=allowlist + token, cwd=…, pass_fds=(control,), start_new_session=True)`. `leader` (pid, `psutil` create time, cmdline digest; cmdline must carry the token) is committed before `release` is written to the control pipe; a failed commit closes the pipe. The launcher then starts the registry argv as its child with inherited stdio and the token in its environment; `start` (inputs only there) is written after `release`. stderr is kept in a 4 KiB memory ring, never logged or returned; deadlines per registry; close sends `cancel` (or nothing after `human-step-complete`), closes stdin, waits the cleanup deadline, then runs the D13 kills and `release_interaction_session` |

Errors keep the existing envelopes: core `DeliveryInteractionError(DeliveryRuntimeConflictError)` with
`ERR_DELIVERY_INTERACTION_*` codes mapped by MCP `_raise` (`target_server.py:1243-1250`) and Cockpit `_http_error`
(`target_work.py:819-835`).

### 1.8 Session lifecycle

| From | Event (channel) | To | Effects |
| --- | --- | --- | --- |
| — | Builder block with linked request (MCP settlement) | `needs-session` or `unavailable` | Block, request, interaction and `created` receipt in one transaction |
| `needs-session`, `postponed` | Help with this step (Cockpit `open`) | session `awaiting-input` | Lease; nonce in memory; panel shows `launch_summary` and inputs; nothing launched |
| session `awaiting-input` | Start check (Cockpit `start`) | session `starting` | Validate inputs; commit `spawn`; start the launcher; commit `leader`; `release`; the launcher starts the handler; `start` on stdin; `input_ref`; Cockpit drops its references (D13) |
| session `starting` | handler `awaiting-human` | session `awaiting-human` | Readiness `interaction-awaiting-confirmation`; panel per §1.13 |
| session `awaiting-human` | linked `answer` accepted (N03 boundary, §1.13) | `resolved`; session unchanged | Request resolution, ledger entry, `confirmation_id` and receipts in one transaction |
| session `awaiting-human` | answer declined, cancelled, refused, channel missing or request state invalid | unchanged | Nothing written |
| session `awaiting-human`, interaction `resolved` | Cockpit reads the resolution bound to its session | session `finishing` | `human-step-complete{outcome}` |
| session `finishing` | handler `finished` | `completed`; session `closing` | Observations; binding unchanged |
| any open session state | Not now (`postpone`) | `postponed` / `user-postponed`; session `closing` | `cancel` |
| any open session state | `expires_at` passes (Cockpit timer) | `postponed` / `session-expired`; session `closing` | `cancel` |
| any open session state | handler `failed`, exit or protocol violation | `preparation-failed` or `unavailable`; session `closing` | By registry code |
| session `closing` | exclusion holds (D13) | lease released | Only now may another session or writer acquire the Change |
| session `closing` | cleanup deadline passes | still `closing` | D13 kills; exclusion check again |
| session `closing` | exclusion unknown | session `contained` | Lease kept; attention `interaction-handler-unverified` with `containment` |
| session `closing` or `contained` | **Check again** (`recheck`) | released, or `contained` with a fresh `containment` | No timer; no new session |
| any session state | Cockpit exits (clean) | as Not now or `session-lost`; session `closing` | Shutdown hook runs close and the exclusion check before exit; if it cannot finish, the lease stays |
| any session state | Cockpit dies (SIGKILL), including between spawn and `leader` | unchanged until a Cockpit acts | Handler sees EOF (P7); an unreleased launcher exits at control-pipe EOF (P11). Nothing is released by time: the next Cockpit start, or `open` or `recheck` on that Change, finds the holder dead (pid + `started_at`) and runs the D13 kills and exclusion check, by token alone when `leader` is missing. Then released, or `contained`. Interaction becomes `postponed` / `session-lost`, or `preparation-failed` / `session-lost` if it was `resolved` |
| `resolved` (session `awaiting-human` or `finishing`) | session lost before `finished` | `preparation-failed` / `session-lost` | After release the same Builder task is reacquired from the answered pause (D14); the resolution cannot support a result |
| `preparation-failed` or `stale`, request unresolved, no session | same-task Builder reacquisition | `withdrawn` | Withdrawal receipt, binding change and claim activation in one transaction (D14) |
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
the HTTP test client and the maintained E2E stack (`e2e/support/start-work-portfolio-stack.mjs`); N03's D13 `answer`
resolver and boundary, ledger readers `resolve_confirmation` and `confirmation_applies`, the schema-2
request-resolution receipt and the L replay row; the retained Builder handoff and its same-task acquisition
(`workspace_coordination.py:1288-1349`); `psutil` 7.2.2, but not `worker_stall.psutil_user_processes` (D13).

### 1.10 Contracts for successors

**N07 (B1 assisted-check runner)** builds on exactly these N06 surfaces:

1. One `InteractionHandlerDescriptor` for B1 added to `DEFAULT_INTERACTION_HANDLERS`: `argv` runs the candidate's
   handler inside `{candidate_worktree}`; `human_step: sign-in`; one `url` input, `private`, with a `url_policy`
   (`host_policy`, `paths` templates with typed identifier slots, and `query_keys` only if a B1 target needs a
   query, each with a value pattern);
   `target_classes` (for example `sharepoint`, `confluence`); `platforms: (macos,)`; `resources: (edge-profile,)`;
   observation kinds for launch, restart and owned cleanup; failure codes classified repairable or environment.
2. The candidate-side handler implements protocol v1 from its own source, reads inputs only from `start`, never
   echoes them, treats stdin EOF as cancel, and reports only registry-declared kinds and labels. Every process it
   starts keeps the inherited environment, so the spawn token marks it as custody (D13); a process started
   through a service manager (for example `open -a`) leaves custody and is N07's to track.
3. Profile custody and cross-Change contention for `edge-profile` are N07's: the N06 lease ends when the session
   ends and does not prove the browser or profile was released.
4. N07-B's evidence reassessment uses N04 applicability over interaction-backed observations; N06 adds no
   applicability rule.
5. N02 U1 and U2 were answered (a): this repository's live controller, Cockpit included, is pinned and upgraded
   through `/upgrade-delivery`, so Cockpit runs the pinned release. Whether candidate code launched from it
   needs a launcher change is N07's question (G8).

**N09-B** lists **Help with this step**, **Check again** and the interaction reasons in its capability inventory
and keeps `/continue-change`'s `human` yield for them, including the `confirmation` hand-off to MCP `answer`
(§1.13). **N04** maps interaction-backed observations like other `manual-procedure`
and `command` evidence; an activation makes open interactions `stale`. **N08-B** does not mount interaction routes in
degraded mode. **N10** covers V17 and V22 in the cumulative matrix; the real B1 device run is N10-H.

### 1.11 Exclusions

B1 handler, synthetic sites and Edge profile custody (N07); evidence applicability after revision (N04); the
**Change requirements** control (N04); prompt retirement (N09-B); generic interactive-browser tools and B5's policy;
OS keychain storage; a separate loopback form server, runner process or Unix-socket channel (D1); defining a
user-only confirmation mechanism or channel (N03's boundary and U2, §1.13); confirmation through chat text; Windows.

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
- **D3 No N06 change to N03's confirmation or locator shapes** (P12). N03 §1.5 and §1.9 expect N06 to add
  confirmation channel `interaction` and an `interaction:` locator scheme. Neither is needed. The channel records
  the capture route (`mcp-elicitation`, or N03-C's `cockpit` under U2 (a)); an `interaction` value would name a
  target, not a route. The interaction binding is carried by the scope's `procedure`, by the rendered question
  whose digest the ledger keeps (`interaction_id`, `session_id`, `candidate_head`), and by
  `DeliveryInteraction.confirmation_id`. `DeliveryUserConfirmation` stays schema 1 with N03's channel enum, the
  locator schemes stay N03's, and N06 adds no nested version step beyond the frontier widening for
  `interactions` (§1.6). N03 G5 closes; F6 records the N03 text this supersedes.
- **D4 Confirmation through N03's boundary only.** The MCP `answer` tool accepts caller-set
  `provenance: user-confirmed` today (`target_server.py:442-460`; Cockpit `AnswerRequestBody` defaults it,
  `target_models.py:381`), and both Builder block routes store a worker-supplied `resolution` verbatim
  (`runtime_reads.py:710-731`, `runtime_settlement.py:524-558`). N03-A closes all three for scoped requests. N06
  defines no channel: a linked request is a scoped `confirm-check` request answered through N03's `answer`, with
  an interaction branch in its resolver and transaction (§1.7). Round 1 of this plan made a Cockpit-only route
  the boundary (wrong, P10); its revision refused `answer` on linked requests and accepted a removed
  `confirmation: {kind: request-resolution}` record (incompatible with N03's ledger, P12).
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
- **D13 Custody until exclusion, with positive process ownership** (P7, P11; programme §5.2). A crash or a
  reused pid must never release custody or aim a signal at another process.
  - *Pre-spawn authority.* Before any process exists, Cockpit commits the session's `spawn{token, intent_at}`
    (state `starting`). The token is 128-bit random and marks ownership; it authorizes nothing, so its
    visibility to the same user (P5) is harmless.
  - *Release-gated launcher.* Cockpit starts `owlbear_cockpit.interaction_launcher` with `start_new_session=True`
    (pid = pgid = sid), the token in its argv and environment, and a control pipe. It runs nothing until it reads
    `release`; EOF or any other bytes first make it exit without starting the handler (P11).
  - *Identity before execution.* Cockpit reads the launcher's `psutil` create time, checks the token in its
    cmdline, commits `leader{pid, create_time, cmdline_digest}` under a session-id and token CAS, and only then
    writes `release`. The launcher starts the registry argv as its child with the token added to the allowlisted
    environment; Cockpit then writes `start`. A failed commit closes the control pipe. A Cockpit crash at any
    point therefore leaves either no handler or a recorded leader.
  - *Pinned leader.* After `release` the launcher reaps its child and then waits; it never exits on its own. A
    live leader pins its group for the whole custody: POSIX never gives a new process the pid of an active
    process group, and `setpgid` joins only groups of the caller's session, whose members descend from the
    leader.
  - *Who may be signalled.* (1) The recorded group, by `killpg(SIGKILL)`, only right after the leader was
    verified live by pid, create time and cmdline token. (2) Any current-user process whose environment or
    cmdline carries the token, one at a time through `psutil.Process.send_signal`, which refuses a pid whose
    create time changed. Nothing else is ever signalled (I11).
  - *Exclusion.* Holds when no live process carries the token, the leader identity is not live, and no member of
    the recorded group or session is ambiguous. A member is ambiguous when it lacks the token while no process
    holds the leader's pid: it may belong to a reused group or be a descendant that cleared its environment. A
    live process holding the leader's pid with another create time proves the recorded group ended before that
    process was created (the fork rule above), so token-less members of a group it leads are not ours and are
    ignored. Zombies count as exited.
  - *Unfiltered scan.* `worker_stall.psutil_user_processes` skips the caller and every descendant
    (`worker_stall.py:347-370`), because Delivery's own Git children are never a stopped worker's leftovers. A
    launcher stays Cockpit's child under `start_new_session=True`, so that scanner would never see it and exclusion
    would hold with the handler alive. `interaction_custody` scans every current-user process, the caller's
    descendants included, through its own `psutil_same_user_processes()`; the worker scanner is unchanged.
  - *Containment.* A failed scan, an unreadable environment or cmdline inside the recorded group or session, an
    ambiguous member or a kill the OS refuses keeps the lease in `contained` with a bounded `containment`
    record. Nothing releases it by time; **Check again** (`recheck`, §1.7) re-runs the kills and the check.
  - *Missing identity.* A session with `spawn` and no `leader` (a crash between spawn and commit) is checked by
    token alone; the blocked launcher has normally exited at control-pipe EOF already (P11).
  - *Token here, not in N08 D12.* N08 rejects an environment marker for controllers because children inherit it;
    for an interaction, inheritance is the point, since every descendant is custody.
  - *Residual.* A descendant that both calls `setsid` and clears its environment escapes; registry handlers are
    repository code, and N07 owns Edge profile custody (§1.10 items 2 and 3, G15).
- **D14 Interaction writes replay through receipts; the binding changes only by receipt** (P12, P13). During a
  retained Builder handoff the loader refuses a pending publication (`delivery_application_loader.py:603-607`) and
  rebuilds the expected frontier from `snapshot.frontier` with only the handoff binding substituted
  (`:1010-1053`). It derives that binding only as the settlement result or N03's request-resolution successor
  (`:1582-1605`, `:1831-1890`), and anchors lifecycle receipts only to those two baselines (`:1755-1777`).
  - *Binding preserved.* No N06 write during a handoff changes the outcome binding except `withdrawn`. `complete`
    does not clear the block: the linked answer already resolved request and block through N03's
    request-resolution receipt (`runtime_receipts.py:309-348` requires `updated_block.resolved`), and the Builder
    reacquires from that answered pause through the existing same-task acquisition. `created`, `postponed`,
    `resolved`, `completed`, `failed` and `stale` receipts carry interaction state only; the loader requires the
    binding to equal the one it already derives.
  - *Withdrawal.* A failure before confirmation (`preparation-failed` or `stale`, request unresolved, no session)
    needs the Builder without an answer. The same-task acquisition transaction that consumes the handoff
    (`workspace_coordination.py:1318-1349`) gains one participant, a `withdrawn` receipt: the interaction becomes
    `withdrawn`, and the binding becomes the settlement result with the block resolved (`resolution_note`
    `interaction-withdrawn:<status_reason>`, `resolution_locators` `(request_id,)`) and the request unresolved, so
    it can never support evidence. The loader admits it as a third baseline, exclusive with N03's
    request-resolution receipt for that request: both, or a withdrawal of a resolved request, fail bootstrap.
    Without a handoff the same withdrawal is an ordinary portable write before Builder acquisition.
  - *Identity and order.* Every receipt names its handoff (`settlement_id`, `builder_handoff_context`) and is read
    through that context, so a receipt of an earlier handoff never replays into a later one. The loader merges
    N06's receipts and N03's answer and lifecycle receipts into one chain from the settlement frontier to the
    local frontier: each link's `before_frontier_digest` equals the previous link's after digest; a `resolved`
    receipt shares its transaction, frontier digests and `confirmation_id` with its N03 request-resolution
    receipt; a lifecycle baseline takes the interactions replayed up to its link. A gap, fork, reordered link,
    unbound local interaction or byte difference fails the existing bootstrap check (V20). Outside a handoff (no
    retained handoff and no binding with `builder_handoff_context`, `:603-607`), interaction writes record pending
    publication like other portable writes.
  - *Restart cases.* (1) Failure before confirmation, restart before reacquisition: binding = settlement result,
    interaction `preparation-failed` or `stale` from its receipt; the Change is available and readiness offers the
    retry. (2) Restart after that reacquisition: the handoff is consumed and the loader derives the acquired claim
    from the withdrawn baseline (G18). (3) Restart between the answer and `complete`, or between `complete` and
    reacquisition: binding = N03's successor, interactions from receipts. (4) Restart after reacquisition from the
    answered pause: as today, plus the interactions.
- **D15 Session beside its own Builder handoff** (round 3). A request-bearing Builder settlement keeps the ended
  writer as a passive `kind="handoff"` writer with `builder_handoff` (`workspace_coordination.py:1288-1316`);
  `release` refuses it (`:894`), a coordination update refuses to change a record that holds it (`:1000-1001`),
  and only the same-task acquisition consumes it (`:1318-1349`). An interaction created by settlement always
  meets that writer.
  - *Admission.* `open` admits exactly two custody shapes: no writer and no handoff (the block route released the
    writer at `resume_commit`, `change_workspace.py:1260`), or the handoff whose `settlement_id` equals the
    interaction's `handoff_settlement_id`, whose writer is its `original_writer` with kind `handoff`, and whose
    `branch_head` equals `candidate_head`. An active writer of any kind, a foreign handoff or any other custody
    owner is `_SESSION_BUSY`.
  - *Fence.* `ChangeCoordination` validates that a session beside a handoff names that handoff's
    `settlement_id` (`workspace_models.py:1633-1660`). The ownership-update rule gains one exception: a
    replacement that differs from a handoff-holding record only in `interaction_session` and keeps that relation.
    Every other handoff mutation still refuses.
  - *Release and reacquisition.* The session never releases or replaces the handoff; the handoff outlives it.
    `_prepare_builder_handoff_acquisition` and every other route that consumes or replaces a handoff refuse while
    `interaction_session` is present, `closing` and `contained` included. After the D13 release, the same-task
    acquisition consumes the handoff as today, with D14's withdrawal when no confirmation exists. Unrelated
    custody stays refused both ways (I6).
- **D16 One consent generation** (round 3; N03 `:486-513`). The linked answer consumes N03's consent generation in
  the transaction that records the confirmation, the interaction `resolved` and both receipts; N06 adds no
  generation or boundary of its own. The N06 binding inside that generation is the rendered `interaction_id`,
  `session_id` and `candidate_head` beside N03's request, criteria and frontier digest, plus the coordination
  participant that requires the same session in `awaiting-human`. Today the generation is the expected frontier
  digest, made unrepeatable by the ledger append. Opening, reopening or recovering a session writes no frontier,
  so the session id in the question and the participant, not the digest, separate one session from the next. If
  PR #360 replaces the digest by an explicit server-owned generation consumed on accept, decline or cancel (as
  N05's `merge_consent` generation, N05 D14), the same binding enters that generation's subject: any session or
  interaction change supersedes it, a decline or cancel consumes it without an N06 write, and a fresh `answer`
  while still `awaiting-human` mints the next. Either way a consumed or superseded generation records nothing
  new, and a replay returns the recorded disposition.

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

N03 (PR #360 at `f4d09d774`) owns the only user-only confirmation. MCP `answer` on a scoped request asks the user
through form elicitation from one server-injected `Annotated[DeliveryConfirmationOutcome, Resolve(...)]` parameter,
on the legacy `elicitation/create` route or the modern `InputRequiredResult` round trip. An `accept` appends one
`DeliveryUserConfirmation` to the Change ledger (I10) together with the request resolution and, during a retained
handoff, a schema-2 request-resolution receipt, in one transaction. Decline, cancel or a missing channel writes
nothing (`ERR_DELIVERY_CONFIRMATION`), and the SDK's `RequestStateBoundary` refuses forged, foreign, expired or
re-bound state. Each confirmation consumes N03's consent generation (`:486-513`; D16). N03 U2 (open user
decision, N03 `:541`) decides whether a Cockpit click also counts. N06 adds no channel; it adds the interaction
branch of §1.7 to that `answer`.

**Journey under U2 (b), chat only** (N03's recommendation):

1. The handler reports `awaiting-human`; Cockpit moves the session to `awaiting-human`. The panel shows the
   question, says to confirm in VS Code chat, offers a copyable `/continue-change <change-id>` and keeps **Not now**.
2. Readiness reads `interaction-awaiting-confirmation`. `/continue-change` acquires `human` with
   `confirmation{request_id, expected_frontier_digest}` and, per `w-orchestration`, calls MCP `answer` with only
   the Change, request and frontier identifiers. The agent supplies no decision, and a caller `resolution` would
   confer nothing.
3. The resolver renders the interaction question (§1.7) and VS Code shows the form; the user picks **Observed**
   (`passed`) or **Not observed** (`failed`).
4. The §1.7 transaction resolves the request, appends the ledger entry and sets the interaction `resolved`.
5. Cockpit's session manager, which reads the frontier at most once a second while `awaiting-human`, sees the
   resolution bound to its session, sends `human-step-complete{outcome}` and moves the session to `finishing`.
6. The handler reports `finished`; `complete`, close and release follow (§1.8); continuation reacquires the
   Builder task.

Decline, cancel, a missing channel, a refusal or an invalid request state records no confirmation and no N06
write (whether a decline consumes the generation is N03's rule, D16); the session stays `awaiting-human` until the
user answers a fresh `answer`, selects **Not now**, or the session expires. An expiry during the elicitation
supersedes the generation, so the late answer records nothing.

**Journey under U2 (a), Cockpit clicks also count.** Steps 1 and 3 change: the panel shows **Observed** and **Not
observed**, and N06-C's `POST …/confirm` hands the decision to N03-C's Cockpit boundary adapter. That adapter
builds the channel-`cockpit` confirmation behind N03-C's exact-`Origin` and `SameSite=Strict` cookie checks and
calls the same `PortfolioApplication.answer` dispatch, so steps 4 to 6 are identical. The chat journey stays
available. Residual risk is N03 U2 (a)'s: an agent driving a browser can click.

**U2 (c) or (d).** (d) keeps human checks chat-only, so N06 follows (b). (c) needs an N03 plan revision for the
presence helper; N06 follows (b) until it lands.

**Order.** N06-A starts after N03-C (execution plan §4.2), and N03-C starts only after U2 is answered, so the answer
is known before any N06 code. N06-A proves the dispatch through `Client(assemble_target_server(...))` on both
protocol routes; N06-B proves journey (b) end to end with a real Cockpit, launcher and handler; N06-C ships and
proves journey (a) only if U2 is (a), and otherwise proves that no confirm route exists (G14).

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
| P10 | Round-1 gate source reads on `1600efa60` (source equal to `634a77be7`) | Both Builder block routes copy the worker's `DeliveryRequest`, `resolution` included (`runtime_reads.py:710-731`, `runtime_settlement.py:524-558`); `DeliveryRequestResolution.provenance` is a caller-set literal (`runtime_models.py:821-837`); MCP `answer` forwards it (`target_server.py:442-460`); `run()` calls `uvicorn.run(app, host=_HOST, port=port)` with the default access log (`main.py:372`); the session-open response carries the nonce and the guard admits header-less clients (this plan); `psutil` 7.2.2 is locked (the `mcp` version is corrected in P12); no `elicit` call exists in `serve/` | Gate findings 1, 2, 3 and 5 hold; confirmation moves to N03's boundary (D4, §1.13); D13; access log off (§1.7) |
| P11 | `p11_launcher.py` on `e2fa3d913` (macOS, `psutil` 7.2.2): a launcher started with `start_new_session=True`, a control pipe (`pass_fds`) and a token in argv and environment | pid = pgid = sid; `psutil` reads the token from its cmdline and environment; closing the control pipe before `release` makes it exit 0 without spawning and leaves no token holder; after `release` its child and grandchild inherit the token in the same group (3 holders); `killpg` of the verified leader leaves no token holder | D13 release gate, token ownership and group kill (Ubuntu in G6) |
| P12 | Round-2 gate source reads on `e2fa3d913` (source equal to `634a77be7`) and lane-c `86289635f` | N03 now defines D13 (`Resolve` parameter, legacy and modern routes, SDK `RequestStateBoundary`), the ledger with `confirmation_id` and channel enum (§1.5), I6, I10, the schema-2 request-resolution receipt binding the ledger append and the L replay row (§1.7), `ERR_DELIVERY_CONFIRMATION`, N06 expected to add channel `interaction` and an `interaction:` locator (§1.5, §1.9), U2 open (`:511-570`); the `confirmation: {kind: request-resolution}` shape no longer exists. The loader refuses a pending publication beside a Builder handoff (`delivery_application_loader.py:603-607`) and rebuilds the handoff frontier from `snapshot.frontier` with one binding substituted (`:1010-1053`). N08 D12 identifies controllers by pid, create time and cmdline digest and rejects an environment marker because children inherit it. `uv.lock` locks `mcp` 2.3.0 (P10 recorded 2.2.0 in error). The round-1 URL rule admits `?client_secret=…` and `/%61ccess_token=…` | Round-2 findings 1–5 hold; D3, D4, D13, D14, §1.5, §1.13 |
| P13 | Round-3 gate source reads on `origin/dev` `141795676`, merged as `edab21d5a`, and lane-c `f4d09d774` (the gate cited pre-merge lines `workspace_coordination.py:951` and `delivery_application_loader.py:1592`) | A request-bearing Builder settlement replaces the build writer by a `kind="handoff"` writer with `builder_handoff` (`workspace_coordination.py:1288-1316`, `:1312`); `release` refuses it (`:894`); updates refuse while it is held (`:1000-1001`); only `_prepare_builder_handoff_acquisition` consumes it (`:1318-1349`); the model pins writer = `original_writer` with kind `handoff` (`workspace_models.py:1633-1660`). The loader also refuses pending publication while any binding carries `builder_handoff_context` (`delivery_application_loader.py:603-607`), derives a handoff binding only as the settlement result or the request-resolution successor (`:1582-1605`, `:1831-1890`) and anchors lifecycle receipts only to those (`:1755-1777`); that receipt requires a resolved block (`runtime_receipts.py:309-348`). `psutil_user_processes` skips its caller and the caller's descendants (`worker_stall.py:347-370`). N03 `:486-513`: single use; for scoped requests the expected frontier digest is the generation, consumed by the ledger append; N05 binds its own `merge_consent` generation (lane-c N05 plan `:135`, `:350`). The round-2 path rule admits `/invite/<GUID>` (alphanumeric runs ≤ 12, no credential word) | Round-3 findings 1–5 hold; D13–D16, §1.5 |

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

- **Prerequisites:** N06-P and N03-C (execution plan §4.2); N03-C needs N03-A's boundary, ledger and receipts as
  amended by PR #360 and an answered N03 U2 (G14); added by this plan: N09-A2 (coordination v2, pause K-inventory).
- **Editable paths:**
  - new `serve/delivery/src/owlbear_delivery/interaction_registry.py`, `application_interactions.py`,
    `interaction_custody.py`
  - `runtime_models.py`: `DeliveryInteraction`, `DeliveryInteractionObservation`, `DeliveryFrontier.interactions`
    and version widening; `DeliveryInteractionError`
  - `runtime_settlement.py`, `runtime_reads.py`: both request-bearing block routes (interaction creation and
    validation, `created` receipt)
  - `runtime_receipts.py`: `_DeliveryInteractionTransitionReceipt`; handoff change-intent widening
  - `delivery_runtime.py` facade: frontier writers for interaction status with their transition receipts,
    `resolve_request`'s interaction branch, `publish_result` admissibility (§1.7); N03 `evidence.py` gap reasons
  - `workspace_models.py`: `ChangeInteractionSession`, `ChangeCoordination.interaction_session`, version widening;
    `workspace_coordination.py`: lease open, update, recheck and release with the no-op frontier participant and
    the K3 check; the session-beside-handoff relation, its update exception and the acquisition refusal (D15)
  - `application_models.py`: views, `DeliveryContinuationReason` additions and the `confirmation` handle;
    `application_acquisition.py`: `human` results, busy under an open session, Builder retry for preparation
    failure and stale; `application_readiness.py`, `work_items.py`: reasons, `HELP_WITH_STEP`,
    `CHECK_HANDLER_STOPPED`, progress rows, static probe
  - `portfolio_application.py`: `answer`'s interaction dispatch (§1.7); `delivery_application_loader.py`:
    `interaction_handlers` composition parameter, N03 §1.7 normalized comparisons for the new frontier field, and
    the D14 extension of N03's L row (one receipt chain, the withdrawal baseline)
  - `delivery_state.py`: snapshot version
  - `state_formats.py`, `state_migration.py`: §1.6 entries, `NESTED_MODELS`, marker step
  - `owlbear_delivery/__init__.py`; `serve/delivery/tests/fixtures/module_surface.json`; N02 fingerprint and golden
    fixtures
  - `serve/delivery-mcp/src/owlbear_delivery_mcp/target_models.py`, `target_server.py`: views, error codes, the
    interaction branch of N03's `answer` resolver; no new tool
  - `serve/tools/src/owlbear_tools/delivery_diagnostics.py`: version mirror
  - frontend companions: `serve/cockpit/web/src/api/workItems.ts`, `components/workItemPresentation.ts`,
    `WorkItemDetail.tsx` (interaction-linked requests show status and reason without answer controls),
    `WorkPortfolioPage.tsx`; component test; `serve/cockpit/src/owlbear_cockpit/target_models.py`
  - tests: new `serve/delivery/tests/test_interaction_registry.py`, `test_interactions.py`,
    `test_interaction_custody.py`; `test_state_formats.py`, `test_state_migration.py`, `test_delivery_runtime.py`,
    `test_work_items.py`, `test_portfolio_application.py`; `serve/delivery-mcp/tests/test_target_server.py`,
    `test_delivery_adapter.py`; `serve/tools/tests/test_delivery_diagnostics.py`; `tests/test_cockpit_boundary.py`
    (reason, progress and action parity); `tests/test_delivery_worktree_authority.py` (new frontier writers; lease
    in the K-inventory); `tests/test_agent_ecosystem_validation.py`
  - skill and agent text: `share/skills/w-packet-building/SKILL.md` (block with a `confirm-check` request naming the
    interaction procedure; cite the interaction's `confirmation_id`; copy machine observations; never collect
    values in requests), `share/skills/h-decision-requests/SKILL.md` (no URLs, hostnames, credentials or tokens in
    request answers), `share/skills/w-orchestration/SKILL.md` (on `interaction-awaiting-confirmation`, call MCP
    `answer` with only the Change, request and frontier identifiers and tell the user to answer the form; never pass
    a resolution; on other interaction reasons, yield with the Cockpit instruction), `share/agents/repairer.agent.md`
    (never answer scoped requests)
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
    `release_interaction_session` finds exclusion in the injected process table.
  - Linked answer (§1.7, §1.13) with the session `awaiting-human`, through `Client(assemble_target_server(...))`
    with an `elicitation_callback` that accepts `passed`, on `mode="legacy"` and `mode="2026-07-28"`: the rendered
    form carries the registry question, `interaction_id`, `session_id` and `candidate_head`; one transaction
    resolves the request, appends one ledger entry (channel `mcp-elicitation`), sets the interaction `resolved`
    with that `confirmation_id`, and writes N03's schema-2 request-resolution receipt and the `resolved` transition
    receipt; the predecessor ledger is a byte prefix of the new one (I10); continuation before the answer returns
    `human` with the `confirmation` handle. Then `complete` with registry-valid observations → `completed`,
    session `closing`; `release` frees the lease; the binding is unchanged throughout; the same Builder task is
    reacquired from the answered pause with the interaction in its build context.
  - The Builder submits a `manual-procedure` `passed` `human-confirmed` observation citing the interaction's
    `confirmation_id` plus copied machine observations at `exact_commit = candidate_head`; the result promotes and
    N03's evaluator shows the criterion `covered`.
  - The same journey answered `failed`: the interaction is `resolved` and its view reads not observed; a `passed`
    `human-confirmed` observation citing it → N03 `confirmation-not-applicable`.
  - Builder handoff (D15), through both block routes: after a request-bearing `settle_worker_invocation` the
    passive `handoff` writer and `builder_handoff` remain; `open` succeeds beside them, the coordination record
    validates the relation, the journey completes, and only after the D13 release does the same-task acquisition
    consume the handoff. After a `transition_delivery` block (writer released at `resume_commit`), `open` succeeds
    with no writer.
  - Withdrawal (D14): before any answer the handler fails with a repairable code (and, separately, the handler
    digest changes); after release, `acquire_change_action` reacquires the same Builder task in one transaction
    with the `withdrawn` receipt; the request stays unresolved and cannot support a result. Restart through the
    default loader after the failure and before reacquisition, and after reacquisition → available, byte-identical.
  - Restart replay (D14), parameterized after each write of the journey during the retained Builder handoff
    (`created`, `postponed`, reopen, `resolved`, `completed`, `failed`, `withdrawn`) and with N03's defer and resume
    receipts before and after the answer and the failure: restart through the default loader before publication →
    the Change is available and its frontier, binding, ledger and interactions are byte-identical. Publication then
    writes snapshot 4 with them, and a fresh host restores them.
  - Pause request while `needs-session` → `open` refused; with an open session → `update`, the linked answer,
    `complete`, `postpone` and `recheck` succeed and the pause converts after release (N09 K2).
  - Format: frontier 20 with interactions and coordination 3 with a session round-trip byte-identically; every
    golden record of earlier versions round-trips unchanged; `delivery-migrate` marker step on a disposable portfolio
    with a passive Builder handoff and an N03-format Change changes only the marker.
- **Negative scenarios:**
  - Block refused with `interaction-request-invalid`, nothing written: unknown handler, `applies_to.kind` `waive`,
    non-empty options, a summary other than the registry question, criterion not current, missing or non-head
    `resume_commit`, more than 64 interactions.
  - Registry refuses a credential-named input, a `public` url input, an unknown placeholder, an unregistered label.
  - Fabrication, assembled (`Client(assemble_target_server(...))`, default loader, real worktree), each for an
    interaction-linked request and for an ordinary scoped waiver request, through both block routes
    (`transition_delivery` block and Builder `settle_worker_invocation`): (1) the worker supplies a request already
    resolved `user-confirmed` → N03's validation refusal, nothing written; (2) the agent calls MCP `answer` with
    `provenance: user-confirmed` through a client without elicitation → `channel-unavailable`; (3) Cockpit HTTP
    `answer_request` → 409. Each leaves no ledger entry and the request unresolved; a Builder result with a
    `human-confirmed` observation or a `waived` record citing it is refused, finalization refuses, and no criterion
    reads `covered` or `waived`.
  - Linked answer refused before anything is asked, frontier and coordination bytes unchanged: no session, or a
    session in `awaiting-input`, `starting`, `finishing`, `closing` or `contained` →
    `_NOT_AWAITING_CONFIRMATION`; a stale interaction → `_STALE`. Declined, cancelled, no capability, no
    back-channel → N03's refusals; nothing written; the session stays `awaiting-human`.
  - Session moved between render and apply: the test callback expires and reopens the session during a legacy
    elicitation, or between modern rounds → nothing written (coordination participant or SDK question pin).
  - Consent generation (D16), through `Client(assemble_target_server(...))` on both routes: declined and cancelled
    → no ledger entry, interaction and session unchanged, and a fresh `answer` asks again; superseded, by a frontier
    change or by closing and reopening the session (new session id, same frontier digest) between render and apply
    → nothing written; concurrent replay, two clients applying the same accepted state at once and a re-send after
    success → exactly one ledger entry, one `resolved` interaction and one transition receipt, and every other
    call returns the recorded resolution and writes nothing.
  - Custody relation (D15): `open` beside an active `build`, `plan`, `repair` or `finalize` writer,
    `finalization-attention`, a handoff of another settlement or branch head, a continuation action, a publication
    lease or a recovery fence → `_SESSION_BUSY`, nothing written. With a session open in each state, `closing` and
    `contained` included, the same-task handoff acquisition and every other handoff-consuming route refuse, and a
    coordination update that changes the handoff beside the session refuses.
  - Linked answer after the branch head, an acceptance version or the handler digest changed → `_STALE`; status
    `stale`; readiness `interaction-stale` → same-task Builder reacquisition with the `withdrawn` receipt (D14).
  - `postpone`; expiry; `fail` → request unresolved; a Builder result citing it as satisfying → refused
    (`confirmation-unresolved` or `interaction-not-completed`); finalization refuses.
  - A result with a machine observation carrying a handler digest but no matching completed interaction, a
    different kind, label or result, or another commit → `interaction-evidence-unmatched`.
  - A `waived` record citing an interaction's confirmation (`passed` or `failed`) → N03
    `confirmation-not-applicable`; finalization refuses; frontier bytes unchanged.
  - Replay tamper (D14): an interaction changed locally without a receipt, a receipt chain with a frontier-digest
    gap or fork, a `resolved` receipt whose `confirmation_id` or digests differ from its request-resolution
    receipt's, two receipts reordered, a `completed` receipt beside a changed block, a `withdrawn` receipt beside an
    N03 request-resolution receipt for the same request, a withdrawal of a resolved request, or a receipt naming
    another handoff's `settlement_id` → the existing bootstrap failure; the Change is unavailable; nothing is
    rehashed.
  - Crash injection (N02-B harness) between the lease and the frontier participant of `open` → restart sees either
    no lease and no change or the whole open. Crash after the linked answer before `complete` → the session stays
    leased past `expires_at`; the next `open`, `recheck` or Cockpit start finds the holder dead, finds exclusion,
    and only then the interaction becomes `preparation-failed` / `session-lost` and the same Builder task is
    reacquired from the answered pause; the resolved request cannot support a result (`interaction-not-completed`); no
    completion or machine observation is fabricated.
  - Custody over injected process tables (D13): a live owned process → `_HANDLER_ALIVE`, lease kept; a process
    holding the leader pid with another create time and no token is never signalled and does not block release;
    a token-less member of the recorded group with no process at the leader pid → `contained` /
    `ambiguous-member`, never signalled; a failed scan → `contained` / `scan-failed`; a token holder that descends
    from the scanning process is found (the scanner does not filter descendants, D13).
  - Recovery route (finding 4 of round 2): after a transient scan failure → `contained`; the clock advances past
    `expires_at` and the 60-minute maximum → still `contained`, every acquisition `busy`, a new `open` →
    `_SESSION_BUSY`; `recheck` with the wrong session id or state → refused, nothing changes; `recheck` of an open
    session with a live holder → `_SESSION_BUSY`; `recheck` with a healthy table → released, interaction
    `postponed` / `session-lost`; then `open` succeeds. Run with the holder alive and with a dead holder.
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
- **Size / risk:** L / high. Four widened families, a new receipt family, a marker step, custody, settlement and
  loader replay changes and a new admissibility rule; the risks are a custody hole between session and writers,
  which the K-inventory test and the `busy` scenarios pin, and a handoff replay gap, which the D14 restart
  scenarios pin.

### 3.3 N06-B — Secure local input, handler launch and V22

- **Prerequisites:** N06-A.
- **Editable paths:**
  - new `serve/delivery/src/owlbear_delivery/interaction_inputs.py`, `interaction_protocol.py`
  - new `serve/cockpit/src/owlbear_cockpit/request_guard.py`, `interaction_sessions.py`, `interaction_launcher.py`,
    `routes/interactions.py` (no confirm route); `main.py` (`run()` installs the guard, the access logger with
    `access_log=False`, the session manager, its startup `recheck` of dead-holder sessions and its shutdown);
    `target_models.py` (bodies with `SecretStr` and `hide_input_in_errors`); `routes/target_work.py` (shared error
    mapping only)
  - `owlbear_delivery/__init__.py` and `module_surface.json` if exports change
  - tests: new `serve/cockpit/tests/test_request_guard.py`, `test_interaction_sessions.py`,
    `test_interaction_launcher.py`, `serve/cockpit/tests/support/synthetic_interaction_handler.py`,
    `synthetic_registry.py`, `process_fixtures.py` (unrelated groups, env-cleared descendants);
    new `serve/delivery/tests/test_interaction_inputs.py`, `test_interaction_protocol.py`;
    `tests/test_cockpit_launch.py` (guard installed by `run()`)
  - this plan's N06-B row; execution plan status row
- **Positive scenarios:**
  - Journey (b) end to end (§1.13): real Cockpit process (`run()` on a disposable portfolio, synthetic registry,
    isolated port) and `Client(assemble_target_server(...))` on the same workspace. `open` returns descriptors,
    `launch_summary` and a nonce and launches nothing; `start` with a valid `https` URL commits `spawn`, starts the
    launcher, commits `leader`, releases it, and the handler receives the value on stdin only and reports
    `awaiting-human`; continuation returns the `confirmation` handle; MCP `answer` with an `elicitation_callback`
    accepting `passed` (legacy and modern routes) resolves the request; Cockpit sees it, sends
    `human-step-complete`, the handler reports `finished` → `completed`; the D13 group kill and exclusion check
    pass; the lease is released; no token holder remains.
  - An inputless handler launches only at `start` with an empty input set; a `choice` input is accepted.
  - Same-origin requests with `Origin: http://127.0.0.1:<port>` pass; header-less local clients pass. G12: the
    maintained clients (the built SPA, `cockpit list`, `test_cockpit_launch.py`, the E2E stacks) run against the
    guarded app assembled by `run()`, not against an unguarded `TestClient`.
- **Negative scenarios (V22):**
  - URL admission through the real guarded `POST …/start`, each with the sentinel: `?client_secret=S`, `?e=S`, any
    query on the default policy, an undeclared or repeated key or a bad value under a test policy with
    `query_keys`; path segments `/%61ccess_token=S`, `/%2561ccess_token=S`, `/a;jsessionid=S`, `/a%3Bjsessionid=S`,
    `/token/x`, `/a%2Fb`, `/../x`, `/eyJ…`, a 32-character alphanumeric run; userinfo; an explicit port; any
    fragment (`#access_token=…`, a bare `#`, `#%61ccess_token=…`); a non-`https` scheme; a non-round-tripping
    parse; over 2048 characters; a host outside `suffix-allowlist` (also after IDNA normalization). Each → 422
    with its bounded code; no launcher started; lease unchanged.
  - Path structures, under a test policy declaring `/wiki/{space:[A-Z]{2,16}}/pages/{page:[0-9]{1,20}}` and
    `/docs/{id:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}}`: `/invite/<GUID>`, `/s/ab3-x9k`,
    `/join/k2f-9qz`, `/docs/<GUID>/share` and `/wiki/ENG/pages/12/x` → 422 `url-path-undeclared`, no launch;
    `/wiki/ENG/pages/123456` and `/docs/<GUID>` pass; the default policy refuses every non-root path. Registration
    refuses templates `/invite/{id:[0-9a-f-]{36}}` and `/s/{x:[a-z0-9-]{1,16}}` and a slot without a pattern or
    maximum length.
  - Sentinel absence, asserted on every captured byte: HTTP responses (success and error), Cockpit logs (`caplog`),
    the real `run()` process's stdout and stderr, MCP `get_change` and `show_work_item_view` JSON, frontier,
    coordination, snapshot and receipt bytes, the launcher's and handler's argv and environment (read with
    `psutil` in tests), and a forced spawn failure whose input carries the sentinel.
  - Access log through the real `run()` wiring: the sentinel in a query string on an accepted route (200), on a
    guard-rejected request (403), on an unknown route (404), on a 422, and in a malformed request line sent over a
    raw socket never appears in stdout or stderr; the access line shows the route template or `unmatched`.
  - Local HTTP cannot confirm: a header-less local client with the nonce from `open` calls every Cockpit route;
    none resolves the request; `POST …/confirm` → 404; Cockpit `answer_request` on the linked request → 409.
  - Expired session: `start` after `expires_at` → `_EXPIRED`; with a short test TTL the Cockpit timer cancels the
    handler, the D13 kill leaves no token holder, the exclusion check passes before release, status `postponed` /
    `session-expired`, request unresolved; an elicitation answered after that expiry writes nothing.
  - Cancelled sign-in: handler `failed{user-cancelled}` and user **Not now** → request unresolved; a Builder result
    citing it as satisfying is refused; cancel is not pass.
  - Guard: cross-origin `Origin`, `Sec-Fetch-Site: same-site` or `cross-site`, or a foreign `Host` → 403; nothing
    changes. Missing, wrong or closed-session nonce → 409; a second `start` in one session → refused.
  - Protocol: oversize line, unknown message, a message echoing the input, non-zero exit before `awaiting-human`,
    start or cleanup deadline exceeded → `preparation-failed` or `unavailable` by registry code; lease released.
  - Crash injection around launch (real processes, macOS and the Ubuntu CI workers; the test Cockpit wrapper
    SIGKILLs itself at an injected point): (1) right after the launcher starts, before `leader` is committed;
    (2) after `leader`, before `release`; (3) after `release`, before `start`; (4) during `awaiting-human`. Each:
    the lease survives `expires_at`; another Cockpit's `open` → `_SESSION_BUSY`; the restarted Cockpit finds the
    holder dead and recovers by token for (1) and by leader for (2)–(4); released with no token holder and the
    request unresolved. Variants of (1): a stub launcher that ignores control-pipe EOF is found by token and
    killed; with the process scan failing → `contained` / `scan-failed`, then **Check again** after the scan
    recovers → released, with no new session opened in between.
  - Live-Cockpit identity failure (real processes, macOS and Ubuntu; D13 unfiltered scan): the `leader` commit is
    made to fail while Cockpit stays alive, with a stub launcher that ignores control-pipe EOF and stays
    unreleased. The session's own Cockpit runs close: its scan finds its own child by token, kills it, and only
    then releases; the handler never ran. The same test with `worker_stall.psutil_user_processes` injected as the
    process source must fail its assertions (it hides the launcher and would release with it alive). A normal
    journey's release from the live holder likewise sees its own launcher until it exits.
  - Uncooperative handlers (real processes, macOS and Ubuntu): one ignores stdin EOF, one stalls after the
    confirmation without `finished`, one starts a grandchild in its group, one starts a grandchild that calls
    `setsid` but keeps its environment. Cockpit `SIGKILL` or expiry → lease kept while any is alive; after the
    D13 kills, released with no token holder.
  - Reused or foreign groups (real processes from `process_fixtures.py`; the session's recorded `leader` is set to
    the fixture's pid with another create time and token): (a) an unrelated `start_new_session` process with
    children, its leader alive → never signalled (fixture processes still alive afterwards), session released;
    (b) the unrelated leader exits and its children remain in the group → never signalled, session `contained` /
    `ambiguous-member` with their pids, no release by time; after the fixture ends them, **Check again** →
    released. (c) Our own launcher killed externally while the handler (token) lives → the handler is killed by
    token and the session released; (d) as (c) with a grandchild started under `env -i` → `contained` /
    `ambiguous-member`, never signalled, then **Check again** after the test ends it → released.
  - Recovery route over HTTP: `POST …/session/recheck` with the holder Cockpit alive and from a restarted Cockpit
    without the nonce: wrong session id or state → 409, nothing changes; a `contained` session after a transient
    scan failure → released; under a pause request → accepted and the pause converts after release.
- **Inner loop:** `uv run pytest serve/cockpit/tests/test_request_guard.py -q`, then
  `uv run pytest serve/cockpit/tests/test_interaction_sessions.py -q`.
- **Closeout:** `uv run test --changed`; scoped Ruff;
  `uv run pytest tests/test_cockpit_work_items.py tests/test_cockpit_launch.py tests/test_package_boundary.py -q`;
  `npm run test:e2e:work` (the guard runs in the real stack).
- **LC:** load form (startup gains the guard and session manager; no format change): the live copy loads and lists
  through a guarded Cockpit with unchanged hashes.
- **Size / risk:** M / high. The security boundary of the package: input admission, launch custody and signals.

### 3.4 N06-C — Presentation, MCP/HTTP projection and synthetic E2E

- **Prerequisites:** N06-B. Under U2 (a), N03-C's Cockpit boundary adapter (already merged before N06-A).
- **Editable paths:**
  - `serve/cockpit/web/src/api/workItems.ts` (interaction view, session calls), new
    `src/components/InteractionPanel.tsx` (**Help with this step**, launch summary, **Start check** with the input
    form from descriptors and no value echo, waiting text, confirmation question with chat guidance and a copyable
    `/continue-change` (U2 (b)) or **Observed** / **Not observed** (U2 (a)), **Not now**, **Explain existing
    evidence** filtered from N03-C's projection, **Check not available here** with the reason, and the contained
    view with its processes and **Check again**), `WorkItemDetail.tsx`, `workItemPresentation.ts`,
    `WorkPortfolioPage.tsx`; component tests
  - under U2 (a) only: `serve/cockpit/src/owlbear_cockpit/routes/interactions.py` `POST …/confirm` through N03-C's
    adapter, and its tests
  - `serve/cockpit/web/e2e/interaction.spec.ts`, new `e2e/support/start-interaction-stack.mjs`,
    `e2e/support/interaction-cockpit.py` (calls `owlbear_cockpit.main.run` with the synthetic registry) and
    `e2e/support/elicitation-client.py` (an MCP client on the same workspace that answers the elicitation), seed
    additions
  - `work_items.py`, `application_models.py`, MCP `target_models.py`: view fields not added in A, if any
  - `tests/test_cockpit_boundary.py`; `setup/operating-owlbear.md` (Help with this step, confirming in chat,
    privacy expiry, cancel, Check again); `share/skills/w-orchestration/SKILL.md` wording if the view changed
  - this plan's N06-C row and package closeout; execution plan status row
- **Positive scenarios (real Chromium, built bundle):** the card shows **Needs your decision** and **Help with this
  step**; the panel shows purpose, why human, what **Start check** launches and one instruction; nothing runs before
  **Start check**; a valid URL is accepted and the field is cleared; the confirmation question appears. Journey (b):
  the panel offers chat guidance and no confirm control; the elicitation client calls `answer` with the
  continuation handle and accepts **Observed** → completed. Journey (a), only under U2 (a): a click on
  **Observed** → completed, and journey (b) also still completes. The card returns to **Waiting for chat to
  resume**. **Explain existing evidence** lists the scoped criteria. A `none` interaction shows **Check not
  available here** with its reason and no Help control. A contained session shows its processes; **Check again**
  after they end returns the card to Help.
- **Negative scenarios:** a credential URL shows the bounded error and keeps the session; **Not now** returns the
  card to postponed with Help available; a short-TTL session expires with the privacy-expiry text; a page served
  from a second loopback port cannot open, start, post input, recheck or confirm (403); under U2 (b) `…/confirm`
  → 404; under U2 (a) `…/confirm` without N03-C's cookie or exact `Origin` → 403 and nothing is written; after a
  Cockpit restart the panel reports a lost session only after the exclusion check, or
  `interaction-handler-unverified`; the URL bar never contains an input or nonce; TypeScript and Python unions
  disagree → parity fails.
- **Host rehearsal:** on a disposable portfolio in a real VS Code window, a Builder blocks with an interaction-linked
  request through Copilot, the user starts the synthetic check in Cockpit, answers the elicitation form in chat
  through `/continue-change` (or clicks under U2 (a)), and `/continue-change` reacquires the same task and submits
  the result. Evidence on the PR (G5; N03 G10).
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

Cross-plan note, not applied here (N06-P does not edit the N03 plan): N03 §1.5
(`confirmation_id` and ledger `channel` rows) and §1.9 (N06 bullet) say N06 adds channel `interaction` and an
`interaction:` locator. Under D3 N06 adds neither; the N03 owner should amend that text (F6, G16).

Premises found false or incomplete on `ac3bf23f9` (F1–F5) and `e2fa3d913` with lane-c `86289635f` (F6, F7):

| ID | Premise | Evidence | Consequence |
| --- | --- | --- | --- |
| F1 | Execution plan §5 N06 assumes an origin-checked form host is available; Cockpit has no request guard | `main.py:57-62`; P2: body-less cross-port POST executed, rebinding `Host` accepted | D5 adds the guard for all of Cockpit in N06-B; until then, and on the frozen live controller until an authorized `/upgrade-delivery`, live Cockpit's body-less POST routes (for example `target_work.py:638-640`) are forgeable from other loopback pages |
| F2 | Programme §5.3 proposes extending `answer` with typed interaction outcomes | MCP `answer` accepts caller-set `provenance: user-confirmed` (`target_server.py:442-460`); HTTP defaults it (`target_models.py:381`); block routes keep worker resolutions (P10) | D4: no typed interaction outcome; a linked request is a scoped `confirm-check` request answered through N03's boundary, whose `passed` / `failed` decisions are the outcomes (§1.13) |
| F3 | Programme §9.3 step 1 has the agent launch the check session | The continuation controller has no terminal tool (`orchestrator.agent.md:8`) | D1, D7: Cockpit launches at **Start check** (programme §4.2 allows preparation without a running agent) |
| F4 | N03 §1.9 expects N06 to add `confirmation.kind = interaction` and an `interaction:` locator scheme | Not needed under D2 | D3; N03 G5 closes without an N03 schema change |
| F5 | §9.3 forbids values in access logs; the default uvicorn access log records query strings, and middleware cannot suppress it | `main.py:372`; P2; P10 | uvicorn access log off; a route-template access logger (§1.7); asserted through real `run()` in N06-B |
| F6 | N03 at `86289635f` (§1.5, §1.9) expects N06 to add ledger channel `interaction` and an `interaction:` locator | P12; the channel names a capture route, and the binding already lives in scope, question digest and `confirmation_id` | D3: no N06 change to N03 shapes; cross-plan note above; G16 |
| F7 | Round 1 of this plan assumed interaction writes reload like other portable writes | The loader refuses a pending publication beside a Builder handoff and rebuilds that frontier from the snapshot (`delivery_application_loader.py:603-607`, `:1010-1053`; P12) | D14: interaction transition receipts and an extension of N03's L row |
| F8 | Round 2 of this plan assumed a Builder interaction opens with no writer present | A request-bearing settlement keeps a passive `handoff` writer that only same-task acquisition consumes (P13) | D15: session beside its own handoff; acquisition refused while it is open |
| F9 | Round 2 of this plan reused `worker_stall.psutil_user_processes` for exclusion | It skips the caller's descendants, and the launcher is Cockpit's child (P13) | D13: an unfiltered same-user scan of its own |

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

Sol plan round 2 (`revision-required`, on `e2fa3d913`; round-1 fragment rejection and access-log replacement
accepted). Premises checked against source and N03 at `86289635f` (P11, P12).

| Finding | Disposition | Where |
| --- | --- | --- |
| 1 HIGH: N03 integration incompatible (removed `confirmation: {kind: request-resolution}` shape, linked `answer` refused, undefined "boundary tool", no executable entry under U2 (b)) | Accepted. A linked request is an N03 `confirm-check` scoped request answered through N03's `answer` (D13) with an interaction branch: the resolver asks only while the session is `awaiting-human` and renders interaction, session and head; `passed` / `failed` are shown as observed / not observed; one transaction writes the resolution, the ledger append (I10 preserved), the interaction `resolved` with its `confirmation_id`, N03's schema-2 receipt and the transition receipt, guarded by the session. `confirm_interaction`, the `answer` refusal and `interaction-request-not-waiver` (now N03 I6) are removed. Channel and locator stay N03's, so no nested version step (D3, F6). The (b) entry is the continuation `confirmation` handle passed to `answer` by `/continue-change`. Both journeys have assembled proofs; (a) ships only if U2 is (a) | §1.1, §1.4, §1.7, §1.8, §1.13, D3, D4, I3, I4, I10, §3.2–§3.4, F6 |
| Found while verifying finding 1: interaction writes during a retained Builder handoff do not survive a restart | Added. The loader refuses pending publication beside a handoff and rebuilds that frontier from the snapshot; every interaction write now carries a transition receipt replayed by an extension of N03's L row, with restart and tamper scenarios | R17, I10, §1.6, D14, F7, §3.2 |
| 2 HIGH: crash between spawn and identity persistence | Accepted as suggested. `spawn{token}` committed before any process; a release-gated launcher (token in argv and environment) runs the handler only after `leader` is committed; recovery by token when `leader` is missing; crash injection at four points including right after spawn, on macOS and Ubuntu | §1.6, §1.7, §1.8, D13, P11, §3.3 |
| 3 HIGH: group ownership after pgid reuse | Accepted. A Delivery-owned leader stays alive and pins its group; `killpg` only right after verifying it by pid, create time and token; otherwise only token holders are signalled, one by one; token-less group members without a live leader are ambiguous and contained, never signalled; reused-group tests with present and absent replacement leaders, plus our leader killed with and without an env-cleared descendant | I11, D13, §3.2, §3.3 |
| 4 MED: no recovery route for a contained session | Accepted. `recheck_interaction_session` (exact session-id and state fence, no nonce, not pause-gated, never time-based, opens nothing), Cockpit `POST …/session/recheck` and **Check again** (`CHECK_HANDLER_STOPPED`), `containment` in the view; proved after a transient scan failure with a live holder and after restart | §1.6, §1.7, §1.8, §3.2–§3.4 |
| 5 MED: URL rejection incomplete | Accepted. Descriptor `url_policy`: no query by default, declared keys and value patterns only; path segments unreserved after one decoding, credential words and token-like segments refused; negatives through the real guarded `start` | R9, §1.5, §1.10, §3.3 |

No finding was rebutted. One limit on finding 1: both U2 journeys have defined assembled proofs, but journey (a)
is built and proved only if the user chooses U2 (a), because an unchosen Cockpit confirmation channel would add the
authority U2 exists to decide. U2 is answered before N06-A starts (§1.13 Order).

Sol plan round 3 (`revision-required`, on `334a8c642`; the pre-spawn release gate and **Check again** accepted;
the conditional U2 journey and the phase and LC split accepted). Premises checked on the `origin/dev` merge
`edab21d5a` and lane-c `f4d09d774` (P13); the gate's line numbers are from before that merge.

| Finding | Disposition | Where |
| --- | --- | --- |
| 1 HIGH: session admission rejects its own Builder handoff (`kind="handoff"` writer retained by request-bearing settlement) | Accepted. `open` admits no writer, or exactly the passive handoff of the interaction's own settlement (`handoff_settlement_id`, `original_writer` with kind `handoff`, `branch_head` = `candidate_head`); the coordination model validates that relation and the update rule gains only that exception. The session never releases or replaces the handoff; same-task acquisition and every other handoff-consuming route refuse while a session exists in any state, and consume it as today after the D13 release. Every other writer or custody owner stays refused both ways. Tests through both block routes | R18, I6, §1.6, §1.7, D15, F8, §3.2 |
| 2 HIGH: D14 neither binds nor reconstructs binding changes | Accepted, by preserving the binding. `complete` no longer clears the block: N03's answer already resolves request and block through its request-resolution receipt. The one N06 binding change is a `withdrawn` receipt in the same-task acquisition transaction for an unconfirmed failed or stale interaction, admitted by the loader as a third baseline exclusive with N03's answer. Receipts name their handoff and carry frontier digests, so N06, answer and lifecycle receipts form one ordered chain. Restart cases before and after that reacquisition, around the answer and around `complete`, plus tamper cases. The counted-retry wording is removed; the 64-interaction bound ends a loop | R17, I10, §1.5, §1.6, §1.7, §1.8, D14, §3.2, G18 |
| 3 HIGH: scanner reuse omits Cockpit-owned descendants | Accepted. `interaction_custody` has its own unfiltered same-user scan; `worker_stall.psutil_user_processes` keeps its semantics. A live-Cockpit identity-commit failure with an unreleased launcher that ignores EOF must be found and killed, and fails if the worker scanner is injected | §1.7, §1.9, D13, F9, §3.2, §3.3 |
| 4 HIGH: confirmations must consume N03's consent generation in the answer transaction | Accepted; the apply already ran under N03's `expected_frontier_digest` CAS with a session participant, but it did not say it consumes the generation, and the session is not part of the digest. The plan now consumes "N03's consent generation" by reference (today the frontier digest; an explicit server-owned generation if PR #360 adopts one, as N05's `merge_consent`), names the N06 binding in it (`interaction_id`, `session_id`, `candidate_head`, plus the session participant), and adds no boundary. Negatives: declined and cancelled, superseded by frontier change or session reopen, concurrent and sequential replay | I3, §1.4, §1.7, §1.13, D16, §3.2 |
| 5 MED: path admission permits bearer URLs through global heuristics | Accepted. A `url` input's path must match a handler-declared template of literal segments and typed identifier slots; the default admits only the root; undeclared paths are refused with `url-path-undeclared`; registration refuses bearer-route literals and unbounded slots. The round-2 checks remain a second filter. Tests with GUID and short hyphenated bearer links against declared document identifiers | R9, §1.5, §1.10, §3.3 |

No finding was rebutted. Finding 4 was partly met already (the apply was in N03's CAS); the revision makes the
consumption explicit and adds the session binding and the negatives.

## 4. Progress

| Phase | PR | Exact head | Proof | Challenges | Status |
| --- | --- | --- | --- | --- | --- |
| N06-P | #359 | `334a8c642` | Probes P1–P13 | Sol plan round 1: revision-required (findings 1–5 accepted; confirmation delegated to N03's boundary, custody until exclusion, fragments, access log) → revised; Sol plan round 2: revision-required (findings 1–5 accepted; linked requests answered through N03's scoped `answer` with ledger append, release-gated launcher with token ownership, pinned leader and contained ambiguity, recheck route, URL admission policy; handoff replay receipts added) → revised; Sol plan round 3: revision-required (findings 1–5 accepted; session beside its own Builder handoff, binding preserved with a receipt-backed withdrawal, unfiltered custody scan, N03 consent generation consumed with the interaction binding, handler-declared URL paths) → revised | in review |
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
| G6 | Handler EOF, the release-gated launcher, process-group kill, `psutil` create time, token reads from cmdline and environment, the exclusion check, crash recovery and spawn redaction behave the same on Ubuntu | P5, P7 and P11 ran on macOS only | POSIX semantics; N08 G7 | N06-B tests on the Ubuntu CI workers | N06-B merge |
| G7 | Chromium's public-to-local network restrictions | P2 and P8 used a loopback attacker origin | The guard does not depend on them | — | Nothing |
| G8 | Launching candidate code from a pinned Cockpit release | N02-D and N07 are not designed against each other yet | D1, §1.10 item 5 | N07-P | N07-A |
| G9 | Edge profile custody and cross-Change contention | N07 scope | §1.10 item 3 | N07 | N07-A |
| G10 | Interaction-backed evidence after a requirement revision | Applicability is N04 | N03 survival rules | N04-B, N07-B | Nothing in N06 |
| G11 | LC exercises interaction records | Live state has none | Disposable fixtures in N06-A | N06-A fixtures; N10-M | Nothing (recorded per phase) |
| G12 | No legitimate client calls Cockpit with a cross-origin `Origin` or a non-loopback `Host` | Static search only at implementation | P8 header-less clients pass | N06-B: every maintained client against the guarded app assembled by `run()` (§3.3); the frozen live controller is unguarded until an authorized upgrade | N06-B merge |
| G13 | Python cannot erase a value from memory after use | Immutable `str`/`bytes`; freed heap, swap and core dumps | References dropped at handoff; process ends with the session | — | Nothing (documented limit, U1) |
| G14 | N03's boundary as N06 consumes it (D13 resolver taking tool arguments, ledger, schema-2 request-resolution receipt, L row) and the answer to N03 U2 | PR #360 (`f4d09d774`) is a plan, not code; it may replace the frontier-digest generation by an explicit one (D16); U2 is an open user decision | N03 §1.5, §1.7, D13; §1.13 covers every U2 answer | N03 / user; N06-A re-checks at start; a divergence stops for a plan revision | N06-A start (N03-C needs U2) |
| G15 | A handler descendant that leaves custody is detected | One that both calls `setsid` and clears its environment escapes; one started by a service manager escapes | D13 residual; registry handlers are repository code | N07-P for B1 (Edge profile custody) | Nothing in N06 |
| G16 | N03's plan text agrees with D3 | N03 §1.5 and §1.9 still say N06 adds channel `interaction` and an `interaction:` locator | F6; cross-plan note in §3.5 | N03 owner | Nothing (D3 rules for N06) |
| G17 | VS Code shows Delivery's elicitation to the user on the route it negotiates (journey (b)) | Host behavior | N03 G10 and its N03-B rehearsal | N03-B; N06-C host rehearsal repeats it for an interaction | N06-C merge |
| G18 | Same-task acquisition and the loader's acquired-claim derivation accept a block resolved by withdrawal with its request unresolved (D14) | Source-traced only; today both start from the settlement result or N03's successor | P13; D14 restart cases | N06-A (a divergence stops for a plan revision) | N06-A merge |
