# OwlBear decisions in force

The owner's decisions for OwlBear and its Delivery, by topic. Each topic lists its rows by origin, the rules
in force with their rows, the owner's words, what was replaced and what is open. How to record a decision is
in C-31; who may change one is in the workspace instructions ("Prior decisions by origin"). The full rows
TD-1..TD-382 as first recorded, and the research report of 2026-10-10..12 this file began as, are at commit
`04b1d8ec4`: `git show 04b1d8ec4:.owlbear/research/delivery-liveness-first-rebuild.md`. What is built, the order of
the remaining work and where the code differs from these decisions are in [the plan](owlbear-plan.md).

## C-01 Asking the owner

**Rows:** decided TD-41, TD-42, TD-43, TD-150, TD-156, TD-340, TD-364, TD-448.

- A read-back offers three close variants of the decision, fewer only when fewer really differ, never padded, the
  matching one at varying positions, plus one or two other directions, the opposite among them [TD-41, TD-156, TD-364].
- It closes with "take your recommendation (…)" naming it, "none of these: show me more options" and "explain
  first"; free text stays open; no other recommendation mark [TD-41, TD-156].
- The question shows the decision's record and what changed since [TD-156].
- When the direction itself is in doubt, ask the direction first, then the nuances, stating the reason [TD-41].
- Used at the end of ideation, before design approval and for the assistant's consequential choices [TD-41].
- "Take your recommendation" makes the result the assistant's `autonomous` choice, with reasons [TD-41].
- "Show me more options" gives a bounded set across directions, each with pros, cons, risks and its own percentage
  that it is a good choice, not adding up [TD-41, TD-42].
- For a free-text chat answer, offer 2 to 5 readings that fill gaps differently, plus "your words as written", "show
  me more readings" and "explain first"; the owner chooses the one meant [TD-43, TD-340].
- Comments on Delivery's pages are taken as written; one that contradicts the approved brief is held for the owner,
  never applied [TD-340, TD-79, TD-153, TD-193].
- Every challenge of owner input extracts intent and reports what is missing and what is overdone, not only what is
  wrong; the owner's words are evidence of intent, not a literal spec [TD-150].
- Free text and unclear answers are read back at once; a chosen paraphrase counts as confirmed; a session ends with
  one check of everything it records [TD-448].

**Owner's words:**

- TD-41, 2026-10-11: "3 options in the same direction"
- TD-42, 2026-10-11: "A separate percentage per option that it is a good choice, not adding up"
- TD-43, 2026-10-11: "let me choose the one i emant, not the one i wrote"
- TD-150, 2026-10-15: "if there is anything missing … intent has to be extracted"
- TD-156, 2026-10-15: "a polar opposite … with your recommendation in brackets"
- TD-340, 2026-10-18: "TD-43 covers chat answers; page comments are taken as written"
- TD-364, 2026-10-18: "Three as the norm; fewer only when fewer really differ, never padded"

**Replaced:** TD-41 by TD-156 and TD-364; TD-43 by TD-340.

## C-02 Permissions and agent writes

**Rows:** decided TD-29, TD-45, TD-46, TD-81, TD-82, TD-102, TD-146, TD-320.

- SDK steps allow every shell command except hook or signing bypass, force push and, in read-only steps (plan,
  reviews, challenges, judges), any write [TD-82, TD-320].
- Nothing blocks an agent's writes outside its worktree, a plain `git push` or GitHub writes through `gh` [TD-320].
- Agents are told never to push or write to GitHub; Delivery does the git and GitHub writes. This is an instruction,
  not an enforced block [TD-29, TD-320].
- Every security restriction and every security relaxation the assistant introduces is reviewed with the owner
  [TD-81, TD-102].
- After each read-only run, a change to shared Git config or the hooks folder stops the Change with a question to
  the owner and is never restored automatically [TD-146].

**Owner's words:**

- TD-29, 2026-10-10: "agree on agents never push...Github write"
- TD-45, 2026-10-11: "Keep it permanently on the SDK route"
- TD-46, 2026-10-11: "Allowed: Delivery's own state, temporary files, the user's tool caches"
- TD-81, 2026-10-13: "i want to review each of these decisions you made regarding security"
- TD-82, 2026-10-13: "Drop it: allow all except rows 2-6"
- TD-102, 2026-10-14: "Also every security relaxation"
- TD-146, 2026-10-15: "Build the narrow check now"
- TD-320, 2026-10-18: "agents are told never to push or write to GitHub, nothing blocks it"

**Replaced:** TD-23 by TD-82; TD-45 by TD-82 and TD-320; TD-29 by TD-320; TD-81 by TD-102; TD-46 by TD-365.

## C-03 Models and credits

**Rows:** decided TD-21, TD-27, TD-32, TD-47, TD-54, TD-56, TD-75, TD-94, TD-117, TD-144, TD-333, TD-378.

- No cost question: credits are shown per Change and step, never used to stop or ask [TD-21].
- Model and credits are separate. Unreadable credits are logged and the result is accepted; spend shows as unknown,
  never zero [TD-94].
- Models and effort per role: reviews `gpt-6.1-sol` xhigh; challenges `gpt-6.1-sol` high; design and planning
  `claude-opus-5.5` high; building and roles not yet chosen `claude-opus-5.5` medium [TD-27].
- A benchmark on OwlBear's work compares `gpt-6-luna` max with `claude-haiku-5.5` high, and `claude-haiku-5.5` xhigh
  with `gpt-6.1-sol` low; it only informs the cheap tier, chosen with the owner afterwards [TD-27].
- The watcher's model and effort are chosen with the owner after TD-27's benchmark has run [TD-47, TD-378].
- Never `auto`: every session names its model. Discarded turns (probes, tests, a VS Code chat's cancelled first
  turn) use `gpt-6-luna` low; small tasks that must be correct use `claude-haiku-5.5` medium [TD-32].
- Only usage metrics prove which model ran: verified, mismatch or unknown [TD-94].
- A wrong model voids the result: one rerun after a fixed 5-minute wait, behind other ready work when queued; a
  second wrong model in a row asks the owner [TD-117, TD-144].
- An unknown model stops the Change until the owner retries or accepts; accept is offered only while nothing the
  result depends on changed [TD-94].
- Accept is offered for a step's own session and a screenshot round; challenge sessions only rerun [TD-333, TD-71].
- Accepting a screenshot round accepts the whole round and waives only the model check; the verdicts still decide
  [TD-94].
- Before a role moves to another runtime, its behaviour and quality are compared in both runtimes with the same
  model, effort, context and effective tools [R4, report 2026-10-11].

**Owner's words:**

- TD-27, 2026-10-11: "i see sol xhigh as reviewer, sol high as challenger"
- TD-32, 2026-10-11: "we never use auto, ever"
- TD-47, 2026-10-11: "Decide after the benchmark (N2)"
- TD-54, 2026-10-12: "unreadable usage lets the step run until the end"
- TD-56, 2026-10-12: "Accept only while nothing it depends on changed"
- TD-75, 2026-10-14: "i dont think we need an accept button there"
- TD-94, 2026-10-14: "if the model can not be read or is wrong, this is a failure mode"
- TD-117, 2026-10-15: "for wrong model, put back in the queue if there is one, and rerun only once, then ask"
- TD-144, 2026-10-15: "Keep 5 minutes (TD-117)"
- TD-333, 2026-10-18: "challenge sessions only rerun; accept is for a step's own session and a screenshot round"
- TD-378, 2026-10-18: "Run TD-27's benchmark first, then choose with you"

**Replaced:** TD-54 by TD-94; TD-56 by TD-94; TD-75 by TD-94; TD-94 by TD-117 and TD-144.

**Open:**

- No row records TD-27's benchmark result or the cheap tier chosen afterwards; the benchmark has not run (TD-378
  runs it before the watcher's model is chosen).

## C-04 Window steps and the watcher

**Rows:** decided TD-20, TD-34, TD-35, TD-36, TD-44, TD-50, TD-55, TD-86, TD-137, TD-145, TD-223, TD-224, TD-338,
TD-342, TD-365, TD-366, TD-367; autonomous TD-48, TD-67, TD-267, TD-316.

- Before real-project use: New Change, automatic merge with pull-back, thread replies and resolution, visual
  pre-check, deterministic "now" line, step time, quiet warning, credits and the watcher [TD-20].
- Notifications, scanner triage and a knowledge home wait for evidence from real use [TD-20].
- No real project uses OwlBear before the watcher exists, SDK steps included; later release or timing rows do not
  waive this [TD-20, TD-338, TD-297, TD-316].
- Until the watcher exists, steps may run outside VS Code (SDK or CLI) and the owner reads their logs afterwards; he
  accepts SDK steps cannot be watched, controlled or stopped meanwhile [TD-44, TD-50].
- Afterwards, watching may change only how writes outside the worktree are controlled; everything else stays the
  same [TD-50].
- The watcher acts only after an action (stop, then retry) and judges actions, not reasoning, which only prompts a
  closer look or feeds learning; catching exfiltration is no goal yet; it is multi-purpose [TD-55].
- The watcher judges each outside write and outgoing transfer after the fact, stopping the step only if dangerous or
  inappropriate for the task; harmless ones are reported [TD-365].
- Delivery's own state, temporary files and the user's tool caches are never judged [TD-46, TD-365].
- Each agent has a default runtime (initially the SDK) and its own model, effort and context size; the watcher must
  read, steer and stop every runtime in use [TD-34].
- A missing tool ends the step with a report; Delivery retries a temporary error now then later, reruns once in a
  runtime that has it, asks the owner for needed setup, or replans if it exists nowhere [TD-36].
- A guard denial never leads to more tools; while window steps are paused, a window-only tool is asked of the owner,
  naming it, instead of a rerun there [TD-36, TD-367].
- Window steps stay paused and steps run only through the SDK until probes close the gaps: subagent detection,
  built-in exclusion, project hooks, judge shell, read-only containment [TD-137, TD-129].
- Window steps reopen only when windows keep repository hooks and user MCP servers out, subagents are detected and
  counted, and judge effects beyond refs are contained or sandboxed [TD-145, TD-223].
- The whole watcher is built right after the window-step gate [TD-224].
- The watcher's design is decided with the owner when window steps are about to return, not before [TD-316].
- Suspended while window steps are paused, reviewed when the gate passes: runtime and visibility routing, window start,
  the per-project window switch, the read-only worktree [TD-342, TD-34, TD-35, TD-48, TD-67, TD-86].
- Suspended routing: a step uses its agent's default runtime unless its required tools need another
  [TD-34, TD-342, TD-343].
- Suspended visibility: agent need, the Change's always-visible or the global switch makes a step a window chat
  with the same tools as unwatched; changes apply from the next session [TD-35, TD-342, TD-343].
- The SDK guard stays in force: Delivery's own code, the SDK permission callback, not hook files [TD-86, TD-366].

**Owner's words:**

