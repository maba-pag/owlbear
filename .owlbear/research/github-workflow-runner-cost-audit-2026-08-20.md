# GitHub Actions Workflow Runner Cost Audit

> **Owning task:** User request - understand workflow execution and reduce runner time
> **Date:** 2026-08-20
> **Question:** What runs when, what does each workflow protect or publish, and where is runner cost disproportionate to effect?

## 1. Context And Method

This audit covers the five workflows currently under `.github/workflows/`. Workflow triggers, job
conditions, commands, timeouts, path filters, and delegated scripts are observed facts. Workflow
goals and cost implications are inferences from those facts.

The ratings use a 1-5 scale:

- **Usefulness:** 5 means essential or broadly valuable for the workflow's responsibility.
- **Trigger fit:** 5 means the event and path scope match the moment and files needing proof.
- **Runner cost:** 5 means expensive relative to the other workflows; higher is worse.
- **Effect/cost:** 5 means strong useful effect per runner work and maintenance effort.

Timeouts are ceilings, not measured durations. Summed job ceilings approximate worst-case hosted
runner-minute consumption; wall-clock time is closer to the longest dependent path because jobs can
run in parallel.

An unauthenticated GitHub API request returned HTTP 404, but authenticated `gh` access is available
in this workspace. A recent 100-run sample before this optimization exposed 22 Dependency verification runs, 18 Knowledge
source contracts runs, 14 Agent ecosystem validation runs, and 5 Sync dev to main runs. No
MegaLinter or Cockpit verification run appeared in that historical sample. Job timestamps were
available for inspected runs, but this report does not claim p50/p90 durations because no
consolidated timing extraction was completed.

## 2. Sources Studied

| Source | Evidence used |
|---|---|
| [`dependency-verification.yml`](../../.github/workflows/dependency-verification.yml) | PR trigger, classifier outputs, proof jobs, gate, concurrency, and timeouts |
| [`cockpit-verification.yml`](../../.github/workflows/cockpit-verification.yml) | Node compatibility matrix, frontend proof, browser-engine installation, and smoke tests |
| [`megalinter.yml`](../../.github/workflows/megalinter.yml) | Manual inputs, full-codebase lint, reports, SARIF, and fix-publication paths |
| [`agent-ecosystem.yml`](../../.github/workflows/agent-ecosystem.yml) | Consolidated path-filtered repository contract validation |
| [`sync-to-main.yml`](../../.github/workflows/sync-to-main.yml) | Manual consumer projection, SPA build, pruning, commit, push, and dry-run paths |
| [`dependency_ci.py`](../../serve/tools/src/owlbear_tools/dependency_ci.py) | Exact dependency-surface classification and `applicable` output |
| [`sync-manifest.json`](../../.github/sync-manifest.json) | Consumer scopes and excluded development-only paths |
| [`.mega-linter.yml`](../../.mega-linter.yml), [`.pre-commit-config.yaml`](../../.pre-commit-config.yaml) | Linter scope, parallelism, and tooling overlap |
| [`serve/cockpit/web/package.json`](../../serve/cockpit/web/package.json), [`sync-pds-assets.mjs`](../../serve/cockpit/web/scripts/sync-pds-assets.mjs), root and diagram package manifests | Install, test, build, browser, and PDS download commands represented in runner cost |
| [`test_dependency_verification_workflow.py`](../../tests/test_dependency_verification_workflow.py), related contract tests | Workflow invariants and intended regression coverage |
| [`.github/README-automation.md`](../../.github/README-automation.md) and earlier research | Repository automation intent and historical context |

## 3. Workflow Extraction Table

Step counts include every declared step, including steps skipped by conditions. Acquisition counts
include material checkout, runtime/tool installation, dependency installation, browser installation,
and CDN/tool-image acquisition. They exclude action bootstrap, uploads, API calls, and ordinary
validation commands. Counts marked `max` include optional branches; cache hits can make actual network
transfer smaller.

