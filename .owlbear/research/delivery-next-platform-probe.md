# Delivery Next: Platform Capability Probe (R8)

> **Owning task:** none — R8 of the [liveness-first rebuild](delivery-liveness-first-rebuild.md)
> **Date:** 2026-10-10
> **Question:** Which Copilot runtime capabilities (SDK, CLI, dynamic workflows, ACP) are proven on
> this machine for a code-run Delivery loop — structured results, questions, resume, termination,
> unattended permissions, agents, skills, MCP, worktree PR flow — and what does one Change cost?
> **Status:** results of a live probe; conclusions `autonomous`

## 1. Context and Question

The rebuild plan (§3.8 Q7, §3.9) defers the loop technology and surface choice to R8. The
[journey research](delivery-next-journey-and-failure-modes.md) needs evidence for rows B7 (tool
approval nobody sees), X1 (closed window or sleep), X4/X5 (restart, two writers) and design rules
DR5 (re-entry by observation), DR7 (durable questions), DR9 (unattended permissions) and DR10
(confirmed termination before replacement). Decisions TD-5, TD-6 and TD-8 authorized this run.

All probes ran on 2026-10-10 in a private sandbox outside the OwlBear repository. Each probe is a
script in the sandbox; raw results are JSON or logs under `probes/out/`.

## 2. Sources Studied

