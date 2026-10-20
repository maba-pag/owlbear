# GitHub Automation

This guide intentionally is not named `README.md`: GitHub gives `.github/README.md` precedence over
the root README when choosing the repository landing page. The non-special filename keeps the root
OwlBear front door visible while still giving this folder a durable orientation guide.

`.github/` contains repository automation and Copilot support. Changes here affect the OwlBear
repository and its checks rather than an installed project directly.

## What lives here

| Path | Purpose |
| --- | --- |
| `workflows/` | CI, dependency checks, and ecosystem validation |
| `scripts/` | Small checks used by workflows |
| `skills/` | Development-only specialist guidance, including session review and hook authoring |
| `copilot-instructions.md` | The development checkout's workspace identity and repository map |
| `renovate.json` | Repository configuration for dependency update automation |

## What belongs elsewhere

- Portable agents, skills, instructions, and prompts live in [`share/`](../share/README.md).
- Consumer-project Copilot and VS Code templates live under `seed/` and are applied by
  [`setup/init.py`](../setup/init.py).
- Runtime packages and MCP servers live under [`serve/`](../serve/README.md).
- Installation and operating procedures live in the [setup guide](../setup/setup-guide.md) and
  [Operating OwlBear](../setup/operating-owlbear.md).

The development instructions in `.github/copilot-instructions.md` are not the same artifact as the
consumer template at `seed/.github/copilot-instructions.md`. The former describes this repository;
the latter is a placeholder that `init.py` adapts for a project using OwlBear.

## Pull-request checks

The [CI](workflows/ci.yml) workflow and the seven suites it calls are enabled (TD-278), as is the
[Release](workflows/release.yml) walk; every other
automatically triggered workflow stays disabled on GitHub (TD-204), and `gh workflow enable <file>`
restores one. The pre-commit hooks never run on commit (`pre-commit run --hook-stage manual` runs them);
CI's Static suite runs them on every change through `uv run lint --no-fix` (TD-409).

Agents wait for every check on the head commit, so the checks are shaped to finish fast and to
report few rows. One [CI](workflows/ci.yml) workflow runs on every pull request into `main`,
including drafts, and on every push to `main`: a push run is one per commit, never cancelled, and
scoped by the merge against its first parent, so each merge has its own CI for the release walk.
Its scope job lists the suites the PR touches with
[`ci_scope.py`](scripts/ci_scope.py), which owns the path lists below. CI then calls each touched
suite as a reusable workflow; a change to the gate itself runs every suite. Its final job, named
**CI**, passes only when every selected suite passed; it is the one check a ruleset requires (TD-278).
Within a suite every job starts immediately (no `needs`) and installs only what it uses.

| Workflow | Jobs | Runs when the PR touches |
| --- | --- | --- |
| [Python](workflows/python.yml) | 4 hash-sharded test jobs (`worksteal` inside each) | Python sources, tests, setup, seed, manifests, locks |
| [Python browser](workflows/python-browser.yml) | Browser-marked tests with Chromium | `serve/browser*`, `serve/web-content`, manifests, locks |
| [Static checks](workflows/static.yml) | `uv run lint --no-fix` and `uv run format --no-fix`, as locally: Ruff, Markdown, YAML, shell, actionlint, zizmor, EditorConfig, Biome | Every change |
| [Tooling](workflows/tooling.yml) | Lock, toolchain, workflow, hook, and diagram proofs, selected per changed surface | Manifests, locks, workflows, tool configuration, diagrams |
| [Agent ecosystem](workflows/agent-ecosystem.yml) | Agent, skill, prompt, hook, and knowledge contracts | Agent ecosystem paths |
| [Security](workflows/security.yml) | Snyk Code test, high severity and above; on a pull request, one comment per finding | Code, `.snyk` |

The scope evaluates the whole PR diff, so a follow-up push reruns every suite the PR ever
touched. To avoid repeating identical proofs, each job fingerprints its inputs with
`git ls-files -s` and stores a marker cache entry after it passes. A later run in the same PR with
the same fingerprint reports the reused result and skips its work. Python and static fingerprints
cover the whole tree except `.owlbear/research`; the others cover their own inputs. Bump the
`ci-pass-v1` key prefix when a job's commands change meaning without changing those inputs.