| Workflow | Declared steps | Acquisition/download steps | Estimated wall time | When it runs and conditional paths | Ratings | Value breakdown |
|---|---:|---:|---|---|---|---|
| **Dependency verification** | **31 total**: classify 4; Python 9; consolidated Node 7; compatibility 10; gate 1 | **17 max**: one checkout/setup/install path per proof family; includes Chromium installs, PDS CDN verification, and conditional Node/npm setup | **4-15 min typical**; up to 50 min critical path; 90 min summed job-timeout ceilings in the all-proof case | Pull requests targeting `dev`, on `opened`, `reopened`, and `synchronize`, limited to maintained dependency and tooling surfaces. `classify` runs only for matching paths and performs the Node declaration check inline when relevant. Python, consolidated Node, and compatibility proofs run from classifier outputs. The Node job conditionally covers root npm, diagrams, browser, and PDS checks; Cockpit behavior and browser compatibility are owned by the separate Cockpit workflow. `gate` always runs for matching changes; concurrent runs for one PR are cancelled. | Usefulness **4/5**; trigger fit **4/5**; cost **4/5**; effect/cost **4/5** | **Needed:** dependency installation, lock, lint, diagram, and PDS proof for affected surfaces. **Reduced:** unrelated PRs no longer start the workflow; root, diagram, and PDS Node surfaces share one checkout/setup; Node declaration checking no longer provisions a separate runner. |
| **Cockpit verification** | **12 total**: Node proof 7 per matrix entry; browser compatibility 5 | **11 max per workflow run**: two checkout/setup/install paths for the Node matrix plus browser-engine installation and frontend dependency installation | **8-30 min typical**; up to 60 min critical path; 90 min summed timeout ceilings across the two Node matrix entries and browser job | Pull requests targeting `dev` that change `serve/cockpit/web/**`, the Cockpit README, the Node declaration checker, or this workflow. Two Node versions prove install, behavior tests, lint, and production build; a dependent job installs Chromium, Firefox, and WebKit and runs compatibility smoke tests. Concurrent runs for one PR are cancelled. | Usefulness **5/5**; trigger fit **5/5**; cost **5/5 per Cockpit run**; effect/cost **4/5** | **Needed:** runtime compatibility and maintained frontend/browser proof. **Reduced:** the dependency workflow no longer repeats Cockpit behavior, lint, build, or cross-browser checks. |
| **MegaLinter** | **16 total** in `lint` | **4 max**: repository checkout, Node setup, Cockpit `npm ci`, and MegaLinter image/tool acquisition | **5-12 min typical**, 15 min timeout | Manual `workflow_dispatch` only; no branch/path filter. `skip_fixes` disables fixes, `unsafe_fixes` enables broader fixes, and `fix_mode` chooses a fix PR or direct commit. Fix publication only runs when sources changed and the selected mode permits it. SARIF upload depends on Code Scanning availability. | Usefulness **4/5**; trigger fit **2/5**; cost **5/5 per run**; effect/cost **3/5** | **Needed:** whole-repository lint and static/security analysis when maintenance is requested. **Nice:** SARIF, report artifacts, and automated fix PR/commit. **No apparent value:** none clearly; the unconditional frontend install is possible overhead when only non-frontend linters matter. |
| **Agent ecosystem validation** | **8 total** in `validate-agent-ecosystem` | **3**: one repository checkout, uv setup, and Python installation | **2-6 min typical**, 5 min timeout | Pull requests targeting `dev`, restricted to agent, skill, prompt, hook, validator, Knowledge, selected test, workflow, pre-commit, and relevant Python configuration paths. Superseded runs for the same PR are cancelled. The same job runs the Knowledge contract regression, so the former standalone Knowledge workflow is no longer needed. | Usefulness **4/5**; trigger fit **4/5**; cost **2/5**; effect/cost **5/5** | **Needed:** agent, skill, prompt, Knowledge identity, and write-guard validators plus focused regressions. **Reduced:** no hidden post-merge push run and no duplicate checkout/setup for Knowledge changes. |
| **Sync dev to main** | **20 total** in `sync` | **4 max with Cockpit**: checkout `dev`, fetch `main`, Node setup, and the combined `npm ci` plus PDS CDN download/build step. **2** when Cockpit is disabled | **2-8 min typical**, 10 min timeout | Manual `workflow_dispatch`; always reads `dev`. At least one of nine scope booleans must be enabled. Full selection uses a wipe; partial selection uses overlays. Cockpit setup/build/staging runs only when `sync_cockpit=true` (default false). `dry_run=true` skips the push, not the projection or build. | Usefulness **5/5**; trigger fit **4/5**; cost **4/5**; effect/cost **4/5** | **Needed:** consumer projection, stale-file pruning, generated SPA publication, and controlled push. **Nice:** selective scopes, dry-run preview, TODO warnings, and no-change detection. **Reduced:** ordinary non-Cockpit syncs no longer perform Cockpit npm/CDN work by default. |

> The standalone Knowledge source contracts workflow was removed. Its remaining contract tests now run through the consolidated Agent ecosystem workflow.

## 4. What Runs When

### 4.1 Dependency verification

The workflow now has a trigger-level path filter for maintained dependency and tooling surfaces.
Unrelated PRs do not start it. For matching changes, `classify` establishes the exact proof surface
and performs the Node declaration check inline when a Node surface is affected.

