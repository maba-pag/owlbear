# Watcher Agent: Design Draft

> **Owning task:** Delivery rebuild, phase 3 "N1 design" ([rebuild §3.12](delivery-liveness-first-rebuild.md))
> **Date:** 2026-10-14
> **Question:** How should the watcher read, judge, stop and summarise running steps in both runtimes,
> within the decided rules? This is a draft for the owner's design session. It builds on the
> [options research](delivery-next-watcher-options.md) and decides nothing.

## 1. Context and Question

The decided requirements are listed in the options research §1. Since then:

- TD-55 decided the watcher's stance: it intervenes after an action and prevents nothing. It judges
  actions, not reasoning. It stops an outgoing transfer of local data it notices, and it is
  multi-purpose, for example summarising status for Cockpit.
- TD-61 and TD-66 asked for per-agent stages, which the watcher infers.
- TD-69 narrowed what a window step can do. Each agent now has only its own tools, and windows no
  longer offer `ask_user` or the owner's MCP tools (P25). What remains for the watcher in windows:
  - shell and file tools writing outside the worktree;
  - commands that send local data out.

  SDK steps keep the hard guard (TD-45), which denies such calls before they run.

## 2. Sources Studied

| # | Source | Fact used | Limit |
| --- | --- | --- | --- |
| S1 | [Options research](delivery-next-watcher-options.md) | Requirements, G-b "observe and stop" (TD-55), placement options P-a to P-c, claude-mem's transcript-tailing idea (L9) | — |
| S2 | Live feed checks, 2026-10-14: `.owlbear/scratch/ahp/watch/live_feed.py`, throwaway repos, builder steps, `gpt-6-luna` `low`; three window runs, two SDK runs (runtime research P26) | The host's session record `~/.copilot/session-state/<id>/events.jsonl` held every tool call with full arguments in both runtimes. That covered shell calls, two parallel shell calls, `apply_patch` (its argument is the raw patch, with target paths in `*** Add File:` style headers), and a subagent's own calls, marked with `parentToolCallId`. Each line was readable 0.03 to 0.21 s after its own timestamp, polling every 50 ms. A shell call's line was readable 2.9 s before its command's write (the command slept 3 s) | About 35 events, one model. The delay includes the poll. A write in the first milliseconds of a command is seen after the fact, as TD-55 accepts |
| S3 | [Runtime research](delivery-next-agent-runtime.md) P21, P25 | SDK sessions write the same record family. P21: a window subagent's messages and usage are in the parent's record. P25: tool names in both runtimes | Subagent tool calls in the record not checked separately |
| S4 | `vscode_step.py` `_observe` (lines 378-400), `_steer`, `_cancel` (worktree `next/m4-slice1`, `a068a6cf7`) | The window route sees tool names on `chat/toolCallStart`, and inputs only on unconfirmed `chat/toolCallReady` (cut to 2,000 characters). Under auto-approve (D2) most inputs never pass through it. It steers with `chat/pendingMessageSet` and cancels with `chat/turnCancelled`, with acknowledgement | — |
| S5 | `sdk_adapter.py` `_Step.on_event`, `permission`; `permissions.py`, `confinement.py` | The SDK gets the same runtime events live. The guard classifies shell words, paths and URLs with `inside`, `outside`, `resolve` and `_reach`. No TD-46 allowed-outside list exists | — |
| S6 | `budgets.py`, `held.py`, `store.py` (`now`, `log`), `status.py` (`stage`) | The retry and ask patterns, the gate question with options, the "now" line `{tool, summary, at}`, and the activity log. Cockpit shows "Build 3/5" from the plan position | — |

## 3. Analysis

### 3.1 Feed: the runtime's session record, for both runtimes

| Option | Inputs available | Same shape in both runtimes | Survives a runner restart |
| --- | --- | --- | --- |
| F-a Each route's live stream (SDK `on_event`, window AHP actions) | SDK: full. Window: names, plus inputs only for unconfirmed calls (S4) | No | No |
| F-b Tail the host's session record (S2) | Full arguments for every call, subagents included (S3) | Yes, the same harness writes both | Yes, with a stored read offset |

Proposal: **F-b** for the watcher in both runtimes, conditional on the checks below. It is one reader
with one event shape. The routes keep their streams for their own gates. This revises the options
research §3.1, which put live streams first; S2 shows only that the record can carry what F-a lacks in
windows. It is claude-mem's transcript-tailing pattern (S1, L9), rebuilt in a few lines.

Conditions before F-b is relied on, measured in S2 within its limits:
- complete records in both runtimes for file tools, parallel calls and subagents' tool calls: met
  for shell, `apply_patch`, parallel shell calls and a foreground subagent. Background subagents
  are not yet checked;
