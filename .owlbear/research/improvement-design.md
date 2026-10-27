# Improvement: Design

> **Owning task:** the plan's item 9 (formerly "the watcher"), redesigned with the owner on 2026-10-25
> **Date:** 2026-10-25 (approved); status 2026-10-26
> **Question:** How do agents get better from their own work: fewer common mistakes, wrong tool arguments,
> rabbit holes and local optimums that miss the real intent, without being steered off course?
> **Status:** the owner's choices of 2026-10-25, after a pilot, a hindsight review of 83 real moments and Sol's
> challenges (§3); built complete, for Delivery steps and chats, before item 10 (the owner's choice, same day). They replace the live coach of this design's first version and the per-call outside-write watcher
> of [the earlier draft](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-next-watcher-design.md). Catching malicious calls is out of scope for now. Built so
> far: W1a's feed (#640), phase 1a (#652), the Primer (#653), and slices 1 to 4 and 6's Delivery part (#659 to #668,
> §8).

## Names

| Name | What it is |
| --- | --- |
| **Improvement** | The group, and its page |
| **Primer** | The lessons every new agent session gets before it starts (§2) |
| **Spotter** | The live agent beside a working agent; each finding gets its category's configured action, from recording it to steering or stopping (§4) |
| **Spotter cases** | The Spotter's graded example cases: its prompt examples and its regression test (§4) |
| **Retro** | The after-task analysis: reads whole tasks with hindsight, grades the Spotter, proposes lessons and fixes (§5) |
| **Retro chatlogs** | The kept logs of finished agent conversations (Delivery steps, enrolled chats) that Retro reads (§5) |

"Watcher" was the working name; the role and setting called `watcher` became `spotter` and the Spotter's settings
(#662).

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
- **on/off:** replaces the former mode (D-01M5WB09Z3ZKJVN02WGWVHGWBH, D-01M5WBAFQPZT6QBMV3V3HZ83ES); off also stops
  W1a's feed. "Learning" and "live" now describe the actions configured below, not a setting;
- **actions per category of finding:** the Spotter files each finding under one of four broad categories, the
  examples illustrating, never limiting: **hand-off fitness** (the result should not be accepted as it stands: an
  unmet criterion, an unsupported claim, a weakened test), **course and constraints** (recoverable work heading
  materially wrong: a scope or decision conflict, a wrong direction, a costly loop), **outside-state changes** (a
  consequential change beyond the task's files that is not irreversible) and **irreversible harm** (which takes
  precedence). Each category is set to one action it allows: record, show the owner, steer (a note into the running
  turn), refuse the hand-off, stop and resume with the note, or stop and ask the owner. What warrants irreversible
  harm is the Spotter's own judgement within broad categories, never a closed list or a confidence threshold
  (D-01M5W6NGXW27VW024E1B29W3GA). A repeated unresolved finding becomes a question to the owner, never a loop;
- **steer share:** the share of whole Changes and chats whose discretionary actions (steer, refuse the hand-off, stop
  and resume) act; in the rest those findings are recorded instead (the test below). Irreversible-harm actions act in
  every Change and chat, outside the share;
- **intervention cap:** at most this many steering notes per step or chat turn; irreversible-harm actions and hand-off
  refusals are never capped (D-01M5W9S636SC6C6JC4EQAM24NN was folded into the category decision);
- **verbose:** a bounded rationale with its evidence per look, scoped to the machine, a project or a Change, with an
  expiry. Retro may switch it on for a named reason, shown on the page, each look still within its credit limit;
  never an action;
- **looks:** which looks are on, and the sample rate;
- **credit limits:** no daily budgets (D-01M5XCD49YHHR1NQKKY8TQD0C3). Each Spotter look, live or replayed, each Retro
  run and each paid replay run of Spotter cases stops at its own credit limit, and the stop is recorded. The per-look
  limit is one of the Spotter's settings (`look_credit_limit`); the run limits are machine settings
  (`retro_run_credit_limit`, `replay_run_credit_limit`). Each was written into Global once at five times its expected
  cost, a marked assumption (0.75, 20 and 90 credits; the basis is in `settings/carried.py`). There is no SDK credit
  cap: the spend the runtime reports is counted and the work stopped once it reaches the limit, so a call already
  under way can pass it;
- **enrolled chats:** the workspaces or chats the Spotter and Retro may read. Unset reads none. Spotter, Retro and
  curation sessions are excluded by provenance. The check comes before any read, copy or model call.

Roles: `spotter` (the `watcher` role renamed, with a settings migration), `retro`, `retro-review`.

### Looks
A look is one tool-less session on the spotter role over a **card** (the intent with the requester's latest messages
and answers, the applicable decisions from the picker's conflict check, the agent's plan, the moment itself, the
recent actions with their evidence, the open work; each with an event cutoff). It returns a **record**: kind,
sampling probability, the finding's category (none when silent), the note, the evidence references and a short
rationale; the configured action follows from the category. Records written before #697 carry the earlier verdict
(silent, note, interrupt) instead.
Records are kept on this machine in a daily store (`~/.owlbear/spotter/records-<date>.jsonl`), each with its session,
its Change and step or its chat and turn, and its look, so Retro can join them after a restart.
Active Spotter cases are its prompt examples. A look takes no session slot of its own: the agent it looks at holds
one, so waiting for another could deadlock a machine limited to one. Instead it is admitted without blocking, within
its own credit limit and a short timeout; a look that cannot run in time is recorded as skipped, and the agent
carries on as without a Spotter.
- **Hand-off:** Delivery's `submit_result`; in a chat, a turn that ends with a reply to the requester.
- **Plan:** the agent's first reply after a requester message.
- **State change:** W1a's outside writes, publishing, deleting, settings.
- **Sample:** any completed action with the configured probability.

As built for Delivery steps (#668): the hand-off look starts at the submit call, before Delivery may accept it, over a
frozen snapshot of a bounded intake of the step's own agent (subagents left out; a resumed session's transcript seeds
it); at most two looks run at once per step. Each look stops at its credit limit (D-01M5XCD49YHHR1NQKKY8TQD0C3): its
meter adds each billed call's reported cost and the turn is aborted once the limit is reached or a cost is unknown;
the call that passed it cannot be stopped, so a look may overshoot; a retry or extension of the look shares its meter
and does not start once it is closed. Its record keeps the known spend, whether it is complete, the limit and the stop
with its own id and the ids of its SDK sessions, which the chatlogs manifest's `started` line names with that id
(`improvement/credit_meter.py`, `runtimes/credit_limit.py`). A look gets 90 seconds. A look never blocks or changes the step's work or its
acceptance: its files and model call run beside it. Only the session's end waits, bounded: at most 5 seconds for running
looks, then they are stopped, with up to 15 seconds more for their teardown and records; stopped looks are recorded as
skipped. Each record keeps its call and event cutoff, and Delivery's answer to the hand-off is kept beside it in
`outcomes-<date>.jsonl` as the SDK's result type (`success`, `rejected` when the session had ended, `failure` for a
submission Delivery refused). A record naming a state change is marked preliminary until the conflict check
comes with live delivery. The card holds credentials as the agent saw them; only browser context and email addresses
are stripped (the owner, 2026-10-26: a look sends the model what the agent's session already sent it, and the records
are temporary and owner-only; D-01M5VXXFBSWVZ0DZ68G1QG4CYG).

Findings from sampled and state-change looks stay record-only until Retro shows their class is worth it, whatever
their category's action; irreversible harm is the exception and acts per its category at once, also before the
steered-versus-silent test, which is about discretionary steering (D-01M5WB09Z3ZKJVN02WGWVHGWBH,
D-01M5W68MMV8JCVKNKH4VJQ9V14). A stop after the fact only halts what follows; it cannot undo what happened. The line
from §3 holds for every action: correct is not enough; the value must clearly exceed the risk of pulling the agent off
course.

### Where
- **Delivery steps:** from the SDK adapter's event stream (W1a's feed). Steps run only through the SDK: window steps
  are retired (D-01M5WG8RGCBKADW6XPGP0E2FAP; their code is removed, #698), and every runtime used must be readable,
  steerable and stoppable by the Spotter (D-01M5W9YB6VHT7RW53M3133WD3C).
- **Chats:** a follower in the machine host tails each enrolled chat's `events.jsonl`.

As built for chats (`machine_host/chats.py`, `chat_settings.py`, `chat_looks.py`, `chat_offsets.py`,
`runtimes/chat_moments.py`): one follower, holding its own lock from before its first read until its thread ends, so a
handover's next host reads nothing while the old one drains. Every
5 seconds it reads the Spotter's settings (Global's under this machine's; a chat is no project's) and the enrolled
chats; off, unset or unreadable, it reads no chat. A chat is a runtime session folder, listed before the manifest of
OwlBear's own sessions is read, that the manifest does not name (an unreadable manifest reads none, and every session
OwlBear creates, a look's, a `retro-review`'s and a replacement's included, is noted there before it is created or does
not start), whose `workspace.yaml` (read again whenever it or its metadata changes) names an enrolled folder outside
OwlBear's own; only then is its log opened. Its new bytes are read in bounded chunks, each fetched once (an event not
yet complete is continued at the next read), every fetch counting against a pass's bound.
A chat that existed when following began starts at its end then, a later one at its start, and one found again after
it was dropped (its metadata missing meanwhile) at its end then; earlier bytes and a replaced log are context, never
looked at; a restart records the bytes it missed as a gap (D-01M5XCE8ZA4FGYYY45YP44M8RD). One chat look runs at a
time, a draining one counted. It is admitted under the machine's stop barrier: none once an update's fence, a stop or
a stop when idle holds it, and one admitted before is counted as running work from then until it ends, so they wait
for it. It runs under a maintenance lease from before its session to its runtime's confirmed end; an
unconfirmed end keeps the lease and a session slot held, and no chat look starts until the owner recovers it on the
Maintenance page, as for the cases job; Pause admits none while the chats
are still read (D-01M5XCE8ZC030KT2FZ7D6SZCJN). No turn settles while an event is still being written. Every
settlement and admission uses the settings in force (the
per-look credit limit among them); the prompt and cases' snapshot is taken when a turn starts (one begun before
following, at its first live event) and serves that turn's looks. Each look keeps the settings and snapshot it was
admitted with, and its record the chat as its session, the requester message as its `turn`, the case version and
prompt hash, and its meter's spend, limit and stop. A trace of the runtime (2026-10-27) showed the log holds
each model round and a `session.usage_checkpoint` after a prompt's last one, never `session.idle`; marked assumptions
(D-01M5XB9M1A1MNG0S54N367RC70) fill the rest:
- **plan:** the first reply with content after a requester message (one without a source or the user's, not an
  autopilot continuation), whatever it asks for besides;
