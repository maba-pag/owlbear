# Operating OwlBear

> What setup created, how to update or remove it, how the Delivery workflow runs day to day, and
> how to customize an installed project.

Install first with the [setup guide](setup-guide.md). Multi-project and teammate workflows live in
the [sharing guide](sharing-guide.md).

| You want to... | Section |
| --- | --- |
| See what setup wrote into your project | [What Setup Creates](#what-setup-creates) |
| Understand what `git pull` updates | [Shared vs Copied](#shared-vs-copied) |
| Upgrade OwlBear and migrate Delivery state | [Upgrading OwlBear](#upgrading-owlbear) |
| Replace seeded editor and lint configuration | [Refreshing Consumer Configs](#refreshing-consumer-configs) |
| Remove OwlBear from a project | [Uninstalling](#uninstalling) |
| Run, correct, publish, and accept a Change | [Delivery Workflow](#delivery-workflow) |
| Recover Delivery after a new clone or hardware loss | [Portability and recovery](#portability-and-recovery) |
| Launch the human control surface | [Cockpit details](#cockpit-details) |
| Add project-local agents, instructions, or servers | [Project-Specific Customization](#project-specific-customization) |

---

## What Setup Creates

Running `init.py` writes the following files into your project directory:

| File / Directory | Purpose | Idempotency |
| --- | --- | --- |
| `.vscode/settings.json` | Points VS Code at OwlBear agents, skills, and instructions, and carries the seeded Copilot workspace settings | Merged (OwlBear keys as defaults; your existing keys are preserved) |
| `.vscode/mcp.json` | Registers 5 MCP servers (4 OwlBear stdio, including Browser access seeded for wildcard testing, + markitdown) | Merged (OwlBear servers as defaults; your existing servers are preserved) |
| `.owlbear/delivery/config.json` | Declares the Git remote, pull-request target branch, exact GitHub `owner/name` identity, and remote Delivery-state branch | Tracked in Git; exact schema-1 policy is migrated once and schema-2 project edits are preserved on rerun |
| `.owlbear/delivery/runtime/host.json` | Shows the tracked baseline for the shared execution budget and the 60-minute claim timeout | Seeded with `execution_capacity: 3`; existing values are preserved on rerun |
| `.owlbear/delivery/runtime/host.local.json` | Optional per-host overrides for any `host.json` setting | Not seeded; ignored by Git and preserved when present |
| `.owlbear/install-manifest.json` | Records seed paths created or merged by setup, their installed digests, claimed settings/MCP values, and setup-created directories for conservative uninstall | Rewritten atomically on each successful setup; removed when uninstall completes unchanged |
| `.owlbear/hooks/allow-stances-only.py` | Restricts ideation agents to approved stance outputs | Seeded if missing; differing existing hook files prompt/skip/replace (or require `--replace-hooks` non-interactively) |
| `.owlbear/hooks/deny-src-writes.py` | Constrains test-only roles to `tests/`, `__tests__/`, and scratch surfaces | Seeded if missing; differing existing hook files prompt/skip/replace (or require `--replace-hooks` non-interactively) |
| `.owlbear/hooks/deny-writes.py` | Constrains read-only roles to scratch workspace writes only | Seeded if missing; differing existing hook files prompt/skip/replace (or require `--replace-hooks` non-interactively) |
| `.owlbear/hooks/lint-changed.py` | Builder lint feedback hook — runs `uv run ruff check` on edited `.py` files; silently no-ops if `ruff` is not in your project's deps | Seeded if missing; differing existing hook files prompt/skip/replace (or require `--replace-hooks` non-interactively) |
| `.owlbear/hooks/session-context.py` | Injects current git branch + recent commits into agent prompts; silently no-ops if `git` is unavailable | Seeded if missing; differing existing hook files prompt/skip/replace (or require `--replace-hooks` non-interactively) |
| `.owlbear/scripts/test-root.py` | Test-root resolver — discovers toolchain and CWD for a given test file | Always written |
| `.owlbear/.gitignore` | Ignores OwlBear-local scratch, runtime, database, vector, and lock artifacts | Managed rules are merged on rerun; custom rules are preserved |
| `.owlbear/knowledge/.gitkeep` | Knowledge store placeholder | Always written |
| `store/knowledge/.gitkeep` | Knowledge store placeholder | Always written |
| `.github/copilot-instructions.md` | Consumer scaffold for project-specific Copilot instructions — placeholder sections for Project Identity, Directory Structure, Tech Stack, and Resources | Skipped if file already exists |
| `.editorconfig` | Editor formatting rules | Skipped if file already exists; refreshable with `--refresh-configs` |
| `.gitattributes` | Git line-ending and diff rules | Skipped if file already exists |
| `.gitignore` | Project-wide Gitignore rules; OwlBear-local rules live in `.owlbear/.gitignore` | Preserves user content and merges current managed rules on rerun |
| `.markdownlint-cli2.jsonc` | Markdown linting configuration | Skipped if file already exists; refreshable with `--refresh-configs` |
| `.markdownlint.json` | Markdown linting rules | Skipped if file already exists; refreshable with `--refresh-configs` |
| `.markdownlintignore` | Markdown lint exclusion patterns | Skipped if file already exists; refreshable with `--refresh-configs` |
| `.yamllint.yml` | YAML linting configuration | Skipped if file already exists; refreshable with `--refresh-configs` |

Review `.vscode/settings.json` as part of trusting the workspace. The seeded settings include an
additional read-access path for the OwlBear checkout, a list of terminal commands that VS Code may
auto-approve, and `chat.tools.terminal.blockDetectedFileWrites: "never"`. These settings make the
agent workflow usable but are trust-sensitive; adjust them to your project's policy after setup.
Rerunning setup merges OwlBear defaults and preserves existing project values.

Open `.github/copilot-instructions.md` after setup and replace its placeholder project identity,
directory, technology, and resource guidance with the facts and conventions of the consumer
project. Setup skips this file on later runs so those project-specific instructions remain yours.
The seeded Browser MCP entry uses `BROWSER_ALLOWED_DOMAINS: "*"` for local testing; replace it with
exact hostnames before using Browser against production or sensitive sites.

For a fresh workspace, `init.py` writes tracked Delivery configuration and the visible default
`host.json` with one shared execution budget for Planner and Builder claims (`execution_capacity: 3`).
Builds retain exact per-Change writer custody; there is no separate global `writer_capacity` limit.
Create `host.local.json` only for machine-specific execution or timeout overrides; it is ignored and
is not synced to other hosts. Setup does not create mutable Delivery runtime state, worktrees, verification
profiles, or retired task, decision, board, accept, or audit stores.

Finalization evidence is collected for the exact reviewed Change head in its managed worktree. The
checks and procedures may differ by Change; Delivery retains their typed observations and an
independent exact-commit review. This evidence does not claim that GitHub can merge the Change or
that the merged result passes.

### Where these files come from

The source tree is [`seed/`](../seed/) in the OwlBear checkout. `init.py` walks every file in that
tree into the target project, which is why `seed/` intentionally contains no `README.md`: a root
README there would be copied into the consumer project and could overwrite its front door. This
guide is the canonical explanation of the seed tree instead.

Two neighbouring trees are never copied. [`share/`](../share/README.md) holds the portable agents,
skills, instructions, and prompts that VS Code reads live from the OwlBear checkout, and
[`serve/`](../serve/README.md) holds the runtime packages and MCP servers launched from it.
Repository-only CI automation lives in the OwlBear `dev` checkout's `.github/` tree and is not
installed into consumer projects.

## Shared vs Copied

OwlBear uses two different update models:

- **Shared live surfaces:** `share/agents/`, `share/skills/`, `share/instructions/`, and `share/prompts/` stay in the owlbear clone and are read live by VS Code.
- **Copied runtime surfaces:** files under `seed/` are copied into your project by `init.py`; this includes `.owlbear/hooks/` and project-local editor/runtime configuration.

This split is why `git pull` updates shared agents and skills immediately, while copied
runtime files may need a later `init.py` run to refresh. A pull also changes the Delivery code that
the next MCP or Cockpit start runs, so update the checkout through
[Upgrading OwlBear](#upgrading-owlbear) rather than a plain `git pull`.

## Refreshing Consumer Configs

Rerunning `init.py` preserves existing editor and lint configuration so project-specific changes
are not overwritten. The refreshable files are `.editorconfig`, `.markdownlint-cli2.jsonc`,
`.markdownlint.json`, `.markdownlintignore`, and `.yamllint.yml`.

From the consumer project root, check for missing or customized files without changing them:

```shell
uv run --project ../owlbear python ../owlbear/setup/init.py --check-configs
```

The command exits successfully when the files match the owlbear seed and exits with status 1 when
one or more files are missing or different. To intentionally replace those five files with the
current seed versions, run:

```shell
uv run --project ../owlbear python ../owlbear/setup/init.py --refresh-configs
```

`--refresh-configs` does not overwrite `.github/copilot-instructions.md`, hook files, or other
project-specific files that are outside the refreshable set.

## Upgrading OwlBear

Delivery records its state format in `.owlbear/delivery/runtime/format.json`. A newer OwlBear may
need a newer format: its Delivery MCP server and Cockpit then refuse to start with
`state-migration-required` until the state is migrated, and an older OwlBear that has this check
refuses newer state with `state-newer-than-controller`. Neither refusal changes your state. Upgrade
from the project, in a VS Code chat:

1. Run `/upgrade-delivery`, optionally naming an OwlBear commit or ref.

   **Expected result:** the agent reports Delivery health and every Change, and asks you to let
   running work finish first.
2. When asked, stop `owlbear-delivery` (**MCP: List Servers** → **Stop**) and Cockpit.

   **Expected result:** the agent moves the OwlBear checkout forward with `git pull --ff-only`, then
   runs `delivery-controller preflight` and `backup` and `delivery-migrate` `propose`, `apply` and
   `verify` from the new code. The backup is written to a directory outside the project.
3. When asked, start `owlbear-delivery` and Cockpit again.

   **Expected result:** the agent confirms that Delivery is healthy and that every Change is still
   available.
4. Rerun setup from the project root to refresh copied files:

   ```shell
   uv run --project ../owlbear python ../owlbear/setup/init.py
   ```

   **Expected result:** setup preserves your edits and existing Delivery configuration; see
   [Refreshing Consumer Configs](#refreshing-consumer-configs) for the editor and lint files.

The OwlBear checkout is shared: once it moves, every project that uses it runs the new code. Run
`/upgrade-delivery` in each of them before starting its Delivery again. If a project's
`owlbear-delivery` already refuses with `state-migration-required` because the checkout was pulled
directly, run `/upgrade-delivery` there; it skips the online check and continues with the offline
preflight.

The upgrade refuses while a Delivery MCP server or Cockpit still runs for the project, and changes
nothing. To go back after a migration, the backup has to be restored first, which is your decision;
moving the checkout back alone is safe only when no migration was needed. The upgrade also leaves
`.owlbear/controller/` (its lock) and `.owlbear/delivery-migrations/` (the migration journal and the
previous bytes of the migrated records) in the project; the setup rerun in step 4 ignores both in
`.owlbear/.gitignore`.

## Uninstalling

To remove the OwlBear setup from a consumer project, run this command from the project root:

```shell
uv run --project ../owlbear python ../owlbear/setup/init.py --uninstall
```

An interactive terminal asks for confirmation and prints the files it removes or updates. Preview
the plan without changing files by adding `--dry-run`. A non-interactive uninstall requires
explicit confirmation:

```shell
uv run --project ../owlbear python ../owlbear/setup/init.py --uninstall --yes
```

**Expected result:** an interactive run asks before changing anything; `--dry-run` reports the
planned removals without mutation; `--yes` applies the receipt-backed cleanup without prompting.

The command uses `.owlbear/install-manifest.json` to distinguish surfaces created by setup from
files that existed before it ran. A receipt-owned file is removed only when its installed digest is
unchanged. Receipt-claimed settings and MCP values are removed only when the complete merged file
still matches the post-install digest; later edits, including JSONC comments, preserve the whole
file. Managed ignore rules are removed by recorded line additions, so unrelated rules remain.
Freshly created editor and lint configuration files are removed; pre-existing files remain even
when their content happens to equal the seed. Setup-created empty directories are removed only when
the receipt records them as created.

If the receipt is absent, uninstall takes the conservative path and preserves recognized surfaces;
it refuses to operate in a directory with no receipt or recognizable OwlBear surface. It also
refuses the OwlBear checkout and any descendant of that checkout. A non-interactive call requires
`--yes` or `--dry-run`, and `--yes` and `--dry-run` are valid only with `--uninstall`.

Custom seed files, unrelated VS Code settings and MCP servers, custom ignore rules,
`.owlbear/delivery/config.json`, Delivery records, runtime data, knowledge and memory data, and
user-local VS Code profile settings are preserved. In particular, uninstall does not revert the
global Copilot reasoning settings that interactive setup may have written; those settings are
shared across projects and remain under the user's control. The command does not require a GitHub
repository identity.

**Expected result:** unchanged setup-owned files and claimed settings or MCP entries are removed or
updated, while customized files, unrelated configuration, Delivery state, runtime data, knowledge,
memory, and user-local profile settings remain in place.

MCP memory entries are stored as markdown files under `.owlbear/memory/`. The
`owlbear-memory` server creates that directory when it starts or writes the first
entry, so setup does not seed a separate memory store.

---

## Delivery Workflow

This section is the canonical operator procedure. The
[Delivery MCP reference](../serve/delivery-mcp/README.md) lists the exact public tools and startup
configuration, [WIRING.md](../share/WIRING.md) maps agent authority and loading, and the
[Cockpit package guide](../serve/cockpit/README.md) covers launch and configuration for the human
control surface.

### Specification

Use `/ideate` when a rough idea needs a one-question-at-a-time refinement interview. Use `/design`
to create or resume one durable change. The Designer reads the current owner-computed package
identity, revises the complete authored intent and design through compare-and-swap, checkpoints the
unchanged revision, derives and validates Delivery authority, and asks for explicit approval before
admission. A stale package identity returns to read and reconcile; agents never edit package
internals or reconstruct package identity.

Expected outcome: one approved Specification revision is admitted under the configured target root
with deterministic outcomes, dependencies, commitments, and proof boundaries.

### Delivery

After admission, invoke `/orchestrate`. Before dispatching, Orchestrator revalidates existing running
Planner/Builder/Finalizer claims in its entry scope: `/continue-change` reads only its Change with
`get_change`, while `/orchestrate` lists Changes. It asks once whether each
exact prior run was stopped or closed; only a confirmed stop is released, while `worker-stall-wait`
needs no question. Portfolio cycles then acquire a bounded ordered set of launch packages, dispatch
only the worker named by each package, and forward the worker's transition unchanged. Tasks execute
sequentially in the managed Change worktree and their promoted commits advance the Change branch
directly.

- Planning reads one typed plan context, publishes one independently reviewed task chain, and
  returns `advance`, `retry`, `return`, or `block`.
- Build reads one typed task and exact per-Change custody context, commits only its maintained surfaces, publishes
  one independently reviewed exact-commit result, and returns the same transition set.
- Reviewers return only `pass` or `finding` with source-grounded evidence. They never publish,
  repair, choose transitions, or mutate lifecycle state.

Expected outcome: outcomes move through Planning and Build under one shared execution budget, with
exact per-Change writer custody, without Orchestrator scheduling judgment or conversation-derived authority.

For exact ended invocations, Orchestrator uses the typed `settle_worker_invocation` route for retries,
Builder request pauses/returns and report-backed Finalizer failures. Successful submitted/finalized
results already have their owner receipt and are not transitioned twice.

### Correction And Recovery

Worker transitions keep correction finite and typed:

| Condition | Owner and control | Resume behavior |
| --- | --- | --- |
| Local implementation defect | Builder creates a bounded follow-up commit and requests fresh exact-commit review | Continue the same Build claim only after a fresh pass |
| Planning-stage user decision or action | Planning worker returns `block` with an embedded request; the owner records a durable paused result | Only that paused reservation is settled, without counting it as a failure or erasing earlier failures. Answer the request in Cockpit before work resumes; fresh context carries the structured resolution, and exact result replay does not charge another attempt |
| Requestless condition is satisfied | User clears the block in Cockpit | Engine recomputes eligibility |
| Worker returns `retry` | Settle exact invocation | Preserve work; same task after backoff |
| Planner/Builder no-result | `ended-without-result` after return + settled jobs | Preserve; same task after backoff |
| Issuing VS Code window ended | Recorded PID/start time is gone; no writes for 30 seconds and no live process in the worktree or Git admin directory | Auto `worker-host-lost`; preserve work |
| Write/process guard incomplete | `worker-stall-wait`; retry time for recent writes or process/scan details when unresolved | Yield; no question or replacement |
| Stopped chat with live window | User confirms the exact run stopped; Cockpit "Release stuck worker" or `/release-stuck-worker` | One guarded `worker-released-stuck`; no same-cycle replacement |
| Planning-stage premise failed | Planning worker returns `return` with evidence, target and source boundary | Runtime persists typed successor context; Design reopen is currently manual through `/design` |
| Implementation Builder requests `block` or `return` | Orchestrator settles the exact ended invocation, preserving work and completed results | Genuine request-bearing block settles the pause and gates reacquisition until answered. Planning return permits lineage-preserving replan; Design return supplies complete Designer attention, not automatic revision/admission. Raw unsupervised transitions remain refused |
| Retry episode is exhausted | Responsible agent receives bounded read-only diagnosis with the failure history | Nonterminal blocking prevents automatic redispatch; no fabricated user request, clear-block reset or fresh allowance is offered |
| Finalizer returns `proof-failed` or `review-failed` | Orchestrator binds the exact ended invocation to its stored report | Retain report-backed passive attention without occupying a live execution slot. The report is diagnostic evidence, never proof of successful finalization |
| Failed activation or retained active custody | Readiness exposes `/repair-delivery` for read-only diagnosis | The prompt can explain the retained state; it grants no permission to retry, release custody or start replacement work |
| `recover_claim` requested | Requires supported host exclusion | Timeout/`confirmed_lost` do not release custody |
| Earlier valid stage is required | User selects an invariant-checked backward move in Cockpit | Runtime resets only the selected outcome and its affected successors |
| User pauses a Change | **Pause** in Cockpit (or `set_change_intent` `defer`) is accepted at any time; while a step is running it records a **Pause requested** state | The running step finishes and records its result; no new work starts. The Change then shows **Paused**. **Resume** clears a pending request or restores the prior stage. Pause never stops or releases a worker |

The window-exit row also covers a prior-session Orchestrator restart, reload, or closed window. If the
issuing window process remains alive, only the user can confirm whether its earlier run was stopped;
the Orchestrator asks once at session start and does not infer closure from an MCP-server restart.

Recovery requests and `confirmed_lost` are not proof. A returned Planner/Builder no-result uses
`settle_worker_invocation` only after Orchestrator sees the dispatch return and all owned mutating work
settle. For a previous-session loss, each claim records its issuing VS Code window PID and process
start time. The next acquisition can record engine-only `worker-host-lost` only after that exact
window process is gone, no write has occurred in the last 30 seconds, and no live same-user process
has its cwd or an open file under the managed worktree or Git admin directory. A terminal-attached idle
shell whose only link is its worktree cwd and which has no live child is ignored; open files still block. If the
guard is incomplete, readiness reports `worker-stall-wait`: a `next_eligible_at` means the write
guard is still running; without a time, the prompt reports active process names or bounded scan
detail. Yield without settling or recovering. Restarting the MCP server while the issuing window is
alive does not trigger automatic settlement.

When the user states that a specific worker chat was stopped, use Cockpit's "Release stuck worker"
action or `/release-stuck-worker` with the exact active claim identity. At Orchestrator session start,
ask once about each exact `running` claim; do not ask about `worker-stall-wait`. This is a user
decision, not a process command. Delivery applies the same 30-second no-write and worktree/Git-admin
process guard. If it returns `ERR_DELIVERY_WORKER_ACTIVE`, a retry time means the write guard is
pending; otherwise report the active process or bounded observation details unchanged. Custody and
files remain unchanged. Call the route once; do not retry or dispatch a replacement in the same
cycle. Neither
`worker-host-lost` nor `worker-released-stuck` goes through `settle_worker_invocation`.

Both engine dispositions count as failed attempts in the same three-attempt episode and preserve
worktree bytes, staging, commits, and refs. After backoff, a fresh Builder uses Build context and
`prior_attempts` to triage same-task work; Planner retries under the same budget. Three failures
exhaust the episode. A lost or released Finalizer with no report receives a `worker-ended` report
with code `finalizer-ended-without-report` and `checks_state: unknown`; it is not proof. Fresh
exact-head checks and independent review remain required under the original budget.

A dispatch that has not returned in the current session remains unsettled by Orchestrator unless the
user selects the stopped-worker route above. Time, disconnection, and `confirmed_lost` are not proof
for `settle_worker_invocation` or `recover_claim`; do not suggest Git or process-control commands.
Request answers, requestless unblock, exact recovery requests, backward movement, and retained
Integration attention remain user-owned Cockpit controls. Those controls cannot turn a refused
Builder diagnostic into an actionable request or transition.

Corroborated passive Builder handoff and report-backed Finalizer attention release live execution
capacity while preserving their mutation fences. Claims awaiting write/process-guard eligibility and uncertain
engine actions still occupy slots. Once Delivery records `worker-host-lost` or `worker-released-stuck`,
the claim is released but its failed attempt remains. If active claims occupy every slot, new
Planner/Builder work, finalization, and engine continuation stall across the portfolio. A Change
cannot be abandoned while an active mutation claim remains. Timeout and `confirmed_lost` are not
proof; a stopped-chat release is a user decision guarded by Delivery's 30-second write/process check.

Separately, a proven-no-launch reservation can remain pending while another claim in the same
Change is active. It does not consume an execution slot, but a later attempt contains that
outcome's retry budget without an actionable request or unblock path. Once the other claims end,
the supported exit is abandoning the whole Change; do not reset the reservation manually.

Use `/repair-delivery` for bounded read-only diagnosis when normal Delivery inspection is
unavailable. It is not a repair or custody-release command. If the current working directory is
missing or access is denied, the offline diagnostic returns `ROOT_UNAVAILABLE`, unknown pending
effects and exit status 2 without writes. Unknown pending effects must not be read as no effects.

### Publication, Acceptance, And Completed History

When every outcome is complete and the reviewed source boundary is current, run
`/finalize-change <change-id>` for the exact Change head. Delivery publishes or reconciles a draft
pull request for the Change branch, observes the required checks, and marks the PR ready only when
the finalized head is unchanged. Target synchronization, when required, merges only the configured
remote-tracking target into the managed Change worktree; it never updates the target branch or the
user checkout.

When the PR is ready, mergeable and its required checks pass at the finalized head, and the proof
target equals the current target branch head, Cockpit offers **Approve merge** with the repository,
PR, exact head, target, proof and check summary and merge method. One approval sends one merge-commit
request fenced to that exact head; Delivery never enables auto-merge, uses a merge queue, bypasses
rules or updates the target branch. You can also merge the PR in GitHub yourself. If GitHub never
confirms an approved merge, Cockpit shows the PR link with **Check again**, Pause and Abandon; Delivery
never sends the request again. Engine and provider publication (Change branches, draft PRs, Delivery
state) and an approved merge are system work: agents never run `git push`, `gh pr merge` or provider
mutations directly, and no agent tool approves a merge. After the merge, read-only acceptance
observation requires the exact repository, PR, base, finalized head, merged state, merge time, and
provider-reported merge commit; it never completes from local evidence. Completed history preserves
the finalized Change head and accepted merge commit as separate identities. An open or unmerged PR
waits or is deferred; it cannot complete.

Persisted Integration attention remains visible through the current attention surfaces. Use
Cockpit or `/resolve-delivery-attention <change-id> <attention-id>` to inspect that exact attention.
New Integration repair claims, candidates, reviews, and admissions are not created by the current
workflow. Treat a
merge conflict without a current repair claim as an authority gap; if persisted repair-claim context
supplies exact attempt and claim identities, request recovery only through the exact owner operation
and preserve its evidence. The operation still requires supported host-owned exclusion; the default
provider refuses without it and leaves attention/custody intact. Do not edit the target or worktree
directly. Cockpit and the MCP completed-change tools provide bounded list, search, and exact lookup
of receipt-backed history.

### Current Manual Boundaries

- External Change-head adoption proves provenance only. Explicit promotion is required before an
  adopted head becomes review authority, and finalization binds the exact reviewed head.
- A Planning-stage return to Design persists structured successor context, but reopening and revising
  the Specification currently starts with a manual `/design` invocation.
- Target-sync conflict repair remains in the managed Change worktree; Delivery never mutates the
  configured target ref, and merge-conflict repair production is retired outside that bounded path.
- Files under `.owlbear/research/` are frozen comparison evidence, not operational or runtime
  authority. Completed-history search reads current receipt-backed runtime records only.

```text
/ideate -> /design -> explicit admission -> /orchestrate -> /finalize-change <change-id>
Specification: read/revise -> checkpoint -> derive -> validate -> approve/admit
Delivery: acquire -> plan/build -> publish -> worker transition
Correction: returned end/no-result -> settlement -> same-task retry after backoff
  | request answer gate | Planning/Design return
Recovery: prior-session window exit -> automatic 30-second write/process guard; live-window stopped chat -> one user-directed release
Wait: worker-stall-wait -> yield with retry time or process details
  | exhausted episode -> agent-owned read-only diagnosis
Publication: finalize-change -> checkpoint -> draft PR -> finalized head -> ready PR
Acceptance: user merges PR -> observe merged evidence -> completed lookup
```

## Portability and recovery

Admission is the first remote recovery guarantee. Before admission, authored Design drafts are
local working material and are not committed for every revision. At admission, Delivery places the
verified four-file package on the managed Change branch, then opens the first draft pull request.
The normal remote branch is the package backup; local `refs/owlbear/packages/*` refs are not.

Delivery also publishes sparse semantic snapshots to `owlbear/delivery-state`. These snapshots
retain the admitted contract, frontier progress, publication and finalization identities, and
completion evidence. They exclude active claims, writer custody, locks, capacity ledgers, process
identifiers, absolute paths, and transient model output. A new clone recreates ignored runtime state,
the package cache, and open Change worktrees from those remote identities. The next acquisition
applies the recorded-window and write/process guard to an unsettled prior-session claim rather than
treating its age or missing response as proof of death.

For a new machine, clone the project normally, run setup so `.owlbear/delivery/config.json` names
the configured `delivery_state_branch`, and launch Delivery or Cockpit from the project root. Do
not copy `.git`, hidden OwlBear refs, ignored runtime files, or an old managed worktree. If startup
reports a package, Change-branch, target, or state-snapshot divergence, preserve both sides and
resolve the typed attention before acquiring work.

### Pinned controller releases

The OwlBear development checkout runs Delivery from a pinned, immutable controller release so that
new commits on `dev` never change the running controller. Consumer projects run unpinned by default:
the `uv --project <owlbear clone>` entries that setup writes start the checkout's code, and
[Upgrading OwlBear](#upgrading-owlbear) moves it forward.

Pinning is optional for a consumer project. It keeps Delivery on an installed release while the
OwlBear checkout moves; each release holds a full OwlBear environment of about 1.3 GB. To opt in,
upgrade first so the state is current, stop `owlbear-delivery` and Cockpit, and run from the project
root:

```shell
uv --project ../owlbear run delivery-controller --project-root "$PWD" install HEAD \
  --source ../owlbear --bundle-source ../owlbear/serve/cockpit/dist --pin
```

Then set the `owlbear-delivery` entry in `.vscode/mcp.json` to
`"command": "${workspaceFolder}/.owlbear/controller/bin/delivery-mcp", "args": []` and start Cockpit
with `.owlbear/controller/bin/cockpit`. Rerunning setup keeps your edited entry.

| Path | Content |
| --- | --- |
| `.owlbear/controller/releases/<commit>/` | Read-only `git archive` of the commit, its locked `.venv`, the Cockpit bundle and `RELEASE.json` (commit, supported format, interpreter identity, tree digest) |
| `.owlbear/controller/pin.json` | Pinned release `commit`, its `previous` (rollback) release and the digest of its `RELEASE.json` |
| `.owlbear/controller/bin/delivery-mcp`, `bin/cockpit` | Generated launchers; `.vscode/mcp.json` starts `owlbear-delivery` through `bin/delivery-mcp` |

On a pinned workspace every controller whose code is not the pinned release refuses to start with
`controller-not-pinned` before it reads state, including `uv run cockpit` and
`uv run python -m owlbear_delivery_mcp` from the checkout. Start Cockpit with
`.owlbear/controller/bin/cockpit`. A clone without a release shows `owlbear-delivery` as failed to
start until `uv run delivery-controller install --pin <commit>` installs and pins one.

Release integrity protects against accidental and ordinary-tool changes: editor saves, Git commands
in the wrong directory, interrupted installs, package-manager writes and restores. Install seals
every release file and directory read-only and refuses a release it cannot seal; `pin`, `switch` and
`verify` hash the full content and the interpreter against `RELEASE.json`, refuse a writable entry and
report a modified release. Starts do not re-verify the release. It is not a security boundary
against root or another process running as your user.

Upgrade only through `/upgrade-delivery`, which drives `delivery-controller` and `delivery-migrate`:
install, online preflight, stop, offline `preflight`, `backup`, migration, `switch`, `verify` and
`prune` while both controllers are still stopped, then restart and online verification. `preflight`,
`backup`, `pin`, `switch` and `prune` hold the controller lock
exclusively and refuse while any controller runs. `switch <previous>` rolls back only when that
release's own gate accepts the current state; otherwise restoring the backup is your decision.
`verify` detects a release modified after install. `prune` keeps the current and previous releases.

---

## Cockpit details

Cockpit is the browser UI for target work items, requests, typed attention, recovery controls,
completed history, Memory, Ideas, and read-only historical completion search. Launch it from the project root
so it reads this project's `.owlbear/delivery/config.json`, Delivery state, and `.owlbear/memory/`.

1. Open a terminal in the project directory.

   Expected outcome: `pwd` or `$PWD` points to your project, not the owlbear clone.

2. Start Cockpit using the sibling owlbear installation.

   macOS / Linux:

   ```shell
   uv run --project ../owlbear cockpit
   ```

    Expected outcome: Cockpit opens `http://127.0.0.1:8420` and shows this project's
    target workspace. Use `COCKPIT_NO_OPEN=1` to suppress browser auto-open.

3. If your owlbear clone is not a sibling directory, replace `../owlbear` with the path
   to the clone.

    Expected outcome: uv resolves the `cockpit` command from owlbear while Cockpit keeps
    the current project directory as its runtime working directory. If you run the command
    from somewhere else, add `--directory /path/to/project`.

---

## Project-Specific Customization

### Adding local agents

Place `.agent.md` files anywhere in your project (e.g., `.owlbear/agents/`). VS Code loads
agents from all configured locations simultaneously — both owlbear agents and your project
agents will appear in the agent picker.

**Important:** Use unique names for your project agents. VS Code does not deduplicate
same-name agents from different locations — if you create `reviewer.agent.md` locally,
both your version and the owlbear version will appear, which is confusing. Prefer names
like `my-project-reviewer.agent.md`.

To register your local agent directory, add to `.vscode/settings.json`:

```json
{
  "chat.agentFilesLocations": {
    "../owlbear/share/agents": true,
    ".owlbear/agents": true
  }
}
```

### Overriding instructions

Edit `.github/copilot-instructions.md` to add project-specific rules. This file is
auto-detected by VS Code and takes priority over repository-level instructions. You can
also add a `*.instructions.md` file in your project and register its directory in
`chat.instructionsFilesLocations`.

### Adding project-specific MCP servers

Edit `.vscode/mcp.json` to add additional servers alongside the owlbear defaults:

```json
{
  "servers": {
    "owlbear-delivery": { ... },
    "myProjectServer": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "-m", "my_project_mcp_server"]
    }
  }
}
```

> Note: `mcp.json` is merged on subsequent `init.py` runs — owlbear servers are written
> as defaults and your existing entries are preserved. Edit it manually to add new server
> entries or customize existing ones.

### Knowledge MCP storage

The `owlbear-knowledge` server stores its SQLite database and vectors under
`.owlbear/knowledge/` in the current workspace. Launch it from the project root; it has no storage
override or tool-exclusion environment settings.

---

When something does not behave as described here, use
[Troubleshooting](setup-guide.md#troubleshooting) in the setup guide.