- the delay from a call's start to its readable line: 0.03 to 0.21 s over about 35 events, polling
  included.

The reader must:
- bind the exact record of the step's session, whose identity is stored before work starts (§3.3);
- keep incomplete last lines for the next read, and detect a record that is truncated or replaced;
- report its own failure.

The record is the runtime's internal format. A schema test on recorded fixtures guards it. A feed
failure stops a window step with an operational cause, which never counts as a watcher stop; its
retries are bounded like other environment failures.

Confidence: medium-high for the feed; one model, background subagents unchecked.

### 3.2 Judging: rules first, a model for the rest

Each `tool.execution_start` is classified by its **write targets**, not by every path it reaches.
Reading outside the worktree is not controlled in windows: TD-50 changes only how outside writes are
controlled. So `cp /elsewhere/input ./out` and `git -C /elsewhere log` pass.

| Class | Examples | Verdict |
| --- | --- | --- |
| Writes inside this Change's worktree | edits; shell commands whose write targets resolve inside it | Pass |
| Git in this Change's worktree | `git add`, `commit`, `stash` run there. A linked worktree writes into the main clone's `.git/worktrees/<name>`, objects and its own branch, which the command alone does not show | Pass |
| Allowed outside (TD-46) | temporary folders (`/tmp`, the expanded `$TMPDIR`, `/private/var/folders`); the user's tool caches (`~/.cache`, `~/Library/Caches`, uv, npm, pip, Playwright); this Change's own Delivery state; paths the brief names | Pass, logged |
| Unwanted outside writes | a write, redirect, `cp`/`mv` destination, `rm` or editor call on any other path: the main checkout, other worktrees and their `.git` administration, other Changes' state and documents, unrelated refs or Git config | Stop |
| Noticed transfer of local data (TD-55) | an upload whose payload is a local file or data and whose destination is not local: `curl -T`, `-F @file`, `--data-binary @file`; `scp` or `rsync` with a local source and a remote destination. Also any `git push` by an agent, since only Delivery publishes | Stop |
| Unknown | inline interpreter code (`python -c`, `node -e`), scripts, shell forms the parser does not follow (subshells, `;` chains with `cd`, command-specific working directories) | Model judgement |

- Downloads and ordinary network use pass. Catching exfiltration in general is not a goal (TD-55).
- Precedence: protection of other Changes' worktrees, state and documents wins over a broad allowed
  root. A worktree or state folder under `/tmp` is still another Change's.
- Paths are canonicalised: `~` and `$TMPDIR` expanded, symlinks resolved for the allowed roots and
  for the targets. Relative targets resolve against the command's working directory as far as the
  parser follows it. Anything further is "unknown", never pass or stop by guess.
- The rules reuse the guard's helpers (S5) under a separate window policy. The SDK guard itself
  stays unchanged, since it also denies outside reads.
- Reasoning never stops a step (TD-55). An assistant message may only mark the next calls for model
  judgement.
- **Before N2** (TD-47): D5 requires judgement for unknown calls, and §3.12 places N2 before the
  model-backed build. So a rules-only watcher can be built, but switching it on before N2 changes the
  interim (TD-44, TD-50: window steps unguarded until the watcher exists). That is the owner's call
  (O2).
- The brief has no field for outside paths today. The design adds `Brief.outside`, a short list of
  canonical paths approved with the brief (TD-46 "unless the brief names it").

Confidence: high for the classes; the parser's coverage and the model's share are open until
measured.

### 3.3 Stop and D6 retry

- **Identity first.** Before work starts, the runner stores the step's attempt: host, session, chat
  and the turns it owns, plus the record to read. Today the window session is logged only after
  the run (`vscode_adapter.py:154`). Each concurrent step has its own watcher state.
- **Stop.** A stop latches the attempt:
  - queued steering and reminders are suppressed;
  - the owned turns and subagents are cancelled;
  - the attempt's processes are confirmed gone.

  A cancel acknowledgement covers only the named turn (`vscode_step.py:256`), and the leftover scan
  finds processes by worktree. So unconfirmed termination blocks the retry and goes to the owner. The
  shared editor host and the owner's own turns are never touched.
- **The SDK route.** The guard denies outside writes and URL-reaching shell calls before they run
  (TD-45). The watcher still reads SDK steps and keeps its steer and stop there for what the guard
  lets through, for example a transfer from an allowed command's script. TD-50 holds, because the
  stop applies the same rules in both runtimes.
- **Result.** A stop overrides an already submitted result. It clears the accepted payload, refuses
  later results, and is never offered for "accept" (TD-56). The cause is `watcher-stop`. The class,
  target and evidence go in the detail. The detail reports "observed a command writing to X": a
  start event proves the call, not the write. A confirmed effect is named only with completion
  evidence or a check of X.