- **hand-off:** one per requester turn, its final reply (no tool requests, its round ended) once the turn settled:
  a checkpoint after it with the log read to its end, the next requester message, the session's end, or 120 seconds
  without an event while no round or call is open; a later round supersedes it, an abort drops it;
- **state change:** a completed call judged against the chat's workspace and the requester's intent (a chat has no
  Change): a write outside the workspace wherever it goes; else none when the runtime marks a shell call read-only
  (no redirection into a file); else publishing, deleting or settings by its shell command's words or its tool's
  name; a call whose effect is not known is a candidate too, its uncertainty in the moment; it is
  looked at instead of a sample of the same call;
- **sample:** as for Delivery steps.

### Live delivery
- **Delivery hand-off:** an accepted `submit_result` is final (the SDK skips another model round), so the Spotter
  judges the submission before acceptance. When it steers, the tool answers with a non-success note that does not
  count as an invalid submission; the next submission is validated again.
- **Other Delivery findings:** act as their category is set: a steer is sent into the running turn; a stop aborts
  the turn, then resumes it with the note, or waits for the owner. Aborting and resuming a turn is not built yet.
- **Asking the owner:** a stop-and-ask, or a repeated unresolved finding, asks him to allow it (a brief amendment his
  answer approves), run again with the reason, or replan the task with the whole plan in view
  (D-01M5WB8V8ZRGZWWVS9K2CV209E). Amendments come with item 16, after Improvement: until then "allow it" keeps the
  step paused, as item 14's runner gate does for a brief change, while running again and replanning work from the
  start.
