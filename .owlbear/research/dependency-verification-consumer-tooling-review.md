# Dependency Verification and Consumer Tooling Review

> **Owning task:** User-requested workflow and distribution review
> **Date:** 2026-08-08
> **Question:** How should dependency verification, default-branch `.github` projection, and lint tooling be structured so CI is efficient and consumer-facing commands remain coherent?

## 1. Context and Question

The review must preserve these established constraints:

- `main` is the default and consumer-facing branch.
- `.github/workflows/**` must remain on `main` for default-branch workflow registration.
- `.github/renovate.json` must remain on `main` for Renovate configuration discovery.
- Unknown-scope pruning is intentional, manually dispatched, dry-run reviewed, and followed by a full sync when migrations require it.
- Granular sync controls remain valuable.
- `.github/skills/session-review/**` is currently dev-only and is not loaded by initialized consumer projects.

Open questions:

1. Why does Dependency verification display as `verify`, and should the job receive a clearer display name?
2. Which dependency checks are necessary, and can the 4m31s run avoid the 3m17s MegaLinter pull/run that exhausted runner disk?
3. Can locked dependency installation avoid redundant Python/npm work while preserving lock verification?
4. How should `todo_check` avoid reporting its own marker examples without hiding real TODO markers?
5. What creates GitHub's Dependabot "Dependency Graph" workflow runs, what value do they provide here, and where are they configured?
6. Should consumer `main` project only an explicit `.github` allowlist rather than copy all of `.github` and prune known dev-only paths?
7. Which lint commands and root configuration belong on `main`, and which are OwlBear-development-only?
8. Can consumer linting work without inheriting OwlBear's `.pre-commit-config.yaml`, and should a generated consumer-local configuration, direct tool invocation, profiles, or another mechanism own that behavior?

## 2. Sources Studied

| Source | Relevant fact | Evidence limit |
|---|---|---|
| Dependency verification run `31234032250`, PR #156 | A change only to `serve/cockpit/web/.nvmrc` spent 43 seconds installing both locked dependency sets and 197 seconds in static analysis before the Cupcake image exhausted disk while registering its Grype layer. All tests and the build were then skipped. | One representative failed run; it proves waste and the failure mode, not steady-state timing after redesign. |
| `.github/workflows/dependency-verification.yml` | The single `verify` job unconditionally runs `deps-sync`, full static analysis, all Python tests, frontend tests, and the frontend build for every admitted dependency PR. Autofix artifacts are created only after all checks succeed. | Current local source. |
| `serve/tools/src/owlbear_tools/lint.py`, `.pre-commit-config.yaml`, and `.mega-linter.yml` | `lint-full` first runs native pre-commit/frontend checks and then Docker MegaLinter. Every enabled MegaLinter check except Trivy overlaps a native check. | Configuration comparison; it does not compare implementation bugs between wrappers. |
| GitHub workflow syntax | `jobs.<job_id>.name` sets the UI display name. Without it, the current job displays its ID, `verify`. | Owning platform contract. |
| GitHub-hosted runner reference | Standard `ubuntu-latest` runners provide 14 GB SSD. | Published capacity; usable free space varies with the image and preceding steps. |
| MegaLinter flavors | Cupcake contains 93 linters. Flavors exist to reduce image scope. | Current MegaLinter documentation; the exact compressed image size was not needed for the decision. |
| GitHub dependency graph documentation and live Actions history | Dependency Graph supplies Dependabot alerts and dependency review. Python Dependabot graph jobs provide transitive coverage, take precedence over automatic submission, and do not consume Actions minutes. The repository has 36 observed managed graph runs. | The API does not expose this repository's Automatic Dependency Submission toggle. |
| `.github/workflows/sync-to-main.yml` | Infra sync deletes `.github`, copies all of it from `dev`, then prunes only `copilot-instructions.md`; future customization directories would therefore leak to `main`. Its TODO shell grep is unanchored while the Python scanner is anchored. | Current local source. |
| `README-consumer.md`, `serve/tools/src/owlbear_tools/project.py`, `setup/init.py`, and seed hooks | `uv run --project ../owlbear` selects OwlBear's environment but preserves the consumer project as the working directory. Cockpit, setup, doctor, and Delivery-target commands intentionally use that behavior. The current lint/pre-commit commands assume OwlBear-dev configuration and paths instead. Consumer hooks already demonstrate direct Ruff invocation, while Delivery verification uses a tracked consumer-owned command profile. | Current source and command semantics; no consumer migration was executed. |
| Independent Opus 5 review, 2026-08-08 | Independently identified routine MegaLinter duplication, the broken consumer pre-commit contract, explicit `.github` allowlisting, path-classified installs, and the shell TODO false positive. | Advisory review; conclusions were accepted only where independently supported above. |
| `actions/cache`, `actions/setup-node`, and `astral-sh/setup-uv` source and caching documentation | Setup Node caches npm's global download cache, not `node_modules`, using an exact lock hash. Setup uv likewise uses an exact dependency-derived key. The generic Cache Action can add prefix restores, but rolling keys consume quota and can cost more to restore than they save. | Source review establishes behavior; repository-specific benefit still requires measured runs. |
| `bahmutov/npm-install` source and documentation | The Action caches `~/.npm` and always runs `npm ci` when a lockfile exists. Its rolling mode adds month-based restore keys. | It duplicates the current Setup Node cache for this repository; rolling-cache benefit remains workload-dependent. |
| `e18e/action-dependency-diff` source and documentation | The Action parses npm, Yarn, pnpm, or Bun lockfiles, queries npm metadata for size/provenance, and can publish through a write token or a two-workflow artifact path. It does not support `uv.lock`. | Useful only as optional Node advisory analysis; it does not verify installs or reduce runtime. |
| `pozetroninc/github-action-get-latest-release` source and documentation | The Action calls GitHub's releases API and returns the first non-excluded release. | Unrelated to dependency caching or lock verification; dynamic use would weaken deterministic pinning. |

