# Improvement: Design

> **Owning task:** the plan's item 9 (formerly "the watcher"), redesigned with the owner on 2026-10-25
> **Date:** 2026-10-25
> **Question:** How do agents get better from their own work: fewer common mistakes, wrong tool arguments,
> rabbit holes and local optimums that miss the real intent, without being steered off course?
> **Status:** the owner's choices of 2026-10-25, after a pilot, a hindsight review of 83 real moments and Sol's
> challenges (§3); built complete, for Delivery steps and chats, before item 10 (the owner's choice, same day). They replace the live coach of this design's first version and the per-call outside-write watcher
> of [the earlier draft](delivery-next-watcher-design.md). Catching malicious calls is out of scope for now. Built so
> far: W1a's feed (#640), phase 1a (#652) and the Primer (#653).

## Names

| Name | What it is |
| --- | --- |
| **Improvement** | The group, and its page |
| **Primer** | The lessons every new agent session gets before it starts (§2) |
| **Spotter** | The live agent beside a working agent; in learning mode it records what it would do, live it steers (§4) |
| **Spotter cases** | The Spotter's graded example cases: its prompt examples and its regression test (§4) |
| **Retro** | The after-task analysis: reads whole tasks with hindsight, grades the Spotter, proposes lessons and fixes (§5) |
| **Retro chatlogs** | The kept logs of finished agent conversations (Delivery steps, enrolled chats) that Retro reads (§5) |

"Watcher" was the working name; the role and setting called `watcher` are renamed when the Spotter is built.

The evidence came from two investigations:
- prior art on live critics, monitors and cross-run learning, cited in §1;
- an analysis of this machine's 1,910 local Copilot sessions (10–24 October) and Delivery's runs on its two
  sandbox projects.

Two sessions dominate that data, and most Delivery runs are toy harnesses, so its numbers are hypotheses to test,
not thresholds.

## 1. What the evidence says

**Failures.** Only 2.9% of calls fail, and agents rarely retry blindly. Watching each call for failures has
little to gain.

**The costly mistakes:**
- **Repeated across runs:**
  - one check string was refused 6 times;
  - changed_paths claims didn't match 12 times;
  - `python` was not found;
  - shell brace paths were passed to rg.
- **Intent:** in all 23 of the owner's corrections the agent misread scope, asked instead of acting, ignored a
  standing order, or concluded too early.
- **Trajectory shapes:**
  - test-only edits after a red test (21%), though not necessarily wrong;
  - churn on one file;
  - polling loops;
  - compaction thrash.

**Prior art:**
- Cheap detectors are reliable for repetition but blind to drift.
- Critique that isn't grounded in evidence fails, and critics rubber-stamp.
- Learning works only as curated, validated artifacts.
- No published evidence shows live nudges help coding agents, so we measure it ourselves (§3).

Sources:
- [OpenHands stuck detector](https://docs.openhands.dev/sdk/guides/agent-stuck-detector) and
  [condenser](https://docs.openhands.dev/sdk/arch/condenser);
- [Reflexion](https://arxiv.org/abs/2303.11366); [AgentCoder](https://arxiv.org/abs/2312.13010);
- [Agent Workflow Memory](https://arxiv.org/abs/2409.07429); [ExpeL](https://arxiv.org/abs/2308.10144);
  [Voyager](https://arxiv.org/abs/2305.16291);
- [MAST failure taxonomy](https://arxiv.org/abs/2503.13657);
  [code-agent trajectories](https://arxiv.org/abs/2511.00197);
- [OpenAI agent monitoring, red-teamed by METR](https://metr.org/blog/2026-10-22-red-teaming-openai-agent-monitoring);
- [Anthropic, building effective agents](https://www.anthropic.com/research/building-effective-agents).

## 2. Prevention first: fix tools, then the Primer

1. **Tools and contracts.** Derive what can be derived instead of asking the agent: changed_paths from the
   commits, the profile's exact check strings offered as choices. Make errors say exactly what to send. Check the
   toolchain (`python3`, installed dependencies) before the step starts. Every recurring mechanical mistake is
   fixed here, once. Built in part (#652).
2. **Primer.** At the start of every new agent conversation, the few approved lessons that genuinely apply to its
   role, project and tools, with exact commands or examples. There is no quota. Built (#653).

## 3. What the pilot showed: correct is not worth it

A coach that judged frozen moments of real work (24 pilot moments, then 60 fresh ones from last week's chats) was
tested against labels. 83 of them (one pilot moment was a chat-stop artefact) were then judged again with hindsight:
what happened afterwards up to the requester's next message, whether the agent fixed it itself, what silence cost
(Sol medium over each continuation).
- **10 of 83 moments were candidates for a note.** All sat at a **hand-off** (stopping at partial work despite "continue",
  "ready" with an acceptance gap, work handed back that the agent could do, a report with conclusions its evidence
  does not support or a standing decision forbids) or **right after a fresh instruction** whose explicit constraint
  the next actions broke.
- **None was mid-flow.** Repeats, denials, polling, failing tests: the agents fixed them themselves within seconds
  to minutes. The coach's notes there were often correct and still not worth an interruption.
- **The coach's notes were worth it 6 times in 26.** Its judgement improved only when the card held the deciding
  fact (an applicable decision, the open work), and a decision check that missed the right decision turned a note
  harmful.
- **Interruptions have a cost no log shows:** steering pulls an agent onto a small matter and off a larger one, and
  smaller and older models drift most. Even the 10 are not proven worth it: a requester's correction is not proof of
  material cost, and an agent that stopped may have stopped for a good reason.
- The owner's labels on fragments were never decisions; labels come from the full logs (§5).

So the line is: a note only when the problem is visible now, silence would cost at least rework or a broken
constraint or decision, the agent will not fix it itself before that lands, and one short note fixes it without
widening the agent's scope. Otherwise silence, and the moment feeds Retro's lessons and fixes.

## 4. Spotter

### Modes and settings
All settings have no code default; an unset one is an error on the Settings page (Global, with a machine override):
- **mode:** off, **learning** (records what it would do; the start) or live (acts);
- **steer share:** in live mode, the share of whole Changes and chats whose notes are sent; the rest record only
  (the test below);
- **intervention cap:** at most this many steering notes per step or chat turn;
- **verbose:** a bounded rationale with its evidence per look, scoped to the machine, a project or a Change, with an
  expiry. Retro may switch it on within a credit cap and for a named reason, shown on the page; never live mode;
- **looks:** which looks are on, and the sample rate;
- **budgets:** credits per day for the Spotter and for Retro; beyond it, a look or run is skipped and recorded;
- **enrolled chats:** the workspaces or chats the Spotter and Retro may read. Unset reads none. Spotter, Retro and
  curation sessions are excluded by provenance. The check comes before any read, copy or model call.

Roles: `spotter` (the `watcher` role renamed, with a settings migration), `retro`, `retro-review`.

### Looks
A look is one tool-less session on the spotter role over a **card** (the intent with the requester's latest messages
and answers, the applicable decisions from the picker's conflict check, the agent's plan, the moment itself, the
recent actions with their evidence, the open work; each with an event cutoff). It returns a **record**: kind,
sampling probability, verdict (silent, note, interrupt), the note, the evidence references and a short rationale.
Records are kept on this machine in a daily store (`~/.owlbear/spotter/records-<date>.jsonl`), each with its session,
its Change and step or its chat and turn, and its look, so Retro can join them after a restart.
Active Spotter cases are its prompt examples.
- **Hand-off:** Delivery's `submit_result`; in a chat, a turn that ends with a reply to the requester.
- **Plan:** the agent's first reply after a requester message.
- **State change:** W1a's outside writes, publishing, deleting, settings.
- **Sample:** any completed action with the configured probability.

Sampled and state-change looks stay record-only until Retro shows their class is worth it. The line from §3 holds in
every mode: correct is not enough; the value must clearly exceed the risk of pulling the agent off course.

### Where
- **Delivery steps:** from the SDK adapter's event stream (W1a's feed).
- **Chats:** a follower in the machine host tails each enrolled chat's `events.jsonl`.

### Live delivery
- **Delivery hand-off:** an accepted `submit_result` is final (the SDK skips another model round), so the Spotter
  judges the submission before acceptance. When it steers, the tool answers with a non-success note that does not
  count as an invalid submission; the next submission is validated again.
- **Other Delivery notes:** sent into the session with an explicit `enqueue`, never taken to have stopped an action.
- **Chats:** a `Stop` hook (shipped in the seed and wired by the install, inert unless live) asks the machine host for the note tied to
  that chat's turn, waits a bounded time, takes it only once, drops expired notes and honours `stop_hook_active`.

### The steered-versus-silent test
A test starts only once Retro's grades of the learning-mode records are high enough for the looks it would steer
(a threshold set before it starts). Live mode is then promoted only by a test randomised per whole Change (all its steps) and whole chat, the assignment kept
across restarts. The primary outcome is declared in advance: the task completed without material rework or a broken
constraint; credits, time and owner effort beside it. Model, prompt and case versions are frozen during a test;
outcomes are graded blind to the arm where possible; delivery failures are recorded; the promotion threshold is set
before it starts.

### Spotter cases
A frozen card plus the right call and why. Stages: candidate, test case, active example; versioned, with rollback; a
fixed holdout, never an example and used to choose between versions at most once per release of the cases. A change
of active examples runs the regression and is refused if it gets worse. Seeded from the pilot's moments with Retro's
hindsight verdicts. Raw cards stay on this machine; only reviewed, minimised and sanitised cases go to owlbear-data
(`owlbear/improvement/spotter-cases/`), with local provenance references.

## 5. Retro

- **Runs** as a machine-host job like memory curation: one run at a time, its own session slot, pause and the stop
  barrier, restored after an interruption, part of the machine's busy and leftover checks. Triggers: a Change's end
  (after its cleanup), idle (finished enrolled chats), the page's button.
- **Retro chatlogs:** a durable Change-to-session manifest written when a step session is chosen and when it ends, on
  every ending path; at a step's end its `events.jsonl` is gzipped to `~/.owlbear/retro/chatlogs/`, with the files
  the runtime saved large outputs to if still present (missing ones are recorded). A chat counts as finished after a
  day without events; its log is copied when Retro takes it. Logs no finding, case or pending proposal refers to go
  after 30 days. Encrypted reasoning stays unreadable; only its summaries are kept.
- **Units:** a finished Change (every step from the manifest, its reviews and its end) or a finished chat, read in
  segments, each with the chat's later course. Missing evidence makes a finding "unknown", never a proposal.
- **Judges** with hindsight what went wrong, what it really cost and whether the agent recovered (a requester's
  correction is a signal to look, not a cost by itself), and **grades** each Spotter record of the unit: worth it,
  correct but not worth it, wrong, or missed (from sampled silences only).
- **Proposes**, each kind with its own evidence bar (a reproducible, costly tool defect once; lessons and prompt
  rules repeated evidence from independent tasks plus counterexamples):
  - a Spotter case;
  - a lesson for the Primer;
  - a change to an agent, a skill or a prompt;
  - a change to Delivery's logic or a tool contract.
- Judgement is saved first; each finding has a stable id visible where it is published, and a retry reconciles by id
  before creating anything.

## 6. Proposals and the owner

Each proposal is challenged by `retro-review` (Sol): is the evidence real, is the direction right, what could it
break. Survivors, capped per week, reach the owner on the **Improvement page**, which also shows the Spotter (mode,
verbose, budget used, recent records with grades), Retro (runs, state, a button) and the Spotter cases (stages,
versions).
- A proposal states its direction in one line, why (evidence, cost seen), what would change and the review's verdict.
- The owner decides **direction, not details**: accept, reject, redirect (free text, read back) or later.
- Accepted: a Spotter case moves a stage (with the regression); a lesson becomes a pending memory in its folder; a
  project's agent, skill or Delivery change becomes a backlog entry (source `retro`); OwlBear's own becomes an issue
  in its repository for a chat to build. Nothing is edited silently, and a Change's brief bounds what it may change.
- Every publication outside this machine (cases, proposal evidence, backlog entries, issues, memories) is reviewed,
  minimised and sanitised; raw cards, chatlogs and records stay on this machine.

## 7. Build order

Each slice is a pull request, with Sol on its plan and its code:
1. this design;
2. settings and roles;
3. Retro chatlogs;
4. the card builder;
5. Spotter records and cases;
6. the Spotter's looks in learning mode, for Delivery and chats;
7. Retro;
8. the Improvement page;
9. live delivery and the test machinery.

Then item 10.

## 8. Built work

- W1a (#640): its feed, identity and writer are reused by the Spotter.
- #647 (shell parsing) is closed.
- Phase 1a (#652) and the Primer (#653) are built.
- The pilot's harness and data stay in `.owlbear/scratch/watcher-replay/` (not committed).