| Classifier result | Job or path | Work performed | Cost implication |
|---|---|---|---|
| Always for matching paths | `classify` | Full-history checkout, base/head diff, Python classification, and conditional Node declaration comparison | Classification cost is limited to dependency/tooling PRs; Node declaration checking uses the classifier runner |
| `python=true` | `proof-python` | Locked uv install, workspace-lock proof, compilation, Ruff check/format, and broad non-API/non-E2E/non-browser/non-Cockpit tests | High-value broad Python proof |
| `pds=true`, `root_node=true`, `diagrams=true`, or `shared_node_runtime=true` | `proof-node` | One Node setup followed by conditional root npm, diagram exporter, browser, and PDS proofs | One consolidated Node runner, up to 40 minutes; sequential proof steps trade some parallelism for lower runner-minute cost |
| `node=true` | `cockpit-verification` | Dedicated two-version Cockpit install, behavior, lint, and build proof, followed by cross-browser smoke tests | Separate path-filtered workflow owns frontend runtime compatibility; dependency verification retains only its classifier/gate path for ordinary Cockpit package changes |
| `compatibility=true` | `compatibility` | Locked uv install plus selected actionlint, pre-commit, MegaLinter, or Renovate checks | Selective but can repeat setup and lint work |
| Always after dependencies finish | `gate` | Checks expected skipped/success states and writes the summary | Small current cost, not inherently unavoidable if the status design changes |

`compatibility` covers changes to `.pre-commit-config.yaml`, workflows, `.mega-linter.yml`, and
`.github/renovate.json`. A shared `.nvmrc` change now uses one consolidated Node proof runner for
root npm, diagram, and PDS checks; Cockpit behavior and browser compatibility remain in the
separate Cockpit workflow.

### 4.2 Repository contract workflow

| Workflow | Trigger paths | Internal condition | Sequential work |
|---|---|---|---|
| Agent ecosystem validation | Agent, skill, prompt, hook, validator, Knowledge, selected test, workflow, pre-commit, and relevant Python configuration paths | Pull requests targeting `dev`; superseded runs for the same PR are cancelled | Checkout -> setup uv/cache -> `uv python install` -> three validators -> ecosystem, write-guard, and Knowledge contract tests |

The former standalone Knowledge workflow was removed. Its three non-circular contract assertions
remain in `tests/test_knowledge_ops_contract.py` and run through the shared repository-contract job,
so Knowledge changes use one checkout and environment setup. The workflow is PR-only; direct pushes
to `dev` do not create hidden duplicate runs.

### 4.3 Cockpit verification

| Workflow | Trigger paths | Internal condition | Sequential work |
|---|---|---|---|
| Cockpit verification | `serve/cockpit/web/**`, Cockpit README, Node declaration checker, and this workflow | Pull requests targeting `dev`; superseded runs for the same PR are cancelled | Two Node-version proof jobs in parallel -> locked install, behavior tests, lint, and production build -> Chromium, Firefox, and WebKit installation -> compatibility smoke tests |

### 4.4 Manual workflows

| Workflow | Conditional paths | Result |
|---|---|---|
| MegaLinter | Rejects simultaneous `skip_fixes` and `unsafe_fixes`; supports safe, unsafe, or disabled fixes; SARIF upload depends on Code Scanning availability; fix PRs require a same-repository context; commit mode is explicit | Lint result, reports, optional SARIF, and optional source mutation |
| Sync dev to main | Scope inputs select full or partial projection; all scopes use a full wipe, partial selections use overlays; Cockpit selection adds Node setup, `npm ci`, PDS sync, build, assertion, and forced staging; `dry_run` skips only the push | No-change summary, dry-run preview, or rolling commit pushed to `main` |

## 5. Ratings

| Workflow | Usefulness | Trigger fit | Runner cost | Effect/cost | Assessment |
|---|---:|---:|---:|---:|---|
| Dependency verification | 4/5 | 4/5 | 4/5 | 4/5 | Excellent proof for dependency changes with path-filtered entry, conditional runtime checking, and one consolidated Node proof |
| Cockpit verification | 5/5 | 5/5 | 5/5 per Cockpit run | 4/5 | Strong two-runtime and cross-browser proof for frontend changes; its matrix is intentionally expensive but tightly scoped |
| MegaLinter | 4/5 | 2/5 | 5/5 per run | 3/5 | Broad analysis and remediation are useful, but full-codebase scanning is expensive and manual-only is weak for continuous feedback |
| Agent ecosystem validation | 4/5 | 4/5 | 2/5 | 5/5 | Narrow PR-only path filter, superseding concurrency, and merged Knowledge coverage match the responsibility without a second runner |
| Sync dev to main | 5/5 | 4/5 | 4/5 | 4/5 | Essential publication path with sensible manual control; Cockpit work is now opt-in for small syncs |

Cost is relative to these workflows. MegaLinter is expensive per invocation but does not contribute
routine PR cost. Dependency verification is the more important optimization target because it runs on
ordinary PR activity.