- TD-20, 2026-10-10: "The six items, plus the watcher agent"
- TD-34, 2026-10-12: "Each agent has a default runtime (initially the SDK)"
- TD-35, 2026-10-12: "visible steps run as chats in a VS Code window, so you see them in a window"
- TD-36, 2026-10-12: "Known needs choose the runtime up front"
- TD-44, 2026-10-11: "SDK steps may run meanwhile; only their logs can be read afterwards"
- TD-50, 2026-10-12: "i accept that steps inside the sdk cannot be controlled and prevented from doing shady things"
- TD-55, 2026-10-12: "i accept the risk that watcher can only intervene post haste … watcher is generally multi purpose"
- TD-86, 2026-10-14: "non commited guard hooks make no sense"
- TD-137, 2026-10-15: "Pause; run probes 1, 2 and 3 now (I allow the window exception)"
- TD-145, 2026-10-15: "Record as the reopen gate; no work now"
- TD-223, 2026-10-17: "Build the gate now, after TD-208"
- TD-224, 2026-10-17: "build it after the window steps"
- TD-338, 2026-10-18: "The watcher stays a gate before real-project use, for SDK steps too"
- TD-342, 2026-10-18: "The window rows are marked suspended and are reviewed again when the gate passes"
- TD-365, 2026-10-18: "stops the step after an outside write IF it finds the write dangerous or inappropriate"
- TD-366, 2026-10-18: "Only the window part is suspended; the SDK permission callback stays in force"
- TD-367, 2026-10-18: "You are asked, naming the window-only tool, like the 'needs the owner's setup' case"

**Replaced:** TD-34 by TD-343; TD-50 by TD-320; TD-145 by TD-223; TD-55 by TD-365; TD-36 by TD-367.

## C-05 Roles, agents and skills

**Rows:** decided TD-58, TD-69, TD-99, TD-106, TD-108, TD-109, TD-110, TD-134, TD-135, TD-136, TD-139, TD-157,
TD-159, TD-166, TD-167, TD-169, TD-170, TD-329, TD-343; autonomous TD-274, TD-317.

- Delivery's agents, skills, prompts and instructions are not written from scratch: the existing ones are studied
  for good parts, ideas and structure as a base to improve [TD-58].
- Every role has its own agent file; reusing one for several roles needs a recorded decision; the shaper's
  interview depth scales with the Change's size [TD-106, TD-107, TD-93].
- Every role's agent file is `agents/owlbear-<role>.agent.md`, flat, its name matching; Delivery keeps short role
  keys [TD-169].
- Agent files list their tools; each runtime offers exactly those plus Delivery's result tools; nothing is added
  per task [TD-69, TD-99, TD-343].
- The plan challenger and the visual judges do not question the owner; they answer with their verdict, `unsure`
  where intent is unclear [TD-108].
- Who = agent file; how = skill; what this time = brief, plan, task; why = brief outcome and the owner's decisions;
  when and where = engine; tools = agent file plus tool schemas [TD-135, TD-159].
- Model = Settings; rules = agent boundaries and instructions; events = Delivery, not repository hooks; owner-invoked =
  prompt or user-invocable skill; done = criteria plus enforced result contract [TD-135, TD-159, TD-142].
- Substantial or shared procedures become skills; short single-role steps stay in the agent file; the engine keeps
  enforcement [TD-159].
- Skill names are `owlbear-` plus a noun phrase naming the subject area [TD-170].
- Each role preloads only the skills its job needs, and each step sees only those folders [TD-134, TD-166, TD-170,
  TD-125].
- Only the shaper preloads the shaping procedure, one skill; there is no global `/delivery` skill [TD-136, TD-170].
- Steps are strict: one agent, its own skills, project agents and skills off. In the owner's chat OwlBear limits
  only what it adds and hides its skill from the `/` menu [TD-167, TD-274].
- SDK steps run with repository instructions on, its agents and skills off [TD-139, TD-157].
- On conflict Delivery's steps, tools and result format win; repository conventions and required checks still apply;
  real clashes ask the owner [TD-139, TD-157].
- "Project agents and skills off" in SDK steps is not built yet; until its fix after self-update step 5, steps may
  run with them discoverable [TD-274, TD-317, TD-329].

**Owner's words:**

- TD-58, 2026-10-12: "the agent werent the problem with old delivery … they have good parts and ideas"
- TD-69, 2026-10-14: "ofc you need to define tools for eac agent"
- TD-106, 2026-10-14: "we shouldnt have a role without an agent … reusing an agent … should be a decision"
- TD-110, 2026-10-15: "Keep for builder, explain in prose"
- TD-135, 2026-10-15: "Adopt this model for the structure"
- TD-136, 2026-10-15: "No global /delivery; procedure preloaded by the shaper only"
- TD-157, 2026-10-15: "Delivery's steps, tools and result format win"
- TD-166, 2026-10-15: "Per job as listed; each step sees only those folders"
- TD-167, 2026-10-15: "Steps strict; in your chat OwlBear limits its additions and hides its skill from the / menu"
- TD-169, 2026-10-16: "Flat as above, and the designer becomes owlbear-design-judge (settings key migrated)"
- TD-170, 2026-10-16: "Noun phrase (subject area)"
- TD-329, 2026-10-18: "Allowed until the fix after self-update step 5"
- TD-343, 2026-10-18: "A step gets exactly its agent file's tools; nothing is added per task, as built"

**Replaced:** TD-136 by TD-170; TD-166 by TD-170 and TD-169; TD-135 by TD-159; TD-139 by TD-157, C-08 and TD-329;
TD-167 by TD-329.

## C-06 The shaper

**Rows:** decided TD-13, TD-83, TD-93, TD-138, TD-160, TD-163, TD-164, TD-165, TD-244, TD-328, TD-348;
autonomous TD-275, TD-276, TD-277.

- New Change opens a dedicated Copilot shaping chat with a configurable `shaper` role in Settings and allow-all
  permissions, so no prompt is copied [TD-13, TD-83].
- The shaper role defaults to `claude-opus-5.5`, default tier, medium effort [TD-83, TD-93].
- The shaper and its skill reach every project through install-approved symlinks in `~/.copilot`; uninstall removes
  them [TD-165, TD-244, TD-348].
- A new shaper location is proven only when, in a real shaping chat, the shaper is chosen, its skill preloads, its
  tools work and owner settings are restored; prove it in the sandbox before removing old copies [TD-160, TD-163].
- Delivery selects the shaper by name and refuses shaping when it is not listed [TD-163].
- Delivery-sent shaping turns use the role's model and effort; owner-typed turns use the chat's picker, unpinned,
  with one reminder from the shaper to match the role [TD-277, TD-328].
- The Settings page marks the shaper's model and effort as a recommendation for the owner's chat [TD-328].

**Owner's words:**

- TD-13, 2026-10-10: "approved the button to start chat"
- TD-83, 2026-10-13: "A shaper role in Settings"
- TD-93, 2026-10-14: "but make it medium thinking"
- TD-163, 2026-10-15: "Permanent workspace line to the checkout's shaper-only folder"
- TD-164, 2026-10-15: "the pinned run checkout until then; main once live"
- TD-165, 2026-10-15: "Switch now to symlinks in ~/.copilot"
- TD-328, 2026-10-18: "the Settings page marks the shaper's model and effort as a recommendation for your chat"
- TD-348, 2026-10-18: "TD-165/244 replace the location"

**Replaced:** TD-93 by TD-165 and TD-244; TD-106 by TD-165 and TD-244; TD-160 by TD-165 and TD-244; TD-163 by
TD-165; TD-138 by TD-165; TD-164 by TD-244; TD-244 by TD-242, TD-281 and TD-321.

## C-07 Local installs

**Rows:** decided TD-5, TD-131, TD-140, TD-162, TD-346.

- The employer allows local Copilot CLI and Copilot SDK use with the owner's seat [TD-5, TD-346].
- Anything OwlBear keeps outside the repositories must be reviewed, necessary, without real alternative and
  explicitly approved by the owner, after research and a Sol challenge of structure and installs [TD-131].
- Approval is one list giving location, purpose, alternative and what declining means, approved per location and
  artifact kind; a new location or capability asks again [TD-162, TD-346].

**Owner's words:**

- TD-5, 2026-10-10: "Yes, allowed; install them wherever convenient"
- TD-131, 2026-10-15: "absolutely necessary, with no real alternative, and explicitly approved by me"
- TD-346, 2026-10-18: "TD-162 replaces TD-5's 'wherever convenient'"

**Replaced:** TD-5 by TD-162; TD-131 by C-06.

## C-08 Local home and paths

**Rows:** decided TD-147, TD-161, TD-182, TD-198, TD-260, TD-334, TD-335.

- OwlBear's local files live in `~/.owlbear` on every system; no Application Support or XDG folder, no
  `OWLBEAR_HOME` [TD-198].
- Every project's live Delivery database lives under `~/.owlbear`, one folder per project [TD-334, TD-198, TD-265].
- The confirmed project profile lives in the project's data-repository folder and is re-checked on a new clone, so
  a fresh clone needs no new setup [TD-147].
- Only exceptions outside `~/.owlbear`: the `owlbear` link in `~/.local/bin`, login item in `~/Library/LaunchAgents`,
  `~/.copilot` shaper links; each asked for separately at install, removed by uninstall [TD-162, TD-260, TD-335].

**Owner's words:**

- TD-147, 2026-10-15: "Live state in .git; profile to owlbear-data now"
- TD-182, 2026-10-16: "Code tonight; this Mac's files move in the morning install round"
- TD-198, 2026-10-16: "no application support folder, we stay in ~/.owlbear/ with everything"
- TD-260, 2026-10-17: "Both, each asked for separately at install, removed again by uninstall"
- TD-334, 2026-10-18: "Move every project's database under ~/.owlbear too, one folder per project"
- TD-335, 2026-10-18: "The ~/.copilot shaper links join TD-260's list as the third outside exception"

**Replaced:** TD-139 by TD-198; TD-161 by TD-198; TD-182 by TD-198; TD-147 by TD-334; TD-198 by TD-260 and TD-335.

## C-09 Data repository and settings

**Rows:** decided TD-7, TD-52, TD-57, TD-59, TD-64, TD-95, TD-98, TD-105, TD-128, TD-227, TD-243, TD-336, TD-347;
autonomous TD-295, TD-395.

- One private repository, `maba-pag/owlbear-data`, holds every project's research and former `.owlbear/` documents
  in a folder per project, OwlBear's own included; consumer projects no longer contain them [TD-7, TD-95].
- OwlBear's decision record, plan and build designs of unbuilt work stay in its repository, which GitHub's agents
  and reviewer read; they move once history [TD-395].
- Research about a consumer project is never committed into that project [TD-7, TD-347].
- A project's folder name defaults to the repository name; Delivery asks the owner on a collision, and the name can
  be renamed later [TD-98].
- A save on the settings page commits and pushes [TD-64].
- Preferences resolve built-in → global → machine → project, the project winning; global and built-in defaults stay
  separate; capabilities are checked afterwards and a value is never silently replaced [TD-336].
- Machine-only: update channel and registered projects. Project-only: test preparations, data permissions and the
  PR marker [TD-336, TD-243].
- Session limits count agent sessions, never per model: machine-only (default 4) and per project, layered (default
  2). Free slots go round-robin across projects, first-ready within one; waiting spends no budget [TD-336, TD-105].
- Running sessions are never stopped to meet a session limit [TD-336, TD-105].
- The settings page shows the global defaults, each project's differences and each value's source, and asks the
  scope on every edit [TD-243, TD-295].

**Owner's words:**

- TD-7, 2026-10-10: "One shared documents repository for all projects, a folder per project"
- TD-52, 2026-10-12: "Global with overrides per project"
- TD-57, 2026-10-12: "why cant it also hold global settings?"
- TD-59, 2026-10-12: "new private repo maba-pag/owlbear-common cloned to ~/Projects/owlbear-common"
- TD-64, 2026-10-13: "Commit and push"
- TD-95, 2026-10-14: "i dont like common"
- TD-98, 2026-10-14: "folder named after the repo, but changeable in project config dashboard"
- TD-105, 2026-10-14: "global + project, not model"
- TD-128, 2026-10-15: "Rename internals to 'data' too"
- TD-227, 2026-10-17: "Move research into owlbear-data now, before the old-engine removal"
- TD-243, 2026-10-17: "i think we still do need project settings"
- TD-336, 2026-10-18: "preferences can be different between machines and between projects"
- TD-347, 2026-10-18: "TD-227 replaces TD-7's 'commit to dev for now'"

