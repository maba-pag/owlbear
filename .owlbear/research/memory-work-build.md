# Memory Work Build Design

> **Owning task:** item 5 of [the plan](owlbear-plan.md); owner decisions TD-292, TD-293, TD-318, TD-400, TD-403,
> TD-167/TD-274/TD-329 and the design session's four of 2026-10-22 (§1)
> **Date:** 2026-10-22
> **Question:** How are the curator's threshold and modes, its automatic runs, moving a Global entry back, the
> saver's scope recommendation, the one-off sort and project agents and skills off in steps built?
> **Status:** design session held with the owner on 2026-10-22; not built.

## 1. Context and Question

Item 5 is next in the order (TD-394, TD-419). Its parts were decided before; the session settled what the code had
no answer for. In force for this build (decision ids from `find_decisions`):

| Decision | Rule |
| --- | --- |
| TD-292/TD-293/TD-400 | Above one Global confidence threshold, initially 95%, the curator decides alone, including Make global; below it, it asks in interactive mode or skips in automatic mode. Interactive sessions propose Make global. |
| `D-01M5J0T48NCQZNNR5YZC9DMJCF` | The 95% compares the curator's own confidence per entry: one number for everything it would do to that entry, not the saver's stored confidence. |
| `D-01M5J19DCX92T3E338ZP8J3HV1` | Automatic curation runs at once after each merged Change that saved memories, when OwlBear is idle with pending entries, and at once from a Maintenance-page button. |
| TD-292 | The owner makes a curated or approved entry Global on the Memory page; it moves and can move back. |
| `D-01M5J1DACNN11K5CYPDD6D4QPR` | Make global records the project an entry came from; it moves back only there; without that record it cannot. |
| TD-293 | Project lessons stay in the project, general ones go to Global; the saver recommends the scope; an entry waits unused until curated. |
| TD-318, `D-01M5J1FX2GA30802T28A74WEH3` | Existing memories are sorted once: an automatic run first, then one interactive session with the owner for only what it skipped. |
| TD-167/TD-274, TD-329, TD-139 | Steps run with project agents and skills off; repository conventions and required checks still apply. |

## 2. Sources Studied

| Source | Fact | Limit |
| --- | --- | --- |
| `share/agents/memory-curator.agent.md`, `share/skills/w-mem-curation/SKILL.md` | Modes are "periodic" (clear-cut only, defers the rest, no questions) and "manual" (asks the owner); neither records a confidence of its own; promotion needs scope curation first | Periodic runs only when asked in chat |
| `serve/memory-mcp/src/owlbear_memory_mcp/tools.py` `save_memory` | Saves pending with `scope_agents=[]`; no project/Global recommendation; the saver's confidence is 0.7 to 1.0 | — |
| `serve/delivery-next/.../project_host/memory_routes.py` `_globalize` | Make global moves the file from `<data>/<project>/memory` to `<data>/memory` and publishes both; no origin is recorded; only curated or approved entries move | No reverse route |
| `serve/delivery-next/.../web/memory.html` | The page says a Global entry does not move back | Contradicts TD-292 |
| `owlbear-data` memory folders, 2026-10-22 | 117 entries in `owlbear/memory`, 8 in `owlbear-sandbox/memory`, Global empty; 58 curated, 14 approved, 24 pending, 28 deleted, 1 stale | A count, not a classification |
| `serve/delivery-next/.../runtimes/sdk_adapter.py` `options()` | Steps pass their role as `custom_agents`, Delivery's `skill_directories` and `enable_file_hooks=False`, in the SDK's default `copilot-cli` mode | Project discovery is left on |
| `github-copilot-sdk` 1.0.22 `CopilotClient.create_session` | `enable_config_discovery` turns runtime discovery of configuration on or off; `skill_directories` and `agent_directories` work without it; `custom_agents_local_only` concerns where agents execute, not discovery; `mode="empty"` turns skills, custom instructions and more off | Which files discovery covers (agents, skills, instructions) is not documented: slice 6 proves it |

## 3. Design

Six slices, each its own pull request; 1 and 2 are independent, 3 needs 1, 4 needs 3, 5 needs 2 to 4; 6 is
independent.

### 3.1 Slice 1: the saver recommends a scope

- `save_memory` gains `where: "project" | "global"`, required, described as the saver's recommendation per TD-293.
  The entry stores it as `recommended`; it stays pending and in its project, unused, as today.