| ID | Source | Relevant fact | Limits |
| --- | --- | --- | --- |
| S01 | Sandbox [boecht/owlbear-sandbox](https://github.com/boecht/owlbear-sandbox) (private), commits `56b05f8`…`0d0dff4` | Probe scripts `probes/sdk/*.py`, `probes/cli/*`, results `probes/out/`, agent, skill, instructions, `.mcp.json`, extension | One macOS laptop, one account |
| S02 | Versions | Copilot CLI 1.0.95; `github-copilot-sdk` 1.0.19 (runtime protocol 3); Node 24.21.0, npm 11.19.0; Python 3.14.8 (uv venv); gh 2.102.0 | SDK runtime download failed behind the corporate TLS proxy; the SDK drove the installed CLI via `RuntimeConnection.for_stdio(path=…)` |
| S03 | [Python SDK README](https://github.com/github/copilot-sdk/blob/main/python/README.md) | Structured output is **experimental**; permission handler, `ask_user` via `on_user_input_request`, hooks, resume | Docs snapshot for CLI 1.0.94 |
| S04 | SDK docs: [custom agents](https://github.com/github/copilot-sdk/blob/main/docs/features/custom-agents.md), [session persistence](https://github.com/github/copilot-sdk/blob/main/docs/features/session-persistence.md), [usage and billing](https://github.com/github/copilot-sdk/blob/main/docs/features/usage-and-billing.md), [backend services](https://github.com/github/copilot-sdk/blob/main/docs/setup/backend-services.md) | Per-agent `model`; "no built-in session locking"; `totalNanoAiu` cost; headless runtime over TCP | Docs, checked against probes |
| S05 | Bundled `copilot-sdk/docs/workflows.md` in the CLI 1.0.95 cache | Workflow API is experimental, JavaScript extensions only; `ctx.step` journal, `ctx.pause`, limits; execution needs "eligible credentials" | Local copy kept in `probes/notes/` |
| S06 | [Dynamic workflows concept](https://docs.github.com/copilot/concepts/agents/dynamic-workflows), [how-to](https://docs.github.com/copilot/how-tos/use-copilot-agents/use-dynamic-workflows) | Public preview; CLI, app and SDK; `copilot workflow run` shows no approval prompts | Not VS Code |
| S07 | [ACP server reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/acp-server) | `copilot --acp --stdio`; public preview | — |
| S08 | `copilot help permissions|limits|environment|billing`, `copilot mcp --help` | Allow/deny syntax, deny wins; soft credit caps; `COPILOT_ALLOW_ALL=true` trusts the directory; workspace `.mcp.json` | CLI text |
| S09 | [Rebuild plan](delivery-liveness-first-rebuild.md) §3.8–§3.9; [journey research](delivery-next-journey-and-failure-modes.md) | Probe list, decisions, rows and design rules | — |

## 3. Analysis

### 3.1 Environment findings that bound every result

- **Billing identity.** The CLI and the SDK authenticate with the `gh` credential of `boecht`
  (`authType: gh-cli`). Its quota is Copilot Free (chat 200, completions 2,000, premium 0). Every
  probe therefore ran on the user's personal free account, not on the employer seat named in TD-5.
- **Models.** Only `auto` works. `--model` with any id (`gpt-6-luna`, `gpt-5-mini`,
  `claude-haiku-4.5`, …) fails with "not available", although the fetched catalog lists 52 models
  and marks several as policy-enabled. Auto routed to `gpt-6-luna` and `mai-code-1.1-flash`.
- **Branch protection.** Rulesets and classic branch protection both returned HTTP 403 ("Upgrade
  to GitHub Pro or make this repository public"). The repository stayed private and unprotected.
- **Side effect not ours.** A Renovate app on the account opened PR #1 in the sandbox unprompted.

### 3.2 Results

| # | Probe | Verdict | Evidence (S01) | Design implication |
| --- | --- | --- | --- | --- |
| 1 | SDK custom agent, schema-validated result | pass | `p1_structured.py`: pre-selected read-only agent; `send_and_wait_typed` returned a validated Pydantic object in 11.8 s | Workers can return typed exits; the loop still validates and retries on failure, because the feature is experimental |
| 2 | Question round trip; durable question | pass in-process; **fail** across processes | `p2a`: handler answered, reply `CHOSEN=blue`. `p2b`: driver killed while a question was open → runtime answered "The user was unable to respond due to an error" and the model continued; pending-input RPC from a new process returned `success=False`. `p2d`: answer sent as a new message after resume → task finished (`DONE=blue`) | Questions must be durable in the loop, not in the runtime. Unattended workers get no `ask_user`; they return an `ask` exit |
| 3 | Kill driver mid-task, resume | pass | SDK: SIGKILL 5 s into a 6-step loop; runtime and shell died (1 of 6 files); transcript kept; `resume_session` did not continue by itself; a "continue" message finished all 6. CLI: killing the `copilot` launcher left the native runtime running; it finished the turn alone; `--resume` then saw a completed transcript | Re-entry by observation (DR5) is needed and works. A killed launcher is not a stopped writer |
| 3c | Second driver on the same session | partial | `p3c`: `check_in_use` reports the session from a separate runtime process and clears on disconnect; within one runtime it reports nothing and a second resume succeeds (`already_in_use=False`) | The runtime gives a signal, not exclusion; DR10 needs Delivery's own per-Change lock |
| 4 | Termination of started commands | partial | `p4`: `abort()` stopped nothing; disconnect killed the attached background shell; a `detach: true` shell survived client stop with parent PID 1. `tasks.list` reported both with PID, mode and status. `p4b`: `tasks.cancel` on the detached task → `cancelled=True`, PID gone, status `CANCELLED`. `session.idle` never fired while background shells ran | Confirm termination by cancel + PID check from `tasks.list`; record PIDs while the runtime is alive; never wait on idle alone |
| 5 | Unattended permissions | pass | CLI with allow `shell(git:*)`, `shell(npm:*)`, deny `shell(rm:*)`, no allow-all: git and npm ran, `rm` denied by rule, unlisted `touch` denied ("no interactive user response"), exit in 15 s. SDK handler: same decisions. SDK with no handler: every request denied at once, no pending wait | B7 cannot hang headless; denials reach the model as tool errors. The loop owns the policy and shows denials |
| 6 | Custom agents, subagents, model selection | partial | CLI `--agent scout` from `.github/agents/` ran (marker present) but its frontmatter `model` was silently replaced by auto. SDK subagents ran with `subagent.*` events naming the requested models, while billing shows only auto models | Agents and subagent dispatch work; model choice unproven on this identity. Trust billed usage, not subagent events |
| 7 | Repository skills and instructions | pass | `/release-note clamp` ran the repository skill with its argument; `.github/copilot-instructions.md` fact recalled without tools; both listed by `copilot skill list` / `instruction list`. A formatting rule in the instructions was ignored | E1 targets (`.github/skills`, `.github/agents`, instructions) load in CLI sessions; SDK sessions emit `session.skills_loaded`, skill use there untested. Instructions guide; they do not enforce |
| 8 | Workspace MCP server `cwd` in a worktree | pass (with trust) | `p8`: `.mcp.json` ignored in an untrusted folder; with `COPILOT_ALLOW_ALL=true` the server ran with `cwd` = session directory (main checkout or linked worktree, also via `-C`), relative args resolved in the worktree; `PWD` was inherited from the launching shell | A worktree session binds its own MCP server; servers must use `cwd`, not `PWD`; folder trust is a setup step per worktree path |
| 9 | Worktree edit → test → commit → push → PR → CI | pass | `p9`: scoped permissions only; agent failed `npm test` three times (no root package, missing `node_modules`), ran `npm ci`, passed, committed, pushed, opened [PR #2](https://github.com/boecht/owlbear-sandbox/pull/2); `gh pr checks` → `test` pass in 12 s. 53 s total | Missing dependencies in a fresh worktree are fixed inside the agent task (P4). Protection-gated merge untested (403) |
| 10 | Dynamic workflows | partial | CLI `--experimental` + `.github/extensions/r8-echo/extension.mjs`: `workflow run r8-echo` completed (journaled step, schema result) in 4.8 s. `r8-pause` paused; state in the session's SQLite store; resume from a new process needed the owning session, an agent turn and `--allow-all-tools` (scoped allow of `run_dynamic_workflow` was still denied); journal reused, run completed. Python SDK session: "Extensions not available" | Usable from scripts, not as the core loop: experimental, JavaScript-only, session-owned runs, unattended resume needs blanket permission |
| 11 | Cost | measured | See §3.4 | One Change ≈ 25 credits on the Auto price class; ≈ 500 on Sol/Sonnet-5.5 class |
| 12 | ACP server | pass (preview) | `p12_acp.py`: `initialize` → protocol 1, `loadSession`, session `list`/`close`, agent "Copilot 1.0.95"; `session/new` returned modes. Launcher terminated; its native child exited moments later | A third-party front-end remains possible over ACP; no need now |
| — | VS Code Agents window, agent merge, quota exhaustion | untested | Docs: Agent Host sessions survive window close; agent merge handles feedback, checks and conflicts (preview); CLI credit limits are soft and block the next model call; the SDK exposes a pending "session limits exhausted" request | Prove in M4 with the employer seat and the VS Code harness |

### 3.3 Notes per probe

1. **Structured result.** One schema covered nested objects and a `Literal` enum. The agent made
   three read requests; the read-only handler approved them and would have rejected writes.
2. **Questions.** The runtime binds an open question to the connection that registered the
   handler. When that connection dies, the question is answered with an error string and the turn
   goes on. This is worse than a hang: the worker may act without the answer. Sending the stored
   answer as a new message after resume continued the original task correctly.
3. **Resume.** The SDK persists the transcript to `~/.copilot/session-state/<id>/`; an in-flight
   tool call stays open (start without completion). Resume restores context but never re-runs the
   turn. The CLI case shows the opposite risk: the native runtime outlived its killed launcher and
   kept writing.
4. **Termination.** Three runtime levels behave differently: `abort()` ends the model turn only;
   disconnect ends attached shells; detached shells outlive the runtime. `tasks.list` plus
   `tasks.cancel` plus a PID check gives positive confirmation while the runtime lives. After a
   runtime crash only PIDs recorded earlier can be checked.
5. **Permissions.** Deny rules beat allow rules. Unlisted requests are denied in non-interactive
   mode. The log reports enterprise bypass policy as "fail-closed: policy could not be determined",
   yet `--allow-all-tools` still worked; enterprise policy can change this.
6. **Models.** The free identity explains the restriction only partly; the catalog marks some
   models policy-enabled. The silent fallback for agent frontmatter is the risk to design around.
7. **Skills.** Skills loaded without folder trust; workspace MCP servers did not.
8. **MCP cwd.** The SDK persistence guide says provider-backed folder trust covers descendants,
   not linked worktrees at other paths. P8 is consistent: plan one trust grant per worktree path.
9. **PR flow.** The agent added a `Co-authored-by: Copilot` trailer itself.
10. **Dynamic workflows.** The workflow store is a per-session SQLite file with runs, journal,
    phases, agents and credit charges. There is no `copilot workflow resume` command.
12. **ACP.** Only handshake and session creation were tested; no prompt was sent.

### 3.4 Cost (probe 11)

One AI credit equals 10⁹ nano-AIU (CLI `--usage-output-file` and SDK `usage.get_metrics` agree).
Measured on the Auto price class:

| Probe | Credits | Probe | Credits |
| --- | --- | --- | --- |
| P1 typed agent result | 0.095 | P5 CLI / SDK handler / SDK none | 0.27 / 0.15 / 0.16 |
| P2a question | 0.245 | P6 CLI agent / SDK subagents | 0.18 / 0.28 |
| P2 durable (both phases) | 0.49 | P7 skill | 0.31 |
| P3 SDK resume (total) | 0.35 | P9 edit, test, commit, PR | 0.46 |
| P3 CLI resume (second run) | 0.35 | P10 workflow run / three resume attempts | 0.29 / 1.15 |
| P4 / P4b termination | 0.14 / 0.24 | P12 ACP | 0 |

Logged total ≈ 5.4 credits; with unlogged short runs ≈ 7. Catalog prices per million tokens
(input / cached read / output): `gpt-6-luna` 10 / 1 / 50; `mai-code-1.1-flash` 20 / 2 / 120;
`gpt-6-sol` and `claude-sonnet-5.5` 200 / 10–20 / 1,000; `claude-opus-5.5` 400 / 20 / 2,000;
`gpt-6-astra` 1,000 / 100 / 5,000. P9's 0.46 credits match these prices exactly.

**Estimate for one Change** (brief, plan, five tasks each built and reviewed, finalization, PR).
Assumptions: a real repository needs about 5× P9's 192k tokens per build task (≈ 1M tokens,
mostly cached reads, ≈ 100k cache writes, 10k output ≈ 2.8 credits); a review about half
(≈ 1.4); plan ≈ 2; brief ≈ 0.5; finalization and PR ≈ 1.5. Total ≈ 25 credits on the Auto class
(range 10–50). The same token profile costs ≈ 20× on Sol/Sonnet-5.5 (≈ 500), ≈ 40× on Opus-5.5
(≈ 1,000) and ≈ 100× on Astra. Model choice dominates cost; the loop should set it per step.

## 4. Recommendation, Confidence, and Limits

**Loop.** Run Delivery's loop as a small Python program on the Copilot SDK. Each building block it
needs ran in this probe — typed worker results (P1), agent pre-selection and read-only tool lists
(P1, P6), a permission policy in code (P5), resume after a killed driver (P3), runtime task
listing and cancellation (P4b), usage metrics per session (P11), repository skills and
instructions (P7) — but not their combination on a real journey. Do not build the core on dynamic workflows: they are experimental, JavaScript-only, not
loadable in Python SDK sessions, owned by one session, and unattended resume needed
`--allow-all-tools` (P10). They stay an option for parallel reviews inside one step. An
Orchestrator agent in the VS Code harness would put the loop back into model prose (RC2); keep the
harness as an interactive surface.

**Questions (DR7).** Unattended workers run without `ask_user` (no handler, or `--no-ask-user`)
and end with a typed `ask` exit. The loop stores the question with the Change, shows it in the
status view, and on answer resumes the session and sends the answer as a message (P2d). Never
rely on a runtime-held question; a lost driver turns it into "unable to respond" and the worker
continues (P2b). P2d proves only that a stored answer, sent as a message, continues a resumed
session. The answer surface (Q9) and the component that starts a runner when an answer arrives or
VS Code reopens are not yet defined; today's Cockpit answer control records an answer but
dispatches nothing.

**Permissions (DR9, B7).** Each step type gets an explicit allow list and a handler that denies
everything else and records the denial for the status line. Never use allow-all in Delivery
steps. P8 ran with `COPILOT_ALLOW_ALL=true`, so loading workspace MCP servers under default-deny
with folder trust is unproven; prefer one trusted worktree root set at setup, or servers configured
explicitly in the SDK session, over a grant per worktree.

**Termination (DR10, X5).** Delivery keeps its own per-Change writer lock; `check_in_use` is an
extra signal only (P3c). Before a writer counts as ended, the loop reads `tasks.list`, cancels
every task, checks each PID is gone, then disconnects and checks the runtime process (not the
`copilot` launcher) has exited. The loop records task PIDs from tool events as they appear, and a
pre-tool hook should forbid detached shells in Delivery steps (hook enforcement untested). If a
PID cannot be checked, the step stops and names it. A valid result does not mean the writer has
ended. The SDK's typed-result helper (`send_and_wait_typed`, SDK 1.0.19) itself completes on
`session.idle`, which never fires while background shells run (P4). Use a result tool or event as
the step boundary, then tear down as above.

**Journey rows and design rules.**

| Row / rule | Status after R8 | Basis |
| --- | --- | --- |
| B7 unattended approval | proven prevented | P5: scoped rules and handler, no hang, denials visible |
| X1 closed window or sleep | partly proven | P3: work survives as transcript and files; nothing continues by itself (SDK) or something continues unseen (CLI launcher kill); Agent Host behavior untested |
| X4 tool server restart | partly proven | P3: shutdown recorded, transcript recovery documented; restart during a write not tested |
| X5 two windows on one Change | partly proven | P3c: cross-process in-use signal exists; no exclusion within one runtime |
| DR5 re-entry by observation | partly proven | P3: resume plus a "check and finish" turn completed correctly; observation logic is Delivery's to build |
| DR7 durable questions | loop-owned pattern proposed; answer surface and runner activation unproven | P2b–P2d |
| DR9 unattended permissions | proven | P5 |
| DR10 confirmed termination | partly proven | P4b proves cancel-and-verify while the runtime lives; P3 CLI and P4 show orphans otherwise |

**Before M3 commits.** Re-run probes 1, 6, 9 and 11 under the employer seat with explicit models
(sign in with that account or pass `github_token` per session). Prove branch-protection merge in a
public or organization sandbox (TD-6 allows `maba-pag`). Probe the VS Code Agents window with an
SDK-created session to settle Q9.

**Confidence.** High for probes 1, 3, 4, 5, 7, 8, 9 and 12 on this setup: each ran end to end
with recorded output. Medium for 2 and 10: mechanisms are clear, but versions change monthly.
Low for 6 and 11: models were restricted and the Change estimate scales one small task.

**Limits.** One macOS laptop behind a TLS-intercepting proxy, a free personal identity, Auto
models only, a two-function repository, CLI 1.0.95 and SDK 1.0.19. External sources were not added
to `.owlbear/sources/overview.md` because this run was limited to one OwlBear file. PR #2 stays
open in the sandbox; probe sessions remain in `~/.copilot/session-state`; all started processes
were stopped and both probe worktrees removed.
