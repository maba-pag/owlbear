# Improvement: Design

> **Owning task:** the plan's item 9 (formerly "the watcher"), redesigned with the owner on 2026-10-25
> **Date:** 2026-10-25
> **Question:** How do agents get better from their own work: fewer common mistakes, wrong tool arguments,
> rabbit holes and local optimums that miss the real intent, without being steered off course?
> **Status:** the owner's choices of 2026-10-25, after a pilot, a hindsight review of 83 real moments and Sol's
> challenges (§3). They replace the live coach of this design's first version and the per-call outside-write watcher
> of [the earlier draft](delivery-next-watcher-design.md). Catching malicious calls is out of scope for now. Built so
> far: W1a's feed (#640), phase 1a (#652) and the Primer (#653).

## Names

| Name | What it is |
| --- | --- |
| **Improvement** | The group, and its page |
| **Primer** | The lessons every new agent session gets before it starts (§2) |
| **Spotter** | The live agent at an agent's hand-offs; it records notes in shadow until a live test shows a gain (§4) |
| **Spotter cases** | The Spotter's graded example cases: its prompt examples and its regression test (§4) |
| **Retro** | The after-task analysis: reads whole tasks with hindsight, grades the Spotter, proposes lessons and fixes (§5) |
| **Retro chatlogs** | The kept logs of finished agent conversations (chats and Delivery steps) that Retro reads (§5) |

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

## 4. Spotter: live, in shadow first

- **Where:** Delivery steps first. Delivery is the SDK client of every step and receives each event as it happens;
  chats need a hook at the agent's stop first.
- **When:** only at a **hand-off**: the step's `submit_result` (or the end of a turn that reports to the requester).
  Never mid-flow, never on a clock.
- **What it sees:** the intent (task, criteria, scope, the requester's latest messages and answers), the agent's
  stated plan, the hand-off itself, the recent actions with their evidence, and the work still open.
- **What it judges:** does the hand-off match the request? An unfinished requested item, an acceptance gap its own
  evidence shows, work handed back that it could do, a conclusion its evidence does not support or a standing
  decision forbids (the decision-conflict check on the picker role, TD-456/TD-459). Honest partial reports, blockers
  and decision requests are never pushed to continue.
- **What it does now:** records its note, sends nothing. Each recorded note is graded later by Retro.
- **Going live:** only after its grade is high, and then through a steered-versus-silent test on real tasks that
  compares whole-task outcomes, credits and time, including how the agent reacts to the note.
- **Spotter cases:** real hand-off moments with Retro's verdict (speak or stay silent, and why): a few as the
  Spotter's prompt examples, the rest as its regression test (a protected core, recent challenges, a holdout).
  Replace-better, never a growing pile.

Dropped from the first version: the mid-flow coach and its signals, intent checkpoints, `consult_coach`, and the
switches' "rule verdicts" and "stop/retry/steer" parts. The rethinker (D-01M5MFATRF5RFMJY9C8284FDV5) is not part of
this design.

## 5. Retro: after the task, with hindsight

- **Runs:** as a machine-host job, like memory curation: after a Change ends (merged or abandoned), when idle over
  the chats finished since its last run, or by a button on the Improvement page. One run at a time, on its own
  session slot and budget.
- **Reads:** Retro chatlogs: the Copilot runtime's full event log of each finished conversation (every tool result,
  message and compaction summary; compaction only shrinks the model's context, not the log) plus the large outputs
  the agent saw only as saved files. Delivery keeps the chatlogs of the steps Retro and the Spotter cases refer to;
  older ones may go. Encrypted reasoning stays unreadable; only its summaries are kept.
- **Judges:** whole tasks, including what happened after a requester's correction: what went wrong, what it really
  cost, whether the agent recovered, and whether a note at a hand-off would have been worth its risk. A requester's
  correction is a signal to look, not a cost by itself; moments are also drawn at random, and evaluation keeps
  sessions apart.
- **Produces:**
  - grades for the Spotter's recorded notes, and Spotter cases;
  - lesson candidates for the Primer, through memory curation and its approval rules;
  - tool and contract fixes as backlog entries;
  - on the Improvement page: its findings, the Spotter's grade, the Spotter cases, and its proposals, capped, with
    options.

## 6. Rollout and measurement

1. Tool and contract fixes, and the Primer: built. Measure recurring error signatures across runs.
2. Retro, with its chatlogs kept, and the Improvement page.
3. The Spotter in shadow at Delivery hand-offs, graded by Retro.
4. A steered-versus-silent test, only once the grade is high.
5. Chats: the Spotter's hand-off hook, once Delivery shows a gain.

## 7. Built work

- W1a (#640): its feed, identity and writer are reused by the Spotter.
- #647 (shell parsing) is closed.
- Phase 1a (#652) and the Primer (#653) are built.
- The pilot's harness and data stay in `.owlbear/scratch/watcher-replay/` (not committed).
