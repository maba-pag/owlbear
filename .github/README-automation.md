# GitHub Automation

This guide intentionally is not named `README.md`: GitHub gives `.github/README.md` precedence over
the root README when choosing the repository landing page. The non-special filename keeps the root
OwlBear front door visible while still giving this folder a durable orientation guide.

`.github/` contains development-only repository automation and Copilot support. The consumer
`main` branch deliberately excludes this directory; changes here affect the OwlBear repository,
its checks, or its manual sync process rather than an installed project directly.

## What lives here

| Path | Purpose |
| --- | --- |
| `workflows/` | CI, dependency checks, ecosystem validation, and the manual `dev` to `main` sync |
| `scripts/` | Small checks used by workflows and the sync manifest projection |
| `skills/` | Development-only specialist guidance, including session review and hook authoring |
| `copilot-instructions.md` | The development checkout's workspace identity and repository map |
| `sync-manifest.json` | The allowlisted source paths and consumer exclusions for rolling `main` |
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

Agents wait for every check on the head commit, so the checks are shaped to finish fast and to
report few rows. Each workflow is path-filtered, every job starts immediately (no `needs`), and
each job installs only what it uses.

| Workflow | Jobs | Runs when the PR touches |
| --- | --- | --- |
| [Python](workflows/python.yml) | 4 hash-sharded test jobs (`worksteal` inside each) | Python sources, tests, setup, seed, manifests, locks |
| [Python browser](workflows/python-browser.yml) | Browser-marked tests with Chromium | `serve/browser*`, `serve/web-content`, manifests, locks |
| [Cockpit](workflows/cockpit.yml) | Unit tests and the browser smoke build, in parallel | `serve/cockpit/web`, `biome.json` |
| [Static checks](workflows/static.yml) | Ruff, repository-wide Biome, HTMLHint | Python, JSON, frontend, lint configuration |
| [Tooling](workflows/tooling.yml) | Lock, toolchain, workflow, hook, PDS, and diagram proofs, selected per changed surface | Manifests, locks, workflows, tool configuration, diagrams |
| [Agent ecosystem](workflows/agent-ecosystem.yml) | Agent, skill, prompt, hook, and knowledge contracts | Agent ecosystem paths |

`paths` filters evaluate the whole PR diff, so a follow-up push reruns every workflow the PR ever
touched. To avoid repeating identical proofs, each job fingerprints its inputs with
`git ls-files -s` and stores a marker cache entry after it passes. A later run in the same PR with
the same fingerprint reports the reused result and skips its work. Python and static fingerprints
cover the whole tree except `.owlbear/research`; the others cover their own inputs. Bump the
`ci-pass-v1` key prefix when a job's commands change meaning without changing those inputs.

uv caches are scoped per install profile (`python-tests`, `python-browser`, `dev-tools`). Python
test environments skip the torch/CUDA model stack that only the deselected `model` tests import;
keep the `CI_SKIPPED_PACKAGES` lists in the Python workflow and Copilot setup identical.
[`test_ci_workflows.py`](../tests/test_ci_workflows.py) owns these workflow-shape contracts.

## MegaLinter toolchain updates

[Renovate](renovate.json) updates the native and action MegaLinter declarations together. Ruff,
`ruff-pre-commit`, and Biome are derived pins, not independent routine updates. The
[synchronization workflow](workflows/sync-megalinter-toolchain.yml) adds those pins and both lockfiles
to the same PR using the proposed release's tagged linter-version manifest. It also aligns the
[Biome schema](../biome.json); it never follows a moving `latest` manifest.

Activation requires the workflow and [synchronizer](scripts/sync_megalinter_toolchain.py) on the
repository's default branch and the PR's `dev` base. Configure the repository `PAT` Actions secret
with single-repository Contents write and Pull requests read access. A PAT is required for changed
pins so its push triggers fresh CI; the workflow deliberately has no `GITHUB_TOKEN` write fallback.
The commit author remains `github-actions[bot]`, which Renovate already accepts through
`gitIgnoredAuthors`. No commit is made when the PR is already aligned.

Only non-draft, same-repository `renovate[bot]` PRs on `renovate/` branches are eligible. Trusted
base-branch code rejects unexpected paths, symlinks, and non-version edits before resolving locks.
PR lockfile changes are discarded in the disposable checkout and regenerated from the trusted
baseline, with Python builds and npm install scripts disabled. Publication checks the open PR's
identity and uses an exact-head lease, so a concurrent Renovate update is not overwritten.

The [Tooling workflow](workflows/tooling.yml) independently checks
Ruff, Biome, their locks, and the schema on the resulting commit. Local check-only equivalent:

```shell
uv run --locked python .github/scripts/sync_megalinter_toolchain.py --check
```

For an existing MegaLinter PR, request a Renovate rebase after activation. Old grouped PRs containing
unrelated edits fail closed; recreate them under the new policy. Missing metadata, unavailable
packages, or missing credentials leave a visible failed workflow instead of selecting newer tools.
After correcting a transient failure, rerun the failed job on the current PR head. An unexpected
bundled downgrade is reflected exactly in the reviewable PR, rather than silently retaining drift.

Keep GitHub Dependabot alerts enabled: disabling independent Renovate updates is not a security
exception policy. An urgent Ruff or Biome fix unavailable in MegaLinter requires an explicit reviewed
exception or a newer MegaLinter release; the parity check intentionally blocks silent divergence.

## Changing the sync boundary

Treat [`sync-manifest.json`](sync-manifest.json) as the source of truth for the source allowlists
and excluded roots that feed `main`. The [sync workflow](workflows/sync-to-main.yml) owns the
transformations around those inputs, including the consumer README rename, pruning, and generated
outputs. When a projection changes, update the manifest, workflow, and regression coverage in
[`tests/test_sync_manifest.py`](../tests/test_sync_manifest.py). Do not edit `main` directly; the
manual sync workflow generates it from `dev`.