uv caches are scoped per install profile (`python-tests`, `python-browser`, `dev-tools`). Python
test environments skip the torch/CUDA model stack that only the deselected `model` tests import;
keep the `CI_SKIPPED_PACKAGES` lists in the Python workflow and Copilot setup identical.
[`test_ci_workflows.py`](../tests/test_ci_workflows.py) owns these workflow-shape contracts.

## Snyk

Snyk's GitHub integration in the `porsche-ag-fdi3-scanners` org (EU region) has its pull-request
checks off (TD-382). Renovate keeps dependencies current.

The [Security](workflows/security.yml) suite runs the Snyk CLI inside the required CI gate (TD-360),
only for changes from `maba-pag/owlbear` itself: GitHub gives its token neither to a copy of OwlBear
nor to a fork's pull request, so their CI never selects the suite, and the push run after a merge
scans the merged code. Delivery never runs Snyk in other projects (TD-363):
`snyk code test` at high severity and above, never `monitor` or `--report`, so it writes nothing
into the org. Only Snyk Code runs: its tests are unlimited, while dependency tests would spend the
org's small private-test quota on what Renovate already does (TD-382). Each finding prints its rule,
file and line, so a failing run is fixed like any failing test. It
authenticates with the org service account `owlbear-ci` in the Org Collaborator role (TD-361; a
read-only CLI tester role replaces it once the Group offers one), whose token is the `SNYK_TOKEN`
Actions secret.

A Snyk Code finding on a pull request gets one comment from the Security job with a box and an empty
`Reason:` line ([`snyk_findings.py`](scripts/snyk_findings.py), TD-363). The lead chat judges it: a
real finding is fixed; for a false positive it writes the reason under the box. The owner's tick
starts [Snyk ignore](workflows/snyk-ignore.yml) from `main`, which runs only for edits by his account
(`maba-pag`, ID 238680231) and reads the comment as it is then, since GitHub may reorder or replace
queued runs: a ticked box over a written reason sets the finding "Not vulnerable" in Snyk without
expiry, records the policy in a receipt comment (which a stale editor copy cannot erase, so a finding
is ignored once), marks the box with the policy's ID and re-runs the failed CI once it has ended, whose
`snyk code test` then honours the ignore (Consistent Ignores). A tick over an empty reason, or one
Snyk refuses, is unticked with why. The lead chat works through the same account, so the tick is
the owner's by agreement, not proof (TD-363); an ignore can also be set in the Snyk web UI.

## Releases

The [Release](workflows/release.yml) walk tags each merge to `main` whose pull request carries
`release:minor` or `release:major` once that merge's own push CI passed (TD-302, TD-306); see
[`release.py`](scripts/release.py). It only reports what it would tag until the repository variable
`RELEASE_TAGS` is `on` (TD-315). Tags are created through the REST API with the owner's fine-grained token in the
Actions secret `RELEASE_TOKEN` (this repository only; Contents and Workflows write; TD-404), since GitHub refuses the
workflow token a tag on a commit whose workflow files differ from every branch tip. A major gets `vN.0` and `vN`
(TD-392).

## Dependency updates

[Renovate](renovate.json) is the only updater (TD-382, TD-408): routine updates arrive grouped per ecosystem on
Friday, majors on Sunday after 72 hours. Ruff, Biome and every pre-commit hook share one weekly **lint toolchain**
pull request with a three-day minimum age, and their majors share one on Sunday, so the Ruff pin, its hook and the
installed Ruff that [`check_ruff_toolchain.py`](scripts/check_ruff_toolchain.py) compares move together (TD-409).
The schema URL in [`biome.json`](../biome.json) follows Biome through the `customManagers:biomeVersions` preset.

GitHub's Dependabot alerts are on and feed Renovate's security pull requests, which open at once, grouped per
ecosystem. Dependabot opens no pull requests itself: there is no `dependabot.yml` and its security updates stay
off (TD-408). pre-commit.ci is not installed, since its hook updates cannot be switched off (TD-410).

## Reviews

CodeRabbit reviews a pull request once, when it gets the `coderabbit` label, whoever opened it (TD-413), as
[`.coderabbit.yaml`](../.coderabbit.yaml) sets, with the [review brief](instructions/code-review.instructions.md)
as its guideline (TD-411). Its free open-source allowance is about one review an hour for all of `maba-pag`'s
pull requests, so agents or workflows add the label only to a code or CI pull request whose CI passed; a
docs-only one gets it by hand. `@coderabbitai review` asks again; CodeRabbit never replies on its own (TD-412).