- **Outside writes:** W1a's reports stay on the Change, leaving out Delivery's own state, temporary files and tool
  caches; the state-change look sees every outside write, those included. Its findings on them stay record-only until
  Retro shows that class is worth it, but irreversible harm acts per its category at once
  (D-01M5W68MMV8JCVKNKH4VJQ9V14, D-01M5W7C4R6M99MVWHR8X1GMCBT).
- **Chats:** a `Stop` hook (shipped in the seed and wired by the install, inert while no category's action steers)
  asks the machine host for the note tied to
  that chat's turn, waits a bounded time, takes it only once, drops expired notes and honours `stop_hook_active`.
  Whether a running chat turn can take a steer before its end is open.

### The steered-versus-silent test
A test starts only once Retro's grades of the record-only findings are high enough for the looks it would steer (a
threshold set before it starts). Discretionary actions (steer, refuse the hand-off, stop and resume) act beyond the
steer share only once a test, randomised per whole Change (all its steps) and whole chat with the assignment kept
across restarts, shows them worth it. Irreversible-harm actions are not part of the test: they act in both arms. The primary outcome is declared in advance: the task completed without material rework or a broken
constraint; credits, time and owner effort beside it. Model, prompt and case versions are frozen during a test;
outcomes are graded blind to the arm where possible; delivery failures are recorded; the promotion threshold is set
before it starts.

