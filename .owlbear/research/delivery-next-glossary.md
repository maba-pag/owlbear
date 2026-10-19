# Delivery Glossary: Words That Look Alike

> **Owning task:** Delivery rebuild, owner direction of 2026-10-14 ([rebuild §3.8](delivery-liveness-first-rebuild.md))
> **Date:** 2026-10-14
> **Question:** What exactly does each of Delivery's near-synonyms mean, so that agents, prompts, code
> and the owner use one meaning per word? Every row is a draft (`autonomous`) until the owner confirms it.
> **Status 2026-10-19:** design history; the record and the code win where they differ. Intent:
> [the record](delivery-liveness-first-rebuild.md); status: [the plan](owlbear-plan.md).

## 1. Context and Question

The owner asked for definitions of word pairs "that may feel similar but aren't", starting with review
and challenge (TD-71). Each definition names the property that separates it from its neighbour. Where
code or records use a word against the proposed meaning, the row says so. Renames follow only after
confirmation.

## 2. Sources Studied

| # | Source | Used for |
| --- | --- | --- |
| G1 | Decision table and §3.13 in [the rebuild](delivery-liveness-first-rebuild.md): TD-27, TD-34, TD-36, TD-45, TD-50, TD-55, TD-56, TD-69, TD-71, D4, R1, R5 | Decided meanings |
| G2 | `owlbear_delivery_next` at `a068a6cf7`: `models.py` (`StepKind`, `Exit`, `Stop`, `PersonCheck`), `roles.py` (`SESSIONS`), `runner.py` (`_challenge`, `_brief_review`, `_reviewer`), `loop.py` (`brief_review`, the check order), `api.py` (pause, resume, abandon) | How the code uses each word |
| G3 | `share/instructions/owlbear-system.instructions.md` §1 | `decided`, `approved` and `autonomous` |
| G4 | [Watcher design draft](delivery-next-watcher-design.md) | Words the watcher introduces |

## 3. Terms

### 3.1 Judging work

| Term | Proposed meaning | Separating property |
| --- | --- | --- |
| Review | An independent judgement of finished work in fresh sessions that did not make it: the task review after each task, the final review of the whole Change before publication, and the visual review of the screenshots after it (TD-74, `decided`). Its verdict decides the Change's path: pass, or findings that become work | Judges finished work |
| Challenge | A test of a work product while its step is still making it: the plan challenge and the brief challenge (TD-73) on the challenger role, or a subagent the worker starts. Its findings go back into that step: another round, or to the owner while shaping. "Accept" never applies to it (TD-71) | Judges work in progress, inside the step that makes it |
| Check | A verification by fixed means rather than judgement: the project's check commands, the visual check's capture and error comparison, a person-only check (`PersonCheck`) | Mechanical or human procedure, not a model's opinion |
| Test | A check written as code in the project | A kind of check, never a review |

Conflicts found in the code (G2):
- The plan challenge's session label is `plan-review` (`runner._challenge`, `roles.SESSIONS`).
  Renamed to `plan-challenge` with TD-73.
- The brief review is a challenge (TD-73) and becomes the brief challenge. Delivery still binds its
  verdict to the brief version (`loop.brief_review`), so that a changed brief is challenged again.
- The screenshot judgement is the visual review (TD-74). Its capture, console errors and detector run are the
  visual check; the two judges' verdicts are the review (TD-78).

### 3.2 The owner's part

| Term | Proposed meaning | Separating property |
| --- | --- | --- |
| Decided | The owner chose it directly: an answer, or his own words (G3) | Only the owner changes it |
| Approved | Part of something the owner approved without being asked about it separately (G3) | Can be superseded with a recorded reason |
| Autonomous | Chosen by an agent or the assistant (G3) | Can be superseded with a recorded reason |
| Approve (a brief) | The owner releases one brief version for planning | Acts on a plan of work, before it is done |
| Accept (a held result) | The owner takes a step's held result as valid without running the step again (TD-56) | Acts on finished work whose evidence Delivery could not complete |
| Question | Delivery asks the owner and waits; the Change does not move until he answers (`Exit.ASK`) | Needs the owner; blocks the Change |
| Steering | A message added to a running session: by Delivery, the watcher, or the owner in a window | Changes a session's course; does not wait for the owner |
| Reminder | Delivery's steering to a session that went idle without a result | A kind of steering, only on idleness |

### 3.3 Units of work

| Term | Proposed meaning | Separating property |
| --- | --- | --- |
| Change | The owner's unit of intent: one brief, one branch, one pull request | What the owner asks for |
| Task | One item of a Change's plan | What the planner splits a Change into |
| Step | One stage of Delivery's loop for a Change, one of ten kinds (`StepKind`: shape, plan, build, review, integrate, publish, follow, check, merge, cleanup) | Delivery's state; may run zero, one or several sessions |
| Attempt | One run of a step; a retry or rerun is a new attempt | The thing the watcher stops and counts (D6) |
| Session | One agent conversation in a runtime | A runtime object; a step's attempt may use several (worker, challenger) |
| Turn | One model response cycle inside a session | The unit a model is billed and cancelled by |

