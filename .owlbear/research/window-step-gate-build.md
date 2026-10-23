# Window-Step Gate: Build Design (Item 8)

> **Owning task:** plan item 8, the window-step gate (D-01M5DW3X00J966NS961EVFHR33, D-01M5DW3X00SPY1FH9P8M2SGRFZ)
> **Date:** 2026-10-23
> **Question:** What does Delivery build so that window steps can reopen?
> **Evidence:** [window-step gate probes](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/window-step-gate-probes.md)
> **Provenance:** the gate's criteria were agent proposals the owner accepted without intent of his own; he
> declined to decide the gate on 2026-10-23. Every choice here is `autonomous`.

## 1. What Holds Already

- Tool allowlists: each window agent file names its role's tools, which hides the window's own tools and every MCP
  tool outside the role (runtime research P19, P25). No role names the `task` launcher, so windows start no
  subagents.
- Read-only containment (TD-146): read-only sessions run in the Change's read-only worktree `<slug>.ro`, reset
  before each session; refs a session creates or moves, and changes to the shared Git config or hooks, void its run.

## 2. Slices

| # | Slice | Built by |
| --- | --- | --- |
| 1 | **Hooks off, VS Code MCP servers off.** Each window step places `.github/copilot/settings.local.json` with `disableAllHooks: true` (merged into an existing JSON object; anything else refuses the step) and restores it like its other window files. Its window settings pin `chat.mcp.access: none` beside the harness and model. | this pull request |
| 2 | **Host record.** Find the step's record (`~/.copilot/session-state/<id>/events.jsonl`) by its folder and launch time; void the step when the record shows its agent offered a tool outside the allowlist plus the runtime's always-present ones (`skill`, `sql`, `task_complete`, `parallel`). | — |
| 3 | **Subagents in windows.** The SDK rule (TD-374 to TD-376): the agent file names `task` when the role's setting is on; each start is detected live from the `subagent` part on the parent's `task` call; model, tokens, tool calls and duration come from the record's `subagent.completed` into the same `subagents.Watch`; a start the setting does not allow voids the step. | — |
| 4 | **Read-only approvals.** Read-only window steps run with `autoApprove: default`; each call the window asks about is answered by `permissions.decide` with the step's policy and offered tools, not refused wholesale. Calls the harness approves itself (its terminal read rules) stay contained by §1. | — |
| 5 | **Live proof.** The probes again, through the product path: a repository with hook files, a VS Code MCP server, a subagent, a read-only step that tries to write. Then the gate holds, and the suspended routing decisions (D-…5KGRQ) come up for review. | — |

## 3. Limits

- `disableAllHooks` also silences the owner's user and plugin hooks in steps; machine policy hooks still run.
- Servers from the runtime's own user config (`~/.copilot/mcp-config.json`) and the built-in GitHub server still
  connect; the allowlist keeps their tools from the model. No per-step switch was found for them.
- Writes outside the repository remain the watcher's (TD-365, item 9).
