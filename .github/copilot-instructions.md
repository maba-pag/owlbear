# OwlBear — Copilot Workspace Instructions

## 1. Project Identity

OwlBear is a laptop-resident AI development system built around VS Code and GitHub Copilot agents. It plans and executes work through Delivery workflows and shared workspace artifacts. VS Code is the IDE; the filesystem is the integration point.

## 2. Repository Branches

| Branch | Role | Contents |
| --- | --- | --- |
| `main` | The only long-lived branch and GitHub's default | Full workspace: `share/`, `serve/`, `seed/`, `setup/`, `.owlbear/`, `store/`, `tests/`, `pyproject.toml` |

Uncoordinated repository maintenance reaches `main` through a pull request: its required `CI`
check must pass on a branch that is up to date with `main`, and it merges with a merge commit
(TD-278). Once its CI passes, a pull request that changes code or CI gets the `coderabbit` label, which buys one
CodeRabbit review from a free allowance of about one an hour; a docs-only one goes without (TD-412). Target delivery
uses the branch, worktree, and
integration target in its per-change coordination record; never substitute `main` by convention.
Consumers clone the same branch ("clone = install"); versions will be git tags. There is no
generated consumer branch and no sync workflow (TD-203).

### Plan and Status

[The plan](../.owlbear/research/owlbear-plan.md) holds where OwlBear stands, the order of the remaining work and
where the code differs from [the decisions](../.owlbear/research/delivery-liveness-first-rebuild.md). Read it when
you start or resume work and after a context compaction; a pull request that changes what it says updates it. The
old Delivery redesign programme and
[its execution plan](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/delivery-redesign-execution-plan.md) are superseded history (TD-202).
[.owlbear/decisions.md](../.owlbear/decisions.md) is the generated, read-only view of the decisions in owlbear-data;
until the owner has reviewed their migration, the decision record stays authoritative (TD-437).

### Asking the Owner

When the owner decides or re-decides anything consequential, including a read-back or a recorded
decision under review, ask one decision per question with the structured question tool, as his
decisions TD-41..43, TD-150 and TD-156 in
[the decision record](../.owlbear/research/delivery-liveness-first-rebuild.md) define:

- The message shows the decision's record (its words and origin) and what changed since.
- Options: three close variants of the decision (fewer only when fewer really differ, never padded),
  the matching one at a varying position and never verbatim; one or two other directions, the opposite
  among them; then, in this order,
  "take your recommendation (…)" naming the recommendation in the brackets, "none of these: show me
  more options" and "explain first". No other recommendation mark; free text stays open.
- "Take your recommendation" is recorded `autonomous` with its reason. "Show me more options" asks
  again across directions, each with pro, con, risk and its own percentage that it is a good
  choice. "Explain first" (his shorthand "nmdpcro": details, pro, con, risk, opinion) explains each
  option neutrally, then asks again.
- Free text is never recorded as written: offer two to five readings that fill its gaps differently,
  plus "your words as written", "show me more readings" and "explain first".
- Before asking, challenge the proposal against his intent: what it lacks and what it overdoes,
  not only what is wrong (TD-150).
- Record each answer as C-31 of the decision record says: edit its topic in the same change, never
  append history rows; number it after the highest TD number in the record on a freshly fetched `main`.

## Directory Structure

| Directory | Purpose |
| --- | --- |
| `serve/` | Python workspace packages; source under `serve/*/src/`, package tests under `serve/*/tests/` |
| `share/agents/` | Agent definitions (`.agent.md`) |
| `share/skills/` | Agent skills (`SKILL.md` — `w-`, `r-`, `h-` prefixed) |
| `share/instructions/` | Instruction stubs (`.instructions.md` — pointers to skills) |
| `share/prompts/` | Prompt files (`.prompt.md` — user-facing one-shot commands) |
| `.owlbear/` | Project ops data: Delivery authority, research, sources, scratch, scripts, hooks |
| `store/` | Reference-only knowledge corpus manifest and placeholder directories |
| `seed/` | Template files copied to new projects by `setup/init.py` |
| `setup/` | Workspace initialiser (`init.py`), setup guide, sharing guide |
| `tests/` | Workspace regression and integration tests |

## 3. Web Frontend

The Delivery engine's pages in `serve/delivery-next/src/owlbear_delivery_next/web/` are the only web frontend:
plain HTML, CSS and JavaScript the machine host serves, with no build step. Their tests are the package's pytest
suite, including its `browser`-marked Playwright tests. The root `package.json` holds only Node tooling (Biome, on
the Node version pinned in `.nvmrc`); every `serve/` package is Python, so use `uv run`.

## 4. Test Domain Mapping

### GitHub Cloud Sessions

Use explicit affected test selections and scoped checks. If scope is unknown, inspect the owning
tests before choosing a check. Never run the whole-project suite or `uv run quality`.
Follow the
applicable [cloud-agent](instructions/cloud-agent.instructions.md) or
[code-review](instructions/code-review.instructions.md) instructions. Required external CI gates remain unchanged.

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