- **D6 count.** The step keeps one persistent watcher-stop count, across replacement sessions and
  runner restarts, independent of the target. Today's budgets count per cause signature
  (`budgets.py:256`). The first stop retries once. The next session's first message gives the
  reason: "Your previous attempt was stopped: it ran a command writing to X outside the worktree.
  Stay inside the worktree, or report that you need X."
- **Second stop** asks the owner, with the gate-question pattern (S6):
  - add the path to the brief's `outside` list. This makes a new brief version, approved by that
    answer (TD-46: the brief names it);
  - run again with the reason;
  - stop the Change.
- **Writes already made** stay in place and are named in the question. The watcher does not undo
  them.
- **Steering.** One use only, proposed: when the model judges a call doubtful but not a stop, the
  watcher sends one steering message restating the boundary. P8 showed window steering as the next
  turn; SDK `immediate` steering is unproven. Both need proof, including a steering message queued
  when a stop cancels the turn.
- **Runner restart.** A window turn runs unwatched while the runner is down (S1, L4). On start, the
  runner recovers only attempts it durably identified, under the owning Change's lock. Ambiguous
  ownership keeps today's busy refusal (`_busy`). It never sweeps all window sessions.

Confidence: high for the result and count machinery (TD-54, deadlines); medium for stopping
everything an attempt started.

### 3.4 Stages and status (TD-61, TD-66)

The watcher infers stages from the same feed, per role. Stages may overlap and may be uncertain, for
example with background subagents:

| Stage | Evidence |
| --- | --- |
| Preparation | session start: preloaded skills, `recall_memory`, reading the task |
| Working | the first edit or non-reading shell call (builder); the first diff read (reviewer); the first plan draft (planner) |
| Challenge #n | a subagent whose stated role or purpose is a challenge or review, from its start to its end. Delivery's own in-step challengers (plan challenge, brief review) are separate sessions: their engine metadata is evidence the watcher uses, not a replacement for inference (TD-66) |
| Fixing #n | work tools after challenge #n ends, while no other challenge runs |
| Finalizing | `git commit`, `save_memory`, `submit_result` |

The "now" line gains `stage` and a confidence. Cockpit shows "Build 3/5 · Fixing #1", marked when
unsure. A short status summary by a cheap model waits for TD-47. Until then the last tool and the
stage are shown.

Confidence: medium. The rules need a check against real records of each role.

### 3.5 Placement

Inside the runner (P-a): one watcher thread per running step, tailing that step's bound record.
Recovery after a runner restart is in §3.3.

### 3.6 Build slices

1. Measurements left: background subagents, and a second model.
2. Feed reader: bound record, offset, partial lines, truncation, reader failure, and a normalised
   event (kind, tool, arguments, parent, time), with the schema test on recorded fixtures.
3. Attempt identity stored before work; per-step watcher state; restart recovery of identified
   attempts.
4. Window policy: write targets, TD-46 classes with precedence, transfer evidence, Git in the owned
   worktree, `Brief.outside`; test-first per class, including symlinks, `cd` chains and other
   Changes' paths.
5. Stop latch, late-stop override, persistent watcher-stop count, the owner question with a brief
   amendment.
6. Stages and the Cockpit field.
7. After N2: model judgement for unknown calls, steering, status summary.

Proof, as in §3.12's row, in a throwaway repository: the watcher reads a running window step and
stops an outside write. The step is retried with its reason, a second stop asks the owner, and one
doubtful call is steered. Also: a stop after `submit_result` voids the result, and an SDK step's
stages appear in Cockpit.

## 4. Recommendation, Confidence, and Limits

Proposals for the owner (all `autonomous` until decided). Sol challenged the first draft; 17
findings are folded in above.

- O1 The watcher reads the host's session record in both runtimes (F-b). Completeness and delay
  passed in S2; background subagents are still to check.
- O2 Switch on a rules-only watcher for window steps before N2, with unknown calls logged and shown?
  Or keep it off until the model judge exists after N2? The first guards window steps sooner. The
  second keeps D5's judgement complete. Either way the interim of TD-44 and TD-50 changes only by
  the owner's choice.
- O3 The second stop can add the path to the brief's `outside` list as a new brief version, approved
  by that answer.
- O4 A feed failure stops a window step with an operational cause that never counts as a watcher
  stop.
- O5 SDK steps keep the guard unchanged. The watcher reads them and can steer and stop there by the
  same rules, for what the guard lets through.
- O6 The brief gains an `outside` list of canonical paths, approved with the brief.

Limits:
- S2 is five Luna runs.
- The record format can change with the runtime.
- A start event proves a call, not its effect.
- Writes faster than the poll are seen after the fact, as TD-55 accepts.
- Shell parsing is never complete; what it cannot follow is "unknown".