- The Memory page shows the recommendation on pending entries. Only the curator or the owner acts on it.
- Every agent and skill that tells roles how to save (the memory handbook `h-mcp-memory`, `h-memory-structure`,
  the producing roles' agent files) names the new argument.

### 3.2 Slice 2: Make global records its origin; moving back

- `_globalize` writes `origin: <project name>` into the entry as it moves it; the commit names it.
- A new route moves a Global entry back to its `origin`, from the Memory page with that project chosen (TD-291),
  under the same locks, staleness check and publication as Make global; refused with the reason when the entry
  has no `origin` or `origin` is not the chosen project. The page drops "does not move back" and shows the button
  only where the move is allowed.
- Entries made Global before this slice have no `origin` and cannot move back (`D-01M5J1DACNN11K5CYPDD6D4QPR`);
  Global is empty today, so none exist yet.

### 3.3 Slice 3: curator modes and the threshold

- The curator gets Make global as a memory MCP tool, so it can act alone; it records `origin` as the page
  does (§3.2). Built here, where it is first used.
- The modes are renamed to what the decisions say: **automatic** (was periodic) and **interactive** (was manual).
- For each entry the curator judges everything it would do to it (keep, edit, scope, merge, delete, Make global)
  and states one confidence for that whole set. At 95% or more it acts in both modes. Below 95%, automatic mode
  leaves the entry as it is and reports it as skipped with the reason; interactive mode asks the owner in his
  question format. Interactive sessions propose Make global for general lessons (TD-292).
- The threshold is one value, 95% at first (TD-400), read by the run, not written into the skill: a global-only
  field of the Global settings layer (`settings/config.py` `GlobalLayer`, like `visible`, TD-35), so every machine
  and both modes use the same number and changing it needs no release. The owner confirmed it on 2026-10-22, with a field on the Settings page.
- **Which memory a run curates.** One folder per run: a project's memory folder in `owlbear-data`, OwlBear's own
  (`owlbear/memory`, served through the machine host's OwlBear route, TD-435) included though OwlBear is never a
  registered project. Global is read for comparison; the curator writes to it only by Make global (§3.2). The
  memory MCP server's curator tools (`curate_memory`, `delete_memory`, `commit_memory_batch`) take an optional
  folder name, limited to the project folders of `owlbear-data` and defaulting to the bound one, so one interactive
  session can work across folders (§3.5); each mutation publishes to its own folder.
- Each run's report lists per entry its action, the confidence and, for a skip, why; it is kept with the run (§3.4).
- The memory-curator agent and `w-mem-curation` are rewritten for this. Prose-assertion tests that pin the old
  wording (plan §4, C-26) are replaced by behavioural ones.

### 3.4 Slice 4: automatic runs

- A machine-host job runs the curator in automatic mode on one memory folder (§3.3), in an SDK session with the
  memory MCP server on that folder, like a step session; its model and effort are the memory-curator role's
  settings. Runs of one folder never overlap; a trigger during a run queues one more.
- Triggers (`D-01M5J19DCX92T3E338ZP8J3HV1`):
  1. **After a merge:** when a Change merges and its steps saved at least one memory entry, its project's run
     starts at once. OwlBear's folder has no Changes, so only the other two reach it.
  2. **Idle:** when OwlBear is idle and a folder holds pending entries that no finished run has judged, its run
     starts. The idle detection is the idle updater's (`machine_host/auto_update.py`), not its permission rules.
     An entry a run skipped does not start another run until it changes, so unchanged skips never cost a session
     again; the button and the merge trigger still judge them.
  3. **Button:** the Maintenance page's "Curate memory now" starts it at once for the chosen folder, or for all.
- While paused, the merge and idle triggers run only when "Curate memory while paused" is on, a machine setting
  beside "Update itself while paused", off by default; the button always runs at once (the owner, 2026-10-22).
  Update behaviour is unchanged.
- A run counts against the machine's sessions (TD-336). Its state and last report show on the Maintenance page.
- Built so far: Delivery's own `owlbear-curator` role (SDK only, its memory tools and a structured report as
  its result, no subagents), the machine host's job (`machine_host/curation.py`, state in `~/.owlbear/curation.json`)
  and the Maintenance page's Curate now per folder. The merge and idle triggers come next.

### 3.5 Slice 5: the one-off sort

- An automatic run over every memory folder of `owlbear-data` (today `owlbear` with 117 entries and
  `owlbear-sandbox` with 8), under §3.3's rules, from the Maintenance button with "all" chosen. The inventory is
  the folders, not the registered projects: OwlBear's own folder holds most entries.
- Then one interactive curator session in the owner's chat for only the entries that run skipped, read from its
  report, across their folders through §3.3's folder argument. The sort is done when that session ends; nothing
  marks the entries otherwise.
- The memory stored for all agents, "Frame substantive user decisions before asking", predates the owner's current
  question format (workspace instructions, "Asking the Owner") and is one of the entries this sort judges.

### 3.6 Slice 6: project agents and skills off in steps

- Step sessions set `enable_config_discovery=False` and keep their explicit `custom_agents` and
  `skill_directories`, so only Delivery's agent and skills load (TD-167/TD-274).
- Repository conventions still apply (TD-139). If discovery off also drops the repository's instructions
  (`.github/copilot-instructions.md`, `AGENTS.md`, `.github/instructions/`), the step passes the repository's
  instruction folders as `instruction_directories`, which load without discovery.
- Proof first, before the change: a session in a disposable clone that holds a project agent, a project skill and
  a repository instruction lists what loaded, through the session's RPC, with discovery on and off. The test pins
  the result: role's agent and Delivery's skills present, project agent and skill absent, the instruction present.
- The owner's chat is unchanged: there OwlBear limits only its own additions (TD-167).

## 4. Recommendation, Confidence, and Limits

- Build in the order 1, 2, 6, 3, 4, 5: the two small independent slices first, slice 6 because it is independent
  and closes TD-274's gap, then the curator chain; slice 3 carries the folder routing that 4 and 5 need.
  Confidence 85% that the slices are cut right; the risk is slice 3, where the curator's confidence must be stated
  consistently enough to compare with 95%.
- Sol challenged this design on 2026-10-22 (five findings, all taken): the threshold in the Global layer, not the
  machine's; the sort's inventory by folder, OwlBear's included; a folder argument for the curator's tools; no
  idle rerun for unchanged skips; Pause stated as this design's choice, update behaviour unchanged.
- Not decided here, left to each pull request (TD-389): field names, the job's module, the report's format.
- Open technical point: whether `enable_config_discovery=False` covers agents, skills and instructions as §3.6
  assumes; slice 6's proof settles it before any code changes.
- Item 5 also listed three residuals from #238, #244 and #249; they are built.