## 3. Analysis

### 3.1 Job name and observed cost

`Dependency verification` is the workflow name. `verify` is the job ID and becomes the displayed job
name because the job has no explicit `name`. Add `name: Verify dependency update` only after checking
the repository's ruleset UI for an exact required-check reference. The available token cannot read
rulesets, so this compatibility point remains unresolved.

PR #156 is the discriminating example for path classification. A one-line Node version change paid
for both ecosystems, then failed before any behavior test or build ran. The 197-second static-analysis
step did not execute useful project analysis: it spent its time pulling the broad image and failed on
runner capacity. Deleting runner files or buying a larger runner would preserve the duplication and
therefore treats the symptom.

The routine gate should use the repository's native checks. Trivy is the only unique MegaLinter signal
and should remain a separately scheduled or manually dispatched security check, or later become a
focused direct Trivy invocation. Keep `uv run megalint` as an explicit maintainer command while it has
a supported use; do not put the Cupcake image back in every dependency PR.

### 3.2 Dependency and verification routing

Classify changed paths before setup and installation, inside the admitted workflow rather than with
top-level path filters. The workflow must still produce one required check for all labeled dependency
PRs, and unknown or mixed changes must conservatively select the combined route.

| Change class | Required route |
|---|---|
| Python manifests, lock, version, or Python runtime image | Check the uv lock, install the locked Python environment, run native repository checks and Python tests. |
| Cockpit Node manifest, lock, or Node version | Run `npm ci`, frontend lint/typecheck/tests, and build. Run PDS sync only for PDS-relevant dependency changes. |
| Workflow/action dependency | Run focused YAML and Actionlint checks plus workflow contract tests; no frontend install unless the changed action affects frontend setup. |
| MegaLinter image/config | Validate its config and run the explicit MegaLinter/security path, not the ordinary dependency route. |
| Mixed or unrecognized dependency surface | Run the combined conservative route. |

Keep `uv run deps-sync` simple for maintainers. CI should invoke the relevant deterministic primitives
directly after classification instead of adding workflow policy flags to that human-facing command.
The 43-second combined install is secondary to the 197-second failure, but classification removes the
irrelevant npm or Python half and makes later timing actionable.

Autofix write-back should remain fail-closed: publish and apply a fix only after that classified route
passes. A failed infrastructure step should not authorize unverified source mutation. Instead, make
the routine route reliable and preserve generated diffs in the job summary or a diagnostic artifact
when useful; do not feed an unverified patch to the privileged writer.

### 3.3 Dependency Graph versus Automatic Dependency Submission

