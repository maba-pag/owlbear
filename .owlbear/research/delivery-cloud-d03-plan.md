# D03 — Recovery Package Plan

## Status and authority

**D03 is source-ready under the approved bounded contract; current dev is integrated and focused
integration verification passed. Ready-for-review/CI and human acceptance remain, not more D03-E implementation.**
The [integration request](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5869138354)
authorizes merging current dev, focused verification and then marking the PR ready for review.
Ready-for-review is not package acceptance, approval, merge into dev/main, D04 or live activation.
Bounded C's and D's recorded evidence and named external limits below are preserved.
This is the package record required by the [cloud execution guide](delivery-cloud-flight-handoff.md).
The programme's [user requirements](change-continuation-delivery-redesign.md#11-requirements-from-the-user)
record the same explicit scope revision. Shared governance is unchanged.

### Current handoff

The [cumulative acceptance review](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5868092173)
at **`b49a2a8f0017bcf2aa25274b2fec8962d72f02a5`** found **source-ready, pending named gates**,
with an empty source/bounded-proof blocker list. It supersedes the stop-era pending static,
coordination identity/disappearance and receipt call-form findings. The receipt factory's changed
reflection/static typing was acknowledged without a demonstrated required-consumer defect; do not
reopen speculative compatibility work. The approved `2e377a6` semantics remain unchanged.

[Coordinating evidence](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5867978559):
all **27 PR-changed Python files** passed Ruff **0.16.5** lint/format, and **14 named final-repair
cases passed in 11.80s** on Python **3.14.7**, with one existing Starlette/AnyIO warning. These are
the coordinator's exact-candidate executions, not this integration session's runs. They used a
disposable candidate checkout and existing locked environment with candidate imports verified.
Untraceable older **44/seven/five** totals are excluded from credited proof.

**Integration commit: `ee1cf7106e4e582ad78ee39ae63ffa07fd02b8e4`.** Its parents are the reviewed
`b49a2a8f0017bcf2aa25274b2fec8962d72f02a5` and freshly fetched live
`dev@29f095863aaf71541f5ac55a470573d04f6cdf6f`. The original fork was
`d7d5d2d358255e154d486448f4711b72d9b2b5b4`; it is not the current integration target.
The normal two-parent merge required no conflict resolution and produced tree
`b1a9163c44f8752bcc4f4e6ce0823c9d2b1db0e8`, matching the prior non-mutating prediction.
All `serve/` source/tests, root dependency manifests and lockfile are unchanged from the reviewed
candidate. Preserve its D03 replay/containment/frontend evidence rather than rerunning it.

The integration delta is limited to cache/dependency workflow proof and Ubuntu/actionlint config,
model references, setup reasoning settings, ecosystem expectations and related guidance.
This session directly ran **18 selected tests: 18 passed in 7.56s**, using Python **3.14.7**,
uv **0.12.15**, pytest **9.1.1** and selected locked packages in an external disposable environment.
Delivery, Delivery MCP and Tools imports were asserted to resolve inside this checkout.
The environment also includes the browser/knowledge/memory MCP packages required by the existing
registered-role test; no live server or provider was invoked.

The exact selection below used `uv run --locked --no-sync python -m pytest -q --tb=short -n 0
-p no:cacheprovider -m 'not api and not model and not e2e'` with disposable basetemp.
Each item is a separate node appended to the named file, not a whole-module run:

- `tests/test_agent_ecosystem_validation.py`:
  `test_recovery_workflows_require_host_exclusion_not_caller_confirmation`,
  `test_prompt_validator_accepts_current_prompt_roots`,
  `test_repair_delivery_prompt_is_an_ordinary_read_only_entry`,
  `test_orchestration_transition_envelope_matches_registered_field`,
  `test_declared_mcp_tools_exist_in_live_registries`,
  `test_retired_delivery_operations_are_absent_from_active_customization_prose`.
- `tests/test_setup_init_settings.py`:
  `test_copilot_profile_creation_and_reasoning_settings`,
  `test_copilot_profile_preserves_unrelated_entries`,
  `test_copilot_profile_decline_preserves_file`,
  `test_copilot_profile_malformed_json_is_left_unchanged`,
  `test_copilot_profile_skips_noninteractive_and_non_macos`.
- `tests/test_dependency_verification_workflow.py`:
  `test_dependency_workflow_runs_without_dependency_label_gate`,
  `test_pull_request_proof_workflows_skip_draft_jobs_and_run_when_ready`,
  `test_dependency_verification_is_read_only_and_has_no_renovate_runner`,
  `test_dependency_proofs_install_committed_state_and_run_behavior_checks`,
  `test_gate_requires_only_current_read_only_proofs`,
  `test_cache_probes_are_opt_in_and_isolated_from_required_proofs`,
  `test_dependency_workflow_actions_are_pinned`.

Ruff **0.16.5** `check` and `format --check` passed for `setup/init.py` and those three test files.
Pinned **actionlint 1.7.12** passed with
`actionlint -config-file .github/actionlint.yml .github/workflows/dependency-verification.yml`;
ShellCheck was available, Pyflakes was not, so no embedded-Python Pyflakes pass is claimed.
No behavioral fixes or conflict resolution were needed; no new cumulative A–E rereview was required.
No competing writer was active, no source redesign or authority backend was added, and no live
services, production state, provider effects or protections were changed.