**Replaced:** TD-7 by TD-227; TD-59 by TD-95 and TD-128; TD-64 by TD-98; TD-52 by TD-243 and TD-336; TD-243 by
TD-336; TD-105 by TD-336.

## C-10 Test preparation

**Rows:** decided TD-60, TD-80, TD-92, TD-96, TD-107, TD-118, TD-119, TD-120, TD-121, TD-130, TD-349; autonomous
TD-65.

- Three tiers: dev (the Change's worktree), test, live; Delivery's checks never touch live [TD-60, TD-96].
- Test is a copy of live running the Change's code; one frozen snapshot is restored separately for the before and
  the after capture [TD-96].
- Projects declare preparation options: live copy, live copy plus test data, or test data only, each with export
  and restore, masking, isolation and cleanup; the preparer picks one, Delivery validates and runs it [TD-96].
- The owner's standing per-project permissions cover data classes, keys, isolation and retention; with no safe
  option Delivery asks or blocks [TD-96].
- Every project declares at least one preparation option before a check launches; without one Delivery asks; the
  sandbox has the data-only option `none` [TD-120].
- A data-only preparation that copies no data classes may declare no isolation [TD-121].
- Each live-copy preparation declares its live identities; a test environment naming one is refused [TD-118].
- Restore, seed, cleanup and checks get only declared variables; export and masking run only declared, committed scripts
  [TD-118].
- Agents keep allow-all and may write the project settings that hold preparation permissions [TD-119, TD-82].
- Check preparation has its own `preparer` role, default `claude-haiku-5.5`, default tier, effort low; a later check
  reuses the recipe that last launched, and preparing again follows only a failed launch [TD-80].
- The preparer has its own agent file and edits only test-system setup files; its edits are discarded after the
  check and never become Change code [TD-107, TD-106].

**Owner's words:**

- TD-60, 2026-10-12: "we should adopt a three tier model of dev, test, live system/repo"
- TD-80, 2026-10-13: "own role default haiku 5.5"
- TD-96, 2026-10-14: "but its not something i decide but that is decided by an agent"
- TD-107, 2026-10-15: "B"
- TD-118, 2026-10-15: "A: declared live identities + explicit test environment"
- TD-119, 2026-10-15: "B: keep allow-all"
- TD-120, 2026-10-15: "A: require an option; add 'none' for the sandbox"
- TD-121, 2026-10-15: "Allow empty isolation for data-only without data classes"
- TD-130, 2026-10-15: "Keep project-only"
- TD-349, 2026-10-18: "TD-92 becomes history"

**Replaced:** TD-60 by TD-96; TD-65 by TD-96; TD-92 by TD-120 and TD-82.

## C-11 Visual checks

**Rows:** decided TD-14, TD-24, TD-38, TD-40, TD-49, TD-51, TD-77, TD-78, TD-79, TD-91.

- UI changes always get design and layout testing. The agent's check suffices to merge unless it is unsure or the
  brief sets a person-only check: then the merge waits for the owner. He may view any screenshot freely [TD-14].
- Before and after screenshots are captured and shown to the owner without interrupting the run, so he can
  intervene or simply see the difference [TD-24, TD-38].
- When a Change alters a page, shaping captures the target's current pages and writes the visual states against
  them; approval waits for that capture [TD-38].
- Compare per Change, not per task. Retake "before" if the target's UI changed since shaping; the shaping set stays
  the design reference [TD-38].
- Capture the specified UI states at the configured desktop widths; reviewers judge screenshots and errors [TD-49].
- The capture collects console errors, and page errors (uncaught exceptions) count as console errors: new ones
  since "before" fail the check, existing ones are reported [TD-49, TD-51].
- The detector's findings are evidence for the judges, never a fail on their own [TD-77].
- Every visual review has two parallel judges, correctness and design, and no repeat-verdict button. Correctness
  fails return to the build; design fails return or go to the owner by a project-overridable setting [TD-74, TD-78].
- Check every visual expectation against visible evidence, not hidden attributes or passing tests; unclear intent
  means unsure. Shaping writes visible expectations [TD-91].
- The owner passes or fails on one page with the comparison, both verdicts and findings. Fail needs a finding or
  comment, which becomes a next-review criterion, a Pass comment a note; brief contradictions are held [TD-79, TD-340].

**Owner's words:**

- TD-14, 2026-10-10: "there needs to always be visual testing regarding design and layout"
- TD-24, 2026-10-10: "screenshots of the before/after are created … this does not interrupt the process"
- TD-38, 2026-10-11: "1: agree"
- TD-40, 2026-10-11: "3 is confiremd option 3 now"
- TD-49, 2026-10-12: "As the first, plus: a task can add 'browser use' for the reviewer"
- TD-51, 2026-10-12: "Page errors count as console errors: new ones fail, existing ones are reported"
- TD-77, 2026-10-14: "evidence for the judges"
- TD-78, 2026-10-14: "can we make it configurable if design failures go back automatically?"
- TD-79, 2026-10-14: "you pass/fail recommendation"
- TD-91, 2026-10-14: "Also shaping hint for visible expectations"

**Replaced:** TD-49 by TD-343.

## C-12 Review loops and rounds

**Rows:** decided TD-71, TD-74, TD-123, TD-124, TD-175, TD-176, TD-190, TD-193, TD-208, TD-209, TD-212, TD-215,
  TD-219, TD-220, TD-235, TD-323, TD-330, TD-331, TD-332; autonomous TD-187, TD-189, TD-205, TD-207, TD-211,
  TD-213, TD-218, TD-233, TD-237, TD-253, TD-322, TD-380.

- Three reviews: each task's build, the Change's end, the visual check; challenger and subagent judgements are not
  kept. The final review covers a task's last repair, CI and the PR the final loop's [TD-71, TD-74, TD-332].
- Build, final, plan, pack and brief loops have per-role settings: 3 rounds, 10 new findings per round, last round at 4
  or fewer, owner at 7 or more [TD-209, TD-211, TD-213, TD-220, TD-221].
- The final review uses the builder's round settings unless its own are set [TD-211].
- Repairs, progress and failures never reset a subject's round limit. From round 2, judge prior rejections and new
  findings, no other earlier ones; disputed rejections go to the owner before repair [TD-208, TD-323, TD-330].
- A worker's reasoned rejection gets one independent fresh-session recheck, counted apart from repair rounds,
  before the owner is asked; if upheld, the owner is asked [TD-124, TD-176, TD-330].
- At or below the last-round threshold, end early. Every final round gets a rejections-only check outside the round
  count, with no new findings; disputed rejections go to the owner [TD-208, TD-233, TD-330].
- Repairs after the last round stay unreviewed and are shown with standing rejections. Only at max rounds with the
  owner threshold of new findings does he choose another round or reject and retry [TD-208, TD-233].
- The producing session gets one repair chance (final review: a fresh one, reused once), then a fresh session;
  an unresumable one is replaced, recorded, budgets unchanged [TD-123, TD-175].
- A fresh session that takes over a repair gets Delivery's own records, never the transcript [TD-187, TD-322].
- The planner may reject plan-challenge findings with reasons, the same way as the builder and the pack updater
  [TD-190, TD-220].
- For an upheld rejection the owner chooses per finding Fix, Reconsider or Drop, never Pause; Reconsider needs a
  note and runs once per finding, outside rounds [TD-193, TD-219].
- A note contradicting the brief is held; Drop never waives a criterion and reopens only on new evidence; after
  Fix only a wrong premise may be raised [TD-193, TD-219].
- Reconsidering may clarify or withdraw, never enlarge; an unsure finding returns once, then only Fix or Drop. Owner
  notes travel whole; owner-decided repairs commit; drops reach only outside reviews [TD-193, TD-205, TD-323].
- Added work is never reviewed twice: each later addition gets one final round beyond max, judging unjudged rejections,
  new commits in focus, not blind to the rest; task additions go to its next round [TD-215, TD-235, TD-237, TD-331].
- Only the owner may restart a review loop for a large addition; restarting retires open questions and merge
  consent [TD-215, TD-235, TD-237].

**Owner's words:**

- TD-71, 2026-10-14: "no we dont keep what challenger and subagent judge"
- TD-74, 2026-10-14: "agree theres a review for each task build and at the end of a change"
- TD-123, 2026-10-15: "Sol's modified C, per loop as listed"
- TD-124, 2026-10-15: "Independent recheck first, then ask me"
- TD-175, 2026-10-16: "Fresh session with the old session's transcript summary attached; recorded; budgets unchanged"
- TD-176, 2026-10-16: "One fresh-session recheck; counted separately; if upheld, I'm asked"
- TD-190, 2026-10-16: "Build the planner's rejections next, the same way"
- TD-193, 2026-10-16: "Sol's three without Pause"
- TD-208, 2026-10-17: "i dont want round 3 rejections to go to me … we only do three rounds"
- TD-209, 2026-10-17: "3/10/4/7"
- TD-212, 2026-10-17: "postponed"
- TD-215, 2026-10-17: "also possible for the user to just restart the loop via button"
- TD-219, 2026-10-17: "Keep it as built; it runs only when you pick it and never counts as a round"
- TD-220, 2026-10-17: "All three now, inside the current TD-208 build"
- TD-235, 2026-10-17: "what i def dont want is two different review/challenge rounds for the same work"
- TD-323, 2026-10-18: "As built: loop reviewers judge rejections only; dropped findings reach reviews outside a loop"
- TD-330, 2026-10-18: "td218 is bs. 124 and 176 generally stand"
- TD-331, 2026-10-18: "Each later addition gets one round beyond the maximum, as built"
- TD-332, 2026-10-18: "TD-74 counts reviews per task and Change"

**Replaced:** TD-71 by TD-74; TD-175 by TD-187; TD-189 by TD-208; TD-193 by TD-208, TD-219, TD-323; TD-205 by
  TD-380; TD-207 by TD-208, TD-219; TD-212 by TD-219, TD-220, TD-236, TD-330; TD-218 by TD-330; TD-233 by TD-323;
  TD-237 by TD-245.

## C-13 Retry and Accept as done

**Rows:** decided TD-210, TD-214, TD-216, TD-217, TD-341; autonomous TD-245, TD-246, TD-252, TD-324.

- Retry uses a fresh builder and the plan; final-review retry selects tasks or replans from the brief. Archive
  rejected attempts, never delete them [TD-210].
- A retry of published work keeps the same PR: Delivery adds commits that undo the rejected work and rebuild it,
  never force [TD-214].
- Final-review findings identify their plan tasks; several are allowed, or none only with a reason [TD-216].
- The owner selects tasks to rebuild; selecting none accepts the remaining findings as the owner's decision and
  continues to publishing [TD-217].
- "Accept as done" names in its confirmation the criteria the remaining findings report unmet; confirming accepts
  them as the owner's decision [TD-341].
- Show task-review and final-review status separately per task, distinguishing open findings, unverified repairs
  or rejections, and settled findings [TD-217].
- Finding details must work by keyboard and touch, not hover alone; show unreviewed repairs and standing
  rejections [TD-217, TD-252].
- After a rebuild, the last rebuilt task's builder runs every kept task's checks and fixes failures, reviewed in its
  rounds; CI stays the second net [TD-246, TD-324].

**Owner's words:**

- TD-214, 2026-10-17: "Keep the same PR"
- TD-216, 2026-10-17: "it always names the task that is attached to a finding"
- TD-217, 2026-10-17: "tick = rebuild … not disabled at zero: why not keep everything?"
- TD-341, 2026-10-18: "Accept as done names the unmet criteria in its confirmation"

**Replaced:** TD-217 by TD-246.

## C-14 Brief, approval and amendments

**Rows:** decided TD-73, TD-122, TD-179, TD-181, TD-185, TD-221, TD-236, TD-249, TD-255, TD-422; autonomous TD-254.

- The brief review is a challenge, not a review, named "brief challenge" [TD-73].
- Challenge the brief before approval; the shaper may revise or reject with reasons. Apply the shaper's round
  settings and show standing rejections at approval; no post-approval challenge [TD-208, TD-221].
- The shaper requests a challenge when the saved draft is ready [TD-249, TD-254].
- Approval requires the current brief to be challenged, except an unreviewed last-round revision the owner
  explicitly accepts in the approval dialog [TD-249, TD-255].
- Approval foregrounds outcome, owner decisions with origins, and non-goals; criteria, visual and person checks
  stay under collapsed technical details [TD-122, TD-179].
- Levels follow origin, not field: the owner's direct choices are `decided`, generated items in the approval
  `approved`, later implementation choices `autonomous`; authorship and authority are recorded [TD-179].
- Approve is a bounded delegation: the dialog says it authorises the work and intent-preserving changes, not new
  product commitments [TD-179].
- Weaker means what could now pass that failed before, judged cumulatively [TD-179].
- Only a redundant or over-specific generated check may be replaced, with independent evidence of equal coverage, else
  ask the owner; check tightening for scope, cost; never edit a check for a failing build [TD-179].
- Anyone proposes, the artifact's owner prepares, an independent challenger judges the exact change; doubt about
  intent goes to the owner. Existing loops and limits apply, changes batched per challenge [TD-179].
- Scope of amendments: criteria, UI flag, visual states, person checks, constraints, assumptions; plan tasks and
  test commands stay autonomous [TD-179].
- The approved baseline is kept; every later change is listed (old → new, reason, level, challenger); an objection
  pauses dependent work; undo is promised only where possible [TD-179].
- Design amendments end to end before adding amendment code; until then proposals may be challenged and recorded
  but must not be applied [TD-181, TD-185].

**Owner's words:**

- TD-73, 2026-10-14: "for me it feels like a challenge"
- TD-122, 2026-10-15: "list the decisions instead and maybe hide the ac and tests behind a rolldown menu"
- TD-179, 2026-10-16: "we already have a three level hardness for decisions … transport this same system to this"
- TD-181, 2026-10-16: "Tonight: page (rules 1, 2, 7, 8 display) in item 5"
- TD-185, 2026-10-16: "this needs to be designed end to end, not as this tiny part"
- TD-221, 2026-10-17: "option 2 (brief is challenged before approval)"
- TD-236, 2026-10-17: "'Designer' meant the shaping of the brief (already TD-221), not the UI judge"
- TD-249, 2026-10-17: "The shaper requests the challenge once the draft is ready"
- TD-255, 2026-10-17: "Approvable, but the approve dialog makes me tick that I accept the unreviewed last revision"
- TD-422, 2026-10-20: "Before item 10: after the watcher, so the first real project has amendments"

**Replaced:** TD-249 by TD-255.

**Open:**

- The end-to-end amendment design (TD-185), its session with the owner before item 10, after the watcher [TD-422].
- Known gap: a builder's or reviewer's proposal sends the Change back to planning against the unchanged brief.

## C-15 Design pack update

**Rows:** decided TD-76, TD-101, TD-125, TD-177, TD-194, TD-256, TD-325, TD-357, TD-368, TD-414; autonomous TD-270,
  TD-273, TD-290, TD-381.

- Extract Impeccable once into Delivery's own design skill; do not install it [TD-76, TD-101].
- Settings offers one update for detector and skills together, with affected checks and an independent challenge
  of the whole pack [TD-101, TD-113].
- The pack updater writes its candidate and implements accepted findings, using its own configurable role
  [TD-123, TD-125].
- The updater may change its whole candidate, but only in its own folder and without shell access; read upstream
  skills at the pinned revision [TD-194, TD-273].
- A change to the detector's or adapter's code is checked with the running code; the owner approves its diff and
  CI's unit tests must pass [TD-194, TD-414].
- Affected checks rerun after its edits; changing expected evidence (golden expectations, calibration) asks the
  owner [TD-177].
- The challenger checks each change is needed by the upgrade and asks the owner when unsure, with every changed file
  and one line per file on what changed and why it is suspicious [TD-194].
- Its challenge rounds follow C-12's loop with the updater's values [TD-193, TD-220, TD-323, TD-330].
- Without a pass, stop before activating and ask: activate the unreviewed repair or discard. Another round only at
  max rounds with the owner threshold of findings; Discard whenever waiting [TD-208, TD-256, TD-273].
- Every pack update opens a PR; its merge activates it as machines take the version. The challenger's pass, owner
  approval of detector code changes and his word on an unreviewed repair gate it [TD-194, TD-256, TD-302, TD-357].
- Its PR gets OwlBear's PR labels and becomes a version as they say [TD-307, TD-308].
- Owner-started pack updates run at once and end to end, paused or not: commit, PR, CI, merge on green; failure asks
  the owner. Started paused, the machine takes the version at once [TD-287, TD-325, TD-368].
- One design pack update runs at a time on the machine; every project's pack page shows it and names who started it
  [TD-290].
- A pack update whose package skill changed since it started stops, so its PR holds only what was challenged
  [TD-381].

**Owner's words:**

- TD-76, 2026-10-14: "extract"
- TD-101, 2026-10-14: "extract once, have a button that updates it"
- TD-125, 2026-10-15: "shouldnt the challenger return the result to the updater and the updater implements them"
- TD-177, 2026-10-16: "changing expected evidence (golden, calibration) asks me"
- TD-194, 2026-10-16: "Anything in its copy; … a code change waits for your approval"
- TD-256, 2026-10-17: "Stop before activating … activate the unreviewed repair, or discard the update"
- TD-325, 2026-10-18: "it runs fully end to end, including merge"
- TD-357, 2026-10-18: "Activation is the merge"
- TD-368, 2026-10-18: "It merges itself once CI passes, paused or not"
- TD-414, 2026-10-20: "A: the run checks with the running code; you approve the glue diff; CI's unit tests …"

**Replaced:** TD-76 by TD-101; TD-101 by TD-302, TD-357; TD-125 by TD-302, TD-357; TD-177 by TD-194; TD-194 by
  TD-357; TD-273 by TD-357; TD-302 by TD-307.

## C-16 Versions, labels and release

**Rows:** decided TD-298, TD-302, TD-306, TD-307, TD-308, TD-310, TD-354, TD-355, TD-356, TD-392, TD-393, TD-404;
  autonomous TD-240, TD-314, TD-315.

- Tags are versions; "stable" means major versions only, the channel for those afraid of a broken build [TD-354].
- A major version's commit gets two tags, `vN.0` and `vN` (the first `v1.0` and `v1`) [TD-392].
- OwlBear becomes v1.0 after the self-update and the old engine's removal, with its documentation rewritten
  [TD-393].
- Only labels on merged OwlBear `main` PRs make versions: `release:minor` the next minor, `release:major` the next
  major; no label, even a forgotten one, makes none; both make a major [TD-306, TD-356].
- A workflow makes the tag once that merge commit's own CI passes [TD-302, TD-306].
- Tags are created with a fine-grained token the owner makes (this repository; Contents and Workflows write) and
  stores as the Actions secret `RELEASE_TOKEN`; it serves only that [TD-404].
- No label is checked or protected; no CI check asks for or checks a label [TD-306, TD-307].
- Minors may be unproven. `release:major` alone makes a major version; testing a minor first is the owner's, not
  an enforced gate [TD-302, TD-307, TD-355].
- A global list sets the labels on every OwlBear-opened PR; a project may replace it whole. Empty at first;
  OwlBear's own project sets `release:minor` [TD-243, TD-308].
- Projects may suppress OwlBear's PR attribution line [TD-308].
- A design pack update's pull request gets those labels and becomes a version as they say [TD-307].
- Renovate sets no release label; the owner labels dependency PRs to release them. Others reach machines with the
  next labelled merge [TD-310].
- Chat-authored OwlBear PRs get `release:minor` for runtime changes, none for docs or tests; `release:major` only
  on the owner's word [TD-314].

**Owner's words:**

- TD-298, 2026-10-18: "No count or days: green CI and one finished Change, then it asks you"
- TD-302, 2026-10-18: "i see no problem in setting tags for unproven versions, as long as these are minor versions"
- TD-306, 2026-10-18: "nl label is the same as release:none, even if it a=was just forgotten"
- TD-307, 2026-10-18: "this is defending against an imaginary but nonexistent attacker"
- TD-308, 2026-10-18: "projects can use this to mark a pr from owlbear to whatever it likes"
- TD-310, 2026-10-18: "No label in config; you label by hand when you want it released"
- TD-354, 2026-10-18: "Call them versions; 'stable' means major versions only"
- TD-355, 2026-10-18: "release:major alone makes a major version; testing a minor first is yours, nothing checks it"
- TD-356, 2026-10-18: "Major wins"
- TD-392, 2026-10-19: "The major commit gets both tags, v1.0 and v1"
- TD-393, 2026-10-19: "After the self-update and the old engine's removal, with the docs rewritten"
- TD-404, 2026-10-19: "A fine-grained token you create, secret RELEASE_TOKEN, used only to create tags"

**Replaced:** TD-240 by TD-298, TD-302; TD-298 by TD-302; TD-302 by TD-306, TD-307, TD-355.

## C-17 Runtime and self-update

**Rows:** decided TD-239, TD-289, TD-297, TD-299, TD-300, TD-301, TD-352, TD-353, TD-369; autonomous TD-247,
  TD-296, TD-305, TD-309, TD-415.

- Run one installed OwlBear runtime per machine under `~/.owlbear`, never a developer checkout [TD-239, TD-247].
- Never track `main`. Automatically take the newest version in the machine's chosen channel: every minor by
  default, or majors only [TD-239, TD-300, TD-354].
- The runtime never moves backwards on its own [TD-239].
- No real project may use OwlBear before the watcher exists, including for SDK steps [TD-297, TD-338].
- A machine set to major versions only starts at the newest major; until `v1.0` exists that is `v0.1` [TD-369].
- Idle for a self-update: no agent step, check environment or pack update runs in any project, no page or chat used
  for 15 minutes, and open pages announce it 2 minutes ahead with Postpone [TD-301].
- Update when idle and Update while paused start on; automatic updates obey both; Run updates now still works,
  as does an owner's pack update started while paused [TD-288, TD-325, TD-352].
- Run updates now skips the 15 minutes without use and the announcement, and waits for running steps, check
  environments and pack updates to end [TD-353].
- After an update, Delivery comes back as it was (running stays running, paused stays paused), and the page tells
  the owner once which version it now runs [TD-299, TD-350].
- After each merge, Run updates now (`owlbear update`) takes the tagged version; a failed update is repaired forward by
  hand (recommendation taken once step 4 was built and rehearsed) [TD-299, TD-309, TD-350, TD-415].
- Deploying sessions need not re-review merges from the owner's other sessions; report which such merges are
  included [TD-309].
- A self-update switches only after the new version answered in a standby; a later failure restarts it once and tells
  the owner [TD-305].

**Owner's words:**

- TD-239, 2026-10-17: "runtime in .owlbear, auto-update to newest tag when idle"
- TD-289, 2026-10-18: "After each Sol-accepted merge, stop, update, start and press Resume myself, as I did"
- TD-297, 2026-10-18: "Create and push the annotated tag v0.1 at 8ebc00afe now"
- TD-299, 2026-10-18: "As it was, and the page tells you once which version it now runs"
- TD-300, 2026-10-18: "never track main"
- TD-301, 2026-10-18: "Nothing runs, no page or chat used for 15 minutes, and open pages announce it 2 minutes ahead"
- TD-352, 2026-10-18: "your button still updates"
- TD-353, 2026-10-18: "It skips the 15 minutes and the announcement, and waits for running steps"
- TD-369, 2026-10-18: "A major-only machine starts at the newest major; until v1.0 exists that is v0.1"

**Replaced:** TD-239 by TD-241, TD-242, TD-300, TD-302, TD-306, TD-354; TD-247 by TD-289; TD-289 by TD-309,
  TD-350; TD-296 by TD-305; TD-297 by TD-354; TD-309's deploy by hand by TD-415.

## C-18 Pause, stop and resume

**Rows:** decided TD-259, TD-287, TD-288, TD-350, TD-351, TD-397; autonomous TD-282, TD-283, TD-284, TD-303,
  TD-304, TD-313.

- Login and post-crash starts are paused; a start from stopped runs; restarts and updates keep their running or
  paused state; a paused start on purpose remains possible [TD-299, TD-350].
- While paused, Delivery continues no Change by itself until the owner presses Resume in the UI, which shows how
  many Changes would continue; opening the UI or a chat grants nothing [TD-259, TD-350].
- The pause holds Delivery's automatic work on Changes; the owner's own actions and the listed maintenance run
  [TD-287, TD-351].
- Pause never blocks owner-triggered actions, automatic maintenance, or a new Change's shaping session [TD-287].
- A test review is a regular Change: the owner may start it while paused, its steps wait for Resume, and its
  dialog says so [TD-397].
- Cleanup runs fully while paused, including branch deletion, PR closure and pull-back; automatic Change publishing
  and merging wait for Resume [TD-303, TD-325, TD-351].
- Answers and approvals take effect and show as answered immediately; resulting automatic Change work waits for
  Resume [TD-283, TD-351].
- The pause is shown prominently at the top of every page (with Resume), never by pausing each Change [TD-287].
- Paused pages offer Resume and Run updates now; updates also run pending maintenance but wait for pre-pause steps,
  with the reason shown [TD-288].
- Offer separate Pause and "Pause and stop when idle". The latter starts no work, waits for all projects' steps,
  then stops; tooltips say plain Pause may still update [TD-288].
- With Update while paused off, hide "Pause and stop when idle"; manual updates remain available
  [TD-288, TD-352].

**Owner's words:**

- TD-259, 2026-10-17: "Paused until I press Resume in the UI, which shows how many would continue"
- TD-287, 2026-10-18: "any maintenance action including pack update, self update, any cleanup"
- TD-288, 2026-10-18: "option 4, plus a global setting if to update while paused and if to update while idle"
- TD-350, 2026-10-18: "only a login start and after a crash owlbear is paused"
- TD-351, 2026-10-18: "The pause holds Delivery's automatic work on Changes"
- TD-397, 2026-10-19: "You can start it while paused; its dialog says its steps wait for Resume"

**Replaced:** TD-259 by TD-350; TD-282 by TD-350, TD-351; TD-283 by TD-350, TD-351; TD-288 by TD-352; TD-304 by
  TD-352; TD-313 by TD-350.

## C-19 Machine host and UI

**Rows:** decided TD-11, TD-85, TD-104, TD-113, TD-241, TD-242, TD-262, TD-265, TD-281, TD-321, TD-416, TD-420,
  TD-421, TD-431, TD-432, TD-433, TD-443; autonomous TD-294.

- One Delivery host per machine serves every registered project (one dashboard, one process); registered projects
  keep advancing while their folders are closed [TD-104, TD-242].
- Isolate each project's stores, worktrees, repository and credentials; one project's failure must not stop
  others [TD-242].
- One repository per Change (a backlog entry may name several or none); Change groups are dropped
  [TD-103, TD-104, TD-241].
- Adding projects requires an explicit UI action; opening VS Code must not start or alter Delivery
  [TD-281, TD-321].
- Install chat-tool configuration only with consent; commit nothing from OwlBear into consumer projects
  [TD-11, TD-321].
- The optional agent workspace (`setup/init.py`) asks before writing and hides its files from Git, so nothing shows
  as new [TD-420].
- Add project offers an existing folder or a new project; the installer may open it at its end [TD-421].
- A new project gets folder, name, Git identity, an optional GitHub repository, Delivery's chat tools (with consent),
  the agent workspace, the first commit and push; designed before built [TD-421].
- The new-project dialog asks visibility first and warns only when the account's plan cannot protect a private
  repository; CI and protection are ticked and recommended, the agent workspace ticked [TD-431, TD-432].
- A project created this way is a real project: Delivery's work on it waits for the watcher [TD-433, TD-338].
- Organise one machine-wide UI by work, not project mode; tag items and actions with their project and offer
  project, Global and All filters [TD-241].
- Keep maintenance next to its data, with an overview linking actions and runs: memory in Memory, pack and engine
  updates in Settings, test review per project [TD-113].
- Mac first: Linux and Windows are clearly stated as not supported yet before OwlBear goes to a colleague [TD-262].
- The machine host's web UI is the one UI (TD-85's "cockpit" meant it); the old Cockpit was audited, its memory purge
  ported and Cockpit deleted before v1.0 [TD-416].