Keep Dependency Graph enabled. The managed `Graph Update` jobs are not redundant with lint or tests:
they submit the resolved Python dependency tree used by Dependabot alerts, security updates, dependency
review, and Renovate's vulnerability handling. GitHub documents these Python graph jobs as free of
Actions-minute charges and automatically active when Dependency Graph is enabled.

Automatic Dependency Submission is a separate setting under repository Settings, Security, Advanced
Security, Dependency Graph. For Python, Dependabot graph jobs take precedence, so disabling Automatic
Dependency Submission does not disable the managed Python graph jobs. The API could not reveal the
toggle state. Inspect it in the UI and disable it only if it is separately running for another ecosystem
whose lockfile parsing already gives complete coverage; there is no evidence that disabling Dependency
Graph itself is beneficial.

One current managed run still scans retired pip paths and fails. That is GitHub-owned graph-job state,
not a source workflow. Inspect the Dependency Graph manifests/settings for stale package-manager roots;
do not conflate that cleanup with the dependency PR workflow redesign.

### 3.4 Consumer lint contract

Copying OwlBear-dev's active `.pre-commit-config.yaml` to consumer `main` is incoherent. It references
dev-only validators and the pruned Cockpit frontend, including an `always_run` skill validator. Running
`uv run --project ../owlbear lint` from a consumer project selects OwlBear's executable environment but
pre-commit searches the consumer working tree for configuration. No supported generic configuration
exists there, and OwlBear-specific hook aliases cannot safely express fix policy for arbitrary projects.

| Alternative | Assessment |
|---|---|
| Ship the active dev pre-commit file | Reject. It is not runnable against the consumer projection or arbitrary target projects. |
| Generate an active consumer pre-commit file | Reject as the default. It would overwrite or compete with project-owned policy and cannot infer every ecosystem safely. |
| Ship an opt-in template | Acceptable documentation aid, but it does not define a universal `lint` command. |
| Wrap a consumer-owned pre-commit config | Useful when a project already owns one; preserve its semantics rather than mapping OwlBear-specific hook IDs. |
| Direct tool discovery and invocation | Preferred baseline. Detect manifests/configs and invoke project tools from the consumer cwd, as the existing Ruff edit hook already does. |
| Tracked consumer quality profile | Preferred for exact project-specific verification commands. Extend the existing Delivery verification-profile pattern only when stable explicit commands are needed. |

Split command discovery by audience. Consumer-safe commands include Cockpit, setup, doctor, and
Delivery target management. OwlBear repository maintenance includes PDS sync, MegaLinter maintenance,
Cockpit frontend typecheck, and root dependency maintenance. A future generic consumer `lint` should
discover direct tools or consume consumer-owned policy; until then, do not advertise dev lint commands
as consumer commands merely because the tools package is installed.

### 3.5 Consumer projection and TODO scanning

Preserve granular sync controls and intentional unknown-scope pruning. For the infra scope, replace
copy-all-then-prune with an explicit `.github` projection containing:

- `.github/workflows/**`
- `.github/renovate.json`

This retains default-branch workflow registration and Renovate discovery while excluding present and
future `.github/{agents,skills,instructions,prompts}/**` without a growing blacklist. Because infra sync
already removes `.github` before checkout, checking out only the allowed paths also removes an existing
`session-review` directory from `main` on the next full infra sync.

The TODO scanner defect is narrower than first assumed. Python's `_TODO_RE` already matches only markers
at the beginning of a line. The sync workflow used unanchored `grep`, so inline examples and its own
source matched. It now uses `grep -rHnI '^> \*\*TODO:\*\*'` and no longer needs a self-exclusion.

### 3.6 Marketplace Action review

None of the four reviewed Actions should be added to solve the observed failure:

- Keep the caches already built into Setup uv and Setup Node. They are maintained by the setup owners
	and cover the same package stores as the generic Cache Action and `npm-install` without another
	dependency in the workflow.
- Do not adopt `npm-install`: it still runs `npm ci`, duplicates the existing npm cache, and introduces
	another third-party execution surface. Its rolling mode is a separate cache-policy decision.
- Treat Dependency Diff as an optional Node advisory feature only. It can report dependency growth,
	duplicates, install size, provenance changes, and replacement suggestions, but adds registry calls
	and comment/artifact authority while leaving Python dependencies uncovered.
- Do not adopt Get Latest Release. It has no verification or caching role, and dynamic latest-release
	resolution conflicts with the repository's SHA-pinning and lockfile policy.

