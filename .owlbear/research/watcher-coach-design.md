# The Improvement Watcher ("Coach"): Design

> **Owning task:** the plan's item 9, redesigned with the owner on 2026-10-25
> **Date:** 2026-10-25
> **Question:** How can a watcher help a running agent avoid common mistakes, wrong tool arguments, rabbit-holing
> and local optimums that ignore the real intent, with enough context to help but not so much that it is
> overwhelmed, and turn what it sees into better agents, skills and tools?
> **Status:** the owner chose this design ("take your recommendation", 2026-10-25), after a Sol challenge. It
> replaces the per-call outside-write watcher of [the earlier draft](delivery-next-watcher-design.md). Catching
> malicious calls is out of scope for now. Nothing of it is built yet except W1a's feed (#640).

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
- No published evidence shows live nudges help coding agents, so we measure it ourselves.

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

## 2. Prevention first: fix tools, then brief

1. **Tools and contracts.** Derive what can be derived instead of asking the agent: changed_paths from the
   commits, the profile's exact check strings offered as choices. Make errors say exactly what to send. Check the
   toolchain (`python3`, installed dependencies) before the step starts. Every recurring mechanical mistake is
   fixed here, once.
2. **Pre-flight briefing.** At step start, add the few lessons that genuinely apply to this role, project and tools,
   with exact commands or examples. There is no quota.

## 3. Live: the coach (seconds behind, never blocking)

**Observation stream.**
- Every SDK event of a step, normalised and keyed by session, agent and call id:
  - starts, permission requests and completions (result content, errors, exit codes, edit metadata);
  - assistant messages and plans;
  - compactions.
- W1a's identity and writer are reused; its outside-write report logic is not.

**When it looks.** Progress-sensitive scheduling replaces fixed clocks:
- Cheap signals (repeated error signature, unchanged failure after edits, a test-only edit after a red run,
  churn on one file, polls with no work between, a turn ending in a question while tools could act, compaction
  thrash) only *ask for a look* and gather evidence. They never presume trouble.
- Also an occasional check-in when much has happened.
- At most one assessment per worker in flight; triggers coalesce; cooldown and a budget per step; relevance is
  re-checked before anything is delivered.
- Thresholds start as hypotheses and are tuned on labelled runs.

**What it sees.** A small card that indexes the evidence rather than holding all of it:
- the intent: task, criteria, scope, non-goals, plan task, applicable standing decisions;
- what the worker has stated about its approach;
- the last actions, summarised;
- the signal that fired.

Observations, worker claims and coach hypotheses are kept apart, each with references to its evidence. A
budgeted, read-only retrieval returns exact outputs, diffs, code or older attempts when needed, so the coach is
neither starved nor flooded.

**Intent checkpoints (the worker's side).** At an approach change, the worker states in one line:
- the criterion it serves;
- the next experiment;
- the result it expects;
- when it will switch approach.

This is cheap, gives the coach the plan to check against, and makes drift visible. It is not demanded every N
calls.

**What it does.** Usually nothing. Otherwise one advisory note, explicitly below the owner's instructions: an
observation plus one small experiment that tells two explanations apart, not a new plan. Example: "The last two
patches leave failure X unchanged; criterion C needs Y; check Z to tell A from B before another patch. If already
ruled out, carry on."
- Delivered through the SDK's immediate steering, if it proves to arrive between experiments; to be tested live.
- One open note per issue; none repeated without new evidence; no rebuttal demanded; the coach never stops a step.
- The worker can also ask: a `consult_coach(question, evidence)` tool for focused help.

**Bigger picture.** When churn persists, or about every N turns, a stronger model re-reads the original intent
and evidence *independently* of the fast coach's view: is this still the right problem, or a local optimum?
- This is the rethinker's job (D-01M5MFATRF5RFMJY9C8284FDV5), running on the same evidence store. It changes
  that decision's form and needs the owner's word.
- Advice before `submit_result` is an explicit, bounded checkpoint, or it is best-effort. Advice that arrives too
  late never restarts work that is done.

## 4. After runs: the curator (batched, over informative outcomes)

**Reads:** steps with an informative outcome (sent back, retried, owner corrections, reviewer findings, repeated
error signatures), together with the coach's notes and whether they helped.

**Produces:**
- lesson candidates (scoped, with evidence and the cases they do NOT apply to) into pending memories;
- improvement proposals when a pattern recurs (a tool, contract or error message; a skill or agent text; a
  project profile), raised as owner questions with the evidence;
- coach calibration: wrong, stale or derailing notes, and useless signals.

Lessons are curated from corroborated evidence, never from mere obedience. They are retired when a verified fix
removes their cause, or when they don't help on eligible exposures.

## 5. Shape, and why

- **Two time scales, one evidence store, separately attributed assessments.**
  - Live help and learning need different inputs (a partial trajectory, versus a complete one with its outcome)
    and give different outputs (a note, versus a lesson or proposal).
  - They don't need two permanent agents.
  - The stronger check must be independent of the fast coach's narrative.
- **Overlap on purpose:** the coach acts early on partial evidence, the curator late with the outcome, and the
  reviewers judge the final work.
- **Deterministic parts** decide when to look and supply facts. They never certify that something is fine.

## 6. Rollout and measurement

1. Tool and contract fixes, plus pre-flight from approved lessons. Measure: recurring error signatures across
   runs.
2. Coach in shadow on a labelled replay set: does it detect, and what does it miss?
3. Live notes on randomly chosen eligible runs, with others in shadow only. Measure:
   - accepted outcomes, rework, steps sent back or retried;
   - total credits and time, including the worker's reaction;
   - a sample of wrong, stale and derailing notes.
4. The curator over the collected outcomes.

## 7. Built work

- W1a (#640) stays; its identity and writer are reused.
- #647 (shell parsing) is closed.
- The switches decision's "rule verdicts" and "stop/retry/steer" parts no longer fit and need revisiting.