- TD-85's module tabs are done; its end-to-end review of the pages' user flows and information and their visual
  overhaul are one backlog entry [TD-443].
- Keep live Change data in per-project SQLite databases under `~/.owlbear`; git-shared owlbear-data remains files
  [TD-265, TD-334].

**Owner's words:**

- TD-85, 2026-10-14: "cockpit needs tabs for the other modules again: memory"
- TD-104, 2026-10-14: "lets do one instance of owlbear for multiple consumer projects on the same computer"
- TD-113, 2026-10-15: "1, but maintenance overview now"
- TD-241, 2026-10-17: "subpages have a filter for each project or the global view with everything"
- TD-242, 2026-10-17: "One host for the machine serves every registered project"
- TD-262, 2026-10-17: "Mac first; Linux and Windows clearly stated as not supported yet"
- TD-265, 2026-10-17: "Move to SQLite as part of TD-242 (the machine host)"
- TD-281, 2026-10-17: "Opening a window never touches Delivery; projects are added only in the UI"
- TD-321, 2026-10-18: "TD-281 replaces TD-11's task; TD-11 keeps: .mcp.json only with consent, nothing committed"
- TD-416, 2026-10-20: "Audit Cockpit; delete it at once if nothing is worth porting … at the latest at v1.0"
- TD-420, 2026-10-20: "Keep it optional; it asks before writing and hides its files from Git"
- TD-421, 2026-10-20: "set up a new local folder, optionally with the installer, and create the repo … a gui workflow"
- TD-431, 2026-10-20: "we first ask if repo should be private or public, and in that choice we already warn"
- TD-432, 2026-10-20: "Offered in the dialog, ticked by default"
- TD-433, 2026-10-20: "no" (Delivery does not work on a new project before the watcher)
- TD-443, 2026-10-21: "Tabs done; the UX review and the visual overhaul become one backlog entry"