### 3.7 Confidence-gated findings

| Finding or fix | Pros | Cons | Principal risk | Confidence | Disposition |
|---|---|---|---|---:|---|
| Replace dependency-gate `lint-full` calls with native lint, HTML lint, and typecheck | Removes the failed 197-second Cupcake pull and duplicated checks; separate MegaLinter workflow retains Trivy | The dependency gate no longer runs Trivy inline | Native and MegaLinter configurations could drift | 99.7% | Implemented |
| Anchor sync TODO grep | Matches the Python scanner and removes self/example false positives | Intentionally ignores indented markers | A deliberately indented marker is not reported | 99.8% | Implemented |
| Allowlist `.github/workflows` and `.github/renovate.json` in consumer sync | Prevents current and future customization leakage while preserving default-branch automation | New consumer-owned `.github` files require an explicit update | A future required GitHub config could be omitted until added | 99.2% | Implemented |
| Keep Setup uv and Setup Node caching; reject `npm-install` | Avoids duplicate cache/install logic and another third-party Action | Does not provide rolling restores across lock changes | Exact-key misses remain on dependency updates | 99.5% | No new Action |
| Reject Get Latest Release for dependency verification | Preserves deterministic SHA pins and lockfiles | None for the stated problem | A future unrelated release-discovery use case needs separate review | 99.9% | No new Action |
| Keep Dependency Graph enabled | Retains alerts, dependency review, security updates, and Python transitive submissions | Managed runs remain visible and stale roots may need cleanup | Disabling it would silently reduce supply-chain coverage | 99.3% | Keep |
| Add a clearer job display name | Improves Actions and ruleset readability | May change an exact required-check context | Existing branch rules could stop recognizing the check | 96% | Implemented by user decision |
| Add path-classified setup, install, and test routes | Avoids irrelevant ecosystem work | Adds workflow policy and mixed/unknown fallback complexity | A missed path class could under-test a dependency update | 91% | Declined; keep combined gate |
| Add rolling or prefix cache restores | Could reduce exact-key misses on dependency updates | More restore/upload time, storage, and cache-poisoning surface | A large stale cache may be slower than fresh downloads | 82% | Declined; keep exact caches |
| Add Dependency Diff as Node advisory analysis | Adds lock-diff, size, duplicate, provenance, and replacement signals | Node-only; registry calls and comment/artifact machinery | More supply-chain surface and noisy advice without faster CI | 88% | Declined |
| Stop shipping the active dev pre-commit policy and choose a consumer lint contract | Removes a known broken consumer command surface | Direct discovery, opt-in templates, and tracked profiles serve different users | Choosing centrally could override consumer-owned policy | 94% for defect, 84% for mechanism | Direct discovery implemented by user decision |
| Change Automatic Dependency Submission or stale managed roots | Could remove redundant or failing managed scans | Repository setting and current state are not visible to source review | Disabling the wrong feature reduces graph coverage | 78% | Declined; settings unchanged |

## 4. Recommendation, Confidence, And Limits

Proceed in four bounded phases:

1. **Restore a reliable gate.** Completed: the dependency workflow now uses native checks, keeps
	MegaLinter/Trivy in its separate workflow, and anchors the sync TODO grep. Add a clearer job name
	only after confirming required-check settings.
2. **Keep the combined gate.** Selected: setup, installation, and tests remain conservative rather
	than path-classified. Existing exact-key caches remain unchanged.
3. **Repair distribution contracts.** Completed: sync explicitly projects workflows and Renovate,
	stops projecting the active dev pre-commit file, and exposes consumer lint through direct discovery
	of consumer-owned Ruff configuration and package lint scripts. Consumer help hides dev-only commands.
4. **Keep repository settings unchanged.** Selected: Dependency Graph and current Automatic
	Dependency Submission/settings remain unchanged. Stale managed roots are not modified without
	settings evidence.

Agreement with the independent Opus review is high on all load-bearing conclusions. The only material
qualification is artifact policy: preserving failed-run diagnostics is useful, but privileged write-back
must still require successful verification.

The confidence table above governed implementation. Changes above 98% were applied directly; the
remaining decisions were resolved by the user. The combined gate, exact caches, no Dependency Diff,
direct consumer lint discovery, and unchanged dependency settings are now explicit policy. Renaming
the job may require a corresponding ruleset update if `verify` was an exact required-check context.
