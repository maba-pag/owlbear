# Watcher Agent: Design Options and Reusable Implementations

> **Owning task:** Delivery rebuild, phase 3 "N1 design" ([rebuild §3.12](delivery-liveness-first-rebuild.md))
> **Date:** 2026-10-12
> **Question:** Which designs can satisfy the decided watcher requirements, what can be reused from
> Delivery's own code and from claude-mem, and what must be decided with the owner? Nothing here is
> decided; it prepares the owner's design session.

## 1. Context and Question

The watcher is first-release scope (TD-20) and carries several decided roles:

| Requirement | Source |
| --- | --- |
| Read, steer and stop every runtime in use (`sdk` and `window`) | TD-34 read-back, §3.12 phase 3 |
| Window tool approval: auto-approve on; sandbox only if it limits nothing needed | D2 ([runtime research](delivery-next-agent-runtime.md)) |
| Autopilot for every role except those that ask the owner through the question tool | D4 |
| Sandbox off, no hook: the watcher judges whether an action outside the repository is malicious or permissible | D5, N1 |
| The watcher stops the chat when an agent writes outside the worktree maliciously or unwantedly (including other Changes' documents); it does not block intended, allowed outside actions | D6 |
| Allowed outside writes: Delivery's state, temporary files, the user's tool caches, paths the brief names | TD-46 |
| A stopped step is retried once with the reason, a second stop asks the owner | D6, N9 |
| The SDK route keeps its own hard guard permanently | TD-45 |
| Watching changes only how outside writes are controlled; everything else stays the same | TD-50 |
| Until it exists, SDK steps run and their logs are read afterwards | TD-44 |
| Model and effort chosen after the N2 benchmark | TD-47 |
| Proof: it reads a running step, steers it once, stops an unwanted outside write, the step is retried once with its reason, a second stop asks the owner | §3.12 phase 3 build row |

The design session must settle: what the watcher reads, how it steers and stops, which outside actions it
allows, D6's retry, and its model (after N2).

## 2. Sources Studied

| # | Source | Fact used | Limit |
| --- | --- | --- | --- |
| L1 | [Runtime research](delivery-next-agent-runtime.md) P8 | AHP session created by Delivery, `isolation: folder`, `autoApprove: default`, **no window tools**: a shell call waited for Delivery's decision; Delivery denied it; the file was not created. A steering message sent during a turn ran as the next turn and was obeyed | One run per check; window-client tools not covered |
| L2 | Same, P10 | With `autoApprove: autoApprove`, `permissions.deny` did not stop shell calls; files were written inside and outside the repo. `sandboxEnabled: on` blocked the outside write | One run per case; write timing against observer events not measured |
| L3 | Same, P6, P11 | P6: in a window session without session auto-approve, the first window tool hung and was denied. P11, sandbox on: `curl` to localhost and an outside write asked for confirmation, Delivery denied both, nothing was written; but `uv` and the stdio MCP server failed. Sandbox off: the outside write went through without asking. Delivery's stop ended a `sleep 120` process | One window, one run per check |
| L4 | `serve/delivery-next/src/owlbear_delivery_next/vscode_step.py` (worktree `next/m4-slice1`, `9f43c9ace`) | `_observe` records tool names (`chat/toolCallStart`) and usage; only for unconfirmed `chat/toolCallReady` calls it builds a `ToolCall` (input cut to 2,000 characters) and answers through `approve` → `_confirm`. `_steer` sends `chat/pendingMessageSet` steering. Closing the runner's connection does not by itself cancel the host turn | Not yet a full watcher feed |
| L5 | `sdk_adapter.py`, `permissions.py` (same worktree) | SDK route: `on_permission_request` → `permissions.decide` (the TD-45 hard guard): denies reads and writes outside the worktree, shell calls that reach URLs, commands outside the step's allow list, unknown tools. No TD-46 exception list. `on_event` sees tool starts, messages, usage and subagent events | — |
| L6 | Installed SDK `copilot/session.py`; [platform probe](delivery-next-platform-probe.md) row 4 | `session.send(..., mode="immediate"|"enqueue")` and `session.abort()` exist. Probe: `abort()` stopped no process; task cancel plus a PID check did | `immediate` mid-turn not probed |
| L7 | [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) README, v13.36.0, fetched 2026-10-12 | Apache-2.0. Five lifecycle hooks; observations compressed by a model; SQLite + FTS5, optional Chroma; context injected at session start; 3-layer "progressive disclosure" search (`search` → `timeline` → `get_observations`). For hosts without hooks: "we watch the chat log files" | README only |
| L8 | [claude-mem architecture overview](https://docs.claude-mem.ai/architecture/overview) | Pipeline `hook → SQLite → worker → model → SQLite → next session's context hook`; worker is a Bun/Express HTTP service on a per-user port; compression via the Claude Agent SDK, Gemini or OpenRouter | Docs, not code |
| L9 | [`transcript-watch.example.json`](https://raw.githubusercontent.com/thedotmack/claude-mem/main/transcript-watch.example.json), [adapters.md](https://raw.githubusercontent.com/thedotmack/claude-mem/main/docs/adapters.md) | Declarative JSONL schema maps transcript lines (`session_context`, `tool_use`, `tool_result`, `session_end`) to events; watches `~/.codex/sessions/**/*.jsonl`, keeps a read offset in a state file; adapters normalise to one REST event shape | Schemas shipped for Codex and DeepSeek Harness only |
| L10 | [Platform integration guide](https://docs.claude-mem.ai/platform-integration.md) | REST API (`/api/sessions/observations`, `/api/context/inject`, `/api/search`); full harness table lists Claude Code, Codex, Cursor, Windsurf, OpenCode, OpenClaw, Antigravity, Kimi; VS Code chat only as "build your own extension" | Docs, not code |
| L11 | [claude-mem telemetry](https://docs.claude-mem.ai/telemetry.md) | Anonymous PostHog telemetry **on by default** (opt-out); redacted error text sent unless `CLAUDE_MEM_TELEMETRY_ERRORS=0`. Separately, the installer offers a hosted "CMEM Pro" trial (opt-in) | Docs |
| L12 | [`McpIntegrations.ts`](https://github.com/thedotmack/claude-mem/blob/main/src/services/integrations/McpIntegrations.ts) | A `copilot-cli` installer writes `~/.github/copilot/mcp.json` and injects a context placeholder into the current folder's `.github/copilot-instructions.md`; it prints "MCP-only integration providing search tools and context. Transcript capture is not available" | Source read, not run |
| L13 | [`file-context.ts`](https://github.com/thedotmack/claude-mem/blob/main/src/cli/handlers/file-context.ts) | "File Read Gate": a `PreToolUse` hook that denies whole-file reads of files of 32 KB or more with stored observations, routing the agent to outline tools; Claude Code main sessions only; never denies on its own failure | Source read, not run |
| L14 | [claude-mem hook lifecycle](https://docs.claude-mem.ai/architecture/hooks.md) | Tools on a skip list (`TodoWrite`, `AskUserQuestion`, …) are discarded; `<private>` tags are stripped at the hook and again in the worker; the rest goes to the compression model; hook calls are fire-and-forget with a 2 s timeout | Docs |
| L15 | [VS Code: Manage approvals](https://code.visualstudio.com/docs/agents/run/approvals) (page dated 2026-10-07) | Autopilot auto-approves all tools like Allow all. Assisted permissions (experimental, Agent Host only; Copilot harness needs folder isolation, worktree sessions always use Allow all): an LLM judge approves calls, others need confirmation. Terminal rules: `false` requires approval but does not block; `chat.tools.terminal.blockDetectedFileWrites` (default `outsideWorkspace`) requires approval for detected outside writes; terminal auto-approval is "not a security boundary" | Docs |

## 3. Analysis

### 3.1 What the watcher reads

| Option | Window route | SDK route | Assessment |
| --- | --- | --- | --- |
| R-a Live protocol events (AHP actions; SDK `on_event`) | Received by `vscode_step._observe` (L4), which keeps only names, usage and unconfirmed inputs today | Received by `_Step.on_event` (L5) | Structured, no extra process; a watcher feed (full call inputs, both runtimes in one shape) must be built on top |
| R-b Transcript files (`~/.copilot/session-state/<id>/events.jsonl`) | Written by the host per session | Same file family (the records read for TD-53) | Useful after the fact and across restarts (claude-mem's transcript-watch pattern, L9); lags the live stream |
| R-c VS Code UI (chat window) | Not readable by an agent | — | Not an option |

Recommendation for the design session: R-a for live watching, R-b only for crash recovery and the TD-54
"session record" fallback. Confidence: high (both streams are in use today).

### 3.2 How the watcher stops an outside write

The decided mechanism is G-b: the watcher stops the chat (D6) with auto-approve on (D2), Autopilot (D4) and
no sandbox or hook (D5). The other rows are possible strengthenings that would change D2 or D4 and need the
owner's decision.

| Option | Mechanism | Before or after the write | Evidence | Trade-off |
| --- | --- | --- | --- | --- |
| G-b Observe and stop (decided) | Auto-approve stays; the watcher sees each call as it starts, judges it, and cancels the turn (`chat/turnCancelled`; SDK task cancel plus PID check) | May be after a fast write | Cancel and process end shown (P3, P11); P10 shows unwanted writes do happen; whether the start event arrives before a write was not measured | Cannot prevent a single fast write; the stop reason must report what was written |
| G-a Delivery as approver | Window session with `autoApprove: default`, interactive mode; calls wait for Delivery's `chat/toolCallConfirmed` | Before | P8 (AHP shell tool, folder isolation) and P11 (sandbox confirmations reached Delivery). P6: a window tool without auto-approve hung | Changes D2, and D4 (Autopilot auto-approves every tool, L15). Window-tool coverage, the right mode and per-call latency unproven |
| G-c Assisted permissions | A host LLM judge approves calls; the rest need confirmation (L15) | Before, for calls it does not approve | None of ours | Experimental, Agent Host only, folder isolation; the confirmation path to Delivery and Autopilot interaction unproven; changes D2 |
| G-d Selective rules | Terminal rules and `blockDetectedFileWrites: outsideWorkspace` route matching calls to confirmation (L15) | Before, for detected writes | P10: `permissions.deny` did not stop shell calls under Allow all | Best-effort detection ("not a security boundary"); skipped under Allow all and Autopilot |
| G-e Sandbox | `sandboxEnabled: on` | Before | P10, P11: blocked the outside write; broke `uv` and the stdio MCP server | Excluded by D2's condition and D5 |
| Hybrid | One of G-a, G-c or G-d for the calls it catches, G-b for the rest | Mixed | — | Combines their limits; still changes D2 or D4 |

Confidence: medium. Only G-b fits the decisions as they stand; prevention is a proposal, not a requirement.

### 3.3 Deterministic policy vs model judgement

The SDK guard (`permissions.decide`) is not a drop-in watcher policy: it denies every outside read and write,
URL-reaching shell calls and commands outside the step's allow list, and has no TD-46 exceptions (L5). Used
unchanged in windows it would refuse allowed caches, temporary files and brief-named paths and restrict more
than outside writes, against TD-50. What can be reused are its classification helpers (path extraction,
`inside`, command parsing) under a separate window policy that implements TD-46 exactly.

TD-46's allowed set is mostly path-based. A model is needed for calls a policy cannot classify (e.g. a script
whose effects are not visible from its arguments) and for D5's "malicious or permissible" judgement. Option:
policy first, model for the remainder; TD-47's model choice then matters for the remainder only.

Denying one call is not the same as D6's stop: a stop ends the step and counts towards the single retry; a
denial (only possible under G-a, G-c or G-d) lets the step continue. Which one each verdict triggers is a
design question. Confidence: medium.

### 3.4 Steering and the D6 retry

Both routes can steer: window `chat/pendingMessageSet` (P8: obeyed as the next turn), SDK `send(mode=
"immediate")` (L6, unprobed). Stopping differs by route: a window cancel ended the turn and its process
(P3, P11); SDK `abort()` ends only the model turn, so processes need task cancel plus a PID check (L6), which
the SDK teardown already does. D6's "retry once with the reason, then the owner" maps onto existing Delivery
machinery: a stop becomes a step result with a cause; the retry carries the reason in the next session's first
message; the second stop raises an engine question (the pattern of the TD-54 usage gate).
Confidence: high for the machinery, medium for SDK steering.

### 3.5 Where the watcher runs

| Option | Description | Trade-off |
| --- | --- | --- |
| P-a Inside the runner | The watcher is a component of the step runner that already holds both event streams | No new process or IPC; one watcher per step. If the runner dies, a window turn may run on unwatched (closing the connection does not cancel it, L4), so recovery must cancel it explicitly |
| P-b Separate watcher session | A model session (SDK) that receives a condensed event feed and returns decisions | Needed only for model judgement; can be shared; adds latency and cost |
| P-c External daemon (claude-mem style worker) | A background HTTP service that hosts post to | Durable across steps; a second lifecycle to supervise; heavier than the problem |

Likely combination for the session: P-a for the policy and steering, P-b invoked only for unclear calls.

### 3.6 claude-mem, examined objectively

What it is: a memory system. It records what agents did, compresses it with a model and injects relevant
history into later sessions (L7, L8). Its only blocking is the File Read Gate, which denies large whole-file
reads in Claude Code to save tokens (L13); it does not steer, cancel or judge writes, and has no retry
lifecycle. Its "observer" observes for memory, not for control.

| Aspect | Fit for the watcher | Fit for context injection |
| --- | --- | --- |
| Copilot support | — | Shipped for Copilot CLI as MCP-only: search tools and context, no capture (L12). Nothing from Delivery's window or SDK sessions would be recorded unless Delivery feeds it. The installer edits the workspace's `.github/copilot-instructions.md`, which OwlBear manages |
| Capture by hooks | Hooks feed memory asynchronously (fire-and-forget, L14); not a control path | Claude Code and the listed harnesses only |
| Capture by transcript watch (L9) | Pattern reusable (schema-mapped JSONL tailing with a stored offset) for crash recovery and the TD-54 fallback; no Copilot schema exists, we would write it | Same |
| Model compression into observations | Not needed for control decisions | Could summarise past steps for future planners; overlaps OwlBear memory MCP and the knowledge layer ([always-on memory research](always-on-memory-integration.md)) |
| Progressive disclosure search (index → timeline → details) | — | A good retrieval pattern for any memory Delivery injects (token-cheap index first, details on demand) |
| Session-start injection | — | The idea maps to Delivery's prompt assembly (`prompts.session`), which already injects the Change's own context |

Direct use risks, from its own docs and source:
- **Telemetry.** Anonymous telemetry is on by default and redacted error text leaves the machine unless
  switched off (L11). For company use it needs an explicit opt-out and a review.
- **Hosted mode.** The installer offers a hosted trial; this is opt-in and separate from telemetry.
- **Model and data flow.** Captured content not on the skip list and not in `<private>` tags goes to the
  configured compression provider (L14). Its model choice sits outside OwlBear's role and model rules
  (TD-27, TD-32).
- **Footprint.** It needs Node 20+ and Bun, plus `uv` for Chroma, and a long-lived worker on a per-user port:
  a second runtime and daemon next to Delivery.
- **Capture gap.** Its Copilot support is recall only (L12); capture from our runtimes means writing a
  transcript schema or posting Delivery's events to its REST API.
- **Pace of change.** v13.36.0 at reading; the gate's source changed within the last day (L13). Coupling
  Delivery to its API means tracking fast-moving internals.

Assessment: claude-mem cannot serve as the watcher (it does not control a run). As Delivery's context
injection it is possible but not attractive now: recall-only Copilot support, so Delivery would build the
capture; overlap with OwlBear memory; telemetry and data-flow reviews; an extra runtime. Worth adopting as
ideas, re-implemented in a few lines where they serve a decided need:
(1) schema-mapped transcript tailing with a stored offset, for R-b; (2) progressive disclosure for any
memory injection (index first, details on demand); (3) a single normalised event shape for both runtimes
before the watcher sees them (claude-mem's adapters, L9). Confidence: medium-high (README, docs and two
source files; no code run, as the research rules require).

## 4. Recommendation, Confidence, and Limits

**Owner, 2026-10-12, after reading this:** intervention after the fact is accepted, prevention is not
needed (TD-55: G-b only). claude-mem is out for the watcher and ignored for Delivery for now; it may
later supplement or replace the memory MCP, which would be a separate memory topic. For Copilot that
needs a capture path first, since its shipped Copilot support only searches (L12).

Options to put to the owner, not decisions:

1. Watcher inside the runner (P-a), on a feed built from the live event streams both routes already receive
   (R-a); transcript files only for recovery (R-b).
2. Keep the decided G-b (observe and stop) as the baseline. A window policy built from the SDK guard's
   helpers implements TD-46; a watcher model judges the rest.
3. Optional strengthening for the owner to weigh: prevention through G-a, G-c or G-d for the calls they
   catch. Each changes D2 or D4 and needs a probe of the complete configuration first.
4. D6 retry and owner question reuse the engine-question pattern built for TD-54.
5. claude-mem: adopt three ideas, not the product.

Open and to be measured before building:
- whether the window's start event arrives before a write;
- under G-a, G-c or G-d: window-tool coverage, the mode, and per-call latency;
- SDK steering with `mode="immediate"` mid-turn;
- the watcher model after N2 (TD-47).

Limits: claude-mem was studied from its README, documentation pages and two source files (no clone, no code
run). The window findings rest on single probe runs (P6, P8, P10, P11).
