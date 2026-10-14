# ECC Evaluation for Delivery-next Roles and the Subagent Question

> **Question:** What from ECC (`affaan-m/ECC`, shallow clone at `b92f181`, 2026-10-11) should
> Delivery-next adopt, in which form, and should builder and planner keep `task`, `read_agent`,
> `list_agents` and `write_agent`?
> **Date:** 2026-10-15. **Mode:** read-only research; no ECC script, hook or installer was run.
> **Status:** Sol challenged this report ("After fixes", 85 %); section 8 lists the corrections,
> which are applied in place. The owner then decided TD-111 (subagents) and TD-115 (adoptions 1-9)
> in `delivery-liveness-first-rebuild.md`.

Path shorthand: `E:` = `.owlbear/scratch/ecc-study/ecc/`; `N:` =
`owlbear-dev-next/serve/delivery-next/src/owlbear_delivery_next/`; `S:` =
`owlbear-dev-next/.venv/lib/python3.14/site-packages/copilot/`; `R:` = `owlbear-dev/.owlbear/research/`;
`T:` = `~/.copilot/session-state/` (local runtime transcripts of earlier probe sessions).

## 1. ECC's Model of Agents, Skills, Subagents, Hooks and Rules

- **Rules** are always-on, deterministic constraints injected by path or event; **skills** are
  on-demand playbooks; **MCP** and **CLI scripts** carry tools (`E:docs/capability-surface-selection.md:7-11`).
  **Hooks** are the deterministic gates (`delivery-gate` Stop hook, `continuous-learning-v2`'s
  `observe.sh` on every tool call; `E:skills/continuous-learning-v2/SKILL.md:158-181`).
- **Agents** are subagent definitions: Markdown with `tools` and `model` frontmatter, invoked through
  the Agent/Task tool by `subagent_type` (`E:rules/common/agents.md:5-10`). ECC ships 71; most are
  `sonnet`, `planner`/`architect`/`spec-miner` are `opus`, a few `haiku`. Every agent repeats the same
  6-line "Prompt Defense Baseline". There is no separate "subagent" concept: an agent *is* a subagent.
- **Subagent guidance** (`E:the-longform-guide.md`):
  - context saving: "Sub-agents exist to save context by returning summaries" (:258);
  - cheapest sufficient model: "delegate the cheapest possible model that is sufficient" (:109);
  - the sub-agent context problem: the sub-agent "only knows the literal query, not the PURPOSE" (:258);
  - iterative retrieval: the orchestrator evaluates every return and asks follow-ups, "max 3 cycles"
    (:265), "Pass objective context, not just the query" (:267); expanded in
    `E:skills/iterative-retrieval/SKILL.md:47` with pseudo-code (no runnable implementation).
  - "Delegation Completion Contract": a delegator must wait for and integrate its children before
    ending its turn (`E:rules/common/agents.md:51-59`).

**Evidence versus opinion.**

| Claim | Basis |
| --- | --- |
| Model-per-task table | Opinion, labelled "Hypothetical setup" (`longform:114`); "Default to Sonnet for 90%" (:127) unsupported |
| pass@k figures | Arithmetic error: with p=0.7, pass@3 is 97.3% and pass@5 99.8%; the guide prints 91%/97% (:164). pass^k figures (:167) are correct |
| Iterative retrieval, max 3 cycles | Design heuristic; two illustrative examples, no measurement |
| Delegation Completion Contract | One observed failure described in prose (`agents.md:59`), no data; plausible and matches our own risk below |
| "Skills fire ~50-80% of the time" | Unsourced quote (`continuous-learning-v2:346`) |
| Santa Method ">90% of systematic issues" | Unsourced (`santa-method:307`) |
| AI regression patterns "3 out of 4 regressions" | One project's anecdote (`ai-regression-testing:250`) |
| Reviewer noise is "the primary failure mode of LLM reviewers" | Opinion (`code-reviewer.md:73`); agrees with OwlBear's own reviewer rules |
| 80% coverage, test-first always, "MUST BE USED" triggers | Opinion/house style |