**Replaced:** TD-11 by TD-281; TD-242 by TD-281; TD-85 by TD-416 and TD-443.

## C-20 Repository policy

**Rows:** decided TD-10, TD-15, TD-16, TD-25, TD-26, TD-30, TD-155, TD-203, TD-204, TD-222, TD-226, TD-229, TD-230,
  TD-231, TD-238, TD-251, TD-319, TD-326, TD-362, TD-363, TD-379, TD-382, TD-407, TD-408, TD-409, TD-410, TD-411,
  TD-412, TD-413, TD-447; approved TD-280; autonomous TD-22, TD-278, TD-360, TD-361.

- One long-lived default branch, `main`, holds all source; consumers clone it and versions are tags
  [TD-203, TD-231].
- OwlBear builds itself through its own Delivery, with a manual repair PR when Delivery is broken; direct chat
  development stays allowed beside it for good. No downloadable releases [TD-238, TD-319].
- OwlBear `main` accepts PRs only, with required CI and strict up-to-date checks, merge commits, no bypass actor,
  and protection from deletion or history rewrites [TD-278, TD-280, TD-326].
- No OwlBear merge queue on the personal account; move to a free organization with a queue when another
  contributor arrives or Delivery builds OwlBear [TD-278, TD-326].
- Delivery merges automatically once every gate passes, including no unanswered comments or open discussions, and
  pulls the result back to the local clone; the sandbox keeps merging automatically [TD-15, TD-155, TD-238].
- The assistant merges PRs at the right time, with merge commits, not squash, so commits the records cite stay
  reachable [TD-229, TD-280].
- Pull-back assumes the local copy is dirty and updates it reliably without conflicts, by rebase where needed,
  without losing local work [TD-26].
- When the target lacks "require branches to be up to date" or "require conversation resolution", Delivery shows
  a visible note, not a warning, and behaves as if they were on [TD-25].
- Automate CI fixes and PR feedback, including replies and resolving fixed threads. Ask the owner for upheld
  rejections, brief-contradicting notes, or CI still failing after fix retries [TD-16, TD-193, TD-340, TD-379].