| Gate | Current disposition |
| --- | --- |
| Bounded A–E source and closeout proof | Source-ready review and named exact-`b49a2a8` evidence retained for unchanged behavior |
| Target integration | Conflict-free two-parent merge published at `ee1cf71`; 18 focused tests, four-file Ruff lint/format and pinned actionlint passed |
| Ready-for-review | Complete: PR #326 is ready for review at integrated head `aba7684`. |
| Required CI | All four workflows passed at PR head `653a102`: [Source](https://github.com/maba-pag/owlbear/actions/runs/36440136593), [Dependency](https://github.com/maba-pag/owlbear/actions/runs/36440136312), [Cockpit](https://github.com/maba-pag/owlbear/actions/runs/36440136399), and [Agent ecosystem](https://github.com/maba-pag/owlbear/actions/runs/36440136595). The local repair candidate is based on that head and still needs exact-head CI after publication. |
| Focused repair proof | The 91-case HTTP module passed under Python 3.12.14 xdist with deterministic retry clocks. Four residual backend/tooling cases pass on Python 3.12.14 and 3.14.7, including Python 3.12 xdist. The full 116-case WorkPortfolio test file passes locally on Node 24.21 after its test fix; scoped Biome passes. |
| Follow-up review | The [whole-package review](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5873016029) identified five bounded repairs on `653a102`. Local Opus challenges found and drove fixes for stale-result replay under successor custody, post-start retry accounting proof, and completion-ledger accuracy. The fourth challenge found no source defect and identified missing selected-Change proof at the entry limit; the regression is now covered. The fifth challenge confirmed the diagnostic boundary and found a stale historical test description, corrected below. Candidate CI and PR re-review remain pending publication. The earlier [Opus 5.5 review](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5871033530) found no concern with the retry-clock fix or preserved custody assertions. |
| Human/host acceptance | Existing ordinary dispatch/transport and platform limits remain; no broader optional-host recovery requirement |

The `f802aed` HTTP failure was a retry-window timing dependency: the retained writer returns
`busy/active-custody` during backoff; after it expires, finalization-failed readiness returns
`unavailable/finalization-failed`. `dbf5ad3` freezes retry time in both HTTP refusal fixtures, without
changing production behavior. The same bounded clock is now used in the registered MCP finalizer
fixture. The quality orchestration test now stubs Docker-runtime discovery as its sibling does.
The full-suite timeout cases are the 256-record capacity proof and the repeated MCP registration
for `observe-acceptance`; each now has a 60-second per-test bound, with the global timeout and test
assertions unchanged. The four residual failure cases pass together on Python 3.12.14 and 3.14.7;
the same four pass under Python 3.12.14 xdist. All nine changed Python files pass Ruff lint/format.
At `717aa83`, one inspector-restoration test raced portfolio polling: it awaited the detail but
mutated the portfolio fixture before initial list load completed, then checked the restored table
before the next poll. It now awaits the table before changing the fixture and awaits table
restoration after the fixture is reset. A second test renders 16 readiness reasons; D03 added eight cases but
the test retained Vitest's 20-second default. Its per-test timeout is now 60 seconds; the global
timeout and assertions are unchanged. Commit `958345e` contains only these Cockpit test and handoff
changes. The complete 116-test file passes locally on Node 24.21 and scoped Biome passes; fresh
exact-head CI is pending. Earlier code failures at `aba7684` remain repaired in `f802aed`; do not
reopen them or approve obsolete runs. This is acceptance closeout, not another D03-E cycle.
Earlier stop-era details remain in the
[immutable pre-integration record](https://github.com/maba-pag/owlbear/blob/b49a2a8f0017bcf2aa25274b2fec8962d72f02a5/.owlbear/research/delivery-cloud-d03-plan.md#current-handoff).

### Historical E evidence

The following cumulative continuation evidence is historical. It started at
`ef011e797e8c273ff52bd37e4ab3990cc1db646b`, following the
[bounded proof request](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5861710203).
The approved `bf4bc48` replay proof and reviewed `e0e384b`/`ef011e7` HTTP, offline and frontend
continuation remain prior evidence. The `3568c41` prompt-assertion correction is preserved.
The owning engine execution, publication, transaction and retry implementations have not changed
since that replay proof; subsequent production edits concern readiness prompts. The existing
frontend proof is retained without another installation or build. `2e377a6` remains controlling:
an unavailable host does not become a completion prerequisite or permission to release custody.

Evidence reconciliation identified dedicated fresh-application public recovery-receipt replay,
forged recovery-field rejection, and absent-host still-writing descendant containment across
restart as focused proof additions. A cumulative source review also identified a degraded-entry
defect: coordination or snapshot records could mark a selected Change as seen even when its runtime
frontier was missing, allowing a false healthy structural result. The diagnostic now counts runtime
records only, preserving unknown inventory versus verified absence. Direct-CLI no-write regressions
cover missing and unsafe runtime ancestry. Independent read-only review closed this finding and the
initial/repeated V10 reload-snapshot and setup-cleanup findings.

The cumulative reviewer also identified a missing safe diagnostic prompt for readable
`coordination-unavailable` readiness and non-discriminating MCP forged-input coverage. Both are
repaired and independently reviewed: real restart reads assert the diagnostic prompt on Change and
WorkItem readiness; forged requests use otherwise-successful replay and assert exact strict-input
rejection without host verification. Completed
recovery replay snapshots now include raw index, refs, retry ledger, coordination bytes and journal
directory membership before and immediately after reload and after successful registered replay.
The final focused review closed the post-replay snapshot gap. These are bounded fixture invariants,
not claims of general host exclusion or automatic dirty-workspace recovery.

Source checkpoint: `8fcfcb6`. The final follow-up only strengthens the shared replay test closure
and the existing process test's exact `busy`/`active-custody` assertion. No recovery owner, provider
composition, strict schema, dependency or frontend source changed in this continuation. One writer
implemented source/tests; the coordinating session owns this record and publication.

Fresh parent-executed checks on the unchanged starting source passed: the three HTTP/MCP
finalizer-before-checks/restart nodes (**3 passed, 8.39s**), explicit role/import/diagnostic bootstrap,
authority and TypeScript-parity nodes (**10 passed, 3.13s**), and strict recovery/repair adapter
mapping/validation plus operation annotations (**19 passed, 2.06s**). The initial finalizer
`busy`/`unavailable` assertion did not reproduce in the three-case selection; its original cause
remains unknown. No classification as a pre-existing defect is inferred.

These commands used uv **0.12.19**, Python **3.14.7**, pytest **9.1.1**, and checkout-resolved
Delivery, MCP and Cockpit imports. `uv sync --locked --python 3.14.7 --package owlbear-cockpit
--package owlbear-delivery-mcp --package owlbear-tools --group dev` created an isolated selected-package
environment outside the checkout. Execution used `uv run --locked --no-sync --python 3.14.7
python -m pytest`, explicit nodes, one worker and no cache provider; no dependency overlays or
lockfile changes. A console-script collection attempt could not resolve the repository's `serve`
test-helper namespace; `python -m pytest` from the repository root resolved it before behavioral
execution. Scoped Ruff **0.16.5** lint and format checks passed on the seven production boundaries:
portfolio application, work-item model, MCP models/server, HTTP models/routes and offline diagnostics.
These checks do not retroactively change C's historical toolchain evidence.

**Writer-reported proof on the new candidate:** the explicit selected recovery/MCP/HTTP/diagnostic/
readiness suite passed **50 tests in 14.91s** before the final shared-closure refinement. It includes
completed receipt replay, caller-authored extra fields, stale identity, absent-host live-descendant
containment, process-exclusion positive controls, selected-runtime CLI accounting and restart prompts.
Earlier 25/12/15/5/6/3/49-case selections overlap and are not additive or final-source proof.
After the final shared-closure and exact-reason assertions, the six explicitly selected MCP/HTTP
completed-replay and core/MCP/HTTP process-containment functions passed **8 cases in 10.59s**:
MCP claim/proposal replay (two), HTTP claim replay (one), the existing process-exclusion control
(two orphan-child variants), and three absent-host V10 cases. The first attempt at the added reason
assertion failed twice because it expected `operation-in-progress`; the observed, contract-consistent
`active-custody` is now asserted without weakening the existing `busy` requirement. One existing
Starlette/AnyIO deprecation warning remains. This final selection supersedes its affected cases in
the 50-case run, not the unchanged strict-input/diagnostic/prompt cases.
The remaining exact HTTP unknown-Change/CLI node initially passed **1 test in 2.71s** with a
degraded inventory (`CONFIG_MISSING`, `UNSAFE_ENTRY_NAME`, `PENDING_EFFECTS_UNKNOWN`), so it could
not assert verified `CHANGE_NOT_FOUND`. The `.storage.lock` scanner fix removed that false unknown;
the current fixture now asserts `CONFIG_MISSING`, no `CHANGE_NOT_FOUND`, `pending_effects: false`,
incomplete inspection and unchanged project bytes. Verified absence remains covered by the separate
complete-root direct-CLI regression. A selected-change entry-limit regression also proves that an
incomplete runtime listing suppresses `CHANGE_NOT_FOUND` and reports unknown pending effects.
The prior continuation reported production Ruff and whitespace passes on its selected boundaries.
It also reported four lint findings in `test_recovery.py` and formatting failures in four of its
seven selected Python files. Comparing those files with `ef011e7` established only that the findings
predated that continuation. **The former classification as baseline debt was incorrect:** that
revision is on this PR, and the actual-base comparison above establishes PR ownership. The prior
selected checks are not a cumulative static pass.
The parent did not rerun delegated checks; unlike the parent checks
above, these are writer reports, not independently captured stdout.

| Bounded capability | Current evidence | Remaining obligation |
| --- | --- | --- |
| Exact result replay and four interrupted engine rows | Approved `bf4bc48`; prior exact selected 12-case run and independent review. Cumulative source comparison retains the unchanged engine/publication/retry owner proof; later readiness overlays have their own affected selections | Prior evidence, not a new 12-case pass; required external regressions remain |
| Malformed operation journal and unavailable provider readback | Retained registered MCP/HTTP canonical-loader cases cover malformed/foreign intent/result and unknown readback across restart, without repeated effects or recreated result contents. Fresh strict recovery selections cover stale claim/proposal identities and forged preservation paths, commands, budgets, receipts and stop assertions | Prior engine-action journal/readback evidence was not rerun; required external regressions remain |
| Finalizer failure before checks | Registered MCP case plus HTTP acquire/execute, core report, and restart/refusal proof. The report journal is nonempty; protected state is compared immediately around reload and API refusal. The three exact nodes passed freshly on the starting source | The initial `busy`/`unavailable` failure did not reproduce; its cause is not established. This checks `WORKSPACE_DIRTY` preflight with `checks_state=not-run`, not every failure category or live host dispatch |
| Failed claim activation with/without writer | Retained MCP/HTTP variants compare claim/attempt, frontier, retry ledger, coordination, workspace/index/status and repository refs across restart and repeated read/refusal; sibling acquisition is separately verified | Named durable-field snapshots are not universal no-loss proof; required external regressions remain |
| V10 absent-host containment | New core, registered MCP and HTTP cases retain a real still-writing descendant through two application reloads. Exact refusal, no replacement/release, full protected snapshots and subsequent signalled writes are asserted; setup and test cleanup close the synthetic worker | No actual laptop/VS Code exclusion claim; enabling broader recovery still requires independent host authority |
| Degraded/offline entry | Retained malformed-coordination HTTP/CLI same-root proof and new unknown-Change coverage; direct CLI missing/unsafe runtime-ancestry cases prove incomplete diagnosis, truthful pending-effect accounting and no project-tree writes | D's installed POSIX/no-write evidence remains historical. Other failure classes are not all composed through both adapters; D07 migration and D08 ordinary host acceptance remain |
| Readiness prompts and rendering | New `coordination-unavailable` diagnostic prompt is checked through real restart Change/WorkItem reads and the applicability table. Retained pending/interrupted, continuation and state-specific prompt proof; unchanged frontend has prior 116-test, Biome and build proof, including inert text and absent/null prompts | Browser/E2E proof not claimed; broader frontend suite not run |
| Recovery contract and cumulative package | Historical registered replay/strict-input/V10 and parent role/import/authority/parity proof supplement retained A–D evidence. Exact-`b49a2a8` closeout proof and cumulative review supersede the pending static/diagnostic findings | Source-ready, not package approval; current integration, CI and human/host gates are listed in the current handoff |

**Historical evidence:** the [post-stop record at `3568c41`](https://github.com/maba-pag/owlbear/blob/3568c4111fd40c6fd7a9151a16dfe3ece11e6b0c/.owlbear/research/delivery-cloud-d03-plan.md#current-handoff)
reports the earlier 29-case selection and six-case corrected retained-journal selection. Those are
prior worker evidence, not new passes or proof of this continuation.

**Prior `ef011e7` continuation validation:** the writer reports an initial explicit HTTP/readiness selection across
`tests/test_cockpit_work_items.py` and `serve/delivery/tests/test_portfolio_application.py` passing
**33 tests in 21.65s**, and the registered MCP malformed-journal/readback selection passing
**4 tests in 9.29s**. These precede the later restart/offline/inventory refinements. The HTTP run emitted
one existing Starlette/AnyIO `BlockingPortal` deprecation warning; the MCP run had no warning.
Scoped Ruff and whitespace checks were reported passing. The writer's format check reported
two differences at lines 1245 and 1482 of that test module unchanged from its session baseline.
That does not establish base-branch debt; the actual PR-base comparison above governs ownership.
The writer also reported an initial finalizer `busy`/`unavailable` assertion failure whose cause was
not established; isolated and final reruns passed. It is not classified as a proven pre-existing defect.

After adding fresh-restart provider-readback containment and pre-read finalizer restart comparison,
the exact two-case HTTP selection passed **2 tests in 3.85s** (one existing Starlette/AnyIO
`BlockingPortal` deprecation warning). The real degraded HTTP+CLI selection then passed **1 test in
2.19s** (same existing warning); the CLI used `sys.executable -B` with the source-tree diagnostics
script and actual argparse flags. The full-repository tree snapshot, diagnostic redaction and
`writes_performed=false` assertions passed. `ruff check` and `git diff --check` passed. The captured
Python commands/stdout/import provenance were inspected by the coordinating session, which did not
rerun the writer's tests. They show uv **0.12.15**, Python **3.14.7**, checkout-resolved Cockpit,
Delivery and test-helper imports, and editable `file://` distribution origins. Commands used
`uv run --project serve/cockpit --locked --python 3.14.7` with explicit test-tool overlays
(`pytest==9.1.1`, `pytest-xdist==3.8.0`, `pytest-timeout==2.4.0`, `pytest-asyncio==1.4.0`,
`httpx2==2.13.0`). This is selected-project locked execution with overlays, not a fully locked
whole-workspace test environment.

After the post-checkpoint invalid-result directory review finding, the exact HTTP and registered MCP
`invalid-result` parameters passed **2 tests in 5.17s** (one existing Starlette/AnyIO
`BlockingPortal` deprecation warning). Scoped Ruff on both changed test modules and `git diff --check`
passed. No frontend rerun was needed for this Python-test-only repair.
An initial collection failure lacked the local MCP package; adding the checkout's
`--with ./serve/delivery-mcp` resolved it. These selected counts overlap and are not additive.

**Prior frontend validation, retained for unchanged inputs:** Node **24.21.0** / npm **10.9.8**;
locked `npm ci` installed 314 packages
and reported zero vulnerabilities. `npm --prefix serve/cockpit/web test --
src/__tests__/WorkPortfolio.test.tsx` passed **116 tests in 102.99s**. Scoped Biome check passed and
`npm --prefix serve/cockpit/web run build` passed TypeScript and Vite (463 modules). No manifest or
lockfile changed. The coordinating session inspected the captured test/build output without rerunning
it. Local transcripts are session artifacts, not prerequisites for a future checkout.

Prior automated Code Review could not load its configured model; its success wrapper is not a pass.
Prior CodeQL skipped the `ef011e7` test/documentation-only continuation, not production changes.
Final validation after publishing `8fcfcb6` again could not initialize automated Code Review, and
CodeQL timed out. Neither is a passing final-source result; the tool explicitly disallowed retry.
An earlier reviewer-reported zero-alert scan predates final publication and does not close this gap.
Required dependency/source/Cockpit/ecosystem CI inspected at the starting `ef011e7` is `action_required`,
not current-head passing proof.
Historical C exact-pin limits and D's POSIX/host limits remain unchanged. Package acceptance, merge,
D04 and live activation are not claimed.

**Next outcome:** finish the closeout's exact-candidate review and any supported repairs before
restoring source readiness, then obtain package acceptance review and the named external gates.
The earlier statement that no source repair remained is superseded by this closeout's static and
diagnostic findings. Keep ordinary host transport separate from cloud source proof, reuse valid
prior evidence, and do not substitute an executor/backend redesign or treat containment as recovery
success. No package approval, merge or live activation is implied.

### D repaired baseline

The [D repair request](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5850248740)
addresses the [acceptance findings](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5850210697)
against `5feb888`: installed startup must prevent bytecode before package imports; unavailable or
skipped inspection must not imply absence/completeness; schema-less local host overrides must match
the owner's structural default; initial descriptor-stat failure must remain bounded. The ordinary
session prompt also requires a supported command-execution route. This remains D-only work below
Delivery runtime construction, without transaction replay or recovery authority. The approved
[D contract](#d-offline-diagnosis) and [phase scope](#d03-d--read-only-offline-entry) remain unchanged.

Repair checkpoint `2d4eecd` fixes structural accounting and introduces an installed launcher;
final source and committed regression proof are at `15351d8`.
The subsequent whole-project installed-console regression exposed a remaining startup write:
Python site initialization could compile the virtual-environment hook before a Python launcher
disabled bytecode. The final POSIX shared-script launcher starts the installed environment's sibling
Python with `-I -B` before initialization. It does not depend on the prompt's environment guard.
The direct `python -B` source fallback remains supported. No Delivery lifecycle owner changed.

Unavailable or replaced transaction ancestry now reports unknown pending effects. Rejected records
are incomplete; verified missing Delivery/transaction trees remain distinct from unreadable trees.
Only local host overrides receive the owner's default schema 1, including valid nullable overrides;
explicit unsupported versions and malformed fields remain rejected. Initial descriptor-stat errors
retain bounded diagnostics, consistent byte accounting and descriptor cleanup.

The ordinary-session prompt uses the built-in `agent` with only `execute/runInTerminal`, rather than
Ask routing without a terminal tool. It retains fixed-command/no-repair limits and reports unavailable
when the terminal is missing. This is a supported prompt-file routing configuration, not command
enforcement or proof of live host dispatch. No Agent Host migration or new agent was introduced.

**Fresh repair evidence:** delegated checks used Python **3.14.7**, pytest **9.1.1**, uv **0.12.19**
and one pytest worker without its cache. The isolated environment used the repository's direct test
tool pins and Hatchling **1.32.4**; it was not a complete workspace `--locked` environment.

| Check | Observed result |
| --- | --- |
| Diagnostic module after startup repair | **52 passed**, including actual offline wheel build/install, initially cache-free project-local environment, whole-tree membership/content comparison, direct CLI rejection/override cases, real root/ancestor replacement and initial-fstat failure |
| Final portability-adjusted launcher and companions | **7 passed**: actual installed console, stdlib bootstrap, two exact prompt nodes and all three exact authority nodes |
| Scoped static checks | Ruff check and format check passed on diagnostic source/tests and prompt tests; POSIX launcher shell syntax passed |
| Packaging | Writer verified wheel and sdist launcher inclusion; final installed-command regression rebuilt and installed the actual wheel without dependencies and without bytecode environment flags |

The seven-case selection overlaps the diagnostic module. Intermediate 35-case runs and earlier
3.12.3/3.14.6 smoke checks are not additional final proof. Parent-authored regressions were executed
by separate test workers; the coordinating session did not rerun delegated tests. Read-only source
review found no high-confidence defect before the final launcher change; follow-up identified a
portability issue, corrected and covered by the final installed invocation. Final read-only re-review
found no significant issues. CodeQL on `15351d8` reported **zero Python alerts**; automated Code Review
could not load its configured model, so its success wrapper is not a review pass. Secret and
whitespace checks passed. The reduced test environment
reported eight configuration/marker warnings for absent optional pytest plugins in the final
seven-case run; no async or timeout-plugin behavior is claimed by these synchronous checks.

The original candidate's 33/2/3 counts are prior evidence only, preserved at
[`5feb888`](https://github.com/maba-pag/owlbear/blob/5feb888/.owlbear/research/delivery-cloud-d03-plan.md).
This D-only proof does not resolve C's unrun exact-pin checks, required external CI, E's cumulative
transport proof, package acceptance or live activation. Current source/Cockpit/dependency CI inspected
at `5feb888` remains `action_required`. Windows launcher behavior and live prompt dispatch were not
tested; the exercised installed environment is POSIX.

### Bounded C baseline

The user selected **"Bounded recovery now; explicit containment otherwise"**, after the
[capability experiment](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5840061085)
showed descendant escape and indistinguishable stable foreign writes. This supersedes the prior
A/B execution-allocation decision and full automatic dirty-recovery completion requirement.
It does not approve A, B, a weaker provenance provider, or a new runtime/security platform.

**Verified repair `7b93a91`, following `bdb6669` / `2caa5d7` and handoff `755ad93`;
scope approval remains `2e377a6`.**
The [acceptance review](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5840869700)
identified a read-side containment diagnosis defect: an unfinished engine action disables execution,
but public cards can still recommend mark-ready or merge. The
[authorized repair](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5843311091)
now validates captured intent/start/result bytes through bounded, no-follow operation-directory
reads without executing or reconciling them. It distinguishes unstarted, unknown-result,
recorded-failure and unverifiable-journal states and replaces misleading publication guidance.
Present start markers must match even alongside a recorded result. Static diagnostic text names
the engine/publication/checkpoint owner without exposing arbitrary journal failure text. Three
readiness reasons have matching Cockpit types, labels and rendered-reason coverage. Retained
operations also replace stale publication headlines and compatibility `next_action` guidance.
The final verification reproduced a remaining public `list_work_items` leak: that method still
constructed a projector without readiness, despite private-projector tests passing. It now uses
the existing read-only projector, as public show and Cockpit grouped views already do. The loader
matrix calls and repeats the actual public list/show methods inside its state-invariance boundary.
The named repeated-acquisition test now checks the full redispatch/claim-release prohibition
case-insensitively; its no-second-launch and unchanged-frontier assertions remain intact.

The default-loader regression
exercises the existing engine and publication owners, rather than replacing them: a lost provider
response is resolved by exact readback, and a fresh application returns the durable engine result
without another provider mutation. An unresolved provider result retains its original operation;
repeated execution does not replenish its retry budget, and a separate eligible Change can acquire
work. Public containment messages identify missing owner evidence instead of promising a future
"D03 repair" or treating caller confirmation as authority.

Fresh independent review of `7b93a913660da21cf7e72ef7808d664fd4498a17` found no high-confidence
source defects in the accepted diagnosis finding or connected replay/containment boundaries.
The bounded candidate is ready for acceptance subject to the external gates below. The loader,
execution, transaction and exclusion mechanisms are not replaced by this candidate. No executor
decision, producer framework or host backend is needed for the approved bounded scope.

| Capability | Candidate behavior |
| --- | --- |
| Exact completed engine result | Replay through a newly default-composed application; no duplicate provider mutation |
| Acquired but unstarted engine action | Report pending, not lost/failed; retain the exact operation and non-executable read controls |
| Started operation without its result, even with a ready receipt | Contain without invoking the owner again; retain operation custody and consumed budget |
| Provider mutation with unavailable readback | Contain the recorded failure; repeated calls neither mutate again nor consume another attempt |
| Missing, malformed, mismatched or unreadable operation journals | Report unverifiable evidence; no mark-ready/merge instruction, effect execution or reconstruction |
| Dirty, staged or private worktree before effect entry | Reject stale preflight without entering the effect or changing content/index; no recovery success is claimed |
| Unrelated eligible Change | Continue through selected application acquisition without releasing the contained Change |
| Worker closure or dirty-content authority unavailable | Keep existing fail-closed boundaries; diagnosis is not release, preservation or permission |

### Candidate proof and limits

**Fresh writer-observed verification, 2026-09-26:** uv **0.11.0**, locked dependencies and
supported Python **3.14.3**; Delivery and GitHub-adapter imports verified in this checkout.
Python **3.14.7** was unavailable in the installed uv download catalogue. Frontend checks used
pinned Node **24.21.0**, `npm ci` with the unchanged lock, and Vitest **5.0.1**.

| Focused check | Result and scope |
| --- | --- |
| Named repeated acquisition | Reproduced the capitalization assertion failure alone; strengthened full-prohibition assertion passed without changing acquisition behavior |
| Existing diagnosis/loader selection | 17 passed: six journal states, recorded failure, awaiting-merge pending observation, three start/result consistency cases, two loader replay/readback cases, three preflight dirt variants and TypeScript reason parity |
| Public application list/show regression after repair | 9 passed: named acquisition plus six journal states and the recorded-failure/awaiting-merge cases; public list/show now agree with get-change guidance and repeated reads preserve recorded state |
| Connected consumers after repair | 6 passed: no integration-target resolution from reads, grouped list, empty default loader, both replay/readback cases and selected pending-publication isolation |
| Cockpit presentation | Four selected tests passed across two invocations: readiness reason labels, coherent readiness/control mapping, read-only unavailable inspection and retained-operation provenance without caller-confirmed recovery |
| Static checks | Scoped Ruff lint and application/work-item source format passed; Biome passed on the three read-side frontend files; whitespace checks passed |

Selections overlap and are **not additive**. The 17-case run precedes the one-line public-list
repair; the 9/6 selections verify its affected paths afterward. No whole portfolio module or
workspace suite was run. Real loader/owners are used after synthetic setup; only the external
provider is substituted and publication targets a disposable bare remote. No live host pass is claimed.

The old two-hunk test-format baseline claim was not supported by direct comparison with
`dev@d7d5d2d`. All five remaining test-format hunks, including three in the read-side tests, were
formatted without changing their AST; the test module and both source modules now pass format
checks. No lint suppression, assertion removal or execution/custody relaxation was added.

Independent read-only source review of `7b93a91` confirmed the public list/show paths, preserved
ordering/filtering and lack of reconciliation or release. The reviewer did not rerun writer tests.
CodeQL at `7b93a91` reported **zero Python alerts**. Automated Code Review could not load its
configured model; its success wrapper is not a review pass. Subsequent test formatting is
AST-equivalent, not a new execution implementation.

**Named external gates:** exact Python **3.14.7** compatibility remains unrun; required source,
Cockpit and ecosystem CI inspected at `755ad93` was `action_required`. Supported Python evidence
does not claim exact-pin proof. No final JavaScript CodeQL pass is claimed here; this repair changes
no frontend source. Package acceptance remains a separate decision. D/E registered/HTTP cumulative
proof and applicable host transport acceptance retain their allocation, not optional backend demands.

**Prior evidence only:** `755ad93` records overlapping eight/two loader-projection, 24 work-item and
112 frontend case reports on below-floor Python 3.12.3/Node 22.23.2; those do not establish supported
runtime compatibility. Earlier bounded-candidate 12/five/ten/two selections under Python 3.14.3
are not fresh passes or cumulative totals. See the immutable
[previous handoff](https://github.com/maba-pag/owlbear/blob/755ad93277dee734689a4f7c71b89a0e4f8b638b/.owlbear/research/delivery-cloud-d03-plan.md#candidate-proof-and-limits)
for their exact limits. The named capitalization failure is now resolved, not dismissed as baseline.

### Completion ledger

| Outcome | Required behavior and evidence |
| --- | --- |
| Supported recovery | Exact engine-owned durable result or matching publication receipt is replayed/reconciled once under existing custody. A lost response followed by restart returns the same result and resumes only the selected Change; it does not re-invoke an already completed effect |
| Unknown execution | Started without authoritative result, absent exclusion or conflicting receipt remains contained. No cleanup, copying, custody release, blind retry or replacement worker; bytes/index/head and failure budget remain unchanged. A typed stale result after effect entry is durably recorded and releases that action's custody while its retry reservation remains pending. A stale preflight before the start marker records a failed attempt with backoff, without refund/reset, so a retry can proceed after drift is corrected |
| Unattributed mutation | Stable foreign, ignored/private or staged edits cannot become automatic preservation or Builder authority through snapshots, scope, caller assertions or a successful exit code. Keep the original material in place |
| Actionable diagnosis | Public reads distinguish an unstarted retained action, started-without-result, exact recorded failure and unverifiable journals against the original action. Containment replaces mark-ready/merge guidance and names missing evidence, responsible owner and resume condition; repeated reads do not execute, reconcile or mutate authority. No nonexistent repair promise, command assembly, fake approval, inferred termination or unsupported clickable action |
| Continued progress | Unrelated eligible Changes still run; same-Change unknown custody remains occupied. Repeated requests do not mint new equivalent attempts or reset budgets |
| Package integration | D retains offline diagnosis; E retains strict registered/HTTP forwarding and cumulative proof for this revised boundary. Unsupported host recovery is explicitly contained, not a hidden package prerequisite |

### Next assignment and verified baseline

Source anchors: `PortfolioApplication.execute_change_action`, `_read_engine_result`,
`_replay_pending_state_publication`, `_reconcile_pending_state_publication`, `repair_change`,
`get_change`/readiness, `PortfolioCoordinator`, and the existing retry and transaction owners.
Existing tests include
`test_engine_mark_ready_replays_lost_response_and_acceptance_waits_without_merge`,
`test_engine_unknown_result_after_effect_never_reenters_owner`,
`test_selected_acquisition_replays_only_its_pending_publication` and
`test_change_worktree_recovery_contains_unknown_custody_without_target_mutation`.
Use real default composition for claims about wiring; external provider/host fakes may be below
the owner under test. Do not inject successful provenance or call private workspace primitives to
stand in for the public route. Existing passing behavior is evidence, not a reason to duplicate it.

Keep one writer. Run only affected positive/negative tests and direct-consumer checks; compare
introduced lint/format defects and suppressions cumulatively rather than resetting the baseline.
Independently review the exact result against this bounded contract. Keep the plan and PR summary
current; no new narrative appendix or blanket hundreds-test reruns. A successful agent session
or skipped CI does not mean C passed.

The coordinating session ran 10 application cases at `7ed768b` with PR-worktree import provenance
verified: known mark-ready lost-response replay, unknown owner-result non-reentry, selected-Change
publication replay, head/target/dirty/untracked preflight refusals, and unknown-custody worktree
refusal. Result: **10 passed, 399 deselected, 7.89s**. These use existing application fixtures;
they do not establish real default-loader composition or complete the revised C acceptance.
No production code, live state or provider effect was changed by this scope amendment.

The prior A/B design discussion and stronger automation requirement are retained in the
[immutable pre-decision plan](https://github.com/maba-pag/owlbear/blob/7ed768b95571762504e3ca9c1e508eb6a48c06ed/.owlbear/research/delivery-cloud-d03-plan.md).
They are no longer an active user decision, a request for another feasibility experiment, or a
prerequisite for bounded C. A broader capability needs its own concrete proposal and approval;
it is not a promised later D03/D08 deliverable.

### Evidence index

Full prior progress, approval references, review reports and commands remain in the
[immutable pre-correction record](https://github.com/maba-pag/owlbear/blob/ab8bb110c12334bea3f8bd0ce2077b32c5e67c9c/.owlbear/research/delivery-cloud-d03-plan.md).
Consult only the entry needed for a specific claim. Do not replay its superseded next requests.

| Boundary | Source / reported evidence | Current limit |
| --- | --- | --- |
| P specification and D02 prerequisite | Approved plan `6c8c039`; D02 `1ab5ae7`; approval references retained below | No change to admitted safety requirements |
| A exclusion reference path | `4dff7c0`; scoped tests and independent review recorded in the archive | Actual host exclusion remains unproved; fixtures cannot authorize an unsupported live host |
| B retry/result accounting | `7dd03b4`; independent repair review and cumulative scoped proof recorded in the archive | Preserve episodes and outcomes; do not restart or replace this work without an observed defect |
| C admission/provenance | `92160aa`; 604 tests reported across two owning files, overlapping earlier runs | Primitive/provider-fixture proof, not production provenance or whole-C acceptance |
| C replay/accepted-repair fencing | `b6205a6` through `6db0fec`; independent source review, subsequent focused proof at `9d78f94` | Does not establish the missing composed recovery path |
| C finalizer readiness | `9d78f94`, handoff `ab8bb110`; reported 10/6/9/7-case selections and overlapping final three cases; independent narrow review | No additive test total or cumulative C pass; some successor/re-repair matrices remain unproved |
| Last bounded local repair | `f9330ffc`; 24 focused tests, scoped Ruff and independent review | Superseded source requires affected proof; this is not evidence for later changes |

The historical course correction supplied source/history inspection and read-only review, not
product execution proof. Source/Cockpit/ecosystem runs inspected at the decision checkpoint
`2e377a6` were skipped, not passed. Approval, draft state and external CI remain distinct from
implementation acceptance. Keep the draft and protections intact; do not approve obsolete runs.

The raw patch also adds many lint suppressions. Their existence is not automatically a defect, but
increment-relative clean results cannot establish cumulative quality. The next implementation must
identify any required exceptions on its actual completed path and repair introduced defects rather
than reclassifying them as a new baseline. Broad cleanup is not the integration objective.

### Authority references

- Original source inspection: `96f21ec5d87de2a8003d4010281fc4dc47b7d645`, branch `copilot/d03-p`.
- Published package: draft [PR #326](https://github.com/maba-pag/owlbear/pull/326), targeting `dev`.
  Subsequent phases belong on that PR; do not create another package PR.
- At repair start, checkout and reviewed PR head were
  `466b5ea50e8d9569c0e4295941a05b4fb0e84134`; GitHub reported comparison target
  `dev@fd0dec2aaca7831532505573c4d348eaa9012dbb`. These are distinct from the original inspected
  source and from a computed Git merge base. Do not rebase or merge in D03-P.
- D02 prerequisite: accepted source `1ab5ae7e4f56201e3b01dc2a5a88fc8525352806` and acceptance record
  `e45ea3e4bc4e6f7456af8c8ac3c82313a36a3764` are in GitHub's published `dev` history. The checkout
  contains the [accepted checkpoint](change-continuation-delivery-redesign.md#d02-accepted-checkpoint-2026-09-14)
  and the retained-custody implementation described below. D02 was accepted through the preceding
  direct-development procedure, not a newly invented D02 cloud PR gate.
- Prior evidence, **not rerun here**: that checkpoint records independent exact-head Astra PASS,
  837 scoped Python tests, 314 frontend tests, a production build, 22 browser tests and named-host
  dispatch rehearsal. This verifies predecessor acceptance; it is not D03 proof or a claim that
  later dependency updates were tested by that run.
- Specification approval: user [comment 5714163306](https://github.com/maba-pag/owlbear/pull/326#issuecomment-5714163306)
  explicitly approved the presented plan at `6c8c039a05c32ec265e45430d0b8a4e8e05be23c` and requested
  **D03-A only**, implemented by GPT-6 Astra. This is separate from worker-written progress and
  does not authorize B–E, merge or activation.

Repository paths in links resolve from this file. Command paths below use the actual cloud checkout
`/home/runner/work/owlbear/owlbear`; later workers must resolve their own checkout before invocation.

## Contract

The [current handoff](#current-handoff) and the programme's explicitly approved bounded recovery
revision govern this contract. The full-automation analysis retained in Git history is not an
unresolved A/B decision or a requirement to build an execution backend. The remaining detailed
preservation clauses below constrain any use of those primitives; they do not require enabling
automatic dirty recovery when its authority is unavailable. U1-U8 and all no-loss/privacy/exclusion
requirements remain in force. This is reduced automation coverage, not equivalent full-C delivery.

### Result, requirements and exclusions

Deliver bounded, preservation-first recovery of failed finalizers, uncertain claim activation and
interrupted engine actions, plus useful read-only diagnosis when coordination/runtime composition is
damaged. Resume the original Change action only after an owning recovery receipt, never after a
diagnostic or elapsed lease. Cover programme **WP3, P05/P10/P11, V06–V10, V13, V18 and V20**.
The controlling requirements are [U1–U8](change-continuation-delivery-redesign.md#11-requirements-from-the-user),
[failure routing](change-continuation-delivery-redesign.md#61-routing-rules-for-failures),
[preservation and repair](change-continuation-delivery-redesign.md#7-preservation-first-worktree-and-code-recovery),
and the [offline boundary](change-continuation-delivery-redesign.md#111-repair-delivery-is-a-proposed-maintenance-entry).

The user supplies meaningful decisions/permission, not tests, Git commands, JSON edits, digests or
manual process killing. Continuation remains Change-scoped; capacity and shared-target fences remain
engine-owned. Preserve independent review and existing admission promises.

Excluded: D04 revision/evidence-applicability machinery; D05 merge authorization or provider merge
implementation; D06 private-input collection; D07 migration/application of offline repairs and
release management; D08 activation. No live state, host services, real provider writes, automatic
successor dispatch, new scheduler, arbitrary shell runner or controller bootstrap. Do not modify
unknown corruption into a valid-looking record, or treat an existing hash as proof of provenance.

### Existing owners and source findings

| Owner | Reuse and required extension |
| --- | --- |
| [Application](../../serve/delivery/src/owlbear_delivery/portfolio_application.py) | `acquire_change_action`, `execute_change_action`, `repair` and existing finalization/result routes remain the public authority. `repair` currently handles only a legacy stale-Builder proposal; extend it, not a parallel recovery facade. |
| [Coordinator/workspace](../../serve/delivery/src/owlbear_delivery/change_workspace.py) | `ChangeContinuationAction`, `ChangeFinalizationAttempt`, `PortfolioCoordinator`, `ChangeWorkspaceManager`, publication/acquisition locks and immutable action receipts own custody and Git fences. `process_id` is a string supplied by dispatch, not a verified OS PID. |
| [Runtime](../../serve/delivery/src/owlbear_delivery/delivery_runtime.py) | Exact claims, transition/result replay, review repair, finalization invalidation and per-binding retries already exist. `_retry_fingerprint` covers Change/outcome/role/code only; `retry_count` is not an action-wide durable budget. Reuse transitions, but do not assume they close abandoned workers. |
| [Transactions](../../serve/delivery/src/owlbear_delivery/runtime_transaction.py) | Immutable and expected-byte replacement participants, manifests and failure injection support atomic authority publication. Git/provider effects still need intent/readback boundaries; a file transaction does not make them atomic. |
| [Finalization reports](../../serve/delivery/src/owlbear_delivery/finalization_reports.py) | Reports are bounded structural diagnostics, explicitly not authenticated proof. Current schema rejects raw commands/logs and maintained-check paths. Keep that privacy distinction when adding proof-mutation evidence. |
| [Projection](../../serve/delivery/src/owlbear_delivery/work_items.py) and application readiness | Preserve a single readiness basis for cards/acquisition. Add typed recovery/backoff/exhaustion rather than infer readiness in MCP, HTTP or agents. |
| [State publication](../../serve/delivery/src/owlbear_delivery/delivery_state.py), [branch publication](../../serve/delivery/src/owlbear_delivery/change_publication.py), [draft PR](../../serve/delivery/src/owlbear_delivery/draft_pull_request.py) | Reuse exact owner intents/receipts and readback. No generic retry of a provider mutation whose result is unknown. Public snapshots must not acquire private preservation contents or host termination credentials. |
| [Tools package](../../serve/tools/pyproject.toml) | Place the offline entry here, in the consumer-distributed tools boundary. Existing `owlbear_tools/delivery_config.py` imports Delivery; core `owlbear_delivery/diagnostics.py` imports the application. Neither is a safe offline bootstrap import. `owlbear_tools.__init__` is currently inert. |
| [MCP](../../serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py), [HTTP](../../serve/cockpit/src/owlbear_cockpit/routes/target_work.py), [continuation workflow](../../share/skills/w-orchestration/SKILL.md) | Extend strict existing adapters and mechanical dispatch; no transport-owned recovery decisions. The existing `/continue-change` entry already preserves failed custody. |

Important retained states in the inspected source:

1. Failed finalization keeps its writer and attempt even after report retirement; successful
   finalization is refused. `test_continuation_failure_retains_custody_and_blocks_success_and_mutations`
   is the reference negative case.
2. Activation can leave an exact runtime claim with or without a coordinator writer. An error and
   absence of a launch response do not prove the delegate never ran.
3. Engine actions retain immutable `intent.json`, `started.json` and `result.json` under the owning
   Change's `action-receipts`. A blocked result is replayed unchanged; a started action without result
   is not invoked again. D03 must add a linked recovery result, not overwrite those original records.
4. Existing Builder quarantine uses an alternate index and a Git commit, followed by broad reset/clean.
   That is **not** sufficient authority for nonterminal restoration: it neither preserves distinct
   staged bytes as such nor proves authorship, privacy safety or byte identity through Git filters.
5. Constructing `PortfolioCoordinator` creates state and recovers transactions. Offline diagnosis
   must not instantiate it, load `PortfolioApplication`, or import the eager Delivery package.

### A. Exclusion and recovery authority

**Critical T3 contract — not delegated policy invention.**

Accepted evidence is one of:

- **Host-confirmed closed invocation:** an engine-configured, trusted host integration resolves the
  exact issued invocation and confirms termination of the delegate **and all descendant writers and
  outstanding tool jobs**, with no ability to resume that invocation. Bind host instance/generation,
  opaque invocation identity, Change, claim/attempt or engine operation, and the managed resources.
  An acknowledgement of a cancellation *request* is insufficient.
- **Enforced exclusion:** the integration actually prevents every old writer from reaching the
  managed worktree, shared Git metadata/refs and relevant mutation channels. It must remain enforced
  across restart until the old execution is closed. A new directory, token/generation counter,
  revoked MCP permission, advisory lock or branch name alone is not filesystem exclusion.

No supported VS Code termination/exclusion provider was found in the inspected owners. Existing
`host_id`, `session_id`, `process_id`, a diagnostic, `confirmed_lost`, a PID lookup, silence or timeout
cannot be converted into either evidence form. Do not retrofit unverifiable provenance to D02 claims.
An old invocation may be resolved by a trusted host integration only if it can independently match
that exact invocation and all its writers; otherwise it stays contained.

Add one narrow injected host-evidence dependency to `PortfolioApplicationDependencies`, with a
default **unavailable** implementation. It observes/requests closure for an engine-issued identity
and returns `closed`, `excluded`, `still-running`, `unknown` or `unavailable`. Only the configured
owner may produce verifiable evidence; public `repair` accepts an opaque evidence reference at most,
never a caller-authored acknowledgement or boolean that grants release. The core must validate the
reference through the owner, not merely hash/deserialize a caller's fields.

For synchronous engine actions, an owning call that has returned and joined its tool jobs can record
closure evidence itself. A reacquired process lock after a crash does **not** prove a surviving Git
child or outstanding remote request stopped. Unknown outcomes require exact owner readback as well
as exclusion; if either is unavailable, retain custody. Do not build a general process supervisor.

Persist a versioned `RecoveryIntent` and `RecoveryReceipt` in the existing runtime Change directory,
under `recovery-receipts/<recovery_id>/`, implemented in proposed core module `recovery.py`.
The intent binds original custody/intent/report, contract/frontier and coordination byte digests,
heads, branch/worktree registration, supported evidence identity and intended fixed recovery kind.
The receipt records closure/exclusion, preservation and exact owner-effect dispositions separately.
It links the original failure, any resumed action and the immutable intent; it never rewrites a
failure as success. Keep bounded metadata and no file contents/host credentials in public results.

Recovery state is `proposed -> excluded -> preserved (when needed) -> reconciled -> completed`;
`contained`, `stale`, `backoff` and `exhausted` are non-success outcomes. These are recovery stages,
not new Delivery task stages. A failed write cannot skip a stage on replay.

Transaction boundary:

1. Under existing lock ordering, capture/CAS the exact owner and record intent without releasing it.
   Host cancellation/readback must not hold a portfolio-wide lock while waiting.
2. Verify closure/exclusion and reacquire/recheck the same identity before any local mutation.
   Persist evidence; revalidate an ongoing exclusion after restart, rather than trust its timestamp.
3. Reconcile only known owner effects and preserve anything required by the next operation.
4. Atomically publish recovery receipt, exact claim/coordination release and any runtime replacement
   with `RuntimeTransaction` expected-byte participants. Readers must not see free capacity with an
   unfinished recovery. If only one of runtime claim/writer existed after failed activation, release
   exactly that proven owner; a mismatched or malformed record is containment, not reconstruction.
5. A resumed attempt is acquired afresh from the original action's **current** basis after verified
   recovery. Reject the old worker's late submission against retired custody. Preserve the old
   finalizer report/attempt and engine result as history, including checks-not-run.

All entry points touching the same resources must honor this fence, including legacy claim recovery,
Integration recovery, retry transitions, finalization, administrative mutation and acquisition.
Do not leave a caller-confirmation or timeout bypass reachable alongside the new path.

#### Interrupted engine effects

| Original kind | Permitted reconciliation after exclusion |
| --- | --- |
| `reconcile-checkpoint` | Read pending checkpoint/state/branch/draft-PR journals and exact receipts; reconcile the same publication identity through existing owners. Account for a checkpoint-created successor head. Missing or contradictory records remain contained. |
| `sync-target` | Read the existing exact target-sync intent, ref/HEAD and receipt/conflict state. Finish supported interrupted local publication once; a conflict routes bounded Builder repair and fresh review, not reset or force update. |
| `mark-ready` | Read the exact PR/head/draft state and existing ready receipt. Confirm the original authorized effect or invoke an owner-supported idempotent reconciliation; stale head/protection state is not success. |
| `observe-acceptance` | Read the original acceptance/publication/finalization identities and disposition receipts. Waiting is not a merge permission; never manufacture completion or repeat an unknown mutation. |

An owner may replay an effect only where its existing journal/readback contract makes that exact replay
safe. `not-observed` is not automatically `not-applied`. If the owner cannot discriminate, return
`contained / owner-outcome-unknown`. D03-A supplies the closed-worker reference path and recovery
journal; D03-E must cover all four rows before package closeout.

### B. Failure identity, budgets and backoff

Use a versioned runtime-owned retry ledger, proposed module `recovery.py`, with immutable attempt
records and an expected-byte current summary. Store it in the same Change's runtime directory;
update reservations and recovery/action receipts transactionally. Existing per-binding retry counters
must be reconciled into this authority, not become a second allowance.

- Engine semantic key: `(change_id, action_kind, exact_head, target_head, finalization_id)`.
  Exclude new continuation operation IDs, acceptance observations, host/session IDs and error prose.
- Worker/proof key additionally identifies the approved contract, stable outcome/task lineage,
  registered check/procedure or finding class, and original candidate. Do not key on a renamed label.
- A recovery episode links successor repair commits/attempts to the original failure key. A new
  commit, task name, report ID or changed error wording is **not** accepted progress and cannot
  create a fresh allowance for the same failing check. Retain earlier keys; alternating codes must
  not replenish a common action's budget.
- Reset only the affected episode after an engine-accepted result covering its failed claim, or an
  independently recorded, approved new approach bound to that episode. D03 does not invent a generic
  approval API: unsupported new-approach approval remains a decision, not a reset flag.
- Reserve each automatic attempt before dispatch/effect entry; duplicate submission/replay charges
  once. Interrupted reservations remain consumed until exact evidence proves no attempt started.
  Pure observation of readiness neither consumes nor resets the budget.

Proposed programme defaults, made precise for specification review:

| Failure/action | Allowance | Backoff and stop |
| --- | --- | --- |
| Equivalent mechanical or Builder/check repair | At most **two automatic repairs after the original failure** per episode | Earliest next starts at persisted failure time plus 1 second, then 2 seconds; after the second failed repair, `exhausted`. |
| Transient service/read failure | **Three total attempts**, including the first | Retry after 1 second then 2 seconds; third failure exhausts. Unknown writes use readback, not this effect allowance. |
| Repeated acceptance waiting with unchanged semantic key | Yield without merge action; at most three automatic observations before a durable wait | Apply the read backoff between observations; an explicit later continuation can observe once, but does not reset an exhausted failure/repair episode. |
| Active/unknown writer, unsafe preservation, corruption, permission or semantic gap | **Zero automatic destructive repairs** | Named containment/decision/host-needed reason. Read-only diagnostic retries remain bounded separately. |

Use the injected clock; persist timezone-aware `next_eligible_at`, policy version, counts and a fixed
stop code. Early/clock-regressed observations wait; never sleep holding custody locks or poll in an
agent loop. Changing policy version/configuration does not erase accumulated counts. Expose attempts,
next actor, next eligible time and one intelligible stop reason through shared readiness. One exhausted
Change must not prevent independent Changes from using otherwise available capacity.

### C. Preservation, proof failure and resumption

**Bounded C completion rule:** prove an existing supported engine-owned replay/reconciliation
path through real application composition, and contain every unsupported/unknown recovery path
truthfully. Default provenance and proof-attempt producers may remain unavailable. No new runner,
write-attribution system or host adapter is required. A missing authoritative result never permits
re-entry of an effect just because another receipt might suggest it completed; retain existing
owner-specific readback rules and custody checks. The user is not asked to manufacture authority.

The detailed capture/restoration and completed-outcome Builder rules in this section remain safety
constraints on those optional paths. They are not a demand to activate them or a completion gate
when the default host cannot establish their evidence. Keep their negative tests and historical
records; do not delete code or broaden its authority merely to reduce the PR. Ordinary code repair
remains Builder work only when the existing custody and review owners can admit it safely.

Only the workspace owner applies an exact-path proposal under proven exclusion/no competing Builder
claim and exclusive recovery custody. Bind Change version, actual worktree registration/realpath,
branch/HEAD, reviewed and target heads, raw index digest, complete status/path set, per-path raw-byte
digests/types/modes and maintained-surface/last-write evidence. Whitespace alone proves no ownership.

Classify **before** writing preservation objects:

- Proven disposable, admitted post-proof drift: preserve first, then restore only those exact paths.
- Useful admitted code, generated output or proof-procedure changes: preserve and route existing
  Builder repair with reproduced check/finding, constraints and cumulative review baseline.
- Foreign/ambiguous paths, pre-existing staged changes or private/secret-like material: preserve
  in place and contain, without copying content into Git objects, public state, logs or responses.
  Ask only a meaningful inclusion/preservation/permission question where supported.

Extend the current quarantine representation with a private local raw-byte manifest/object store
under `recovery-receipts/<recovery_id>/preservation/`; do not assume `git add` preserves bytes when
attributes/clean filters or line-ending conversion apply. Raw preservation is authoritative;
existing attempt/quarantine refs may supplement it only for already privacy-qualified content.
No automatic remote publication or inclusion in `DeliveryStateSnapshot`.
Create private directories/files with owner-only permissions; no automatic deletion/garbage
collection of preserved evidence in D03. Public receipts expose opaque references, not content.

**Raw-index owner and v1 boundary:** C adds descriptor-backed capture to `ChangeWorkspaceManager`;
the existing temporary quarantine index is not the managed index. Resolve the index using
`git rev-parse --path-format=absolute --git-path index` in the exact registered worktree. Resolve
that worktree's administration directory and common directory through Git (`--absolute-git-dir`
and `--git-common-dir` with absolute path formatting), not a constructed administrative path.
Reject inherited Git repository/worktree/index/object-directory overrides for these reads; no
caller-supplied index path or `GIT_INDEX_FILE` may select the evidence.

The managed index is outside the worktree content root. Permit only the exact Git-resolved `index`
file directly within that registered worktree's Git-resolved administration directory, itself
verified against the registered repository/common directory. Pin directory descriptors and verify
the worktree registration, directory identities and Git-resolved paths again before applying any
proposal. Reject symlinked ancestors/files, nonregular or multiply linked index files, path swaps,
missing index and an existing index lock; do not delete a lock or initialize/refresh the index.
Use read-only Git inventory with optional locks disabled and no external filters/textconv.

V1 supports only a self-contained full index. Detect split-index dependencies using Git's
`--shared-index-path` and sparse-index entries with `ls-files --sparse --stage -z`; either produces
containment, not index expansion or conversion. Capture all ordinary stage/mode/object/path entries
using `ls-files --stage -z` and compare staged state to the exact HEAD. Reject staged/unmerged content
before copying raw index data. Index paths/extensions may contain private metadata: the entire raw
index, not merely changed paths, must pass the same privacy policy before owner-only preservation.
Unknown extensions whose privacy/independence cannot be established remain contained. The index
counts against the existing per-file/total preservation limits; never include its bytes or entries
in public receipts, Git objects or logs.

Read raw bytes from the pinned descriptor, recording content digest and file/directory identity;
check descriptor metadata and the raw digest again around inventory and before every restoration
step. Disable optional Git index refreshes throughout recovery. V1 restoration changes only selected
worktree content and **never rewrites the index**; therefore the raw index must remain exactly the
recorded preimage on replay, even if Git would consider a different index semantically equivalent.
Any index drift retains custody and preserved evidence without restoring a saved index over newer
staging. Raw capture is recovery evidence, not an authorization to modify Git administration.

Supported v1 inventory: regular/binary files, deletions, rename source/destination, executable modes,
and symlink text without following links. Retain raw index bytes and HEAD/ref metadata; reject
unmerged or pre-existing staged content before mutation. Refuse external symlink traversal, special
files, submodule changes, ambiguous hardlinks and root/registration substitution. Do not traverse
ignored credentials, environments or profiles; refuse a repair that would require touching them.
Use explicit bounded policy: at most 256 changed paths, 16 MiB per file and 64 MiB total raw content;
over-limit/type/privacy rejection is containment, never partial success. No claim of perfect secret
detection: provenance/allowlisted maintained paths plus conservative checks are all required.

Durably write and independently verify **all** preserved content, metadata and the manifest before
the first restore. Recheck the original fences immediately before each exact-path effect. Never use
generic reset/clean or expand the selected paths to make the worktree clean. Persist per-path
before/after identity so restart accepts only the recorded preimage or intended postimage; any third
value stops. Partial restore retains original evidence/error and custody until safely reconciled.
An fsync/disk/receipt failure must not report success or discard the last good snapshot.

Record proof-command before/after fingerprints. A mutation produces `proof-mutated-worktree`, the
registered command/procedure identity and changed paths, even if the command exits zero. Arbitrary
command strings, output and secrets stay out of the structural diagnostic API. A bounded local
proof-attempt record binds a maintained procedure to the fingerprints; its observation is not a
passing review receipt. Extend finalization failure category validation deliberately, not by allowing
free-form logs in `ReportFinalizationFailure`.

Restoring disposable drift preserves reviewed HEAD and resumes the original preflight. A Builder
repair creates a new candidate, invalidates old exact-head finalization through existing runtime
owners, and requires fresh cumulative independent review. Fix a mutating proof procedure before
rerunning it; do not alternate restore/formatter indefinitely. Source defects remain Builder work;
semantic gaps return to Designer/user. No weakened tests or acceptance exemptions.

#### Completed-outcome Builder repair

Current `claimable_outcome_ids`/`claimable_task_ids` exclude completed work, and
`prepare_review_repair` requires an existing successful finalization: neither already supplies the
failed-before-proof Builder route. C must add one fenced runtime operation for that route rather
than ask an unclaimed Builder to edit or use an administrative move that erases prior results.

For a reproduced local finding with one proven owning outcome/task, the engine derives one immutable
`DeliveryTaskDefinition` from that task's admitted maintained surfaces, commitments, constraints,
exclusions and proof boundaries, narrowed to the defect. Append the repair task with an
episode/attempt-bound ID and dependencies on the preserved completed task results; retain every old
task/result unchanged and reopen only that outcome to `implementation`. Bind the derivation and
original continuation action in the recovery intent. No arbitrary caller-authored task or broadened
scope. If the owning scope cannot be established, return a bounded planning/design attention rather
than choosing the first outcome or pretending the repair is dispatchable.

Publish the repair-task addition, exact finalizer/failed-claim release and recovery receipt in the
same fenced transaction. The existing `activate_claim`, `show_build_context`, `submit_result` and
independent exact-commit review then carry that task. Preserve the failure episode when the outcome
completes again; acceptance of an unrelated repair task does not prove the original failed check.
The original action resumes only after the repair result and required review, with the failed
whole-Change check still required. Downstream completed receipts remain historical exact-head
evidence; they are not automatically proof of the new candidate.

If successful finalization/publication authority already exists, use the existing draft/readback and
invalidation owners before admitting the repair; a failed draft transition admits no task. If proof
failed before any successful finalization, no fictitious invalidation ID or provider prerequisite is
created. Reject merged/terminal Changes. C's proof must include both branches, duplicate task
publication after restart, preserved prior results and a semantic/out-of-scope finding rejection.
Include a completed downstream outcome during repair/restart: its old receipt stays intact but
cannot certify the repaired candidate or bypass the required whole-Change proof.

### D. Offline diagnosis

Add `serve/tools/src/owlbear_tools/delivery_diagnostics.py` and a `delivery-diagnose` entry in the
existing tools manifest. Also support direct execution with an already installed supported Python,
without importing `owlbear_delivery`, MCP, Cockpit, runtime parsers or mutating tools commands.
Add `share/prompts/repair-delivery.prompt.md` as the ordinary-session entry; no healthy Delivery claim
or constrained Repairer agent is required.

Fixed v1 operation: `inspect`, with discovered/validated project root, optional Change ID and bounded
text/JSON output. No arbitrary paths/commands, repair/apply flags, user digest, network or provider
calls. Inspect executable/package version metadata, configuration presence/schema, supported persisted
record shapes, pending transaction presence and bounded structural log metadata. Initial known
versions come from this checkout: config 2, frontier 18, coordination 1, state snapshot 2.
Structural recognition is explicitly **not** runtime validity or user-provenance verification.

Use standard-library JSON and filesystem inspection for the bootstrap. YAML transaction manifests
are reported as pending opaque evidence (size/type/locator), not interpreted by a handwritten YAML
parser or replayed. Optional unavailable metadata is reported as unknown rather than initializing
dependencies or state. Read fixed paths below `.owlbear/delivery`, never profile directories.
Bound input to 256 entries, 1 MiB per structured record and 8 MiB total; logs, if recognized, to the
last 64 KiB with an allowlisted structural summary only. Truncation is explicit.

Return versioned status `healthy-structure`, `degraded`, `unsupported` or `unavailable`, fixed
diagnostic codes, safe relative locators, inspected schema/version metadata, bounded counts,
pending-effects indication, `writes_performed: false` and one complete maintenance/continuation
prompt. Never echo raw JSON, exception content, URLs, credentials or arbitrary log lines. Do not
rehash unknown data into authority or call missing provenance “confirmed”.

No mkdir, lock-file creation, transaction recovery, bytecode files, Git refresh/fetch or writes to
the inspected root. Enforce descriptor/realpath containment, no-follow regular-file reads and detect
replacement during inspection; dangling/symlink/FIFO/oversized entries produce bounded diagnostics.
The CLI's read-only promise covers its own writes, not ambient access-time changes. Exit 0 only for
healthy structure, 1 for diagnosed degradation/unsupported state, 2 for unusable invocation/root.
The prompt reports that repair writes/upgrade require D07's supported route; it must not promise an
unimplemented auto-fix or require users to repair files manually.

## Phases and proof

### Execution rules

Run only the requested phase. Sequence **D03-P -> D03-A -> D03-B -> D03-C -> D03-D -> D03-E**;
each implementation successor requires the preceding phase's code, cloud-required proof and
independent review with findings resolved on this PR. D03-D is technically independent of B/C, but
this sequence avoids another writer/scheduling path. Each phase may update only its progress/gaps
here, not silently change approved semantics.

All named new modules/tests below are **planned**, not present or passed. No additional testing
framework or dependency is required. Extend existing test files where their fixtures suffice; new
focused recovery/diagnostic files use the existing pytest setup. T3 owns A/C and acceptance, T2 can
implement settled B/D/E mappings; obtain independent different-family review of implementation.

Every command is scoped. From `/home/runner/work/owlbear/owlbear`, use `uv run --locked pytest` with
explicit paths and `-q -n 1 -m 'not api and not model and not e2e'`; `-n 1` overrides root `-n auto`.
The selections below are inner-loop commands once their planned tests exist. Do not run a bare
pytest, workspace test aggregate, MegaLinter, `quality`, or broad autofix. Runtime for these new
selections is **unmeasured**; record actual duration on first use rather than copying D02 totals.

### Mandatory same-phase companions

- **Central mutation authority (A/B/C):** every added or changed frontier-writing runtime operation,
  including C's repair-task/reopen operation, must participate in `_NORMAL_CHANGE_MUTATIONS` and
  invoke `_require_change_mutable` under the existing policy. Settle any permitted attention state
  explicitly in that owner; no recovery exemption or direct transaction side door. The introducing
  phase owns necessary additions to `tests/test_delivery_worktree_authority.py`, without weakening
  existing assertions. Its focused proof is
  `uv run --locked pytest /home/runner/work/owlbear/owlbear/tests/test_delivery_worktree_authority.py::test_runtime_frontier_writers_use_the_central_mutability_policy -q -n 1 -m 'not api and not model and not e2e'`.
  A/B run this when changing frontier mutation behavior; C must run it for the new reopen operation.
- **Workspace authority (A/C):** when touching registration/removal paths, run the existing
  `test_worktree_registration_has_only_named_lifecycle_callers` and
  `test_worktree_removal_has_only_named_cleanup_caller` nodes in that same file. C's index work
  must run `test_delivery_sources_have_no_git_admin_artifact_path`. No allowlist widening just to
  bypass ownership, and no raw administrative paths in production code or workflow instructions.
- **Readiness mirrors (any introducing phase):** adding a reason/action/status or changing a public
  readiness field requires the corresponding `serve/cockpit/web/src/api/workItems.ts` update in
  that phase, not deferred to E. Its editable companions are the existing readiness consumers
  `pages/WorkPortfolioPage.tsx`, `components/WorkItemDetail.tsx` and
  `__tests__/WorkPortfolio.test.tsx` beneath that frontend source root. Add a focused parity assertion
  for backend reason values versus the TypeScript union to `tests/test_cockpit_boundary.py`, and
  render the newly introduced states in the component test. Use the scoped frontend test/build
  commands in E and the new parity node in the introducing phase; do not repeat unchanged proof.

### D03-A — Exclusion and exact recovery reference path

**Editable sources:** `serve/delivery/src/owlbear_delivery/{recovery.py,portfolio_application.py,
change_workspace.py,delivery_runtime.py,work_items.py,__init__.py}`. Add a loader companion in
`delivery_application_loader.py` only for the default-unavailable dependency, not new host settings.
Use existing transactions; change `runtime_transaction.py` only if an identified missing primitive
is necessary, with its owning test. Tests: owning application/workspace/runtime files plus planned
`serve/delivery/tests/test_recovery.py`.

Export versioned recovery intent/result/evidence-reference contracts and map core readiness together.
No registered executable recovery route yet; current public adapters must remain able to serialize
the bounded rejection described below. Include closure evidence capture at the issuing boundary; never make
existing D02 identity strings into authentication. Close known finalizer/claim failures and one
interrupted engine reference path only when both exclusion and effect reconciliation are proven.
Dirty or damaged unknown state stays contained pending C/D.

**Intermediate public contract (A through D):** retain existing request shapes to produce a truthful
bounded result, not successful recovery from an assertion. `recover_claim`, `repair`/`repair_change`
with a proposal, and legacy `recover_integration_repair_claim` must reject release unless the
engine-configured owner independently verifies exact closure/exclusion and all recovery fences.
`confirmed_lost=true` never contributes evidence, including for non-Builder/legacy claims; a missing
flag is not an alternative release route. A's default-unavailable owner therefore permits **no**
public claim release through these forms. An already completed exact recovery may replay its verified
receipt without another release. Read-only diagnosis and other unaffected valid operations remain
available. Expiry/acquisition and retry transitions cannot bypass this decision.

For a syntactically valid request without verified evidence, raise an engine-owned
`ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED` conflict, mapped to HTTP 409 and the existing MCP diagnostic
envelope with `retry_safe: false`. State that custody/files are unchanged and supported host evidence
is required; neither transport retries nor converts it into “recovered”. Invalid input keeps existing
validation behavior. Add the specific classification before generic runtime-conflict handling.
No new executable public recovery operation is enabled by A.

A's required editable companions are core `diagnostics.py`, MCP `target_models.py`/`target_server.py`,
Cockpit `target_models.py`/`routes/target_work.py`, and `share/skills/w-orchestration/SKILL.md`,
`share/agents/{orchestrator,repairer}.agent.md`. Remove instructions to assert `confirmed_lost=true`
as evidence in the same phase that removes its meaning. Update existing frontend confirmation
wording in `api/workItems.ts` and its corresponding Work detail/portfolio consumers so it cannot
promise that user confirmation stops a worker. Reuse the frontend paths in the mandatory companions
above; no broader role grants or new confirmation UI.

Add A tests in `serve/delivery-mcp/tests/{test_delivery_adapter.py,test_target_server.py}`,
`tests/test_cockpit_work_items.py` and `tests/test_agent_ecosystem_validation.py`: invoke the actual
core with an unavailable/unknown host-evidence owner through each registered recovery route and
assert the same non-retryable rejection, unchanged claim/writer/index/content, and no provider effect.
Cover legacy Planner, Builder and Integration identities, read-only `repair` diagnosis versus rejected
proposal application, exact receipt replay,
and forged/unknown evidence. Keep invalid-input tests. Name new cases `exclusion_required` and run
that selection across the three transport test files with the common pytest flags; include affected
workflow-contract tests and frontend copy tests at A closeout, not only E.

**First discriminating check:** a controlled worker continues writing after lease expiry while a
second application attempts recovery. It must remain the only owner; after a supported close
acknowledgement including child jobs, recovery/restart admits one replacement and no old write can
reach its files/refs. Use a real controlled local process and barriers below the host-evidence port,
not a mocked public recovery method. Test an orphan child separately from its exited parent.

**Negative/replay oracles:** caller-forged receipt, wrong host generation/claim/head, stale proposal,
unknown termination, absent host integration, malformed coordination, failed activation with and
without writer, concurrent recovery, late result, evidence publication failure and crash after each
authority step. No unsupported release; verified evidence and receipt replay survive reopening.

Inner loop:
`uv run --locked pytest /home/runner/work/owlbear/owlbear/serve/delivery/tests/test_recovery.py -q -n 1 -k 'exclusion or activation' -m 'not api and not model and not e2e'`.

Closeout adds existing `test_continuation_workers_cannot_be_recovered_by_timeout_or_caller_assertion`,
`test_continuation_live_worker_remains_excluded_after_lease`,
`test_continuation_failure_retains_custody_and_blocks_success_and_mutations`,
`test_engine_result_transaction_recovers_without_repeating_provider` from
`/home/runner/work/owlbear/owlbear/serve/delivery/tests/test_portfolio_application.py`, and focused
legacy/Integration/retry bypass cases from the runtime/workspace owners. Do not remove their
unproven-worker rejection assertions to enable the positive path.

### D03-B — Durable retry identity and bounded convergence

**Editable sources:** `serve/delivery/src/owlbear_delivery/{recovery.py,delivery_runtime.py,
portfolio_application.py,work_items.py,__init__.py}`; `delivery_state.py` only for a sanitized durable
budget projection if existing snapshot publication would otherwise reset the allowance on resume.
Tests: planned `test_recovery.py`, existing `test_delivery_runtime.py`,
`test_portfolio_application.py`, and affected snapshot tests if that companion changes.

Implement the B policy table, transactional attempt reservation, stable semantic keys/episode aliases,
backoff, exhausted projection and affected-episode reset. Maintain prior failure records separately
from current presentation. Do not reset a budget when a report is retired or when a new operation ID
is minted for acceptance waiting.

**Oracles:** fake clock at either side of each boundary; restarts between reservation/dispatch/result;
duplicate results charge once; new sessions, task labels, operation IDs and alternating prose/codes
do not replenish attempts; a repair commit still failing the same check exhausts; actual accepted
progress resets only its episode. Exhausted Change A does not block otherwise runnable Change B.
No source-state schema reinterpretation; incompatible persisted metadata fails closed.

Inner loop:
`uv run --locked pytest /home/runner/work/owlbear/owlbear/serve/delivery/tests/test_recovery.py -q -n 1 -k 'budget or backoff or fingerprint' -m 'not api and not model and not e2e'`.

Closeout includes owning runtime retry tests and
`test_checkpoint_failure_metadata_survives_reload_and_reanchors_by_head` in
`/home/runner/work/owlbear/owlbear/serve/delivery/tests/test_delivery_runtime.py`, plus an application
acceptance-waiting test proving fresh operation IDs retain the semantic budget.

### D03-C — Bounded recovery and explicit containment

This is the revised implementation assignment approved on 2026-09-25, not acceptance of the older
full-automation promise. Keep the phase ID; do not invent a new package or migrate the excluded
promise to D08.

**Editable sources:** `serve/delivery/src/owlbear_delivery/{portfolio_application.py,
delivery_application_loader.py,recovery.py,change_workspace.py,delivery_runtime.py,
finalization_reports.py,work_items.py,__init__.py}` and owning tests in `serve/delivery/tests/`.
Touch only the real missing boundary discovered by the checks below. A changed report contract
requires its strict MCP/skill companions in the same result; do not add a public endpoint or
workflow merely to make a test convenient. Broader registered forwarding remains E.

**First proof:** execute the current handoff's named positive replay and negative containment
tests on the PR source with verified import provenance. Reuse working behavior. Then exercise the
same result through the default application loader with only external effects faked below the
owning implementation. Fix missing composition, incorrect retry/receipt consumption, or misleading
public readiness/repair diagnostics found by that scenario. Do not bypass unavailable authority.

**Completion oracles:** known completed engine effect plus lost response/restart returns its exact
result without a second provider mutation; only the selected Change's pending publication is
reconciled; started-without-result, contradictory/stale evidence and uncertain workers remain
contained; staged/private/foreign/ignored or raw-index drift stays untouched and unpublished;
repeated requests preserve budgets and occupied custody while unrelated eligible Changes progress.
Mutation during proof is never a pass, even with exit zero. The read/repair result must tell the
truth about unavailable recovery, its owner and resume condition without promising nonexistent
automation or asking users to run commands/kill processes. No new test-provider authority.

Run only affected tests and necessary direct-consumer checks. Preserve existing safety tests for
optional preservation paths. Require scoped static proof and independent exact-result review
before C acceptance; no new blanket test campaign or increment-relative lint baseline. Publish a
concise capability table distinguishing supported automatic recovery from contained cases.

### D03-D — Read-only offline entry

**Editable sources:** proposed `serve/tools/src/owlbear_tools/delivery_diagnostics.py`,
`serve/tools/pyproject.toml`, proposed `serve/tools/tests/test_delivery_diagnostics.py`,
`share/prompts/repair-delivery.prompt.md`; `tests/test_package_boundary.py` and
`tests/test_agent_ecosystem_validation.py` only for this import/prompt contract. No setup, migration
runner, root tooling, live config or general maintenance framework.
The new prompt also requires the existing authority tests in `tests/test_delivery_worktree_authority.py`:
`test_delivery_automation_has_no_special_approval_or_risk_gate`,
`test_delivery_automation_scan_covers_required_roots` and
`test_delivery_sources_have_no_git_admin_artifact_path`. D may add a focused prompt assertion there,
but must preserve the existing scans and constraints.

Implement D's fixed operation and ordinary-session prompt. The entry is distributed through existing
`serve/tools` and `share` sync scopes; no sync-manifest changes are necessary.

**Oracles:** valid synthetic structure; absent MCP; poison imports for the complete Delivery/MCP
packages; malformed frontier/coordination/pending manifest; unsupported versions; missing user
confirmation provenance; unreadable, symlinked, replaced, oversized and special-file fixtures.
Snapshot the disposable tree before/after (including directory membership and contents) and run
against a read-only fixture: no state/lock/bytecode/repair writes, no raw sensitive value in output,
bounded completion and explicit incomplete inspection. Healthy structure must not imply acceptance.

Inner loop:
`uv run --locked pytest /home/runner/work/owlbear/owlbear/serve/tools/tests/test_delivery_diagnostics.py -q -n 1 -k 'malformed or no_runtime_import' -m 'not api and not model and not e2e'`.

Closeout runs that focused diagnostic module once, the new offline-boundary test and
`test_prompt_validator_accepts_current_prompt_roots` from
`/home/runner/work/owlbear/owlbear/tests/test_agent_ecosystem_validation.py`.
Direct CLI smoke uses an agent-created disposable root and `python -B` on the new module, with MCP
unavailable; never point it at live Delivery state during this programme.
Run the three authority nodes with
`uv run --locked pytest /home/runner/work/owlbear/owlbear/tests/test_delivery_worktree_authority.py -q -n 1 -k 'delivery_automation_has_no_special_approval_or_risk_gate or delivery_automation_scan_covers_required_roots or delivery_sources_have_no_git_admin_artifact_path' -m 'not api and not model and not e2e'`.

### D03-E — Registered handoff and cumulative package proof

The approved bounded acceptance applies across C, D and E; their IDs and ownership remain unchanged.
Positive proof is required for supported engine-owned recovery. Unsupported worker/dirty recovery
requires explicit no-mutation containment through the same registered/readiness surfaces, not a
new host backend. Such containment does not mark the individual Change recovered or complete.

**Editable sources:** existing MCP `target_models.py`/`target_server.py`; Cockpit
`serve/cockpit/src/owlbear_cockpit/{target_models.py,routes/target_work.py}`; core
`portfolio_application.py`, `work_items.py`, `diagnostics.py`, exports and recovery owner only for
required assembled fixes; `share/{agents/orchestrator.agent.md,agents/repairer.agent.md,
prompts/continue-change.prompt.md,skills/w-orchestration/SKILL.md,
skills/w-change-finalization/SKILL.md}`.
Include Builder/conflict skill companions only where the C repair return context needs them:
`share/skills/w-packet-building/SKILL.md` and `share/skills/w-target-conflict-resolution/SKILL.md`.
No replacement workflow or broader role grants.

Ship strict recovery request/result mappings, registrations/annotations and shared error taxonomy.
Keep `repair` the high-level diagnose/apply operation: application discovers exact proposals;
callers forward Change/proposal and, where supported, opaque owner evidence references. Reject
caller-authored preservation paths, commands, budgets, effect receipts and stop assertions.
Keep A's rejection semantics until an exact proposal and independently validated host evidence make
the new registered recovery contract executable. E adds strict proposal/opaque-reference forwarding
and positive recovery tests; it must retain A's negative legacy-call tests and remove any remaining
assertion-based workflow advice. Success compatibility covers verified receipt replay and read-only
requests, never unverified legacy release.
Expose one complete `/continue-change` or `/repair-delivery` prompt in readiness; a new UI control
is unnecessary for U1. Required frontend mirrors ship with each introducing phase; remaining E
presentation changes are limited to `serve/cockpit/web/src/{api/workItems.ts,pages/WorkPortfolioPage.tsx,
components/WorkItemDetail.tsx,__tests__/WorkPortfolio.test.tsx}`, not a UI redesign.

Assembled proof uses real application state and `Client(assemble_target_server(...))`, the existing
HTTP test client and temporary repos; fakes are below host/provider owners, not substitutes for
recovery, workspace or runtime methods. Verify all four interrupted engine rows, finalizer failure
before checks, claim activation both ways and offline degraded entry. Show a fresh continuation
for a supported exact-result/publication replay. For Builder repair or original-action resumption
whose custody/provenance cannot be established, assert explicit containment instead of fabricating
authority or counting it as recovered. Unknown outcomes remain contained throughout every
adapter. Include exact stale/foreign/forged fields, absent host capability and independent Change
progress. Review response copy for checks-not-run, preserved bytes, current owner and next action.

Inner loop:
`uv run --locked pytest /home/runner/work/owlbear/owlbear/serve/delivery-mcp/tests/test_target_server.py -q -n 1 -k 'registered_recovery' -m 'not api and not model and not e2e'`.

Closeout, split into bounded selections:

- `uv run --locked pytest /home/runner/work/owlbear/owlbear/serve/delivery-mcp/tests/test_delivery_adapter.py /home/runner/work/owlbear/owlbear/serve/delivery-mcp/tests/test_target_server.py /home/runner/work/owlbear/owlbear/tests/test_cockpit_work_items.py -q -n 1 -k 'recovery or continuation' -m 'not api and not model and not e2e'`.
- New assembled D03 cases in `test_recovery.py`; run only missing/invalidated V06–V10/V13/V18/V20
  proof from A–D. Existing passed phase evidence remains valid only for unchanged relevant inputs.
- Explicit changed-role/registered-tool tests in `test_agent_ecosystem_validation.py` plus affected
  tests in `test_package_boundary.py` and `test_cockpit_boundary.py`. Full module runs are ceilings,
  not automatic requirements.
- Scoped `uv run --locked ruff check` and `ruff format --check` on explicit changed Python files.
  If frontend types/presentation change, use locked npm dependencies and
  `npm --prefix /home/runner/work/owlbear/owlbear/serve/cockpit/web test -- src/__tests__/WorkPortfolio.test.tsx`,
  then one `npm --prefix /home/runner/work/owlbear/owlbear/serve/cockpit/web run build` for the type/bundle
  contract. Current frontend lint authority is Biome, not the historical ESLint command. No browser
  run is required for an unchanged UI; actual interaction changes need the maintained disposable gate.

### Acceptance allocation

| Claim | Cloud-required proof | Other environment |
| --- | --- | --- |
| V06/V07/V13 | C supported engine replay plus unchanged bytes/index/head, privacy and custody for contained cases; preserve negative proof for existing optional restoration paths | External CI broad regressions; general automatic dirty recovery is excluded from bounded D03 |
| V08/V09 | B/C mutation is not success, bounded diagnostics and retry accounting; unsupported repair stays contained | External CI broad regressions |
| V10 | A controlled still-writing process/descendant and absent-host fixtures prove no cleanup, release or replacement, including after restart | Actual host exclusion is required only to enable that broader recovery capability; it is not a bounded D03 completion gate or an automatic D08 assignment |
| V18/V20 | D malformed-runtime read-only CLI; E real degraded API/entry and provenance-negative cases | D07 owns supported repair/migration, D08 owns final host acceptance |
| End-to-end repair | E registered MCP/HTTP -> real core -> provider boundary -> supported replay/continuation, plus unsupported-path containment | Existing ordinary dispatch/transport host acceptance remains; general external-worker/dirty recovery is not silently deferred to D08-H |

## Progress and verification gaps

The [completion ledger](#completion-ledger) owns current status and the next outcome.
The [evidence index](#evidence-index) links the immutable historical record. No historical
test total or increment-level review is a cumulative D03-C acceptance claim.
