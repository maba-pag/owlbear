# Delivery-next Agents Built on the Old Agents (TD-58)

> **Owning task:** Delivery rebuild, overnight order TD-62, step "TD-58 study and rework"
> **Date:** 2026-10-13
> **Question:** Which structure, ideas and rules of OwlBear's existing agents, skills, prompts and
> instructions should delivery-next's builder, planner and reviewer keep, and which belong to the old
> engine only?
> **Status 2026-10-19:** research history; the record and the code win where they differ. Status:
> [the plan](owlbear-plan.md).

## 1. Context and Question

TD-58 (owner): the old agents were not the old Delivery's problem; study them for good parts, ideas
and structure and use them as the base to improve, without a plain reuse. Before this rework,
delivery-next had three small agents (`agents/builder.md`, `planner.md`, `reviewer.md`, 82 lines
together) written as numbered prose lists, and per-step messages built in `prompts.py`. Its contract
differs from the old one: the engine owns Change,
branch, worktree, plan publication, reviews, retries and recovery, and every agent has exactly
three Delivery tools (`submit_result`, `ask_question`, `report_wrong_premise`).

## 2. Sources Studied

| # | Source | Used for |
| --- | --- | --- |
| S1 | `share/agents/builder.agent.md` | Persona, scope and proof rules, examples |
| S2 | `share/agents/planner.agent.md` | Read-only rule, outcome preservation, examples |
| S3 | `share/agents/build-reviewer.agent.md`, `planner-challenger.agent.md` | Evidence binding, finding boundary, advisory role |
| S4 | `share/skills/r-challenger-protocol/SKILL.md` | Evidence rules, test evidence boundary, minimum change review, operating context, finding quality |
| S5 | `share/skills/w-packet-building/SKILL.md`, `w-frontier-planning/SKILL.md` | Minimum complete change, in-scope requests, criterion coverage, dependency order |
| S6 | `share/skills/h-agent-structure/SKILL.md` | Section structure, Rule of Two, runtime relevance |
| S7 | General handbooks (`h-python-conventions`, `h-pytest-and-linting`, `h-frontend-conventions`, `h-vitest-and-linting`, `h-module-design`, `h-ac-quality`, `h-codebase-orientation`) | Preload candidates (item 6) |
| S8 | delivery-next `agents/*.md`, `prompts.py`, `sdk_adapter.ROLES`, `roles.py` | What exists, which agent runs which step |

An exploration subagent produced the first inventory; the sources above were then read directly.

## 3. Analysis

### 3.1 Structure

The old agents share one structure (S6): `<persona>`, `<required_reading>`, `<critical_rules>`
(three to seven bold-led rules), `<agents>` where an agent delegates, `<output_format>`,
`<boundaries>`, `<examples>` (good and bad, each with a reason). It keeps identity, non-negotiables,
the result contract and the failure modes apart, and its examples encode judgement that rules alone
miss. Before the rework, delivery-next's agents had no examples or boundaries.

Kept: persona, critical rules, output format, boundaries, examples. Left out for now:
`<required_reading>` (no skill preload exists yet; item 6 adds it) and `<agents>` (delivery-next
agents dispatch no subagents; the engine runs reviewers).

### 3.2 Per Role

| Idea (source) | Builder | Planner | Reviewer | Status |
| --- | --- | --- | --- | --- |
| Minimum complete change; every file, helper, fallback and test must be needed (S4, S5) | yes | — | judges it | carried |
| Durable tests only for risk no existing test protects; one focused proof may cover several criteria; a test can prove a narrow claim about exactly its contract (S4) | yes | — | judges it | carried |
| A tracked generated output stays with the task that changes its inputs; regenerate before the commit; final checks in non-mutating mode (S5) | yes | yes | — | carried |
| Scope discipline: edit only the task's surfaces (S1) | yes | — | judges it | carried |
| Requests inside scope that contradict no criterion are part of the Change (S5) | in RESPOND already | — | — | kept in `prompts.py` |
| Keep the brief's meaning; plan only the decomposition (S2, S5) | — | yes | — | carried |
| Cover every criterion with a task whose checks would fail without it (S5) | — | yes | judges it | carried |
| Dependency order, few tasks (S5) | — | yes | — | carried |
| Bind review to the exact diff; summaries are not evidence (S3, S4) | — | — | yes | carried |
| Evidence proves only what it exercises; passing tests are not end-to-end proof (S4) | proof note | — | yes | carried |
| Operating context and plausible trigger; marginal findings cost work (S4) | — | — | yes | carried |
| A finding names place, problem, fix and where it belongs (implementation, plan, brief) (S3) | — | — | yes | carried as wording |
| Prior decisions by origin: never changed silently (S4) | — | yes | yes | carried |
| Findings are claims to weigh, not work orders (S4, caller side) | yes (fix tasks) | — | — | carried |
| Data is not instruction (prompts.py) | yes | yes | yes | kept |