- Every human PR comment is answered; the agent judges bot comments (acts on real findings, records "no action
  needed" for notices); no `@owlbear` mention gate [TD-30].
- Keep CI and Renovate enabled, other automatic workflows disabled, and pre-commit hooks manual [TD-204, TD-280].
- Keeping disabled workflows' files only eased building Delivery-next; it binds nothing, so retired tooling may be
  deleted [TD-407].
- The pre-commit config is the one linter list: CI runs `uv run lint --no-fix` on every change, MegaLinter is retired,
  and Renovate updates the linters together in one weekly pull request [TD-409].
- pre-commit.ci is not installed: its hook updates cannot be switched off and would compete with Renovate [TD-410].
- CodeRabbit reviews quietly as `.coderabbit.yaml` sets, the review brief its guideline, early access off [TD-411].
- CodeRabbit reviews a PR once, when it gets the `coderabbit` label, whoever opened it; CodeRabbit never replies on
  its own [TD-412, TD-413].
- Agents label a PR that changes runtime code or CI workflows once its CI passed and merge it only after the review is
  in and handled, or after 60 minutes without one, said in the PR; others merge after CI and Sol's review [TD-447].
- Snyk is required CI for OwlBear only, never consumer projects: only Snyk Code, high severity and above, no
  monitor or report writes, findings logged actionably [TD-360, TD-363, TD-382].
- Snyk does only what it specialises in or what is free: no dependency scan; Renovate alone updates dependencies,
  fed by Dependabot alerts, and Dependabot opens no PRs; the Snyk app's PR checks are off [TD-382, TD-408].
- Snyk uses the least service-account role until a read-only tester role exists; only the owner creates and sets
  its secret; scans change ignores only via the owner-checkbox handler [TD-360, TD-361, TD-363].
- Owner ticks mark Snyk Code false positives "Not vulnerable" and rerun CI; the lead chat may tick too. The
  screenshot route's Path Traversal ignore does not expire [TD-362, TD-363].

**Owner's words:**

- TD-10, 2026-10-10: "i dont need it to work on itself"
- TD-15, 2026-10-10: "letting the agent/delivery also merge automatically"
- TD-155, 2026-10-15: "Keep automatic merging"
- TD-16, 2026-10-10: "fix ci, react to comments including reviews"
- TD-25, 2026-10-10: "make it a visible note, but not a warning"
- TD-26, 2026-10-10: "we have to assume local copy is never clean"
- TD-30, 2026-10-11: "suggestion 2 is accepted"
- TD-203, 2026-10-16: "rename dev to main"
- TD-204, 2026-10-16: "just deactivate all workflows and precommit hooks"
- TD-222, 2026-10-17: "you can remove the snyk workflow"
- TD-226, 2026-10-17: "Build merge-queue support now"
- TD-229, 2026-10-17: "you take care of merging prs, i.e. 449, at the right time"
- TD-230, 2026-10-17: "yes remove the snyk token"
- TD-231, 2026-10-17: "Merge now; I look at the finding in Snyk's project later and tell you"
- TD-238, 2026-10-17: "2 is better than 3"
- TD-251, 2026-10-17: "Keep everything off until the pull-request Change, which switches CI on as part of its flow"
- TD-319, 2026-10-18: "TD-238 replaces TD-10, but chat work stays allowed beside Delivery for good"
- TD-326, 2026-10-18: "a free organization and the queue once someone else contributes or Delivery builds OwlBear"
- TD-362, 2026-10-18: "Make the CI scan match your setting with `--fail-on=upgradable`"
- TD-363, 2026-10-18: "this is only for owlbear, not for consumer projects"
- TD-382, 2026-10-18: "Renovate is first. we dont use dependabot … we dont pay for what renovate gives us free"
- TD-379, 2026-10-18: "Also when a CI check keeps failing after the fix retries"
- TD-407, 2026-10-19: "it was an instruction for the easier implementation of delivery next for now, nothing more"
- TD-408, 2026-10-19: "turn on dependabot alerts, with no dependabot i meant no dep updating by dependabot"
- TD-409, 2026-10-19: "m2" (retire MegaLinter; the pre-commit config is the one linter list, run in CI)
- TD-410, 2026-10-19: "p1" (uninstall pre-commit.ci)
- TD-411, 2026-10-19: "coderabbit config looks good … early access off, good call"
- TD-412, 2026-10-19: "agents or workflows may set the tag" (on code or CI PRs once CI passes; no auto-reply)
- TD-413, 2026-10-20: "Remove the exclusion, so the label alone decides for every author"
- TD-447, 2026-10-21: "A and B: wait only for runtime code PRs" (wait up to 60 minutes, then merge with a note)

**Replaced:** TD-10 by TD-238, TD-319, TD-337; TD-16 by TD-379; TD-22 by TD-226; TD-204 by TD-230, TD-280, TD-360;
  TD-412's labelling by TD-447;
  TD-222 by TD-360; TD-230 by TD-360; TD-238 by TD-278, TD-326; TD-251 by TD-280; TD-278 by TD-326;
  TD-360 and TD-362 by TD-382.

**Open:**

- TD-231: the Snyk Code "1 new Code Analysis issue" is for the owner to read in Snyk later; TD-362 ignores one
  Code finding (the screenshot route's Path Traversal), but no row says whether that was TD-231's issue.

## C-21 Old engine retirement

**Rows:** decided TD-2, TD-183, TD-199, TD-200, TD-201, TD-202, TD-337.

- The Delivery redesign programme is superseded by the new engine [TD-202].
- The old Delivery leaves in dependency-closed batches, each deleting old paths with their tests and unwiring edits
  in one revertible commit; tag `delivery-v1-final` before the first; no `main` sync batch [TD-199, TD-203].
- `h-decision-requests`, `h-process-observations` and `w-deviation-audit` retire with batch 3, once checked that
  the new engine holds what they offer [TD-201].
- `interactive-browser-tools` stays in issue #233; its brief is written only when OwlBear develops itself on
  the new engine [TD-200].

**Owner's words:**

- TD-2, 2026-10-10: "i do want to finish the open changes"
- TD-183, 2026-10-16: "we can start deleting things from dev the moment we have transferred it into the new version"
- TD-199, 2026-10-16: "Six dependency-closed batches"
- TD-200, 2026-10-16: "Keep it in issue #233"
- TD-201, 2026-10-16: "make sure there is nothing in there of any value to us that we can re-use, then option 1"
- TD-202, 2026-10-16: "Delete it now … the redesign programme is superseded"
- TD-337, 2026-10-18: "old changes were implemented and are now on main after being on dev earlier."

**Replaced:** TD-2 by TD-337; TD-183 by TD-199, TD-200, TD-201, TD-202 and TD-203; TD-199 by TD-203; TD-202 by TD-337.

## C-22 Package structure

**Rows:** decided TD-133, TD-168, TD-171, TD-172, TD-173, TD-174, TD-186, TD-191; autonomous TD-158, TD-196,
TD-197.

- Group files by responsibility or kind, named for their readers; keep role agents and skills top-level, without a
  content umbrella [TD-133, TD-168].
- Each package folder holds one responsibility and imports only folders before it in the layer order; a test enforces
  it [TD-171].

**Owner's words:**

- TD-168, 2026-10-16: "No umbrella: agents/ and skills/ at the package root next to web/ and golden/"
- TD-171, 2026-10-16: "As shown, with the three code moves; built with Sol review"
- TD-172, 2026-10-16: "Sol's names as listed"
- TD-173, 2026-10-16: "2, and the owlbear-next script also points at that dispatcher"
- TD-174, 2026-10-16: "step_input"
- TD-186, 2026-10-16: "make sure [the import chain] is still valid"
- TD-191, 2026-10-16: "Same rule as TD-186: one path, spend.py only"

**Replaced:** TD-133 by TD-168; TD-158 by TD-168; TD-196 by TD-274.

## C-23 The owlbear command

**Rows:** decided TD-257, TD-258, TD-263, TD-327; autonomous TD-272.

- One `owlbear` command manages the machine's one instance: with no arguments it starts it if stopped, else shows
  its status. No VS Code button [TD-242, TD-257].
- Use Cyclopts: instant completion without starting Python, no shell startup-file edits, and lazy commands
  [TD-173, TD-257, TD-263, TD-327].
- Ask about starting at login once at install; allow later CLI opt-in/out and show it in the CLI and settings. If
  macOS blocks it, say so and keep on-demand use [TD-258].

**Owner's words:**

- TD-257, 2026-10-17: "start default if not running, status default if running … def no vs code button"
- TD-258, 2026-10-17: "ask at install and offer a cli cmd to activate/deactivate it"
- TD-263, 2026-10-17: "Cyclopts: a static completion file, so TAB is instant; lazy commands"
- TD-327, 2026-10-18: "Cyclopts, as decided in TD-263"

**Replaced:** TD-257 by TD-263; TD-272 by TD-327.

## C-24 Backlog

**Rows:** decided TD-84, TD-103, TD-126, TD-345, TD-405, TD-406.

- Collect potential changes in an evidence-linked inbox; the owner classifies them, adds context, connects several
  and creates linked Changes [TD-84].
- Backlog entries are private GitHub issues in `owlbear-data`, never public, with scope and `project:<name>` labels
  (OwlBear's colour `#A67C52`); saving is online-only; file storage retires after migration [TD-103].
- Repeats are counted in a summary in the issue, comments only for new evidence [TD-103].
- Entries may name several projects or none. Repeats merge only when they name the same projects (or both none);
  otherwise they are linked [TD-126, TD-241, TD-345].
- A finding names the project it was found in, none outside any; an untriaged entry names its origin; they merge
  only on equal sets [TD-406].
- A repeat that does not merge is linked to every matching entry at once; the owner can unlink it [TD-405].

**Owner's words:**

- TD-84, 2026-10-14: "when potential for improvement or changes is identified … this should be collected"
- TD-103, 2026-10-14: "i think we should drop public altogether … offline = no agents = no work possible"
- TD-126, 2026-10-15: "Merge only within a project"
- TD-345, 2026-10-18: "Repeats merge only when they name the same projects (or both none); otherwise they are linked"
- TD-405, 2026-10-19: "Delivery links the new entry to every matching entry at once; you can unlink"
- TD-406, 2026-10-19: "A finding names its project (none outside any); an untriaged entry names its origin"

**Replaced:** TD-84 by TD-103; TD-126 by TD-345.

## C-25 Memory

**Rows:** decided TD-70, TD-72, TD-100, TD-292, TD-293, TD-399, TD-400; autonomous TD-291, TD-318.

- Agents recall owlbear-memory at the start, never pending entries. Producing roles and the pack updater save
  non-obvious lessons for curation; judges only recall [TD-70, TD-293, TD-399].
- Project memory lives in the project's folder of the shared data repository, never in the working repository
  [TD-57, TD-72].
- Project-specific lessons stay in the project; general ones go to Global. The saving agent recommends the scope;
  the entry waits unused in its project until curated [TD-293].
- The owner makes a curated or approved entry global on the Memory page; it moves, and can be moved back to its
  project [TD-292].
- Above one Global confidence threshold (95% at first) the curator decides alone, Make global included; below it, it
  asks (interactive mode) or skips (automatic mode); interactive sessions propose Make global [TD-292, TD-293, TD-400].
- The watcher may save pending, role-scoped lessons about observed agent behaviour, curated like other memory
  [TD-100].
- With a project chosen, the Memory page shows its memory and Global memory, each labelled where it is kept
  [TD-291].

**Owner's words:**

- TD-70, 2026-10-14: "the agents will still use owlbear-memory"
- TD-72, 2026-10-14: "yes, move memory to the common repo"
- TD-100, 2026-10-14: "plus watcher may write memories from watched actions"
- TD-292, 2026-10-18: "mem-curator should have 2 ways to work … 2 plus threshold is a setting"
- TD-293, 2026-10-18: "we should only decide based on the mem … an agent saving can give a recommendation (=pre-set)"
- TD-399, 2026-10-19: "producers save, judges only recall; the updater gets both"
- TD-400, 2026-10-19: "Keep it at 95% at first, as one Global setting"

**Replaced:** TD-72 by TD-291, TD-292 and TD-293; TD-70 by TD-399; TD-292 by TD-400.

**Open:**

- After v1.0 (TD-394): the curator's two modes and threshold setting, moving an entry back to its project, the
  saving agent's pre-set and sorting the existing project memories once by the rule [TD-292, TD-293, TD-318].

## C-26 Tests

**Rows:** decided TD-3, TD-112, TD-311, TD-312, TD-339, TD-370, TD-371, TD-372, TD-373, TD-390.

- Proof over test volume: automated tests are build artifacts and stay minimal; test agent structure, never prose
  wording [TD-3].
- Reviewers split the test files and only report; the curator checks their retire and merge verdicts against the
  code, applies what holds in a reviewed Change the owner can still stop, then measures again [TD-311, TD-339, TD-372].
- A test review starts only on the owner's request, for each registered project from its own Maintenance page; a
  Sol challenge settles the button's place when built [TD-370, TD-371].
- A test review's brief and one-task plan are fixed; the owner's Start in its dialog approves both, so no brief
  challenge or planner runs [TD-390].
- Reviewers run in parallel as Delivery steps of their own, each with its role's values, credits and retry; the
  curator step then checks their verdicts [TD-373].
- Reviewers default to Sol, medium effort, default context; the curator to Opus 5.5, high effort, long context; both
  are roles in Settings [TD-339].
- Keep, rewrite lower, merge or retire; doubt keeps. A removal names the behaviour, a plausible bug and the test that
  still catches it; security guards, incident regressions and public contracts stay [TD-112, TD-339].

**Owner's words:**

- TD-3, 2026-10-10: "proof are important. tests are not. tests are build artifacts"
- TD-112, 2026-10-15: "in some capacity similar to memory curator … Evidence-backed curation as Sol describes"
- TD-311, 2026-10-18: "have multiple sol subagents review the tests, each split of all"
- TD-312, 2026-10-18: "Stop here: measure, merge the curation, and return to the self-update"
- TD-339, 2026-10-18: "td-311 becomes the rule, but with sol medium thinking and short context"
- TD-370, 2026-10-18: "only on user request, on the maintenance page (where should be challenged)"
- TD-371, 2026-10-18: "Every registered project, each from its own Maintenance page"
- TD-372, 2026-10-18: "No: the curator applies what holds in a reviewed Change you can still stop"
- TD-373, 2026-10-18: "Delivery starts each reviewer as its own step in parallel, then the curator step"
- TD-390, 2026-10-19: "Your Start click in the dialog approves the fixed brief and plan; no brief challenge …"

**Replaced:** TD-112 by TD-339 and TD-372; TD-311 by TD-339, TD-371 and TD-373.

## C-27 Status and progress

**Rows:** decided TD-61, TD-66, TD-97; also Q5 (recommendation, no origin).

- Rounds count loops that repeat inside the normal process (challenge or review, then fix), not retries after a
  crash or a network wait [TD-97].
- Workflow position and rounds come from Delivery's own records [TD-97].
- Later, the watcher infers the stages inside an agent session (preparation, working, challenge and fixing rounds,
  finalizing), which may differ by role [TD-61, TD-66, TD-97].

**Owner's words:**

- TD-61, 2026-10-12: "for every agent there are stages. maybe different, maybe identical."
- TD-66, 2026-10-13: "The watcher infers it"
- TD-97, 2026-10-14: "i thought it meant challenge/fix rounds, so things that might repeat inside the regular process"

**Replaced:** TD-61 by TD-66; TD-66 by TD-97.

**Open:**

- Recommendation, not a recorded decision: one status line and one next action per Change (P6) [Q5].

## C-28 Code and tool rules

**Rows:** decided TD-1, TD-19, TD-31, TD-33, TD-63, TD-401, TD-417; autonomous TD-184, TD-391, TD-463.

- Agent-facing tools follow rules T1–T8 of the tool-surface audit, with T7 as re-decided by TD-63 [TD-1, TD-63].
- No tool-count limits; every Delivery tool serves one named process action (T1) [TD-63].
- A test checks that every agent-facing tool describes each field and stays small and flat (about six fields, one
  nesting level); whether the surface works is measured, not counted [TD-63].
- T8 is measured per Change: each Delivery tool's calls, refusals, lint-only refusals, calls after the step ended
  and retries after a refusal, kept on the Change because the activity log drops old events, and shown on its page
  under the spend; wrong-tool selection shows only as missing-tool reports [TD-463].
- No ceilings on agent instructions; use specialist terms without fillers or explanations, but not "caveman" style
  [TD-19].
- Split oversized code without cutting logic: aim for at most 400 lines per module; a test fails at 500 raw lines,
  comments and structure included; pages, scripts and styles count, tests do not [TD-19, TD-33, TD-401].
- Step kinds are a guide, not a gate: a new kind is allowed when no existing step can run its work, recorded with its
  reason; above eleven (the design's ten and the test review's) the count is reported, not failed [TD-391, TD-417].
- Default size and complexity rules of tools such as SonarQube or Snyk guide splits or rework, with wiggle room,
  never as a hard gate; SonarQube itself is not used (licence) [TD-31].

**Owner's words:**

- TD-1, 2026-10-10: "make your proposed rules accepted decisions"
- TD-19, 2026-10-10: "strict budgets for agents dont work … for code this does work if the ceiling means splitting"
- TD-31, 2026-10-11: "take these default rules as an instruction to decide whether something is still acceptable"
- TD-63, 2026-10-12: "i do not agree with t7, this is far too strict. tools follow process"
- TD-401, 2026-10-19: "Pages, scripts and styles count like Python; tests don't"
- TD-417, 2026-10-20: "A guide, not a gate: a new kind is allowed when no existing step can run its work"

**Replaced:** TD-1 by TD-63; TD-19 by TD-33; TD-391's cap by TD-417.

## C-29 Confirmations and input

**Rows:** decided TD-151, TD-152, TD-153, TD-154, TD-396.

- Consequential buttons confirm what happens now, what Delivery then does by itself, what the owner can do after (undo
  and its limits) [TD-151].
- They also say the way forward if he declines, with cost and disruption where they apply; buttons name the action
  [TD-151].
- A bare "are you sure" is the exception; New Change keeps its dialog; cheap, reversible actions get a note after
  the click [TD-151].
- Hints that guide an input or the choice to act, or state a lasting rule, stay at normal size; one click's
  consequences move into its dialog; only pure restatement is cut [TD-152].
- Pass confirms only at the last gate before an automatic merge. Fail always confirms and needs a note, used as
  written for the fix unless it contradicts the approved brief; then it is held for the owner [TD-153, TD-340].
- Settings Save shows the unsaved changes inline and names the layer; every save, global, machine or project,
  confirms in a dialog naming its layer and changes [TD-154, TD-396].

**Owner's words:**

- TD-151, 2026-10-15: "info on what will happen immediately … what the way forward is if he declines"
- TD-152, 2026-10-15: "you removed too much … not over but also not undercompensate"
- TD-153, 2026-10-15: "Sol's rule; Failed needs a note"
- TD-154, 2026-10-15: "Sol: inline summary; dialog only for global"
- TD-396, 2026-10-19: "Every Settings save confirms in a dialog naming its layer and changes"

**Replaced:** TD-154 by TD-396.

## C-30 Subagents

**Rows:** decided TD-53, TD-111, TD-116, TD-129, TD-178, TD-195, TD-344, TD-374, TD-375, TD-377; autonomous TD-376.

- Every role may start any built-in subagent, in read-only steps too under the same read-only guard, which a live run
  proved reaches a subagent's writes (2026-10-19) [TD-82, TD-374, TD-375].
- Each subagent stays monitored (agent, model, tokens, credits, duration) and its use is measured
  [TD-129, TD-195, TD-344, TD-374].
- Use shows per role on the Maintenance page; a Settings switch per role, on by default, turns subagents on or off
  [TD-376].
- A subagent may use any named model; one on Auto voids the step; other models are logged. The main agent is
  checked against its own model [TD-53, TD-377].

**Owner's words:**

- TD-53, 2026-10-12: "Subagents may use any named model; only Auto voids the step"
- TD-111, 2026-10-15: "more research needed"
- TD-116, 2026-10-15: "Remove the researcher"
- TD-129, 2026-10-15: "make this configurable and also monitor use"
- TD-178, 2026-10-16: "As before, but the judge is Sol (another model family) and I see the pairs too"
- TD-195, 2026-10-16: "Keep it off; monitoring stays; no further pilot"
- TD-344, 2026-10-18: "The setting goes; delegation would need a new decision; monitoring stays"
- TD-374, 2026-10-18: "monitored, and measure their use … Every built-in the runtime offers, for every role"
- TD-375, 2026-10-18: "Allowed in read-only steps too, under the same read-only guard"
- TD-377, 2026-10-18: "Keep the Auto check as a safety net for any subagent monitoring sees"

**Replaced:** TD-111 by TD-116 and TD-374; TD-116 by TD-374; TD-129 by TD-195, TD-344 and TD-374; TD-178 by TD-195 and
TD-344; TD-344 by TD-374.

## Standalone decisions

- OwlBear stays on GitHub Copilot [TD-4, decided].
- OwlBear is for the owner's personal use on his laptop; a colleague would at most read the repository and build his
  own variant [TD-9, decided].
- Overlapping parallel Changes show the overlap without asking; integration resolves conflicts and asks only about
  real behavioural collisions; docs, lockfiles and generated files are ignored [TD-12, decided].
- Copilot runs on `maba-pag`'s business seat. Which account makes a project's GitHub writes is a project setting,
  by default the repository owner's account when `gh` has it, else `maba-pag` [TD-17, TD-402, decided; TD-266].
- Charter parts no later decision replaced keep their `approved` origin from the charter and design approval;
  §3.8's allow list was replaced [TD-23, decided, partly; TD-82].
- The pages load the Porsche Design System only from its documented CDN: no own fallback rendering or load
  diagnostic; browser tests reach the real CDN [TD-39, TD-398, decided].
- On those pages dialogs close with PDS's dismiss button and Escape and the confirmation does not focus Cancel first;
  screenshot thumbnails stay plain image buttons, as PDS has no image button [TD-423, autonomous].
- The builder's code is linted once, at submission, on the changed files with the project's linters; no per-edit
  lint, broad-edit warning or session-start context hook [TD-87, decided].
- Lint may refuse 5 builder submits per session; later submits pass marked `lint-unresolved` [TD-88, decided].
- A quality service separate from Delivery runs linters; agents request changes to lint/format configs, CI workflows
  and Git hooks, the owner approves, refused from the start; no suppression grandfathered [TD-89, decided].
- The memory MCP server stays [TD-90, decided].
- Fixing memory publication and curation (F17) follows the plan's order; M4 and M5 no longer exist
  [TD-444, autonomous].
- The old Knowledge agents are not Delivery roles [TD-114, decided].
- The nine ECC adoptions stay agent rules, among them: never weaken tests or checks to get green; failing-before
  proof where feasible; shapers never infer business constraints from code [TD-115, decided; TD-112].
- Watcher lessons need evidence that agent behaviour caused the signal; merging lessons belongs to the curator
  [TD-115, decided].
- delivery-next's browser tests run in CI [TD-127, decided; TD-280].
- Every SDK session runs with repository agent hooks (`.github/hooks`) off; Git hooks are unaffected
  [TD-142, decided].
- The owner's user MCP servers stay as they are in SDK steps (steps cannot see or call them); no separate Copilot
  home [TD-143, decided].
- Only a finished Change leaves a record (brief, decisions, outcome, PR, spend) in its project's folder in the data
  repository [TD-148, decided].
- Work-project data may live in the data repository; `maba-pag` is the owner's employer account, `boecht` his
  personal one [TD-149, decided].
- Delivery does not check for or report commits it did not make in its worktrees; the final review covers them
  [TD-192, decided].
- Never containers; work happens in worktrees for good [TD-225, decided].
- GitHub access stays on the `gh` CLI for good; no GitHub SDK [TD-266, decided].
- A shaping chat never expires; the owner continues in the same or a new chat, and the saved brief stays
  [TD-285, decided].
- Agent sessions keep a total running-time limit, by default planner 30, test preparer 30, builder 40 and reviewer
  20 minutes, each a setting (global and per project) [TD-286, decided].
- Order of the remaining work: TD-358's build work, the research move (TD-227), self-update steps 3c to 5, the old
  engine's removal, v1.0, TD-318's memory work, the window-step gate, the watcher [TD-394, decided; TD-250, TD-228].
- Of TD-392..TD-402, the small items come with TD-358's work; the PDS fallback's removal, then the page split,
  before v1.0; the threshold with TD-318's work; the GitHub account before the first real project [TD-403, decided].
- The build work of TD-319..TD-357 comes before self-update step 3b; TD-274's gap stays until after self-update
  step 5 [TD-358, decided; TD-329].
- After the first real project (item 10), the browser and knowledge packages are rebuilt from scratch, starting from
  the ideas of the issues closed on 2026-10-20; until then they stay untouched, no fixes [TD-434, decided].
- While the owner is away, each reviewed pull request with green CI merges; the runtime updates itself as usual
  [TD-438, decided].

**Owner's words:**

- TD-4, 2026-10-09: "we are bound to github copilot, so we cant just switch platforms"
- TD-9, 2026-10-10: "this project is for personal use on my laptop"
- TD-12, 2026-10-10: "proposal sounds good, approved"
- TD-17, 2026-10-10: "Aim for the first reading, but start with maba-pag doing everything and switch once it works"
- TD-39, 2026-10-11: "PDS's documented CDN loading, nothing else"
- TD-87, 2026-10-14: "lint before end of session, but not after each edit"
- TD-88, 2026-10-14: "5 refusals, linting is hard in edge cases. fixing one thing can break another"
- TD-89, 2026-10-14: "Refuse from the start … Review all existing ones"
- TD-90, 2026-10-14: "After M4, before M5; keep MCP for now"
- TD-115, 2026-10-15: "With the agent work (build order step 3)"
- TD-142, 2026-10-15: "Off for all roles (consistency)"
- TD-143, 2026-10-15: "Leave as is; record the finding"
- TD-148, 2026-10-15: "keep briefs and decisions, of finished changes only"
- TD-149, 2026-10-15: "its allowed, the maba-pag account is an employer account, boecht is personal"
- TD-192, 2026-10-16: "Don't check at all, say nothing; the final review covers it"
- TD-225, 2026-10-17: "Never containers: worktrees for good"
- TD-266, 2026-10-17: "Keep gh for good"
- TD-285, 2026-10-17: "No deadline: you continue in the same chat or a new one whenever you return"
- TD-286, 2026-10-17: "those numbers look really low, i would have expected at least double"
- TD-358, 2026-10-18: "All of it now, before self-update step 3b"
- TD-394, 2026-10-19: "Item 1 → research move → self-update 3c–5 → old engine removal → v1.0 → item 5 → gate → watcher"
- TD-398, 2026-10-19: "Remove the fallback and notice; tests reach the real CDN"
- TD-402, 2026-10-19: "A project setting, defaulting to the owner's account when gh has it, else maba-pag"
- TD-403, 2026-10-19: "Small ones with item 1; PDS removal, then the page split, before v1.0"
- TD-434, 2026-10-20: "once delivery is stable we will work on browser and knowledge packages … saving the ideas"
- TD-438, 2026-10-20: "Merge each reviewed, green pull request overnight; the runtime updates itself as usual"

**Replaced:** TD-17 by TD-402; TD-250 by TD-394; TD-90's timing by TD-444.

**Spent:** TD-6, TD-8, TD-18, TD-28, TD-37, TD-62, TD-68, TD-141, TD-180, TD-188, TD-206, TD-232, TD-234, TD-248,
TD-261, TD-264, TD-268, TD-269, TD-271, TD-279; TD-132 and TD-445 (autonomous, 2026-10-21: TD-132's choices live in
their own decisions).

## C-31 The decision record

**Rows:** decided TD-359, TD-383, TD-384, TD-385, TD-386, TD-387, TD-388, TD-418, TD-419, TD-424, TD-425, TD-427,
  TD-428, TD-429, TD-430, TD-435, TD-436, TD-437, TD-439, TD-440, TD-441, TD-442, TD-446, TD-449, TD-450, TD-451,
  TD-452, TD-453, TD-454, TD-455, TD-456, TD-457, TD-458, TD-459, TD-460, TD-462; autonomous TD-389, TD-426,
  TD-461.

- One section per topic: its rows by origin, the rules in force, the owner's words, what was replaced (numbers
  only) and what is open; no history rows [TD-359, TD-383, TD-386, TD-387].
- The full rows TD-1..TD-382 and the old research report stay at commit `04b1d8ec4`; requirement R4 moved
  into C-03 [TD-383, TD-384].
- In-force lines state intent in at most two lines each; how something is built lives in code, tests and
  pull request texts, not here [TD-385, TD-389].
- A decision records only the owner's confirmed intent; his words are never stored, in decision files, this record
  or commit messages; the record's existing quotes stay as history until the migration [TD-449].
- A new decision edits its topic in the same change: its number on the rows line under its origin and an in-force
  line; nothing is appended elsewhere [TD-389, TD-449].
- Implementation choices go to the pull request text only; an autonomous choice that changes a rule is
  recorded in its topic. New numbers continue after the highest one in this file [TD-389].
- Until a decision system replaces this record, implementation choices the owner would notice on a page are
  recorded as autonomous rows too [TD-418].
- Decisions become a system of their own for OwlBear's work and every project, scoped like memory; it is the next item,
  before item 5 ([design](decision-system-build.md)) [TD-419].
- All decisions, OwlBear's and every project's, live in `owlbear-data` [TD-424]; OwlBear's repository keeps a
  generated full view for GitHub's agents and reviewers, data credentials only in its generator [TD-425].
- Global rules apply to every project at once; a project departs from one only by an exception (the owner took the
  recommendation: per-project adoption at a pinned revision lets rules go stale) [TD-426].
- Read-backs live on the Decisions page; ignoring one leaves the rule in force; only ambiguity, new evidence, a
  conflict or changed consequences queue one; working chats may read back on the same records [TD-427].
- A change of mind with built effect shows an impact report; activating, stopping affected work and scheduling
  fixes are separate steps; fixes are backlog entries grouped by what one Change can do [TD-428].
- Decisions link by a fixed set (replaces, refines, exception to, depends on, related to, promoted from); a
  conflict is a flag the owner resolves [TD-429].
- Decisions are never deleted: replaced, withdrawn and spent ones stay hidden by default; only a leaked secret or
  personal data is purged, with the owner's consent [TD-430].
- OwlBear's own decisions show as a fixed OwlBear scope beside Global on the Decisions page, read from
  owlbear-data's `owlbear/` folder; the repository stays unregistered [TD-435].
- A read-only owlbear-data token serves only a workflow on pushes to main and a daily schedule; pull-request CI
  checks the generated view's own hash [TD-436].
- The record's first migration stops at a preview listing its unclear clauses; the record stays authoritative until
  the owner has reviewed it [TD-437].
- Today's rules come over as inherited: their recorded authority, marked never read back, without quotes; one is
  read back only when work relies on it and its meaning is unclear [TD-454].
- Global: C-01's asking rules (not page comments), security changes reviewed with the owner, consumer research out of
  its project, config changes the owner approves, the nine ECC adoptions; all else is OwlBear's [TD-442].
- No per-topic targeting list: shaping assigns the decisions that apply to each Change and its challenger checks;
  agents may tag topics for search without asking [TD-455].
- In a lead chat a decision is confirmed and saved in the chat; the Decisions page is for looking up and changing,
  never a required stop [TD-450].
- Within approved work or a delegation agents decide reversible details and record consequential ones as theirs;
  anything lasting, wider, contrary to an owner decision or committing outside asks first [TD-451].
- Workers get the decisions assigned to their work and may look up more in Global and their project; challengers
  check the complete list [TD-452].
- Shaping decisions apply from brief approval, project-wide ones to the project's other Changes at once; chat and
  page decisions apply at confirmation [TD-453].
- A Change's rules are picked once at shaping and pinned at approval; its own later decisions attach; a rule replaced
  or withdrawn elsewhere, or a widened scope, is reassessed at the next step boundary [TD-456].
- A failed lookup shows as failed, never as "no rules apply"; no fixed size limit; a short log of wrong picks and
  misses, each with the condition that made it wrong, corrects the picker; no statistics or automatic filters [TD-456].
- A separate picker on Sol at medium effort picks a Change's rules at shaping and answers every later lookup of
  workers and lead chats, reading the complete list [TD-459].
- Every worker of a Change gets the whole picked set; no agent trims it [TD-457].
- Rules carry no role or kind tags and there are no per-role views [TD-458].
- Decisions carry no paths, roles or steps selectors; the picker alone decides what applies to a Change [TD-460].
- An answer during the work is classified by its relayer as event, clarification or brief change; clarifications
  are read back and become Change decisions; a Sol check stops the work when one changes the brief [TD-461].
- The migration rewords statements that only make sense beside their neighbours so each stands alone, the original
  beside it, every reworded one marked for the owner's review in the preview [TD-462].

**Owner's words:**

- TD-359, 2026-10-18: "Consolidate all 30 topics now, in one pass, Sol-reviewed"
- TD-383, 2026-10-19: "Delete the table; one line names the commit that still holds it"
- TD-384, 2026-10-19: "Delete them; R4's comparison moves into C-03"
- TD-385, 2026-10-19: "Apply all: shorten to intent, remove mechanism, spent and duplicates"
- TD-386, 2026-10-19: "One short line per topic, numbers only"
- TD-387, 2026-10-19: "One compact line per topic, numbers grouped by origin"
- TD-388, 2026-10-19: "1 and 2" (keep every quote, each cut to its decisive words; drop "chosen without a quote")
- TD-418, 2026-10-20: "option 2" (implementation choices you would notice on a page are recorded as autonomous rows)
- TD-419, 2026-10-20: "treat them similarly to memories, with scopes to projects, global … we should prioritize this"
- TD-424, 2026-10-20: "all decisions for both owlbear and projects live in owlbear-data"
- TD-425, 2026-10-20: "A: generated full view in OwlBear's repository, data credentials only in the generator"
- TD-427, 2026-10-20: "The Decisions page holds every read-back and ignoring leaves the rule in force"
- TD-428, 2026-10-20: "The corrected model: impact report, three separate steps, fix entries grouped …"
- TD-429, 2026-10-20: "A fixed set …; a conflict is a flag you resolve, never a lasting link"
- TD-430, 2026-10-20: "Never delete …; only a leak (secret, personal data) is purged, with your consent"
- TD-435, 2026-10-20: "A fixed \"OwlBear\" scope beside Global on the Decisions page … without registering"
- TD-436, 2026-10-20: "A read-only token used only by a workflow on pushes to main and a daily schedule"
- TD-437, 2026-10-20: "the record stays authoritative until you review it in the morning"
- TD-439, 2026-10-21: "Do none of it: migrate the record exactly as written"
- TD-440, 2026-10-21: "Split the 4 clear ones; the 4 doubtful ones (3, 4, 5, 8) stay wholly decided"
- TD-441, 2026-10-21: "Add all 7 as written"
- TD-442, 2026-10-21: "The asking rules plus the four candidates"
- TD-446, 2026-10-21: "Tag by topic: the migration proposes roles and steps per topic, I confirm one list"

**Replaced:** TD-359 by TD-383 and TD-388; TD-388 by TD-449; TD-439 by TD-454; TD-446 by TD-455; TD-456 in part by
TD-459.

**Spent:** TD-440 (four mixed lines split by origin, the doubtful ones kept decided) and TD-441 (seven rows without a
  line got one), both applied in their topics.
