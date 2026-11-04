# OwlBear — Copilot Workspace Instructions

## 1. Project Identity

OwlBear is a laptop-resident AI development system built around VS Code and GitHub Copilot agents. It plans and executes work through Delivery workflows and shared workspace artifacts. VS Code is the IDE; the filesystem is the integration point.

## 2. Repository Branches

| Branch | Role | Contents |
| --- | --- | --- |
| `main` | The only long-lived branch and GitHub's default | Full workspace: `share/`, `serve/`, `setup/`, `.owlbear/`, `store/`, `tests/`, `pyproject.toml` |

Uncoordinated repository maintenance reaches `main` through a pull request: its required `CI` check must pass on a
branch that is up to date with `main`, and it merges with a merge commit (TD-278). Changes come from Delivery or from
chats run by hand; the Copilot cloud agent doesn't work on this repository (D-01M5ZEKEK1AKGQ726K7KVAC3C9). A pull
request a chat opens by hand merges after green CI and a Copilot review of its latest commit, every finding fixed or
answered (D-01M5WWSS2EB4SDWNWSEXWWBGH2). One that changes runtime code or CI workflows also gets the `coderabbit` label
once its CI passes, which buys one CodeRabbit review from a free allowance of about one an hour, and that review is
handled before it merges; if CodeRabbit reports its limit or sends no review within 60 minutes, the pull request stops
waiting for it (D-01M5WWSXMG291D6X2XMKJX4XYB). A chat-authored pull request that changes runtime code gets
`release:minor`, one that changes only docs or tests none, and `release:major` only on the owner's word (TD-314). Target
delivery uses the branch, worktree, and integration target in its per-change coordination record; never substitute
`main` by convention. Consumers clone the same branch ("clone = install"); versions will be git tags. There is no
generated consumer branch and no sync workflow (TD-203).

### Plan and Status