## 6. Dependency Verification Cost Model

These are sums of current `timeout-minutes` values, not forecasts of actual duration.

| Changed surface or situation | Jobs that can run | Configured ceiling | Interpretation |
|---|---|---:|---|
| Ordinary or unrelated PR | No dependency workflow run | **0 min** | Path filtering prevents unrelated PRs from starting this workflow |
| Python dependency surface | Base + `proof-python` + gate | **30 min** | Lock proof, compile, lint, and broad Python behavior tests; the matrix uses three runners in parallel |
| Cockpit Node surface | Dependency classify/gate + Cockpit matrix/browser jobs | **100 min nominal** | Two Node-version proof runners plus one browser runner; the dependency workflow still performs its small classifier/gate path |
| Root Node surface | Base + `proof-node` + gate | **50 min** | One Node runner with conditional root `npm ci` |
| Diagram exporter surface | Base + `proof-node` + gate | **50 min** | One Node runner with conditional install, Chromium setup, and render |
| Tooling compatibility surface | Base + `compatibility` + gate | **30 min** | uv setup plus selected tooling checks |
| Shared `.nvmrc` change | Dependency base + `proof-node` + gate, plus Cockpit matrix/browser jobs | **140 min nominal** | Shared runtime proof exercises both dependency surfaces and the dedicated two-version Cockpit workflow |
| All dependency proof categories | Base + Python + consolidated Node + compatibility + gate | **90 min job-timeout sum** | The Python matrix represents up to 130 hosted runner-minutes when its three 20-minute entries are counted; Node proof steps are sequential |

When all dependency proof categories apply, the approximate configured critical path is 50 minutes
through the consolidated Node proof and final gate. A Cockpit change has a separate 60-minute
critical path through its Node matrix and browser job. Actual hosted time depends on queueing,
checkout, cache hits, and cancellation.

## 7. Highest-Value Opportunities

| Priority | Observation | Likely action | Risk or validation |
|---|---|---|---|
| 1 | Run and job timestamps are now accessible, but no p50/p90 or billed-minute summary exists | Measure run frequency, job duration, cache hits, cancellations, and runner minutes before making broad changes | Use at least 20 completed runs per workflow where available |
| 2 | `dependency_ci.py` emitted `applicable`, but the workflow had no path gate | **Implemented path filtering** for maintained dependency/tooling surfaces | Workflow path and classifier contract tests pass; required-check behavior still depends on repository branch-protection configuration |
| 3 | The Node runtime job was unconditional and its checker only compared file declarations | **Implemented inline conditional checking** in `classify` | Node declaration failure still fails `classify` and blocks the gate |
| 4 | Dependency verification had no trigger-level path filter | **Implemented precise trigger paths** for classifier-maintained surfaces | Existing workflow tests now assert the maintained path set |
| 5 | Dependency verification previously repeated setup across separate PDS, root npm, and diagram proof jobs | **Implemented one consolidated `proof-node` job** preserving root, diagram, browser, and PDS checks; dedicated Cockpit runtime/browser proof remains separate | Lower dependency runner-minute ceiling; sequential steps may reduce parallel wall-clock advantage |
| 6 | Agent and Knowledge workflows overlapped on `uv.lock` and `validate_agents.py` | **Implemented one PR-only contract workflow** with shared setup and Knowledge regression coverage | Existing focused validator and Knowledge contract tests pass |
| 7 | Sync detects no changes after projection, pruning, and optional Cockpit build | Compare the projected result before the expensive build, or make no-op/dry-run build semantics explicit | Test first sync, generated SPA output, partial scopes, and stale-file pruning |
| 8 | Browser proofs install Chromium on ephemeral runners | Measure download time, then consider version-keyed caching | Validate cache invalidation and hosted-runner hit rate |

## 8. Recommendation And Limits

The first cost-reduction pass is implemented across the highest-value routine paths: dependency
verification is path-filtered, dependency Node proof setup is consolidated, Node declaration checking
is conditional and inline, and agent/Knowledge contract validation is one PR-only workflow with
superseding concurrency. Dedicated Cockpit runtime and browser proof remains path-filtered. The next
useful step is measurement of actual run frequency, duration,
cache hits, and cancellation waste before changing the remaining policy-sensitive workflows.

Treat MegaLinter and sync-to-main as separate policy-sensitive workflows. MegaLinter should remain
manual until continuous feedback is worth its full-codebase cost. Sync should remain a controlled
publication workflow, but its Cockpit build is a credible no-op optimization target.

Confidence is high for the implemented triggers, paths, conditions, commands, and configured
ceilings. Confidence is medium for actual runtime savings because this report still does not contain
extracted p50/p90 durations, cache metrics, queue time, cancellation data, or billing multipliers.