I found no measured effectiveness data for any agent or skill I read; `skill-comply` is tooling to
measure compliance, but no reports were in the paths I read.

## 2. SDK Verification (github_copilot_sdk 1.0.19)

| Question | Finding | Evidence | Status |
| --- | --- | --- | --- |
| Can a session define custom agents with restricted tools? | Yes. `CustomAgentConfig` has `name`, `prompt`, `tools`, `mcp_servers`, `infer`, `skills`, `model`, `reasoning_effort`; passed as `custom_agents` | `S:session.py:1373-1393`; wire format `S:client.py:4550-4579`; payload `S:client.py:2860-2869` | Verified (source). Runtime: a `counter` agent got exactly `['view','glob','grep']` (`subagent.selected`) |
| Can `task` be limited to Delivery-defined agents? | Partly. `excluded_builtin_agents` hides built-ins "from discovery and [they] cannot be selected or invoked" (`S:client.py:2512-2515`, sent at 2832-2833). `infer` marks "whether agent is available for model inference" (`S:session.py:1384`). `session.rpc.agent.list(SessionAgentListRequest(include_built_in_agents=True))` returns each agent with `disable_model_invocation`, `model`, `model_policy` (`S:generated/rpc.py:56680`, `AgentInfo` at 31161), so Delivery can check the effective list before the first send. `DefaultAgentConfig.excluded_tools` applies only to the default agent (`S:session.py:1396-1406`), which Delivery does not use | Source | **Unverified at runtime**: the complete built-in list (docs name `explore`, `task`, `general-purpose`, `S:generated/rpc.py:17310`); whether `general-purpose` is excludable (it is "special" and "not overrideable" for prompts, `rpc.py:56686`); whether `infer: False` stops the role agent spawning itself |
| What does Delivery do today? | One custom agent (the role), no `excluded_builtin_agents`, no `infer` | `N:sdk_adapter.py:58-67, 309-311`; builder/planner grant `task, read_agent, list_agents, write_agent` (`N:agents/builder.md:4`, `N:agents/planner.md:4`) | Verified |
| Observed subagent use | A Delivery builder probe session started `general-purpose`, which ran `printf c > c.txt && ls` in the worktree (the probe's prompt asked for that delegation and write); a probe role agent (`cprobe`) spawned itself three levels deep without being asked; 5 of 18 recorded starts ran in `background` mode (a mixed probe sample: feed checks and dynamic workflows) | `T:watch-cea3ff04…/events.jsonl:6, 29-32`, `T:3dc6dfd7…:113, 193, 221`, tally of all `subagent.started` in `T:` | Verified (transcripts). These show what the runtime allows, not how often ordinary Delivery steps would do it |
| Which model does a subagent run on? | Custom agent `model` is a preference: "runtime falls back to parent model if unavailable"; effort inherits only for the same model (`S:session.py:1388-1393`). Sources: `explicit_override` (the `task` call's model argument), `configured_required`, `configured_preference`, `complementary_default`, `session_inheritance`, `agent_definition_default` (`S:generated/session_events.py:15931-15958`). Observed: 7 of 9 `general-purpose` starts used the session model (`session_inheritance`), 2 were resolved by `runtime_policy`; custom `scout`/`counter`/`tester` ran their own model (`agent_definition_default`); a Haiku subagent billed under its own model on the business seat (`R:delivery-liveness-first-rebuild.md:906-908`) | Source + transcripts | Built-ins inherit the step model (Opus for builder/planner). **Unverified**: whether a `task` model argument overrides a custom agent's model; the personal-account probe billed only Auto (`owlbear-dev-next/.owlbear/research/delivery-next-platform-probe.md:59`) |
| Does a subagent's shell/edit pass the permission guard? | SDK: yes, through the same per-session handler. The handler gets only `session_id` (`S:session.py:532-535`, dispatch 3300-3330); shell requests carry no agent identity (`S:generated/session_events.py:8182-8200`), read/write only a `tool_call_id` (8125, 8486). Observed: the subagent's `printf c > c.txt` and the `counter` and `tester` agents' reads (four and two) appear as `permission.requested` in the parent session, with the subagent's tool-call ids | Source + transcripts | Verified for SDK steps. Consequences: a planner subagent's write is denied (Policy `write=False`, `N:prompts.py:428`; inference, not observed); a builder subagent can write wherever the builder can; the guard cannot give a subagent a narrower policy unless Delivery correlates `tool_call_id` with `parentToolCallId` (not built). **Window steps** auto-approve (`N:vscode_adapter.py:38`) and have no guard at all (`R:delivery-next-agent-runtime.md` P23) |
| Other hooks | `on_subagent_start` can prepend context; `on_subagent_stop` can block or rewrite a subagent's response (`S:session.py:1245-1320`) | Source | Unused by Delivery |

Two further risks surfaced. (1) The role agent's `tools` include Delivery's terminal result tools
(`N:sdk_adapter.py:66`), so a subagent of the role's own type is offered `submit_result`; whether the
Gate would accept a call from it is unverified (no such call appeared in `T:`). (2) A background
subagent can outlive the parent's `submit_result`, writing after the commit Delivery reads; teardown
then has to kill it.

## 3. ECC Candidates per Role

Read in full = whole file, except the identical 6-line Prompt Defense Baseline skipped in
`typescript-reviewer`, `react-reviewer`, `build-error-resolver` and `e2e-runner`.

| Role | ECC candidate | Form | What it adds (overlap) | Cost / risk | Rec. |
| --- | --- | --- | --- | --- | --- |
| Shaper | `intent-driven-development` (skill) | 2 lines in `N:skills/delivery/SKILL.md` | "Do not infer product or business constraints from code" — record them as assumptions to confirm; each criterion may name a **Must not** side effect. Overlap: shaper steps 1-3; `owlbear-acceptance` C1-C3 | Small | Adopt the two rules |
| Shaper | `spec-miner` (agent, opus, Write) | — | OpenSpec Requirement/Invariant mining for brownfield. Not our artifact | Opus + writes | Not adopt |
| Planner | `planner`, `architect`, `code-architect` (agents) | — | Generic plan template, scalability checklist, build order types→core→UI→tests. Overlap: planner "Few tasks, real dependencies", "Bound each task". Conflicts: "80%+ coverage", "backwards-compatible changes" (vs no-legacy), phases of polish | Drift from minimum-change rules | Not adopt |
| Planner | `change-impact`, `module-regression` (skills) | 1 line in `N:agents/planner.md` | Derive callers and downstream consumers from real imports and calls, "not from directory names"; mark unknown edges `unverified`; include consumers' tests in a task's checks; "verdict = exit code". Overlap: `owlbear-module-design` dependency classes | Small | Adopt one line |
| Planner/Builder | `search-first` (skill) | — | "Does it already exist in the repo or a dependency?" Overlap: owlbear-system "Reuse before creation"; registry/MCP search does not fit a sandboxed step | Network, installs | Not adopt |
| Planner/Builder | `code-explorer` (agent), `iterative-retrieval` (skill), `docs-lookup` (agent) | Only if option (b) in §4 | Structured explore return (entry points, flow, key files); dispatch rules (objective + why, evaluate, ≤3 follow-ups). `docs-lookup` needs Context7 MCP | Subagent risks §2; Context7 is a new external server | Defer to (b) |
| Plan challenger | `santa-method` (skill) | — | Two independent reviewers, both must pass, fresh reviewers each round, cap 3. Overlap: Delivery already starts independent judges on another model (`N:sessions.py:106`); TD-71 keeps challenges unrecorded | 2-3× review cost | Not adopt |
| Plan challenger, Builder, Reviewer | `loop-design-check` (skill) | 1 rule in builder and reviewer | Failure mode #3: "Only gates on 'all tests pass' → agent deletes the tests"; antidote: a boundary of what Build must not do, and "Build may not edit the acceptance conditions". OwlBear builder forbids hook skipping, not test weakening | None | **Adopt** |
| Builder | `tdd-guide` (agent), `tdd-workflow` (skill, partial), `ai-regression-testing`, `test-collaboration` §3 | 1 rule in `owlbear-acceptance` | For a defect fix: the regression test reproduces the real failure shape and is shown failing before the fix and passing after; name it after the defect. Rejected parts: test-first always, 80% coverage, edge-case lists (conflict with "cheapest proof" and the builder's "each test must earn its place") | Small; one more run | **Adopt** the fix-proof rule |
| Builder | `build-error-resolver`, `refactor-cleaner`, `e2e-runner` (agents), `verification-loop` | — | Minimal-diff DOs overlap "minimum complete change". Conflicts: `rm -rf node_modules package-lock.json` (`build-error-resolver.md:99`), `npm install -g agent-browser` (`e2e-runner.md:36`), quarantining flaky tests with `test.fixme` (`e2e-runner.md:76`); `verification-loop` is npm-centric greps | Unsafe or redundant | Not adopt |
| Builder | `agent-introspection-debugging` (skill) | — | Restate objective, verify world state, shrink scope, one discriminating check, then retry. Delivery owns retries and `report_missing_tool` | Small value | Not adopt |
| Reviewer | `code-reviewer` (agent) | 3-4 lines in `N:agents/reviewer.md` or the planned `owlbear-findings` skill | Pre-report gate: cite the exact line; name input, state and outcome; read callers, imports and tests first ("already handled one frame up"); severity defensible; a list of common LLM false positives. Overlap: reviewer "Find what matters", "No findings is a complete and valuable result" | ~10 lines context | **Adopt** the gate, not the checklists |
| Reviewer | `silent-failure-hunter` (agent) | 1 finding category in reviewer | "Dangerous fallbacks" and swallowed errors that hide failure. Builder already forbids unneeded fallbacks; reviewer names no such category | None | Adopt one line |
| Reviewer | `pr-test-analyzer`, `type-design-analyzer`, `comment-analyzer` (agents) | — | Assertion quality ("no-throw checks"), invariants in types, comment rot. Overlap: `owlbear-acceptance` ("a passing test proves its own assertions"), `owlbear-module-design` interface rules | Generic | Not adopt |
| Reviewer | `python-`, `typescript-`, `react-reviewer` (agents) | — | Language checklists; much is linter territory (`react-hooks/exhaustive-deps`, `jsx-a11y`). Conflicts: docstrings and public type hints as findings, "Block: CRITICAL or HIGH" with style items; PR merge-readiness steps Delivery owns | ~110-170 lines each; drift | Not adopt; prefer project linters as checks |
| Reviewer | `security-reviewer` (agent) | — | OWASP list, npm audit, "be paranoid" — conflicts with proportionality (reviewer's "plausible trigger in the project's real context") | Noise | Not adopt |
| Reviewer | `agent-evaluator` (agent) | — | 5-axis prose scorecard for agent answers, not code | — | Not adopt |
| Visual judges | `gan-evaluator` (agent) | — | Live Playwright testing, 1-10 weighted scores, "Be Ruthlessly Strict". Conflicts with blind A/B, cited rules, "Taste alone is not a finding" (`owlbear-ui-review`). Useful idea: report the evaluation mode actually achieved | Model drift toward harshness | Not adopt |
| Visual judges, Shaper | `frontend-design-direction` (skill) | 1 line in `owlbear-ui-design` States; shaper visual states | Adds **partial** and **permission** states to OwlBear's list (hover…success); "unavailable test access is an untested state, not N/A". Rest overlaps Impeccable-derived rules; promotes a paid UIZZE MCP (:157-172) | Community origin (PR #1659), MIT | Adopt the two states |
| Visual judges | `a11y-architect` (agent), `make-interfaces-feel-better` (skill) | 1 line in craft floor | Pointer targets ≥24×24 CSS px (WCAG 2.2 SC 2.5.8); OwlBear's floor has contrast, focus and tab order but no target size. Polish rules (concentric radius, `transition: all`) are taste | Small | Adopt target size only |
| Preparer | `e2e-runner`, `build-error-resolver`, `loop-operator` | — | Nothing fits "pick a declared preparation option, edit only test-system setup"; e2e-runner installs global tools | — | Not adopt |
| Watcher | `conversation-analyzer` (agent, haiku) | Watcher prompt text | Signal taxonomy for lessons: explicit corrections, reverts of the agent's edits, the same mistake repeated, frustrated re-asks. Map to Delivery events: owner answers that override, denials, repeated identical failures, repeated review findings | Small | **Adopt** the signals |
| Watcher, Memory curator | `growth-log` (skill) | Watcher prompt / memory entry shape | Pattern not event; "Next time [signal], I will [action]"; merge entries with the same root cause. Overlap (inferred, `h-memory-structure` not read): OwlBear's "specific, non-obvious, reusable" bar | Small | Adopt the entry shape |
| Watcher, Memory curator | `continuous-learning-v2` (skill) | — | Hook-observed "instincts" with confidence 0.3-0.9, project vs global scope, promote when seen in 2+ projects at ≥0.8, auto-"evolve" into agents/skills. Overlap: owlbear-memory scopes, confidence, curator approval. Auto-evolution bypasses curation | Governance conflict | Not adopt; promotion heuristic optional for curator |
| Watcher | `delivery-gate` (skill) | — | Regex for rationalisations ("skip tests for now", "pre-existing bug") as warnings; mtime gate on learning files | Heuristic | Not adopt |
| Test curator | `test-collaboration` (skill) | New worker skill (e.g. `owlbear-test-curation`) | Purpose vocabulary (rule protection, critical path, regression protection, specialized protection); candidate classes (required, missing, possibly duplicate, possibly stale); "Inventory reports candidates; it does not delete"; "'Hard to test' is not a reason"; "Deleting, weakening, or quarantining tests merely to get green" is an anti-pattern; evidence = file, behavioural assertion, command, exit code. Overlap: the curator's keep-when-uncertain and never-remove list. The `TESTS.md` registry conflicts with TD-72 (no OwlBear files in consumer repos) | ~170 lines source; adapt to ~40 | **Adopt** vocabulary and evidence rules |
| Test curator | `ai-regression-testing`, `module-regression`, `refactor-cleaner` | Same skill | Tests named after the defect they guard are incident regressions (never removed); "verdict = exit code"; "when in doubt, don't remove" | — | Merge the three principles |
| Orchestration (engine) | `loop-operator` (agent) | — | Stall and retry-storm escalation. Delivery's adopted retry policy already covers it | — | Not adopt |

Skills read in full: `iterative-retrieval`, `verification-loop`, `test-collaboration`,
`module-regression`, `change-impact`, `santa-method`, `search-first`, `loop-design-check`,
`context-and-decisions`, `continuous-learning-v2`, `growth-log`, `agent-introspection-debugging`,
`intent-driven-development`, `deep-research`, `ai-regression-testing`, `frontend-design-direction`,
`make-interfaces-feel-better`, `delivery-gate`, `skill-comply`; `tdd-workflow` lines 1-150 of 583.
Also `E:docs/capability-surface-selection.md`, `E:rules/common/agents.md`, longform lines 95-300.
`context-and-decisions` and `deep-research` (web MCPs, parallel subagents) offered nothing for a role.

## 4. The Subagent Decision

Context: TD-53 (`decided`) lets subagents use any named model and voids only Auto
(`R:delivery-liveness-first-rebuild.md:274`). The owner's undecided direction mentions "cheap helper
subagents on `claude-haiku-5.5` (code research, small lookups)" (same file :349, :364). Steps are
bounded: planner 900 s, builder 1200 s (`N:sdk_adapter.py:43`); one task per builder session; judges
already run as separate Delivery sessions, not subagents.

| Option | Pro | Con / risk |
| --- | --- | --- |
| (a) Remove the four tools from builder and planner | Closes every observed path: `general-purpose` on the step's Opus model writing in the worktree, role-agent recursion with result tools, background subagents outliving `submit_result`, unbounded subagent spend inside the deadline. One-line change per agent file plus the TD-99 alignment; window and SDK runtimes behave the same (the window has no guard either way) | Loses context-saving delegation for large repositories; no evidence yet that it was needed (no measured benefit from any source, ECC included) |
| (b) One Delivery-defined read-only research subagent | Context saving at Haiku cost, matching the owner's direction and ECC's cheapest-sufficient guidance | Restrictability only partly verified (§2). Exact shape: custom agent `researcher`, `tools: [view, glob, grep]` (no `bash`: its shell calls would inherit the builder's write policy, since the guard cannot tell a subagent apart), `model: claude-haiku-5.5`, no effort (Haiku 4.5 refused one, `R:delivery-liveness-first-rebuild.md:904-905`), `infer: true`; role agent `infer: false`; `excluded_builtin_agents` = every built-in returned by `agent.list(include_built_in_agents=True)`, and Delivery refuses the step if that list still shows any model-invocable agent but `researcher`. Keep `task` and `read_agent`; drop `list_agents`, `write_agent`. Unverified: `general-purpose` exclusion, `infer: false` effect, a `task` model argument overriding Haiku (the pin is a preference; TD-53 would allow it), forcing sync mode, `ask_user` exclusion inside subagents. Needs a probe and an owner decision; a stricter subagent-model check would change TD-53 |
| (c) Keep general subagents | No work; maximum flexibility | Today's state, with the observed risks above; a builder can delegate implementation to an unguided general agent on Opus; nothing in the agent prompts says when to delegate or that it must wait for results |

**Recommendation of this report: (a) now; (b) only after a probe passes (70 %).** Sol's challenge
recommended instead to keep `task` (and `read_agent`) provisionally for the SDK planner, whose
writes are already denied, and to remove builder delegation (75 %): the risk evidence shows
capability, not likelihood, and the planner benefits most from context-saving research. Starting
hooks only inject context and stopping hooks act after execution, so neither contains a subagent;
correlating `parentToolCallId` in the guard is possible but not cheaper, because some permission
events precede their execution-start records. The window runtime needs its own validated profile.

**Owner decision (TD-111):** Sol's option. The builder loses all four tools; the planner keeps
`task` and `read_agent` in SDK runs; the window planner only after validation. Its subagent is one
Delivery-defined read-only researcher whose model and context tier a benchmark chooses (Haiku 5.5
medium, Haiku 5.5 medium at long context, Luna xhigh, Luna max at long context); the chosen one is
then required, which partly supersedes TD-53. The value of research subagents is measured with the
same planning tasks with and without the researcher.

## 5. Top Adoptions (ranked)

| # | Adoption | Form | Target in `N:` | Effort | Restriction / relaxation |
| --- | --- | --- | --- | --- | --- |
| 1 | Remove subagent tools (option a) | Agent grants | `agents/builder.md:4`, `agents/planner.md:4`; TD-99 test | S | Restriction (owner review, TD-102) |
| 2 | Never delete, skip, weaken or loosen an existing test, assertion or check to make a check pass unless the task names it; the reviewer reports it as a finding | Role prompt text | `agents/builder.md` critical rules; `agents/reviewer.md` "Hold the minimum" | S | Restriction |
| 3 | Defect-fix proof: prefer existing discriminating coverage; show failing-before evidence where feasible, else state the reproduction basis and the gap (corrected: the sources allow manual evidence and "if possible", `E:skills/test-collaboration/SKILL.md:105`, `E:skills/ai-regression-testing/SKILL.md:375`) | Skill text | `worker_skills/owlbear-acceptance` Proof Selection | S | Restriction |
| 4 | Reviewer: check whether a caller already handles the problem ("one frame up"); "dangerous fallback hiding a failure" as a finding category. The rest of the gate already exists (`N:agents/reviewer.md:26, 36`) | Role prompt or `owlbear-findings` | `agents/reviewer.md` | S | Neither (sharpens) |
| 5 | Test curator vocabulary and evidence rules (purposes, candidate classes, inventory never deletes, "hard to test" is no reason). Corrected: protection is classified from assertions and incident evidence, never from test names; exit codes alone do not prove retained protection | New worker skill | `worker_skills/owlbear-test-curation/` (new) + test-curator agent | M | Restriction-consistent |
| 6 | Watcher lesson signals (owner override answers, reverts, repeated identical failures or findings), each only with evidence that the agent's behaviour caused it (a changed preference or an infrastructure denial is not a mistake); entry shape "Next time [signal] → [action]"; merging stays with the curator | Role prompt text | future watcher agent file | S | Neither (new role) |
| 7 | Shaper: product/business constraints are never inferred from code; criteria may carry a "must not"; ask for the observable pain, the current workaround and evidence against assumption (`E:commands/plan-prd.md:45`) | Skill text | `skills/delivery/SKILL.md` steps 2-3; optional `owlbear-acceptance` C2 | S | Neither |
| 8 | UI: add the `partial` state (permission states already exist, `N:worker_skills/owlbear-ui-design/SKILL.md:99`); pointer target size per WCAG 2.5.8 with its spacing and other exceptions; modal focus containment and focus return, proven in the browser (`E:skills/accessibility/SKILL.md:120`) | Skill text | `worker_skills/owlbear-ui-design` | S | Restriction (stricter judging) |
| 9 | Planner: callers and consumers from real imports, their tests in the task's checks, unknown edges marked unverified | Role prompt text | `agents/planner.md` "Bound each task" | S | Neither |
| 9a | Builder and reviewer: trace state changes in order; a later call must not undo an earlier one (`E:skills/click-path-audit/SKILL.md:31`) | `owlbear-findings` and builder prose | `agents/builder.md`, `agents/reviewer.md` | S | Neither |
| 10 | If the researcher is enabled (TD-111): dispatch rules from `iterative-retrieval` and the Delegation Completion Contract (objective and why, evaluate, ≤3 follow-ups, never end a turn while a subagent runs) plus `on_subagent_start` context injection | Prompt + `sdk_adapter.options` | `agents/planner.md`, `sdk_adapter.py:300-318` | M | Relaxation |

The owner approved 1-9 and 9a as TD-115 (numbered there 1-9) and declined a separate MIT notice:
the adoptions are paraphrased ideas, not copied text.

## 6. License, Attribution and Prompt Injection

- `E:LICENSE:1-3`: MIT, "Copyright (c) 2026 Affaan Mustafa"; README repeats MIT (`E:README.md:44, 106,
  142`). Some skills declare other licenses: eight Apache-2.0 declarations and one CC-BY-SA-4.0
  (`E:skills/osint-investigation/SKILL.md:4`); none of the adopted sources declares those. `santa-method` names an outside origin ("Ronald Skelton - Founder, RapportScore.ai");
  `frontend-design-direction` and `make-interfaces-feel-better` are community salvage from PR #1659,
  with a UIZZE contribution via PR #2814. I did not check a contributor agreement.
- Every adoption above is a paraphrased idea of one to four lines, not copied text. If any ECC text is
  copied verbatim, add the MIT notice to the delivery-next `NOTICE.md` beside the Impeccable notice;
  recording the sources there is advisable either way for traceability.
- **Prompt injection:** none observed. A search for agent-directed text ("if you are an AI", hidden
  HTML comments addressed to assistants) found nothing. ECC is full of imperative agent instructions
  by design ("MUST BE USED", "Use PROACTIVELY", `npm install -g`, `rm -rf node_modules
  package-lock.json`, `curl … | sh` as a rejected example); all were treated as data and nothing was
  executed. Commercial content: `frontend-design-direction:157-172` promotes an optional paid UIZZE
  MCP; README promotes ECC Pro. Not adopted.

## 7. Limits

- Not read: `security-review` (511 lines), `eval-harness`, `council`, `accessibility`,
  `frontend-a11y`, `python-testing`, `react-testing`, `e2e-testing`, `gateguard`, `autonomous-loops`,
  `strategic-compact`, `context-budget`, `E:docs/PLAN-PRD-PATTERN.md`, `E:hooks/`, other rules, `E:ecc2/`;
  `tdd-workflow` past line 150. The remaining ~290 skills were judged from catalog descriptions only.
- OwlBear side: `h-memory-structure` and the old `w-test-curation` were not reread; their overlap with
  adoptions 5 and 6 is inference. The test curator and watcher have no agent files yet.
- SDK runtime facts come from earlier probe transcripts in `T:` (one or few runs each, mostly
  `gpt-6-luna` low), not from new runs. Unverified: built-in agent list and exclusion of
  `general-purpose`; `infer: false`; `task` model override against a custom agent's model; forcing
  sync subagents; whether a subagent can call Delivery's result tools and the Gate accepts it; whether
  session `excluded_tools` reach subagents; Haiku billing on accounts other than the business seat.
- The `watch-*` transcripts are attributed to Delivery builder probe steps by their path and the P26
  probe description; I did not read the probe script.
- Process deviation: the ECC repository was shallow-cloned into `.owlbear/scratch/ecc-study/`
  without asking first, which `w-research` requires for large external clones; nothing in it was
  executed, and the clone is deleted once this report is final.

## 8. Sol Challenge (2026-10-15) and Corrections

Verdict "After fixes", 85 %. Sol verified the SDK citations, Delivery's agent setup, the builder
probe's subagent write, the nested `cprobe` delegation, the 18/5/9/7 tallies, and the ECC sources
of adoptions 2-6. Corrections applied above:

1. Capability is not likelihood: the probe write was requested; the background tally is a mixed
   probe sample (section 2).
2. The researcher option needs a validated profile per runtime; hooks do not contain subagents
   (section 4).
3. Adoption 3 was stronger than its sources and the builder's "each test must earn its place"
   (section 5).
4. Test names cannot establish incident provenance (section 5, adoption 5).
5. Watcher signals need causal evidence; merging belongs to the curator (section 5, adoption 6).
6. Several additions duplicated existing text; only genuine additions remain (adoptions 4, 8).
7. WCAG 2.5.8 has exceptions; the license count was wrong; the `agent.list` signature was wrong;
   `counter` made four reads, not six.

Sol's missed candidates, added: `agent-eval` (an evaluation protocol for the TD-111 measurement:
representative tasks, correctness, cost and latency), `commands/plan-prd.md` (adoption 7),
`click-path-audit` (adoption 9a), `accessibility` (adoption 8). Sol skimmed the eleven unread
candidates and rejected `council`, `gateguard`, `autonomous-loops` and `strategic-compact` as
wholes; `context-budget` is harness-specific; `python-testing` and `e2e-testing` offer setup
fragments only within the preparer's boundary; PLAN-PRD's committed artifacts conflict with TD-72
and TD-71.