[The pinned tracker issue](https://github.com/maba-pag/owlbear/issues/713) holds where OwlBear stands, the order of the remaining work, as its
sub-issues, and where the code differs from the decisions. Read it and your item's issue
with its parent when you start or resume work and after a context compaction; a pull request that finishes or changes
an item updates its issue, and the tracker's gap row when it closes or changes a gap. The plan file's
[last version](https://github.com/maba-pag/owlbear/blob/4461a7972278a44a530f92b9c8908564d9a49622/.owlbear/research/owlbear-plan.md) is history. The
old Delivery redesign programme and
[its execution plan](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-redesign-execution-plan.md) are superseded history (TD-202).
The decisions live only in owlbear-data, copied into no repository (D-01M5ZE13N37HZAGJ69VWW69X23); the old decision
record is Git history (TD-466). Look decisions up with `find_decisions` or
`lookup_decisions` and change them only with the decision tools or the Decisions page.

### Asking the Owner

When the owner decides or re-decides anything consequential, including a read-back or a recorded
decision under review, ask one decision per question in his format (TD-41..43, TD-156), written out in
the [shaping skill's Read-Back](../serve/delivery-next/src/owlbear_delivery_next/skills/owlbear-change-shaping/SKILL.md#read-back).
Before asking, challenge the proposal against his intent: what it lacks and what it overdoes, not only
what is wrong (TD-150). In OwlBear also:

- Record each answer with `record_decision`: his confirmed intent, never his words (TD-449); a changed
  decision names the one it replaces. "Take your recommendation" records what the option showed as
  `approved` (`confirmed=true`, `origin="approved"`); details you add stay `autonomous` with their reason.
- Before recording, distinguish new owner intent from implementation/work evidence; do not record an unchanged rule
  again merely because it was used. Keep a finite instruction's explicit bound in its confirmed binding statement,
  not just its rationale. Preserve continuing intent and the owner's scope; implementation or merge implies no expiry.
  Keep mixed intent whole unless the owner confirms its separation; do not mechanically split every instruction.
  If the whole binding cannot fit the statement's limit, ask for faithful wording rather than truncating, hiding
  obligations in rationale or inventing an end condition.
- End the session with one check of everything you record (TD-448). At work completion, use that same check to
  consider only decisions recorded or materially relied on in this work, not the whole inventory.
  For a wholly finite OwlBear project instruction, verify its explicit end condition and every binding clause are
  fulfilled with no continuing intent lost, then use `complete_decision` with the current revision, exact condition
  quote and evidence. Retain history, verify the published receipt and report the completion; do not ask the owner
  to verify historical engineering facts. Investigate uncertain facts and leave unresolved intent active.
  Continuing or mixed rules are not administrative completions. Explain the effect of any proposed intent change:
  `retire_decision` or a replacement through `record_decision` still needs the owner's specific confirmation, and
  a `decided` rule his re-decision. Preserve continuing intent; ambiguity leaves the rule unchanged.
  Do not fake those flags when the completion tool is unavailable: update the installed runtime first.
  If no eligible completion or genuine intent question remains, add no closeout question or extra gate.

### Challenges Run by Hand

PR reviewers get no decisions; the plan and implementation challenges check them (D-01M5ZE13N37HZAGJ69VWW69X23). So a
plan or implementation challenge a chat runs by hand in this repository states the applicable decisions
(D-01M5ZE1JHR9T1VCC9AZ80VATB5); Delivery's own challenges get theirs from Delivery.

- Before the first round, the chat asks `lookup_decisions` which decisions govern the plan or change, in a question
  that names it and what it touches. The picker reads the complete list; a `find_decisions` search, which returns at
  most 20, is never the source.
- The challenger gets the whole answer, untrimmed, checks the work against it and names the decisions the work
  touches or breaks.
- Before a later round, the chat asks again when a round changed the work materially or a governing decision changed.
- Without the tool, the chat asks the host through the installed runtime: `~/.owlbear/runtime/.venv/bin/python`
  calling `agent_reply(workspace(Path("<this checkout>")).lookup_decisions(question))`, with `workspace` from
  `owlbear_delivery_next.commands.chat_client` and `agent_reply` from `owlbear_delivery_next.workflow_steps.lookup`.
  The lead and challengers use this returned agent-facing reply whole; the raw host reply stays unchanged.
  If that fails too, or the answer says `failed`, the challenge says the decisions are unavailable and why, never that
  none apply.
- The list stays in the chat: none of it goes into a commit, pull request or comment on this repository.

## Directory Structure

| Directory | Purpose |
| --- | --- |
| `serve/` | Python workspace packages; source under `serve/*/src/`, package tests under `serve/*/tests/` |
| `share/agents/` | Agent definitions (`.agent.md`) |
| `share/skills/` | Agent skills (`SKILL.md` — `w-`, `r-`, `h-` prefixed) |
| `share/instructions/` | Instruction stubs (`.instructions.md` — pointers to skills) |
| `.owlbear/` | Project ops data: Delivery authority, scratch, scripts; research, designs of unbuilt work and the sources log live in [owlbear-data](https://github.com/maba-pag/owlbear-data/tree/main/owlbear) (D-01M5ZMXT7H851MZZFJA2P9X179) |
| `store/` | Reference-only knowledge corpus manifest and placeholder directories |
| `setup/` | Setup guide, operating guide, sharing guide |
| `tests/` | Workspace regression and integration tests |

## 3. Web Frontend

The Delivery engine's pages in `serve/delivery-next/src/owlbear_delivery_next/web/` are the only web frontend:
plain HTML, CSS and JavaScript the machine host serves, with no build step. Their tests are the package's pytest
suite, including its `browser`-marked Playwright tests. The root `package.json` holds only Node tooling (Biome, on
the Node version pinned in `.nvmrc`); every `serve/` package is Python, so use `uv run`.

## 4. Test Domain Mapping

### GitHub-Hosted Reviews

Copilot code review and CodeRabbit follow the [code-review](instructions/code-review.instructions.md) instructions.
Required external CI gates remain unchanged.

### Local Development and CI

This table maps source paths to their regression scope for local/CI tooling, including
quality-runner `mode=full` with `changed_paths`.

| Source prefix | Test scope | Toolchain |
| --- | --- | --- |
| `serve/*/src/`, `serve/*/tests/`, `tests/` | `uv run test --changed` | manifest- and import-aware pytest scope plus invariant tests |
| `share/` `.owlbear/` | skip (docs/config only, except executable hooks/scripts) | — |
| (unsafe or unknown path) | full Python suite fallback | pytest |

`uv run test` remains the complete Python suite. Use `uv run test --changed` for the agent inner loop; it includes direct consumer tests discovered from workspace manifests and imports, plus cross-cutting invariants. For changed Python sources of `serve/delivery-next`, pytest-testmon picks the package's tests that executed the changed code (its data stays in `.owlbear/scratch/`; the first run records it over the whole package), and tests that start the package in a child process always run. Other changes there (pages, skills, fixtures) run the whole package. Unknown or unsafe Git scope falls back to the full Python suite.

For local development, prefer `uv run test` for the complete Python suite and
`uv run test [PATH ...]` to apply this routing table to explicit paths. Direct pytest commands remain valid
when runner-specific flags or diagnostics are needed.