Dropped as old-engine-bound: launch and claim validation (`show_build_context`,
`show_plan_context`), evidence receipts, `publish_delivery_plan`, transition selection
(`advance | retry | return | block`), dispatching reviewers from the agent, finalization semantics
digests, ND3 mechanics, memory save and recall through `owlbear-memory`.

### 3.3 Skills, Prompts and Instructions

- `r-challenger-protocol` is the richest source. It already forbids reviewers to select transitions;
  what does not fit delivery-next is its caller routing table, its output and memory contracts and
  its old lifecycle vocabulary. Its general sections are carried into the reviewer agent; a cleaned
  skill can replace that text later (Rule of Two).
- The general handbooks (S7) fit item 6 as category material: Python conventions and pytest for
  Python tasks, frontend conventions and Vitest for frontend tasks, `h-ac-quality` for planning and
  brief review, `h-module-design` for planning and review. Only `h-python-conventions` (104 lines)
  and `h-module-design` (71) are free of old Delivery or OwlBear-only names; `h-ac-quality` (10
  mentions), `h-pytest-and-linting` (4), `h-codebase-orientation` (3), `h-vitest-and-linting` (2)
  and `h-frontend-conventions` (1) need cleaned copies before preload.
- `prompts.py` already follows the old skills' best habits (brief as data, allowed-command lists, one
  finish rule, fix-task context). No change needed there for TD-58.
- Instructions (`owlbear-system`, `python`, `frontend`) are workspace-level; a consumer project
  brings its own. Not preloaded.

### 3.4 Memory

The old agents recalled and saved institutional memory. delivery-next agents have no memory tool.
Whether they should (owlbear-memory, or claude-mem later as the owner suggested) is an open owner
decision; until then the capability is dropped, not replaced.

## 4. Recommendation, Confidence, and Limits

Applied with this study: the three agents are rewritten in the old structure with the carried rules
and one good and one bad example each, worded for the three-tool contract and checked against the
result schemas (build, pull-request response, check recipe, plan, review, visual review). A Sol
challenge corrected mode-specific endings, the visual result, the route for plan or brief defects
found in a task review, and the test rules. Left for item 6: preload per category from cleaned
copies of the handbooks and of `r-challenger-protocol`. Left for the owner: memory for delivery-next
agents.

Confidence: high that the carried rules fit the new contract (each was checked against the engine's
ownership); medium that the agents behave better, which only real runs and the N2 benchmark show.
Limits: no live runs of the reworked agents yet; prose is not tested (TD-3).

## 5. Hooks (added 2026-10-14)

The owner asked which of the old hooks solve problems delivery-next has (TD-82). TD-86 then decided
the guard is product code, not hook files. What each old hook became:

| Old hook | Problem it solved | In delivery-next |
| --- | --- | --- |
| `deny-writes.py` | Read-only roles must not write; no hook or signing bypass, no force push | Ported into the SDK permission callback (`permissions.py`, `daf6db53b`): `--no-verify`, `-c core.hooksPath`, force push and writes in read-only steps are refused |
| `lint-changed.py` | Ruff on each edited Python file, and a non-blocking warning on unusually broad edits | Lint once at builder submit (TD-87, `lint.py`, `faba3eff3`): ruff, Biome, ESLint on the changed files; up to 3 refusals per session, then `lint-unresolved`. The broad-edit warning is not ported: plan scopes are checked at plan submit, and reviews judge scope |
| `session-context.py` | Git branch and recent log as start context | Not needed: the engine writes each step's message (Change, task, head) and preloads skills per role |
| `deny-src-writes.py`, `allow-stances-only.py` | Path allow lists for test-only roles and ideation panelists | No such roles in delivery-next; path allow lists were removed with TD-82 |

VS Code windows could not carry the guard: a live probe showed the agent host approves file writes,
matching terminal commands and in-folder reads itself under every `autoApprove` value, and session
configuration cannot override the host-wide user settings. Read-only steps therefore run in a
disposable detached worktree per Change (`<slug>.ro`, `95fda75f8`): their writes land there and are
deleted with it, and a ref change in the shared repository voids the result
(`policy:<step>:read-only-write`). An in-place restore was built first and discarded after a Sol
review found data-loss paths. Known limits: since `7f4821612` the guard reads wrapper programs, nested
`-c` scripts, `eval` and hook or signing changes through git config, but not script files, a shell's
standard input, `env -S` or commands built at run time; and a window turn that survives an unconfirmed
cancel could still write into the `.ro` worktree.