### Spotter cases
A frozen card plus the right call and why. Stages: candidate, test case, active example; versioned, with rollback; a
fixed holdout, never an example and used to choose between versions at most once per release of the cases. A change
of active examples runs the regression and is refused if it gets worse. Seeded from the pilot's moments with Retro's
hindsight verdicts. Raw cards stay on this machine; only reviewed, minimised and sanitised cases go to owlbear-data
(`owlbear/improvement/spotter-cases/`), with local provenance references.

As built (2026-10-27, `improvement/cases.py`, `case_replay.py`, `case_review.py`, `pilot_seed.py`, the machine host's
`cases_job.py`; the owner's decisions D-01M5XB9M1A1MNG0S54N367RC70, D-01M5XCDRZJQJW4JMAQQ5G371YV,
D-01M5XCE8ZEX5WPSCBZ5Y9S4K96, D-01M5XCD49YHHR1NQKKY8TQD0C3, D-01M5XCE8ZFZE8Q1XCN1EE4B29S):
- **Store** (`~/.owlbear/spotter/cases/`, owner-only): each case's frozen card and facts (source, local provenance,
  session family, reserve, unscored, the assumption it rests on), and `versions.jsonl`, each line a whole version:
  every case's stage, call (a category or `none`), why, example text and review. A test case or example needs a review
  of exactly its card, call and why; an example is never in the reserve, synthetic or unscored, and all examples stay
  within 6,000 characters. A rollback appends a copy of an earlier version.