### 3.4 Going again

| Term | Proposed meaning | Separating property |
| --- | --- | --- |
| Retry | Delivery runs the step again on its own after a failure, within its budget (`Exit.RETRY`) | Delivery's choice, counted |
| Rerun | The owner chooses "Run this step again" | The owner's choice |
| Resume | The same session continues, for example after an answer | Same session, not a new attempt |
| Back | The step's outcome sends the Change to an earlier step (`Exit.BACK`), for example build to plan | Changes the step, not only the attempt |

### 3.5 Ending and refusing

| Term | Proposed meaning | Separating property |
| --- | --- | --- |
| Deny | The SDK guard refuses one tool call before it runs; the session goes on (TD-45) | Before the action, one call |
| Stop (`Exit.STOP`) | The Change halts until a named actor performs an action, and a stated condition resumes it (`Stop`) | Halts the Change, waits for a person or event |
| Watcher stop | The watcher ends a running attempt after an action, then D6's retry or question follows (TD-55) | After the action; ends the attempt, not the Change |
| Cancel | Ending a model turn in the runtime; it does not by itself end the turn's processes | A runtime operation |
| Pause | The owner halts a Change, resumable | The owner's choice, reversible |
| Abandon | The owner ends a Change; Delivery cleans up | The owner's choice, final |

"Stop" names both `Exit.STOP` and the watcher's action. **Proposal:** the watcher's action becomes
"interrupt", so that "stop" keeps one meaning.

### 3.6 Runtimes and visibility

| Term | Proposed meaning | Separating property |
| --- | --- | --- |
| Runtime | Where a session runs, from the catalogue: `sdk` or `window` (§3.13) | Delivery's choice per step |
| Harness | The Copilot agent engine behind both runtimes: the same tools, the same session record (P25, P26) | One engine, two runtimes |
| Route | The earlier word for runtime, in the route comparison | **Proposal:** retire it |
| Visible | The owner can follow the session live, because it runs in a window (R1, TD-35) | The owner's view |
| Watched | Visible (R5: "watching is only seeing") | Same as visible; **proposal:** drop "watched" so it is not confused with the watcher |
| Watcher | Delivery's monitor of running attempts: reads, judges actions, interrupts, infers stages (TD-55, TD-66) | Acts; the owner only sees |
| Guard | The SDK runtime's permission policy, before each call (TD-45) | Before the action; the watcher acts after |
| Interactive | A role that asks the owner in the chat, through the question tool (D4) | Mode of the role |
| Autopilot | A role that never asks in the chat; it raises Delivery questions instead (D4, N10) | Mode of the role |

### 3.7 Agents and their material

| Term | Proposed meaning | Separating property |
| --- | --- | --- |
| Role | A job Delivery fills: planner, builder, reviewer, challenger (`roles.py`) | Has a model and effort |
| Agent | The definition a role runs with: prose, tools, preloaded skills (`agents/*.md`) | A file |
| Worker | A session working on a step in a role | A running thing |
| Subagent | A session that a worker starts itself with `task` | Started by the agent, not by Delivery |
| Skill | A named procedure or body of knowledge an agent loads, preloaded or on demand | Loaded by name |
| Instruction | Rules a host applies by file pattern, without being asked | Applied automatically |
| Prompt | The message Delivery sends to start or continue a session | Per session, written by Delivery |
| Tool | An operation an agent can call. Missing: needed but not available (TD-36). Denied: available but refused for this step. Hidden: not offered at all (TD-69) | Three distinct failures |

### 3.8 What is kept

| Term | Proposed meaning | Separating property |
| --- | --- | --- |
| Memory | Agents' durable, reusable lessons in owlbear-memory (TD-70) | For future agents |
| Research | Source-grounded analysis and design drafts in `.owlbear/research/` | For decisions |
| Decision record | A TD, D or R row with its origin (G3) | Authority |
| Activity log | Delivery's record of what a Change's sessions did (`activity.jsonl`) | Evidence of one Change |
| Session record | The runtime's own event file per session (P26) | The runtime's, not Delivery's |

## 4. Recommendation, Confidence, and Limits

- Confirm, change or strike each row. Then the code, prompts and agents follow the confirmed words in
  one pass, starting with `plan-review` → `plan-challenge` and the watcher's "interrupt".
- Open for the owner: none in §3.1.
- Confidence: high where a row cites code or a decision; medium where it proposes a new word.
- Limit: the list covers words found in Delivery-next's code and records. The old Delivery's terms
  (packet, proposal, admission) are left out.
