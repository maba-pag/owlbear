# OwlBear Distribution Under the VS Code Agent Host

> **Owning task:** none — direction research; no Delivery work admitted
> **Date:** 2026-10-07
> **Question:** Can OwlBear replace settings-based loading from a clone and the per-workspace pinned Delivery
> controller with one versioned, plugin-style distribution that works under the VS Code Agent Host, and what blocks it?

## 1. Context and Question

Status quo:

- Consumers load agents, skills, instructions and prompts from `<clone>/share/` through
  `chat.agentFilesLocations`, `chat.agentSkillsLocations`, `chat.instructionsFilesLocations` and
  `chat.promptFilesLocations` ([seed settings](../../seed/.vscode/settings.json)). The dev checkout points the same
  settings at its own `share/` ([settings](../../.vscode/settings.json)).
- Consumers start every OwlBear MCP server with `uv --project <clone> run …` ([seed mcp.json](../../seed/.vscode/mcp.json)).
  The dev checkout starts Delivery from a per-workspace pinned release
  (`.owlbear/controller/bin/delivery-mcp`, 1.7 GB per release; [N02 D1](delivery-n02-plan.md)).
- Every workspace-bound OwlBear server derives its workspace from `Path.cwd()`: Delivery
  ([server.py](../../serve/delivery-mcp/src/owlbear_delivery_mcp/server.py)), memory
  ([server.py](../../serve/memory-mcp/src/owlbear_memory_mcp/server.py)), knowledge and Cockpit. Delivery also refuses
  to start outside the primary Git worktree ([N02 P5](delivery-n02-plan.md#2-feasibility-probes)).
- Reviewer and planner agents enforce read-only behavior through agent-scoped `hooks:` frontmatter that runs
  `.owlbear/hooks/*.py` (for example [build-reviewer](../../share/agents/build-reviewer.agent.md)).

Unknowns from the 2026-10-07 direction discussion:

| ID | Unknown | Why it matters |
| --- | --- | --- |
| U1 | Working directory of plugin MCP servers | Workspace-bound servers read the workspace from `cwd` |
| U2 | Whether MCP servers follow a worktree-isolated session | Delivery refuses linked worktrees |
| U3 | Whether plugin versions can be pinned and auto-update disabled | Delivery state needs an explicit upgrade gate |
| U4 | How a plugin ships a Python runtime | Runtime size and deduplication |
| U5 | Whether the Agent Host loads plugins from `chat.pluginLocations` | Local and dogfood installs |
| U6 | How OwlBear hooks map to the Copilot harness | Read-only enforcement of reviewers |

## 2. Sources Studied

| ID | Source | Fact used | Limits |
| --- | --- | --- | --- |
| S1 | [VS Code agent plugins](https://code.visualstudio.com/docs/copilot/customization/agent-plugins) (edited 2026-09-30) | Plugins bundle skills, MCP, agents, hooks, commands; install from marketplace, Git or `chat.pluginLocations`; 24 h update check; npm/PyPI never auto-update; plugin MCP implicitly trusted | Product docs |
| S2 | [Agent Host concept](https://code.visualstudio.com/docs/agents/concepts/agent-host) | Agent Host reads `.mcp.json` and `~/.copilot/mcp-config.json`; forwards `.vscode/mcp.json` except `${input:}`; user customizations from `~/.copilot` | "Under active development" |
| S3 | [Customization overview](https://code.visualstudio.com/docs/agent-customization/overview) | `chat.*FilesLocations` and `chat.agentSkillsLocations` are deprecated because Agent Host sessions do not use them; migration copies the files | — |
| S4 | [Prompt files](https://code.visualstudio.com/docs/copilot/customization/prompt-files) | Prompt files are not loaded by Agent Host; the Local agent will be removed in a future release | — |
| S5 | [MCP servers](https://code.visualstudio.com/docs/copilot/customization/mcp-servers), [MCP configuration reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration) | `.mcp.json` is the portable format; the add flow lists `.vscode/mcp.json` as deprecated; VS Code `cwd` defaults to the workspace folder | Describes the VS Code layer, not the Agent Host |
| S6 | [Agent harnesses](https://code.visualstudio.com/docs/agents/concepts/agent-harnesses) | Folder isolation edits the workspace; worktree isolation gives the session a separate Git worktree | — |
| S7 | [Hooks](https://code.visualstudio.com/docs/agent-customization/hooks) | Copilot sessions on Agent Host use the Copilot SDK hook implementation; `chat.useHooks`, `chat.hookFilesLocations` configure Local only; agent-scoped hooks are Local only | — |
| S8 | [Agent Plugins spec 1.0.0](https://github.com/agentplugins/agent-plugins-spec/blob/main/spec/1.0.0.md) | Stdio MCP `cwd` defaults to the plugin root and may only be plugin-root or `${PLUGIN_DATA}` rooted; only `${PLUGIN_ROOT}`/`${PLUGIN_DATA}` expand; `PLUGIN_DATA` is for venvs and survives updates | Normative for conforming clients |
| S9 | [Copilot CLI plugin reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference) | Marketplace sources accept `ref` and full `sha`; only first-party or user-opted marketplaces auto-update; plugin agents/skills lose to project ones; plugin MCP wins over user config | CLI behavior; VS Code may differ |
| S10 | [Custom agents configuration](https://docs.github.com/en/copilot/reference/custom-agents-configuration) | Frontmatter has `tools`, `model`, `mcp-servers`; no `hooks` property | — |
| L1 | Static read of VS Code 1.140.0 (`07f806f9`) `out/vs/workbench/workbench.desktop.main.js` and `out/vs/platform/agentHost/node/agentHostMain.js` | See §3; symbols named below are minified and version-specific | Static only; native Copilot runtime (`runtime.node`) not inspected |
| L2 | `~/Library/Application Support/Code/agentPlugins/vscode-synced-customization-agent-host-copilotcli-*` | This workspace's forwarded `.vscode/mcp.json` as a synthetic plugin; no agents, skills or prompts in it | Snapshot of 2026-10-07 |

No Copilot CLI is installed (only the VS Code shim, which offers an install), so no live plugin probe ran.

## 3. Findings

### 3.1 What the Agent Host receives

- **F1 Workspace customizations outside standard folders do not reach Agent Host sessions.** VS Code's
  synced-customization bundler (`Thn`/`Rhn`) bundles only `plugin`, `extension` and `builtin` storage (plus `user` for
  remote hosts) and skips hooks. Workspace files are left to the host's native discovery (`.github/agents`,
  `.github/skills`, `.agents/skills`, `.claude/*`; S9). L2 confirms: the bundle for this workspace contains only
  `.mcp.json`. **Consequence:** `share/agents`, `share/skills`, `share/instructions` and all prompts are invisible to
  Agent Host sessions, in consumers *and* in this dev checkout. Confidence: high.
- **F2 Installed plugins and `chat.pluginLocations` plugins are forwarded** as separate plugin references with their
  profile enablement (`ConfiguredAgentPluginDiscovery`, `Rhn`). Answers U5: yes. Confidence: high (static).

### 3.2 MCP working directory by registration path (U1, U2)

| Registration | Agent Host `cwd` (L1) | In a worktree session | Fit for Delivery, memory, knowledge |
| --- | --- | --- | --- |
| `.vscode/mcp.json` (forwarded) | Explicit `defaultCwd` = window workspace folder | Stays the main workspace folder | Works now; the source is deprecated (S5) and standalone Copilot clients do not read it |
| Repo `.mcp.json` | `PH._scan` sets `defaultCwd` = the session's working directory | The session worktree (`resolveWorkingDirectory`) | Delivery refuses it; memory/knowledge would act on the worktree copy |
| Plugin, legacy Copilot/Claude/OpenPlugin format | `m5` sets `defaultCwd` = plugin folder | Plugin folder | No workspace at all |
| Plugin, Agent Plugins 1.0 format | No `defaultCwd` set in the host layer; spec requires the plugin root (S8) | Unverified | No portable way to name the workspace |

- **F3** No MCP `roots/list` support was found in the host or SDK JavaScript; the native runtime is unread. A server
  cannot currently rely on MCP roots to learn the workspace. Confidence: medium.
- **F4** Placeholders in plugin MCP config are limited to `${PLUGIN_ROOT}` and `${PLUGIN_DATA}` (S8, S9), so a plugin
  cannot pass the workspace path through `args`, `env` or `cwd`.

**U1 answer:** a plugin-registered MCP server does not get the workspace as `cwd`. **U2 answer:** only forwarded
`.vscode/mcp.json` servers keep the main workspace in worktree sessions; repo `.mcp.json` servers follow the worktree.

### 3.3 Version control of plugins (U3)

- CLI marketplaces pin by `ref` or full `sha`; only first-party or user-opted marketplaces auto-update (S9).
- VS Code checks for updates every 24 h when `extensions.autoUpdate` is on and pulls cloned marketplace repositories;
  npm/PyPI plugins update only on explicit confirmation (S1). With a Git marketplace, the marketplace owner, not the
  consumer, decides when content changes.
- `chat.pluginLocations` and CLI path-sourced plugins load live from their directory (S1, S9): an immutable local
  directory is an explicit pin.

**U3 answer:** pinning is possible (`sha`, local path, npm/PyPI), but the default Git-marketplace path updates content
without a consumer decision. That is acceptable for stateless content and not for a stateful runtime unless the
format gate's refusal is the intended upgrade trigger.

### 3.4 Runtime provisioning (U4)

- The spec designates `${PLUGIN_DATA}` for installed dependencies and virtual environments that survive updates (S8).
  It is per installed plugin, not per workspace, so one runtime per user and version is natural.
- Size: a full OwlBear environment is 1.7 GB (N02 U3); a controller-only environment (`owlbear-delivery-mcp`,
  `owlbear-cockpit`, `owlbear-tools`) is 50 MB with no `torch` or `playwright` ([N08 D7, P7](delivery-n08-plan.md)).
  Knowledge pulls `torch`, so one all-in-one environment stays large.

### 3.5 Hooks (U6)

- Agent-scoped `hooks:` frontmatter runs only in the Local harness (S7), and GitHub's custom-agent schema has no
  `hooks` property (S10). Under the Copilot harness the reviewer and planner `deny-writes` guards do not run.
- Copilot-harness hooks come from `.github/hooks/*.json` or a plugin's `com.github.copilot/hooks/hooks.json` and fire
  for every agent in the session, so per-agent guards must filter inside the script. Tool names and payloads differ
  from Local (S7). The remaining per-agent control in the Copilot harness is the `tools` allow-list (S10).

## 4. Analysis

Two concerns behave differently and should be decided separately.

**Content (agents, skills, instructions, hooks): stateless, text, safe to update.**

| Option | Works under Agent Host | Consumer upkeep | Versioning | Notes |
| --- | --- | --- | --- | --- |
| C1 Settings pointing into a clone (status quo) | No (F1, S3) | None | Clone HEAD | Deprecated path |
| C2 Setup copies `share/` into `.github/agents`, `.github/skills` | Yes | Rerun setup; copies drift | Copy time | What VS Code's location migration does (S3); pollutes consumer repos |
| C3 OwlBear agent plugin | Yes (F2) | Install once per user | Plugin version; `sha` pin possible | Project agents/skills of the same name win (S9); prompts must become skills (S4) |

**Workspace-bound runtime (Delivery, memory, knowledge, Cockpit): stateful, bound to one repository.**

| Option | Workspace binding | Pin and upgrade control | Disk | Main gap |
| --- | --- | --- | --- | --- |
| R1 Forwarded `.vscode/mcp.json` + `uv --project <clone>` (consumer status quo) | Correct, also in worktrees | Clone HEAD | One clone | Deprecated source; not read by standalone Copilot clients |
| R2 Per-workspace pinned release (dev status quo) | Correct via `.vscode/mcp.json` | Explicit, per repo | 1.7 GB per release per workspace | Cost and ceremony |
| R3 Plugin-registered MCP | Wrong (F4, §3.2) | Marketplace owner | Once per user | Blocked by U1 |
| R4 Repo `.mcp.json` + stable user-level launcher + per-repo pin file + user-level release store | Session dir; servers must resolve the primary worktree via `git rev-parse --git-common-dir` | Explicit, per repo | Once per user and version; 50 MB controller-only | New launcher; worktree-robust discovery in four servers |

R4 generalizes the existing controller release concept: the store moves from `.owlbear/controller/releases/` to a user
location (the option N02 D1 deferred), the repo keeps only a small pin record, and a bare launcher on `PATH` replaces
the per-workspace `bin/` scripts. The same launcher can run checkout code for this dev repository (unpinned mode).
Its repo `.mcp.json` works in VS Code, the Agent Host and Copilot CLI alike.

## 5. Recommendation, Confidence and Limits

Recommendation (direction only):

1. Distribute **content** as one OwlBear agent plugin (C3). Auto-update is acceptable for it.
2. Keep **workspace-bound servers** registered by the repository, not by the plugin (R1 now, R4 as the target), with
   their runtime pinned per repository and stored once per user. Plugin MCP (R3) is suitable only for
   workspace-independent servers such as `owlbear-browser`.
3. Treat these as prerequisites of any Agent Host move, independent of the distribution choice: prompts to skills
   (S4), agents and skills out of `chat.*FilesLocations` (F1), worktree-robust workspace discovery (§3.2), and a
   Copilot-harness replacement for agent-scoped hooks (§3.5).

Confidence: high for F1, F2, U3 and the hook limits (docs plus code); medium for the `cwd` matrix (static reading of
one minified VS Code build); low for the Agent Plugins 1.0 `cwd` fallback in VS Code (unset in the host layer,
runtime unread).

Limits: no live Agent Host or Copilot CLI run; behavior may change with VS Code releases; company policy on plugins and
marketplaces is unknown; R4 is unprototyped. A five-minute live check would settle the medium-confidence rows: register
a stdlib stdio server that logs `os.getcwd()` and its environment once through `.vscode/mcp.json`, once through a repo
`.mcp.json` and once through a `chat.pluginLocations` plugin, then start Copilot-harness sessions in folder and
worktree isolation and compare the logs.