- **Prompt**: one immutable snapshot (the prompt file, the verbose line, the examples; its hash is of exactly those
  bytes, with the cases' version) frozen when a step starts, or a chat turn begins; a record keeps both.
- **Regression** (a smoke check, not proof): a change of the active examples, a rollback included, is replayed before
  it is written: the scored test cases and their calls, and both prompts, are frozen when it is asked for; an empty
  comparison is refused; false notes, misses and wrong categories are counted apart and none may rise; a run whose
  meter, or any look's, stopped (its limit reached or its spend unknown), the final look's included, is refused
  whatever the answers. A passing change is written only onto the version it was asked against, else refused as
  stale and never rerun.
- **Release** (a marked assumption): a frozen manifest of the reviewed corpus and the grading contract; equal manifests
  are one release, so choosing examples makes none. The reserve (the pilot's holdout, historically exposed by its
  prompt experiments) compares two versions once per release, claimed before the first look.
- **Paid runs** (replays, and `retro-review`'s check of candidates) start only from `owlbear cases` and run as the
  machine host's job on a slot of their own, admitted only while the machine is neither paused nor fenced; each stops
  at its run credit limit (`replay_run_credit_limit`, or `retro_run_credit_limit` for a check and publication), each
  replayed look on its own `look_credit_limit` meter inside the run's, each `retro-review` session charged through
  `credit_limit.Limit`; a run that fails, or that a stopped host left, is recorded with its spend, never rerun.
- **Seed**: the pilot's 83 hindsight moments from their saved cards (no chat log read again; missing evidence a gap),
  as candidates; `should` moments take the category the calls file names; `unknown` ones are left out; wr-p-759028 is
  unscored while TD-435 is absent from its card. Both pilot splits are kept; other families are assigned once.
  Synthetic cases (a marked assumption) stand in for outside-state changes and irreversible harm: never in the
  reserve, never examples, never published. `owlbear improvement reset` retires every marked assumption for good.
- **Publication** runs on its own: `retro-review` minimises and sanitises each test case and example; its answer must
  keep the call; every decoded text of the export and its serialized form must pass `mask.redact`, email and
  home-path checks; it names the case by its local id only; a case changed during its review is not published; one
  that leaves those stages is withdrawn, also while a newer revision is under review (what the shared repository
  holds is kept apart from each review's outcome); an unpushed commit is pending until a later push.

## 5. Retro

- **Runs** as a machine-host job like memory curation: one run at a time, its own session slot, pause and the stop
  barrier, restored after an interruption, part of the machine's busy and leftover checks. Triggers: a Change's end
  (after its cleanup), idle (finished enrolled chats), the page's button.
- **Retro chatlogs:** a durable Change-to-session manifest written when a step session is chosen and when it ends, on
  every ending path; at a step's end its `events.jsonl` is gzipped to `~/.owlbear/retro/chatlogs/`, with the files
  the runtime saved large outputs to if still present (missing ones are recorded). A chat counts as finished after a
  day without events; its log is copied when Retro takes it. The logs of an unfinished Change, and of any unit Retro
  has not judged yet, are kept; once Retro has judged a unit, its logs that no finding, case or pending proposal refers
  to go 30 days later. Encrypted reasoning stays unreadable; only its summaries are kept.
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
- **Marks** each finding that a look during the task could have caught in time to change its course; if such
  findings are frequent, a periodic big-picture look is reconsidered with the owner (the rethinker was dropped,
  D-01M5WBKHD13WNNR1C7PJ6FV6NT).
- Lessons need causal evidence repeated across independent tasks, counterexamples weighed; merging them is the
  curator's (Global, D-01M5WC085F34Y2RVPXFC3ZX53C). A fix becomes an issue (OwlBear) or a backlog entry (a project);
  memory is a bandage, a fix the stitches (D-01M5WAK48NRE79JZFAHDGWS4DA).
- Judgement is saved first; each finding has a stable id visible where it is published, and a retry reconciles by id
  before creating anything.

## 6. Proposals and the owner

Each proposal is challenged by `retro-review` (Sol): is the evidence real, is the direction right, what could it
break. Survivors, capped per week, reach the owner on the **Improvement page**, which also shows the Spotter (its
switch and category actions, verbose, credits spent and looks stopped at their limit, recent records with grades), its looks and outside writes across
Changes (filterable by Change, marking those whose irreversible-harm action stopped a step), Retro (runs, state, a
button) and the Spotter cases (stages, versions). There, and on a Change's page, a finding can be turned into
follow-up work (D-01M5W9AE1G5T7B5NY998CASAJ9). A Change's page shows the Spotter's and Retro's detail for it only
behind a machine-local display switch, clearly labelled and exposed like the theme toggle; a stopped step's reason
always shows (D-01M5W9AEB412SNWYM2CS27H68M).
- A proposal states its direction in one line, why (evidence, cost seen), what would change and the review's verdict.
- The owner decides **direction, not details**: accept, reject, redirect (free text, read back) or later.
- Accepted: a Spotter case moves a stage (with the regression); a lesson becomes a pending memory in its folder; a
  project's agent, skill or Delivery change becomes a backlog entry (source `retro`); OwlBear's own becomes an issue
  in its repository for a chat to build. Nothing is edited silently, and a Change's brief bounds what it may change.
- Every publication outside this machine (cases, proposal evidence, backlog entries, issues, memories) is reviewed,
  minimised and sanitised, credentials included; raw cards, chatlogs and records stay on this machine, unmasked.

## 7. Build order

Each slice is a pull request, with Sol on its plan and its code, and is built complete: where evidence is missing,
marked assumptions or synthetic cases fill the gap and one reset removes them later; nothing is deferred
(D-01M5XB9M1A1MNG0S54N367RC70):
1. this design: built (#659, #660);
2. settings and roles: built (#662); the on/off switch and the four category actions replacing `mode` (#697);
3. Retro chatlogs: built (#663);
4. the card builder: built with 6's Delivery part (#668);
5. Spotter records and cases: records built (#668); cases built (#705);
6. the Spotter's looks, recording only, for Delivery and chats: Delivery built (#668); the chats follower built (#707);
7. Retro;
8. the Improvement page;
9. live delivery and the test machinery.

Then item 16 (the amendment design session, TD-422), then item 10.

## 8. Built work

- W1a (#640): its feed, identity and writer are reused by the Spotter.
- #647 (shell parsing) is closed.
- Phase 1a (#652) and the Primer (#653) are built.
- Settings and roles (#662): the `watcher` role and switch became the `spotter` role and the Spotter's settings
  (settings format 12); the `retro` and `retro-review` roles; the machine values for budgets, Retro's triggers and
  enrolled chats; none has a code default. The daily budgets were replaced by credit limits per look and run on
  2026-10-27 (#704; settings format 16, written into Global once by the machine host's start).
- Retro chatlogs (#663): the Change-to-session manifest, each step's `events.jsonl` and saved outputs captured at its
  end, enrolled-chat discovery and pruning.
- The Spotter's core (#668): the intake (`improvement/events.py`), the card (`improvement/card.py`), the looks and
  their records, budget ledger (removed with the daily budgets) and lifecycle (`improvement/spotter.py`, `runtimes/spotter_look.py`) and the prompt
  (`improvement/spotter_prompt.md`); `improvement` is a layer between `state_store` and `runtimes`. A live test
(2026-10-26) found that the runtime refuses a session credit cap under 30; a look now sets none. The machine
  registry and machine settings moved to `state_store` so a step reads its budget (D-01M5VXXFC28ZFHV7HVDTKFHPVF).
  A live test on 2026-10-26 ran a real hand-off look after #682: a correct note for 0.07 credits in 7.5 seconds.
- Spotter cases (#705): stages, versions, the no-trade regression, releases and the reserve, the seed from the pilot's
  saved cards, synthetic cases, the reset and publication by `retro-review` ("As built" under Spotter cases in §4).
- Spend metrics (#706): every credit OwlBear spends, Spotter looks and Retro included, is recorded on this machine and
  shown on the Metrics page by project, agent, model and day; metrics never limit (D-01M5XCDF6G60VG5GHTWF5QSSDE).
- The chats follower (#707, slice 6's rest): the machine host follows enrolled chats and records looks at their plans,
  hand-offs, state changes and samples ("As built for chats" in §4); every session OwlBear creates is noted in the
  manifest before it is created.
- The pilot's harness and data stay in `.owlbear/scratch/watcher-replay/` (not committed).
