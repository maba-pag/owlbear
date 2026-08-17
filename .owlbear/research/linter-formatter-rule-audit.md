# Linter and Formatter Exception Audit

> **Owning work:** repository lint and formatter policy audit
> **Date:** 2026-08-15
> **Status:** R01, R10, M02-M03, M05-M08, the managed/archive M09 categories, G02-G09, P01-P07, X03-X04, Y01-Y02, F01-F03, and F05-F08 are validated keeps or resolved. M04 remains a fix candidate requiring an authored-document normalization pass. M01, the authored `.owlbear/research` and `.owlbear/sources` M09 categories and their G01 filter portion, plus the F04 config-file ignores, remain deferred for scoped decisions. Prettier policy files were removed; the remaining audit items are deferred for a future grouped decision.
> **Question:** Which remaining linter, formatter, scope, and path exceptions have merit, and which should be removed, narrowed, or replaced after bounded evidence is collected by owning authority and consumer?

## 1. Context and Boundaries

The repository has several independent quality authorities. A setting that looks like an
"ignore" may instead be a consumer-specific path language, a generated-file boundary, a
formatter conflict waiver, or a deliberate test convention. This ledger keeps those cases
distinct and records the evidence needed before changing them.

The earlier ignore-policy and lint-policy changes are preserved in commits `9e5adaa03` and
`986d36ab4324604bade70edd2ef323115f0b6550`. This work extends that audit; it does not reopen
those changes or apply speculative cleanup.

### In scope

- Every rule disabled or relaxed in the active linter and formatter configurations.
- Every explicit file, directory, extension, or project-scope limiter used by those tools.
- Ruff global and per-file ignores, Markdownlint rule settings, EditorConfig overrides,
  yamllint settings, frontend compiler/linter scopes, and duplicated CI/local exclusions.
- The relationship between the authority file and each consumer that reads it.
- A durable queue for one-rule-at-a-time scans and decisions.

### Out of scope for this ledger change

- Fixing findings discovered by a future scan.
- Removing generated, archived, vendor, or machine-managed records without evidence.
- Changing `.vscode/settings.json` editor fallback behavior merely because the root Prettier
  files are gone.
- Reformatting or normalizing unrelated configuration files.
- Treating a successful config parser or schema check as proof that an exception is necessary.

### Success condition

Each completed group has one owning authority, its consumers, a bounded no-fix command matrix, a
finding classification, a decision, and recorded focused verification. Rows without enough
evidence remain explicitly deferred; a green scan does not create a repair obligation by itself.

## 2. Sources Studied

| Source | Role in this audit | Limit |
|---|---|---|
| `pyproject.toml` | Ruff lint, Ruff format, and pytest policy | Ruff configuration does not explain whether every exception is still needed. |
| `.editorconfig` | Repository-wide text formatting defaults and path overrides | EditorConfig checker and individual editors may apply different file sets. |
| `.markdownlint.json` | Markdownlint rule policy for MegaLinter/manual CLI | It is not the rule authority for markdownlint-cli2. |
| `.markdownlintignore` | Bare markdownlint and MegaLinter path exclusions | Its glob semantics differ from markdownlint-cli2 configuration. |
| `.markdownlint-cli2.jsonc` | Pre-commit and VS Code Markdownlint path exclusions | It intentionally mirrors policy without being textually identical. |
| `.yamllint.yml` | Strict YAML rules and the line-length waiver | Line length is delegated to EditorConfig checker. |
| `.mega-linter.yml` | CI linter inventory, global exclusions, and project scopes | Project-mode linters must enforce their own scope. |
| `.pre-commit-config.yaml` | Local fix/check hooks, hook-specific exclusions, and frontend scope | It has a separate top-level exclusion regex and separate hook file filters. |
| `serve/cockpit/web/package.json` | Frontend lint, build, test, and E2E command boundaries | Package scripts do not by themselves prove which files CI invokes. |
| `serve/cockpit/web/tsconfig.json` | TypeScript include and excluded test patterns | E2E TypeScript is linted but is not included in this compiler project. |
| `serve/cockpit/web/eslint.config.js` | ESLint ignores and rule overrides | The configuration is intentionally minimal and has no React plugin. |
| `serve/cockpit/web/.stylelintrc.json` | Tailwind at-rule allowlist | The allowlist may be necessary, redundant, or too broad. |
| `serve/cockpit/web/.htmlhintrc` | HTML rule set and effective HTML scope | The package script currently checks `index.html` only. |
| `serve/tools/src/owlbear_tools/quality.py` | Local quality command routing and pre-commit exclusion parsing | It forwards policy rather than owning individual linter rules. |
| `serve/tools/src/owlbear_tools/megalinter.py` | Native MegaLinter image derivation and invocation | The container supplies the actual linter binaries. |
| `.vscode/settings.json` | Editor formatter selection and local quality command affordances | Language-specific formatter settings are explicit; no repository-wide Prettier fallback remains. |
| `.owlbear/hooks/*.py` and `seed/.owlbear/hooks/*.py` | Direct-run hook source and corresponding scaffold copies | These files must be checked with the project interpreter. |
| Prior research: `delivery-operating-model-reframe.md`, `1595-tailwind-stylelint-redundancy.md`, `environment-audit-research-workflow.md`, and hook research files | Existing reasoning about exceptions, frontend linting, environment authority, and hooks | Historical documents may describe older paths or completed work. |
| MegaLinter 10.0.0 Markdownlint descriptor | [Documentation](https://megalinter.io/10.0.0/descriptors/markdown_markdownlint/) | Defines `list_of_files` as the Markdownlint default and identifies the pinned `v0.49.1` binary | The documentation reflects the pinned release; the local report remains the behavior proof. |
| MegaLinter 10.0.0 CLI lint mode | [Documentation](https://megalinter.io/10.0.0/config-cli-lint-mode/) | Project mode does not receive MegaLinter `FILTER_REGEX_INCLUDE` or `FILTER_REGEX_EXCLUDE` values | The framework documentation establishes the blast-radius risk of switching modes. |

No new external source was required to initialize this ledger. Tool behavior must be confirmed
against the pinned versions and the live repository before a rule is changed.

## 3. Authority Inventory

| ID | Quality surface | Primary authority | Main consumers | Current scope boundary |
|---|---|---|---|---|
| A01 | Ruff lint | `pyproject.toml` `[tool.ruff.lint]` | pre-commit, `uv run lint-python`, MegaLinter | Python project discovery plus per-file ignores |
| A02 | Ruff format | `pyproject.toml` `[tool.ruff.format]` | pre-commit, `uv run format-python`, MegaLinter | Python files selected by Ruff |
| A03 | EditorConfig | `.editorconfig` | pre-commit, MegaLinter, editors | Glob sections and checker arguments; Python indentation is delegated to Ruff |
| A04 | Markdownlint CLI | `.markdownlint.json` and `.markdownlintignore` | MegaLinter, bare markdownlint/manual runs | `MARKDOWN_MARKDOWNLINT_CLI_LINT_MODE: list_of_files` |
| A05 | Markdownlint CLI2 | `.markdownlint-cli2.jsonc` | pre-commit, VS Code extension | CLI2 ignore globs |
| A06 | YAML lint | `.yamllint.yml` | pre-commit, MegaLinter | Root YAML plus explicit legacy ignore |
| A07 | Shell lint | `.pre-commit-config.yaml` hook revision | pre-commit, MegaLinter | Shell files discovered by each consumer |
| A08 | GitHub Actions lint | `.pre-commit-config.yaml` hook revision | pre-commit, MegaLinter | `.github/workflows/*.yml` and `.yaml` |
| A09 | TypeScript ESLint | `serve/cockpit/web/eslint.config.js` | pre-commit, MegaLinter, npm tooling | Cockpit `src` and `e2e` through local hooks; all matching files through CI filter, including root setup TypeScript |
| A10 | TypeScript compiler | `serve/cockpit/web/tsconfig.json` | pre-commit manual hook, frontend build | `src`, `vite.config.ts`, and `vitest.setup.ts`, excluding four test patterns; the manual hook trigger covers all three inputs |
| A11 | CSS lint | `serve/cockpit/web/.stylelintrc.json` | pre-commit, npm script, MegaLinter | Authored Cockpit `src/**/*.css` |
| A12 | HTML lint | `serve/cockpit/web/.htmlhintrc` and package script | pre-commit, npm script, MegaLinter | Package script checks `index.html`; MegaLinter filter is broader |
| A13 | JSON lint | `eslint-json.config.cjs` plus root `package.json` | pre-commit, `uv run lint-json`, MegaLinter | Broad `.json` and `.jsonc` discovery; `.vscode/*.json` is parsed as JSONC; generated and machine-managed paths are globally ignored |
| A14 | Generic file checks | `.pre-commit-config.yaml` | pre-commit | PDS vendor assets have whitespace/EOF exclusions |

The active policy contains no remaining root Prettier configuration. `.prettierrc` and
`.prettierignore` were fallback files with no repository quality command consuming them and are
removed by this change. The `editor.defaultFormatter` value in `.vscode/settings.json` remains a
separate editor fallback decision and is recorded below rather than silently changing it.

## 4. Rule and Exception Ledger

Statuses are deliberately conservative:

- `queued`: identified but not yet scanned.
- `needs-scan`: a plausible rationale exists, but current evidence is insufficient.
- `fix-candidate`: scope or rule shape already suggests the exception may be too broad; confirm with a scan.
- `validated-keep`: the current exception is supported by a reproducible repository-specific observation.
- `blocked`: a required consumer or fixture is unavailable.
- `resolved`: the item has a recorded decision and focused verification.

### 4.1 Ruff global policy

Each code below is a separate scan item even when its source block is shared.

| ID | Current setting | Current rationale | Status | Required evidence |
|---|---|---|---|---|
| R01 | `COM812` ignored globally | Formatter conflict | validated-keep | Normal Ruff check and format check pass; an explicit `COM812` probe reports formatter-conflicting findings at the pinned version. |
| R02 | `CPY001` ignored globally | No per-file copyright headers | validated-keep | Exact probe found 257 header findings; the repository has no copyright-header policy, and the repository-wide Ruff check passes. |
| R03 | `D105` ignored globally | Magic methods inherit behavioral documentation | validated-keep | Exact probe found 6 magic-method findings; surrounding class contracts document their behavior, and the repository-wide Ruff check passes. |
| R04 | `D107` ignored globally | Constructor docs belong on the class | validated-keep | Exact probe found 47 constructor findings; constructor behavior is covered by class documentation, and the repository-wide Ruff check passes. |
| R05 | `ISC001` ignored globally | Formatter conflict | validated-keep | The pinned Ruff probe found 0 `ISC001` findings under the active policy; the ignore remains an explicit formatter-compatibility guard. |
| R06 | `S101` ignored globally | Assertions are needed in tests | resolved | Removed the global ignore, retained test-only scopes plus the exact session-review test scope, replaced the two production assertions with explicit guards, and passed repository-wide Ruff. |
| R07 | `SIM108` ignored globally | Explicit branches are often clearer | resolved | Rewrote both production findings as equivalent conditional expressions; focused and repository-wide Ruff checks pass. |
| R08 | `N818` ignored globally | Existing public exception names | resolved | Replaced the global ignore with exact scopes for `AuthenticationRequired` and `DeliveryStartupDiagnostic`; repository-wide Ruff passes without renaming either API. |
| R09 | `line-length = 120` | Shared project limit | resolved | Fixed all 7 isolated `E501` findings, retained the 120-column limit, and passed Ruff plus the formatter check. |
| R10 | `extend-exclude = ["*.md"]` | Markdown is not Ruff source | resolved | Removed after Ruff file-selection probe showed no Markdown paths. |
| R11 | Ruff format `quote-style = "double"` | Repository formatter preference | validated-keep | `uv run ruff format --check` passes for 3,894 files after formatting the two reported paths. |

### 4.2 Ruff per-file ignores

The entries are copied from `pyproject.toml`. Codes in one row remain separate work items; the
row identifies the shared scope and the first narrow command to use.

| ID | Scope | Codes currently ignored | Status | First scan boundary |
|---|---|---|---|---|
| R12 | `.owlbear/hooks/*.py` | `C901`, `INP001`, `PLR0912`, `T201` | validated-keep | Source and seed hook scans retain only direct-run, stdout-protocol, and path-policy exceptions; repository-wide Ruff passes. |
| R13 | `seed/.owlbear/hooks/*.py` | `C901`, `INP001`, `PLR0912`, `T201` | validated-keep | Scaffold hook scope remains parity-preserving with R12; repository-wide Ruff passes. |
| R14 | `.owlbear/scripts/*.py` | `INP001`, `T201` | resolved | Removed inert `PLR2004` and `PTH201` waivers after fixing both direct-run script copies; retained only package discovery and CLI stdout scopes. |
| R15 | `.github/scripts/*.py` | `INP001`, `T201` | validated-keep | The current CI helper uses stdout as its direct-run contract; the exact scope is retained and repository-wide Ruff passes. |
| R16 | `seed/.owlbear/scripts/*.py` | `INP001`, `T201` | resolved | Removed inert `PLR2004` and `PTH201` waivers in parity with R14; repository-wide Ruff passes. |
| R17 | `.owlbear/scratch/*.py` | `ANN401`, `INP001`, `S603`, `T201` | validated-keep | No tracked scratch Python files produce findings; the structural direct-run boundary remains explicit for transient scripts. |
| R18 | `setup/*.py` | `INP001`, `T201` | validated-keep | Setup entry points remain direct-run scripts with user-facing stdout; repository-wide Ruff passes. |
| R19 | `serve/*/examples/**/*.py` | `INP001`, `T201`, `EM101` | validated-keep | No tracked example Python files produce findings; the script-style boundary remains explicit. |
| R20 | `tests/**/*.py` | `ANN`, `D`, `INP001`, `S101`, `PLR2004`, `TCH` | resolved | Removed inert broad waivers, mechanically fixed imports/decorators, fixed ordinary diagnostics, and moved intentional `N801`, `PLC0415`, `PLR0917`, `S603`, `S607`, `SLF001`, `ERA001`, and `PLW1510` findings to code-local directives. High-volume acceptance and white-box patterns use file-local directives; isolated findings use line-local `# noqa` markers. Root and package test directories remain non-package roots for pytest importlib collection, with directory-level `INP001` handling. |
| R21 | `tests/fixtures/delivery-authority/**/*.py` | `INP001`, `S603`, `S607` | resolved | Fixture files are parsed as inert AST/data text; exact fixture scopes preserve that contract, and repository-wide Ruff passes. |
| R22 | `serve/*/tests/**/*.py` | `ANN`, `D`, `INP001`, `S101`, `PLR2004`, `TCH` | resolved | Removed inert broad waivers, fixed package test diagnostics, and localized intentional subprocess/private-access/import/arity cases to the relevant statements or high-volume files; repository-wide Ruff passes. |

### 4.3 EditorConfig overrides

These are scope limiters rather than linter rule names. Each path section is a separate item.

| ID | Section or override | Current exception | Status |
|---|---|---|---|
| E01 | `[tests/**/*.py]` | `max_line_length = unset` | needs-scan |
| E02 | `[serve/*/tests/**/*.py]` | `max_line_length = unset` | needs-scan |
| E03 | `[serve/cockpit/web/src/**/*.{ts,tsx}]` | `max_line_length = unset` | needs-scan |
| E04 | `[serve/cockpit/web/e2e/**/*.ts]` | `max_line_length = unset` | needs-scan |
| E05 | `[*.md]` | `indent_size` and `max_line_length` unset | needs-scan |
| E06 | `[.owlbear/delivery/runtime/**]` | `max_line_length = unset` | needs-scan |
| E07 | `[.owlbear/legacy/**]` | `max_line_length = unset` | needs-scan |
| E08 | `[.owlbear/delivery/packages/**]` | `max_line_length = unset` | needs-scan |
| E09 | `[*.excalidraw]` | EOL, length, and trailing-whitespace rules unset | needs-scan |
| E10 | `[serve/cockpit/web/public/porsche-design-system/**]` | Generated vendor formatting rules unset | needs-scan |
| E11 | `[.mega-linter.yml]` | `max_line_length = unset` | needs-scan |
| E12 | `[uv.lock]` | `max_line_length = unset` | needs-scan |
| E13 | `[package-lock.json]` | `max_line_length = unset` | needs-scan |
| E14 | `[serve/cockpit/web/package-lock.json]` | `max_line_length = unset` | needs-scan |
| E15 | `[store/**]` | Indent, length, and trailing-whitespace rules relaxed | needs-scan |

### 4.4 Markdownlint rules

| ID | Rule | Current setting | Consumer | Status |
|---|---|---|---|---|
| M01 | `MD013` | disabled | Markdownlint CLI and MegaLinter | deferred |
| M02 | `MD024` | `siblings_only: true` | Markdownlint CLI and MegaLinter | validated-keep |
| M03 | `MD029` | `style: one_or_ordered` | Markdownlint CLI and MegaLinter | resolved |
| M04 | `MD033` | disabled | Markdownlint CLI and MegaLinter | fix-candidate |
| M05 | `MD040` | enabled | Markdownlint CLI and MegaLinter | resolved |
| M06 | `MD041` | `front_matter_title: title\|name\|description` | Markdownlint CLI and MegaLinter | resolved |
| M07 | `MD060` | `style: any` | Markdownlint CLI and MegaLinter | resolved |

### 4.4.1 Markdownlint authority parity

| ID | Finding | Status | Decision and evidence |
|---|---|---|---|
| M08 | Root and seed bare/CLI2 exclusion lists can drift across glob syntaxes. | resolved | Root and seed profiles now rely on the normalized broad `**/worktrees/**` exclusion rather than duplicating `.owlbear/delivery/worktrees/**`. A parity contract covers root and seed profiles; seed-only CLI2 entries and the existing `.owlbear/target` omission are explicit profile differences. |
| M09 | The semantic necessity of the excluded categories was tested across the Markdown consumers. | deferred | Managed/archive categories are supported by ownership or bounded exposure evidence. The authored research and sources categories produced real Markdown findings when exposed; research needs a separate authored-document policy, and sources should be repaired before removing its broad exclusion. |

The bare Markdownlint exclusions are `.owlbear/completed`, `.owlbear/delivery/packages`,
`.owlbear/delivery/runtime`, the generated `.owlbear` index
files, `.owlbear/legacy`, `.owlbear/memory`, `.owlbear/research`, `.owlbear/sources`,
`.owlbear/target`, `.venv`, `**/node_modules`, `**/scratch`, `**/test-results`, `**/worktrees`,
and `megalinter-reports`. The CLI2 file expresses the same root categories with explicit `/**`
globs and names the broader `**/worktrees/**` pattern without a duplicate scoped worktree entry.
The focused contract test in `tests/test_linter_formatter_policy.py` normalizes the two glob
forms, requires root bare/CLI2 parity, and allows only the documented seed profile differences.
At pinned markdownlint-cli2 0.23.2, the broader worktrees glob covers the Delivery worktree path;
M08 therefore closes a drift-prevention gap and removes a redundant scoped entry rather than
changing the effective exclusion. M09
owns whether the exclusion categories themselves should remain.

#### M09 category experiment: `.owlbear/completed`

The category was removed temporarily from the root and seed Markdownlint authorities, the
MegaLinter global filter, and the pre-commit global filter. The path is currently absent and
contained zero Markdown files, so no local Markdownlint findings appeared. The no-fix local
wrapper and manual pre-commit Markdownlint hook both passed; MegaLinter analyzed 114 Markdown
files with zero Markdownlint errors. MegaLinter's overall run exited non-zero because its
unrelated repository formatter descriptor reported 113 files needing reformatting. The Delivery
completed-history implementation still reserves `.owlbear/completed/<change-id>` as a historical
record location, so the exclusion was restored and classified as `validated-keep` for its
machine-managed future contents. The remaining M09 categories are not decided by this probe.

#### M09 category experiment: `.owlbear/delivery/packages`

The category contains the non-admissible `website-to-knowledge-vertical` Design package with
Markdown roadmap records alongside JSON authority/manifest data and lock or completion-residue
artifacts. Its intent and design documents define it as a roadmap-only umbrella that must never
enter Delivery admission, so this is a machine-managed mixed-format boundary rather than ordinary
repository documentation. Removing only the category from the root and seed bare/CLI2 Markdownlint
authorities, the pre-commit top-level exclusion, and the MegaLinter global filter expanded
MegaLinter's Markdown set from 117 to 119 files but produced no Markdownlint findings in the
package. The pre-commit run also produced no package findings; its non-zero result and MegaLinter's
four errors were unrelated existing workspace findings. Restoring all six exclusions, the focused
six-consumer policy contract, and the final no-fix probes preserved the boundary. This category is
therefore a `validated-keep`; the remaining M09 categories require separate experiments.

#### M09 category experiment: generated `.owlbear` indexes

The three index files are produced by `serve/tools/doc-index` and the paired Python and TypeScript
index generators; the documentation index carries an auto-generated, do-not-edit header, and the
producer explicitly tracks all three paths as generated index outputs. Removing only these paths
from the six Markdownlint consumers exposed all three files to the manual/pre-commit authority.
That run analyzed all three indexes: `py-index.md` and `ts-index.md` were clean, while
`doc-index.md` produced 50 unique `MD022` and `MD032` findings. The CI-equivalent MegaLinter run
included all three in its 120-file descriptor set but reported no findings for those paths, showing
that the two Markdownlint consumers do not produce identical diagnostics for generated output.
Restoring all six exclusions and adding the focused six-consumer contract preserves the stricter
manual authority and the machine-managed boundary. The generated-index category is therefore a
`validated-keep`; the remaining M09 categories require separate experiments.

#### M09 category experiment: `.owlbear/legacy`

The legacy root contains 3,207 tracked files, including 2,392 Markdown files and approximately
38.8 MB of historical briefs, completed records, OpenSpec material, target-cutover history,
incident evidence, and design/runtime archives. Migration and retirement tooling still references
legacy records, so this is a retained historical boundary rather than an abandoned scratch path.
A full exposure would add thousands of historical documents to the contributor lint path. Instead,
the category was temporarily exposed across the six Markdownlint consumers and Markdownlint was
run against one representative file from each Markdown-bearing top-level area: briefs, completed,
openspec-final, target-cutover, target-cutover-incidents, target-delivery-cutover-design, and
target-delivery-cutover-runtime. All seven samples were analyzed with no findings and no skips;
`delivery-state-migration` contains no Markdown files. Restoring the broad exclusions and adding a
representative-path six-consumer contract preserves the archive boundary without claiming that a
sample proves the entire historical corpus clean. The legacy category is therefore a
`validated-keep`; the remaining M09 categories require separate experiments.

#### M09 category experiment: `.owlbear/memory`

The memory root is the active institutional store: it currently contains 23 Markdown entries with
YAML lifecycle front matter, comprising 10 `approved`, 12 `deleted`, and one `stale` record. The
canonical producer and consumer is `serve/memory-mcp`, which reads and writes `.owlbear/memory/*.md`
as managed memory records rather than ordinary repository documentation. Removing only the memory
category from the six Markdownlint consumers exposed one representative entry from each present
lifecycle state to the manual/pre-commit authority. All three samples were analyzed with no
findings and no skips. Restoring the broad exclusions and adding a three-state representative
contract preserves the structured memory boundary without claiming that every future entry is
Markdownlint-clean. The memory category is therefore a `validated-keep`; the remaining M09
categories require separate experiments.

#### M09 category experiment: `.owlbear/research`

The research root contains 1,095 authored Markdown files totaling approximately 7.7 MB, including
numbered task records, named research documents, audit ledgers, and a five-file evidence subdirectory.
The research workflow and setup guide define these files as durable or frozen comparison evidence,
not generated runtime state. Removing only the research category from the six Markdownlint consumers
exposed five representative document shapes: a numbered task record, named research, an environment
audit, the active linter ledger, and a subdirectory evidence document. All five files were analyzed;
three produced 17 findings across `MD032`, `MD036`, `MD047`, and `MD056`. Restoring the broad
exclusions and adding a representative-path six-consumer contract preserves the historical research
boundary without forcing a 1,095-file remediation sweep. The research category remains deferred:
keep it outside the general gate for now, define a separate policy for newly authored research, and
do not treat active authored research as machine-managed content.

#### M09 category experiment: `.owlbear/sources`

The sources root contains one authored Markdown document, `.owlbear/sources/overview.md`, totaling
589,420 bytes (approximately 575 KiB). The inventory found no producer or consumer references in
`serve/`, `setup/`, `seed/`, or `tests/`; this is source documentation rather than runtime source
metadata or fetched content. Removing only the sources category from the six Markdownlint consumers
made the manual/pre-commit hook analyze the document and report one `MD037/no-space-in-emphasis`
finding at line 4949, column 139. The CI-equivalent MegaLinter run also analyzed the document and
reported five Markdownlint findings overall, with no unrelated failures. Restoring all six
exclusions and adding a representative-path six-consumer contract preserves the authored source
boundary without forcing a large-document cleanup. The sources category remains deferred: the single
current local finding and five CI-equivalent findings are small enough to repair. Fix those
source-format findings, then remove the broad sources exclusion.

#### M09 category experiment: `.owlbear/target`

The target root is currently absent and contains no files, but Delivery application loading and
migration tooling reserve `.owlbear/target` as retired or machine-managed runtime state. Setup and
seed ignore documentation preserve that ownership, while the seed Markdownlint profiles intentionally
omit the target category as a documented profile difference. The representative-path contract now
asserts that `.owlbear/target/runtime.md` remains excluded by the root bare/CLI2 authorities and by
the pre-commit and MegaLinter consumers, while preserving the seed omission. With no current
Markdown corpus to remediate and a fail-closed runtime boundary to protect, the target category is
therefore a `validated-keep`; the remaining M09 categories require separate experiments.

#### M09 category experiment: `.owlbear/delivery/worktrees`

The category is the managed Change-worktree root. It is currently empty, while Delivery workspace
tests and migration code treat `.owlbear/delivery/worktrees/<change-id>` as operational state. The
root and seed bare/CLI2 profiles already contain the broader `**/worktrees` exclusion, and the
pre-commit top-level filter plus MegaLinter directory filter also exclude representative worktree
paths. Removing only the four redundant `.owlbear/delivery/worktrees` entries leaves the effective
consumer boundaries unchanged. The focused policy contract now asserts both that the broad pattern
remains and that `.owlbear/delivery/worktrees/change.md` remains excluded by all four consumer
families. The scoped duplicate is therefore removed; the broader machine-state exclusion remains
protected, and the remaining M09 categories require separate experiments.

#### M09 category experiment: `.owlbear/delivery/runtime`

The category is the Delivery operational-state root: its current contents are a storage lock,
capacity JSON, and transaction, change, claim, and publication state directories, with no authored
Markdown files. Removing only the category from the root and seed bare/CLI2 Markdownlint
authorities, the pre-commit top-level exclusion, and the MegaLinter global filter did not change
MegaLinter's Markdown set, which remained 117 files, and produced no runtime Markdown findings.
The manual Markdownlint hook reported only the existing `share/agents/memory-curator.agent.md`
MD056 defect; the isolated MegaLinter run reported its existing four Markdown findings and
unrelated descriptor findings. Restoring all six exclusions, the focused six-consumer policy
contract, and the final policy checks preserved the operational-state boundary. This category is
therefore a `validated-keep`; the remaining M09 categories require separate experiments.

### 4.5 YAML, MegaLinter, and pre-commit scope

| ID | Surface | Current limiter or waiver | Status |
|---|---|---|---|
| Y01 | yamllint | `line-length: disable` because EditorConfig owns text length | validated-keep |
| Y02 | yamllint | `.owlbear/legacy/**` ignored | validated-keep |
| G01 | MegaLinter global filter | Egg-info, generated/archived `.owlbear` records, and audit/knowledge DB files excluded; authored `.owlbear` control, research, and source documents overlap the same filter | needs-scan |
| G02 | MegaLinter directory filter | `.benchmarks`, caches, virtualenvs, build/dist, reports, downloads, dependencies, scratch, worktrees, and package artifacts excluded | validated-keep |
| G03 | MegaLinter Markdown | `list_of_files` mode selected so the global filter applies; pinned v10 documentation confirms it is the default, while the explicit setting preserves the filter contract across default changes | validated-keep |
| G04 | MegaLinter TypeScript | Include only `serve/cockpit/web/.*\.(ts|tsx)` | validated-keep |
| G05 | MegaLinter CSS | Include only authored `serve/cockpit/web/src/.*\.css`, matching local Stylelint consumers | validated-keep |
| G06 | MegaLinter HTML | Include `serve/cockpit/web/.*\.html` | validated-keep |
| G07 | MegaLinter Actionlint | Include only `.github/workflows/*.yml` and `.yaml` | validated-keep |
| G08 | MegaLinter JSON | Replace the strict JSON-only descriptor and its `.vscode/` exclusion with one repository-wide JSON/JSONC authority | resolved |
| G09 | MegaLinter EditorConfig | `--disable-indent-size`; indentation remains checked by Ruff for Python | validated-keep |
| P01 | pre-commit top-level `exclude` | Preserves the shared generated, archived, vendor, cache, database, and worktree taxonomy; authored research/source members remain a separate G01 scope decision | validated-keep |
| P02 | pre-commit whitespace/EOF hooks | Retains generated PDS assets outside generic whitespace and EOF mutation hooks; the no-fix deactivation scan found no present defect, but the producer and EditorConfig define a machine-managed vendor boundary | validated-keep |
| P03 | pre-commit EditorConfig hook | Retains the generated-PDS boundary and disables indent-size; the PDS probe was clean, while removing the shared indentation suppression produced Python-only findings | validated-keep |
| P04 | pre-commit frontend ESLint | Retains the local `src`/`e2e` trigger while a parity contract records MegaLinter's broader Cockpit TypeScript superset and the CI-only root setup boundary | validated-keep |
| P05 | pre-commit frontend Stylelint | Local hooks and MegaLinter share the authored `src` CSS boundary; a parity contract covers generated and build-output controls | validated-keep |
| P06 | pre-commit frontend typecheck | Manual whole-project command triggers on every TypeScript input declared by `tsconfig.json`: `src`, `vite.config.ts`, and `vitest.setup.ts` | validated-keep |
| P07 | pre-commit MegaLinter | Manual-only and always-run; no staged-file narrowing | validated-keep |

The duplicated MegaLinter/pre-commit taxonomy is not automatically a defect. The tools use
different path languages and one is a containerized project scan while the other is a hook
dispatcher. The scan must compare effective file sets, not text equality.

The grouped Y validation ran `uv run lint-yaml` and `uv run lint-editorconfig` successfully. The
strict yamllint run analyzed 44 YAML files with no findings, while the selected MegaLinter run also
passed yamllint on the same 44 files and EditorConfig on 925 selected files. Keeping yamllint's
line-length rule disabled avoids duplicate ownership: EditorConfig supplies the repository text
length policy, with intentional path overrides. The `.owlbear/legacy/**` YAML exclusion remains a
historical archive boundary and is consistent with the validated Markdown archive boundary.

The grouped G validation recorded the MegaLinter collection boundary: 5,272 files were found and
925 were kept. The selected post-fix run exited 0 for YAML (44), TypeScript (74), CSS (3), HTML (1),
EditorConfig (925), and JSON/JSONC (18). The global and directory filters therefore remain
validated scope controls for generated, archived, machine-managed, dependency, cache, build, and
worktree content; no filter was broadened merely because the selected run was green.

P04 deliberately keeps the local hook focused on contributor-owned `src` and `e2e` code. The
CI filter also admits project-level TypeScript such as `vitest.setup.ts`; direct no-fix ESLint
probes passed for both the local directories and that CI-only file. The policy test records the
expected subset relationship and representative boundary paths. The residual risk is that a
root TypeScript setup file can bypass the local hook, while CI remains its authoritative check.

P05 narrows MegaLinter to the same authored `src` CSS boundary already used by the package
script and all three local Stylelint hooks. The current tree has three tracked CSS files there;
PDS assets under `public/` are generated vendor JavaScript/SVG/image output, and Vite's compiled
CSS is emitted under `serve/cockpit/dist/`. The policy test records source, future generated, and
compiled-output boundary paths. This removes a latent local/CI scope mismatch without expanding
Stylelint into generated or vendor content.

P06 expands the manual typecheck trigger to match the three inputs declared by `tsconfig.json`:
`src`, `vite.config.ts`, and `vitest.setup.ts`. The no-emit project check passed with no
diagnostics before and after the scope correction. E2E TypeScript and `playwright.config.ts`
remain outside this compiler project and are retained as the separate F03 coverage decision.

P07 was tested by removing only `always_run` while temporarily adding `--no-fix` to the hook entry
as a safety harness; the entry was restored afterward. An explicit manual `--all-files` run passed
in 12.92 seconds, and a representative `--files serve/tools/src/owlbear_tools/megalinter.py` run
also passed in 12.51 seconds. Both invoked the same full MegaLinter scan because `pass_filenames` is
false and the wrapper requests `VALIDATE_ALL_CODEBASE=true`. A tracked path excluded by the shared
pre-commit filter was skipped with exit 0 when no applicable files remained. The initial attempt to
pass `--no-fix` through pre-commit was rejected before hook execution and is not scan evidence.
Restoring `always_run` preserves the intended manual full-workspace gate without adding it to the
normal staged hooks, so P07 is a validated keep.

G08 replaces `JSON_JSONLINT` with the official `@eslint/json` language plugin. The root
`eslint-json.config.cjs` uses `json/json` for strict `.json` files and a later `json/jsonc` block
with trailing commas enabled for `.jsonc` and `.vscode/*.json`. Its global ignore object preserves
the existing generated, archived, dependency, cache, report, and machine-managed boundaries in
root and recursive forms so the local package command and MegaLinter's `JAVASCRIPT_ES` descriptor
share one scope authority. The root `lint:json` script delegates path resolution to
`scripts/lint-json.mjs`; that launcher invokes the package-local ESLint executable from the
repository root. The `eslint-json` pre-commit hook calls the root script, while MegaLinter points at
the same config and executable without requiring a package working-directory hop.

The disposable simulation with ESLint 10.7.0 and `@eslint/json` 2.0.1 linted 564 files without
custom ignores and 97 with the translated exclusion set. It found no findings in the excluded run
and validated `.vscode/settings.json`, `.vscode/mcp.json`, and `.markdownlint-cli2.jsonc`. The one
unexcluded parser failure was the empty machine-managed
`.owlbear/delivery/packages/website-to-knowledge-vertical/authority.json`; strict JSON reports
`Expecting value: line 1 column 1 (char 0)`, so the existing package boundary remains intentional.
The focused package lint, `uv run pre-commit run eslint-json --all-files`, `npm ci`, and the
policy/quality tests passed after implementation. A pinned MegaLinter v10.0.0 container run showed
that `JAVASCRIPT_ES` completed with zero errors and warnings. The wrapper's overall invocation
returned 1 because unrelated Python, TypeScript, YAML, HTML, EditorConfig, diff, and security
descriptors reported findings in the broader working tree; no JSON/ESLint finding was reported.
Residual risk is limited to future MegaLinter or ESLint upgrades; the workflow's package
installation and the pinned JSON descriptor path are exercised end to end.

### 4.6 Frontend compiler and linter boundaries

| ID | Surface | Current limiter or exception | Status |
|---|---|---|---|
| F01 | TypeScript `include` | `src`, `vite.config.ts`, and `vitest.setup.ts` only | validated-keep |
| F02 | TypeScript `exclude` | `src/**/*.test.ts`, `src/**/*.test.tsx`, `src/**/*.spec.ts`, `src/**/*.spec.tsx` | validated-keep |
| F03 | TypeScript E2E coverage | Eleven E2E TypeScript files are linted but are not in `tsconfig.json` | validated-keep |
| F04 | ESLint ignores | `dist`, coverage, Playwright reports, node_modules, generated PDS assets, and config files | needs-scan |
| F05 | ESLint unused-vars | Warning severity with underscore-prefixed args/vars ignored; local and CI consumers set `--max-warnings 0` | validated-keep |
| F06 | ESLint raw PDS elements | Five custom elements rejected through `no-restricted-syntax` | validated-keep |
| F07 | Stylelint Tailwind | Eight Tailwind at-rules allowed: `theme`, `utility`, `apply`, `source`, `reference`, `variant`, `custom-variant`, `plugin` | validated-keep |
| F08 | HTMLHint package script | Only `index.html` is checked by `lint:html` | validated-keep |

The source-test and E2E split is an intentional ownership boundary: the TypeScript project covers
`src`, `vite.config.ts`, and `vitest.setup.ts`, while ESLint covers both `src` and `e2e`. A green
`tsc --noEmit` result is not proof for E2E files, so the separate ESLint coverage remains explicit
instead of expanding the compiler project without evidence. The grouped frontend checks passed
ESLint with no findings, Stylelint with no findings, HTMLHint with no errors, TypeScript with no
diagnostics, and the production build.

### 4.7 Editor and formatter residue

| ID | Surface | Current state | Status |
|---|---|---|---|
| X01 | Root Prettier config | `.prettierrc` removed in this change | resolved |
| X02 | Root Prettier ignore | `.prettierignore` removed in this change | resolved |
| X03 | VS Code global formatter | Removed the repository-wide `esbenp.prettier-vscode` fallback; language-specific mappings remain | resolved |
| X04 | Language-specific formatters | Explicit mappings retained for JSON/JSONC, Markdown, PowerShell, Python, TOML, and XML; repository-backed and editor-only authorities are distinguished | validated-keep |

X03 removes the repository-wide Prettier fallback while preserving explicit language-specific
formatter mappings. X04 remains separate because it evaluates whether each language-specific
formatter is still the correct authority.

## 5. Grouped Evidence Workflow

Use this cycle for a coherent authority and consumer group. Individual ledger IDs remain separate
for traceability, but they do not require serial policy mutation when one bounded evidence set can
answer the shared question:

1. **Record authority and baseline.** Confirm the setting, its consumers, the affected file set,
   current git status, and the narrow no-fix command. Put long output in `.owlbear/scratch/`.
2. **Use an isolated diagnostic.** Prefer a CLI argument, temporary config, or representative
   path list over mutating an authoritative policy file. Keep the exact command and restore any
   disposable diagnostic input immediately.
3. **Scan without fixes.** Run the smallest consumer matrix that can expose the grouped boundary.
   Keep the pinned tool versions, affected paths, and exit status.
4. **Classify findings.** Use exactly one primary class: controlled source defect,
   intentional contract, generated/vendor/machine-managed artifact, archived record, false
   positive/noise, or consumer mismatch.
5. **Choose the smallest durable response.** Fix controlled source; narrow an exception; modify
   the rule; or document a validated keep. Do not hide a finding with a new broad ignore.
6. **Restore and verify.** Run the focused check with the final configuration and each relevant
   neighboring consumer when the decision changes a shared boundary.
7. **Close the group.** Record the decision, evidence paths, working-tree proof, residual risk,
   and deferred follow-up. A row is not complete because the scanner is green.

Useful consumer commands are the repository wrappers where available: `uv run lint-python
--no-fix`, `uv run lint-markdown --no-fix`, `uv run lint-yaml`, `uv run lint-editorconfig`,
`uv run lint-cockpit --no-fix`, and `uv run megalint --no-fix`. Use the underlying pinned tool
only when the wrapper cannot isolate the item. Frontend commands live in
`serve/cockpit/web/package.json`; TypeScript scope experiments should use `npx tsc --noEmit
--project serve/cockpit/web/tsconfig.json`.

## 6. Deferred Work Queue

The Y/F/G grouped pass is closed except for the reopened F04 scope question. Remaining rows are
intentionally deferred; they are not an automatic repair queue. Future work should select a
coherent owner and consumer group, then apply the grouped evidence workflow above.

- Markdown line length: M01 remains deferred with the rule disabled; its prior EditorConfig
   delegation rationale was corrected, and a Markdown-specific length contract is still needed.
- Markdown structure: M02 is a validated keep. M03 and M05-M07 are resolved after authored-content
   remediation and both local/CI-equivalent consumer checks. M04 remains a fix candidate.
- Authored Markdown scope: M09 `.owlbear/research` and `.owlbear/sources`, with dependent G01/P01 filter decisions, remain deferred.
- Ruff global and scoped exceptions R02-R22 are now resolved or validated keeps; no Ruff item remains in the deferred queue.
- Frontend ESLint scope: F04 config-file ignores remain deferred for narrowing or explicit justification.
- EditorConfig path overrides: E01-E15 remain deferred.

### 6.1 Closure re-evaluation

The 2026-08-17 challenge separated evidence-backed policy decisions from closures supported only
by a green scan or the cost of remediating existing content.

- R01 remains a validated keep: `uv run ruff check --select COM812 .` still reports the known
   formatter-conflicting trailing-comma debt, while `ISC001` and the normal formatter check pass.
   R10 remains correctly resolved because Ruff never selected Markdown, so its exclusion was inert.
- M08 remains a good parity correction. The normalized broad worktree rule removes duplicate
   syntax without weakening the managed-worktree boundary.
- M09 is split. Completed records, Delivery packages/runtime/worktrees, generated indexes, legacy,
   memory, and target are machine-managed or historical boundaries with direct ownership evidence.
   Research and sources are authored Markdown; their exposure produced real findings, which proves
   the exclusion has an effect but does not prove that excluding active authored material is the
   right policy. Those two categories are reopened rather than treated as validated keeps.
- Y01-Y02, G02-G09, P02-P07, F01-F03, F05-F08, and X03-X04 remain supported by ownership,
   negative probes, or explicit consumer contracts. P04's local/CI difference is an intentional
   fast-hook versus CI boundary, and F05's warnings are not tolerated because both consumers use
   `--max-warnings 0`.
- G01 and P01 are reopened only for the authored research/source members of their shared taxonomy;
   their generated, archived, vendor, cache, database, and worktree members remain supported.
- F04 is reopened only for `*.config.js` and `*.config.ts`. A no-ignore ESLint probe over the
   current config files passed with no findings, so retaining those exclusions has no demonstrated
   quality benefit. Generated, report, dependency, and vendor exclusions remain supported.
- M01 remains deferred with the rule disabled. `.editorconfig` explicitly sets `max_line_length =
   unset` for `[*.md]`; the heterogeneous authored corpus and lack of a repository-wide Markdown
   line-length contract justify pausing the choice, not validating the old delegation rationale.

### 6.2 Markdown M01-M09 pass

The rule-by-rule diagnostic pass on 2026-08-17 used the pinned markdownlint-cli2 0.23.2 environment,
the current tracked Markdown set, and the normalized exclusions described above. That diagnostic
pass preceded the separately recorded M03/M05/M06/M07 configuration and authored-content changes.

- **M01 / `MD013` — deferred policy decision, disabled.** The 118-file in-scope scan reported 4,768 findings
   at the default 80 columns, 1,825 at 100, 1,340 at 120, and 1,010 at 140. Findings span
   `serve/delivery`, `share/skills`, `share/agents`, `share/prompts`, `.owlbear` authored docs,
   setup, and package documentation; no single generator owns the debt. Even a 120-column prose-only
   probe reported 969 findings in 62 files. Keep the rule disabled until the project chooses a
   Markdown-specific line-length contract; do not claim that EditorConfig currently owns this rule.

- **M02 / `MD024` — validated keep, `siblings_only: true`.** A global duplicate-heading probe found
   one intentional repeated `Frontmatter (YAML)` heading in `share/skills/h-agent-structure/SKILL.md`;
   the headings belong to separate parent sections. Sibling-only checking preserves that reuse while
   still detecting duplicate headings within one section. No config change is warranted.

- **M03 / `MD029` — resolved.** The four findings were controlled source defects: three nested-list
   boundaries in `share/skills/h-ac-quality/SKILL.md` and one continuation/list boundary in
   `setup/setup-guide.md`. The list structures were repaired, `style: one_or_ordered` is enabled,
   and the isolated probe reports zero findings.

- **M04 / `MD033` — fix candidate.** Forty-four of 45 findings are required XML-style agent section
   tags (`agents`, `boundaries`, `critical_rules`, `examples`, `output_format`, `path`, `persona`,
   and `required_reading`) consumed by the agent validator and VS Code agent format. The remaining
   `strong` element in `setup/sharing-guide.md` is ordinary prose markup. Replace that element with
   Markdown emphasis and configure the exact agent tag allowlist; the allowlist probe leaves one
   finding instead of disabling inline-HTML checking globally.

- **M05 / `MD040` — resolved.** Fourteen unlabeled fences across nine authored files were labeled
   as `shell`, `python`, `markdown`, or `text`, and the rule is enabled in root and seed policy.
   The full 118-file isolated probe reports zero findings. The Python example was also formatted to
   satisfy the repository's Ruff formatter when the language label made it executable documentation.

- **M06 / `MD041` — resolved.** The frontmatter-aware configuration
   `front_matter_title: "^\\s*(?:title|name|description)\\s*[:=]"` is enabled in root and seed
   policy. `.owlbear/ideas.md` now has an H1 title and a consistent H2 section hierarchy; the two
   delivery-authority fixtures now have neutral H1 titles, preserving their raw governance-token
   test data without fixture-specific exclusions. The root CLI2 check and bare Markdownlint wrapper
   pass.

- **M07 / `MD060` — resolved.** The `style: any` probe reported 952 findings across 64 files.
   Markdownlint's safe fixer changed 58 files and reduced the set to 126 aligned-table findings;
   those residual tables were normalized to compact spacing across 20 files. `style: any` is enabled
   in root and seed policy, and the root CLI2, bare wrapper, focused policy tests, and MegaLinter
   Markdownlint descriptor all pass.

- **M08 — resolved.** The focused parity contract passes 19 tests. Normalized root and seed bare/
   CLI2 exclusions agree, the broad `**/worktrees/**` pattern covers Delivery worktrees, and the
   documented seed-only differences remain explicit. No further change is needed.

- **M09 — split decision.** Completed records, Delivery packages/runtime/worktrees, generated
   indexes, legacy history, Memory records, and target state have direct machine-managed or archived
   ownership evidence and remain excluded. The research root is authored but 535 of 1,095 files
   currently produce 1,589 findings; retain it outside the general Markdownlint gate as a scoped
   document class and create a separate policy for newly authored research rather than launching a
   1,095-file cleanup. The sources ledger is also authored, but it is one 589,420-byte file with one
   current local finding (and five in the CI-equivalent prior probe); fix its source-format findings,
   then remove its broad Markdownlint exclusion. G01/P01 remain open only for these authored members.

### 6.3 Markdown M03/M05/M06/M07 implementation

The implementation pass changed only the requested Markdown rules and their authored findings. Root
and seed rule authorities now agree on `MD029`, `MD040`, `MD041`, and `MD060`; root and seed ignore
authorities no longer contain fixture-specific exceptions. The root CLI2 check, bare
`uv run lint-markdown --no-fix`, the focused 19-test policy suite, and the CI-equivalent MegaLinter
run all pass. MegaLinter analyzed 118 Markdown files with zero Markdownlint errors; its full run
also reported zero errors for Ruff, Ruff format, EditorConfig, frontend linters, YAML, and repository
checks after the labeled Python example was formatted.

## 7. Evidence and Decision Log

| Date | Item | Observation | Decision |
|---|---|---|---|
| 2026-08-15 | X01-X02 | No repository quality command or config consumer was found for the root Prettier files; their settings were fallback policy. | Remove both files. |
| 2026-08-15 | Hook syntax probe | `uv run --frozen python` parses all ten root/seed Python hooks. `/usr/bin/python3` reports syntax errors in the same `HEAD` bytes. | Treat as an interpreter/tooling mismatch, not a source defect; use the project interpreter for future scans. |
| 2026-08-15 | Research inventory | Existing research covers environment audits, hook ports, frontend Stylelint, and package assurance, but no repository-wide exception ledger. | Create this ledger and preserve the prior research as supporting evidence. |
| 2026-08-16 | R10 | Ruff selected 264 files after removal: 252 Python and 12 TOML; no Markdown paths appeared. `git diff --check` passed. | Remove the inert `extend-exclude = ["*.md"]` setting. Markdown remains owned by Markdownlint. |
| 2026-08-16 | M08 | At pinned markdownlint-cli2 0.23.2, `**/worktrees/**` covers `.owlbear/delivery/worktrees/**`; the current worktree category contains no Markdown. Root/seed drift was also observed. The focused parity test passes with 11 tests, Ruff check/format, and `git diff --check`. | Add the explicit root CLI2 entry and retain a normalized root/seed parity contract. Preserve exclusion-category semantics for M09. |
| 2026-08-17 | M09 / `.owlbear/completed` | The path is absent and empty. Removing it from all six scope authorities produced no local or Markdownlint findings; MegaLinter reported 114 Markdown files with zero Markdownlint errors, while its unrelated overall formatter gate remained non-zero. Delivery completed-history code reserves the path for machine-managed records. | Restore and retain the exclusion as `validated-keep`; continue M09 with the remaining categories one at a time. |
| 2026-08-17 | M09 / `.owlbear/sources` | The root contains one authored Markdown document totaling 589,420 bytes. Exposing it made manual/pre-commit Markdownlint analyze the file and report one MD037 finding; the CI-equivalent MegaLinter run analyzed it and reported five Markdownlint findings overall with no unrelated failures. No runtime producer or consumer references were found. | Keep the exclusion provisionally and classify the authored sources decision as deferred; repair the source-format findings, then remove the broad exclusion. |
| 2026-08-17 | M09 / `.owlbear/target` | The root is absent and empty. Delivery loading and migration tooling reserve it for runtime or retired state, while seed Markdownlint profiles intentionally omit the category. The representative `.owlbear/target/runtime.md` contract protects root bare/CLI2, pre-commit, and MegaLinter exclusions without changing the seed profile. | Retain the target exclusion as a `validated-keep` and preserve the documented seed omission. |
| 2026-08-17 | G03 | MegaLinter v10.0.0 documents `list_of_files` as Markdownlint's default and states that project mode cannot use MegaLinter regex filters. The pinned run invoked markdownlint v0.49.1 with an explicit list of 114 files and returned zero Markdownlint errors. | Retain the explicit `list_of_files` setting as a `validated-keep`; no configuration change. |
| 2026-08-17 | P01 | Removing only the pre-commit top-level `exclude` caused the no-fix local aggregate to fail in EditorConfig. The focused probe reported 26 `.owlbear/legacy/target-cutover/kanban/content/archive/` paths with 2,480 errors; every path was covered by the removed exclusion. Restoring the block made `lint-editorconfig` pass. `tests/test_linter_formatter_policy.py` now compares representative shared exclusions and included controls against MegaLinter. | Retain the top-level exclusion as a `validated-keep` and add the parity regression contract. |
| 2026-08-17 | P02 | Removing only the two PDS hook exclusions made `uv run lint --no-fix` pass with no reported PDS findings. The generated asset producer downloads version-pinned runtime files for offline use, and `.editorconfig` marks the path as minified vendor output with whitespace and final-newline checks unset. Restoring the exclusions and rerunning the no-fix aggregate passed. | Retain both hook-specific exclusions as a `validated-keep`; no additional policy change. |
| 2026-08-17 | P03 | Removing only the pre-commit PDS exclusion made `uv run lint-editorconfig` pass with no PDS findings. Removing `--disable-indent-size` from both the pre-commit hook and MegaLinter argument produced 315 Python-only left-padding errors across `.owlbear`, `seed`, `setup`, `serve`, and `tests`. Restoring both settings made `uv run lint-editorconfig` pass. | Retain the PDS exclusion as a machine-managed boundary and retain the shared `--disable-indent-size` suppression as a `validated-keep`. |
| 2026-08-17 | P04 | Direct no-fix ESLint probes passed for the retained local `src`/`e2e` directories and for the CI-only `serve/cockpit/web/vitest.setup.ts`. The local hooks use the same `src`/`e2e` file trigger, run both directories with `pass_filenames: false`, and MegaLinter's filter remains the broader Cockpit `*.ts`/`*.tsx` superset. `tests/test_linter_formatter_policy.py` now protects these representative scope relationships. | Retain the local `src`/`e2e` scope as a `validated-keep`; accept the documented root setup-file local/CI difference and keep CI authoritative for it. |
| 2026-08-17 | P05/G05 | The current package CSS inventory contains three tracked authored files, all under `serve/cockpit/web/src/`; `npm --prefix serve/cockpit/web run lint:css` passed with no findings. The local package script and all three pre-commit Stylelint hooks already use the `src` boundary. MegaLinter's broader `web/.*\.css` filter was narrowed to the same boundary, and the policy test now protects source, future generated, and compiled-output controls. | Retain the local `src` scope and narrow MegaLinter to authored `src` CSS as validated keeps. |
| 2026-08-17 | P06 | The project typecheck passed with no diagnostics. `tsconfig.json` includes `src`, `vite.config.ts`, and `vitest.setup.ts`, while the original manual hook trigger matched only `src`. The trigger was expanded to those exact three inputs, and `tests/test_linter_formatter_policy.py` now protects the pattern and include list; E2E and Playwright config remain outside this project. | Retain the manual whole-project check and align its trigger with all declared TypeScript project inputs as a `validated-keep`. |
| 2026-08-17 | G04 | Removing only `TYPESCRIPT_ES_FILTER_REGEX_INCLUDE` broadened the descriptor to 75 TypeScript files and exposed one warning in the sole tracked TypeScript file outside Cockpit: the intentional `tests/fixtures/delivery-authority/forbidden-cockpit.ts` fixture. The broadened run also had an unrelated Ruff-format finding. Restoring the filter made the no-fix run report no TypeScript findings and omit the fixture. | Retain the Cockpit-only TypeScript filter as a `validated-keep`; the repository-wide expansion adds fixture noise without improving product coverage. |
| 2026-08-17 | G06 | Removing only `HTML_HTMLHINT_FILTER_REGEX_INCLUDE` made HTMLHint analyze two files: the intended `serve/cockpit/web/index.html` and the minimal `.owlbear/scripts/export-diagrams/render.html`. The latter produced `html-lang-require` and `title-require` errors because the Cockpit `.htmlhintrc` was applied outside its ownership boundary. Restoring the filter left one HTML file, and the local `npm --prefix serve/cockpit/web run lint:html` check passed with no errors. | Retain the Cockpit-only HTML filter as a `validated-keep`; broadening applies the wrong policy to an OwlBear support page. |
| 2026-08-17 | G07 | Removing only `ACTION_ACTIONLINT_FILTER_REGEX_INCLUDE` left Actionlint with five analyzed files and zero findings; those five files are exactly the tracked `.github/workflows/*.yml` files. The restored-filter run produced the same five-file, zero-finding result. Yamllint also remained clean across 44 files; the only overall-run failure was unrelated Ruff-format output. | Retain the workflow-only Actionlint filter as a `validated-keep`; it is an explicit defense-in-depth boundary even though Actionlint's native discovery currently produces the same effective file set. |
| 2026-08-17 | G08 | The disposable replacement simulation used ESLint 10.7.0 and `@eslint/json` 2.0.1. Broad extension discovery linted 564 files and exposed only the empty machine-managed delivery authority; the translated root/recursive exclusion set reduced the scan to 97 files with zero findings and included both `.vscode` JSONC files plus `.markdownlint-cli2.jsonc`. The implemented package command passed, and `tests/test_linter_formatter_policy.py` plus `serve/tools/tests/test_quality.py` passed with 32 tests. | Remove `JSON_JSONLINT`; make `@eslint/json` the sole JSON/JSONC authority through the root flat config, local quality wrapper, pre-commit hook, and `JAVASCRIPT_ES` MegaLinter descriptor. |
| 2026-08-17 | G09 | Removing `--disable-indent-size` from MegaLinter and `-disable-indent-size` from pre-commit produced 315 Python-only left-padding findings across `.owlbear`, `seed`, `setup`, `serve`, and `tests`, including intentional indentation inside documentation strings. Restoring both consumers passed `uv run lint-editorconfig`, `uv run pre-commit run editorconfig-checker --all-files`, and the pinned `ENABLE_LINTERS=EDITORCONFIG_EDITORCONFIG_CHECKER uv run megalint --no-fix` container check; the focused policy contract passed 7 tests. `.editorconfig` and Ruff continue to assign Python indentation ownership to Ruff. | Retain the shared indentation suppression as a `validated-keep` and add a regression contract requiring both local and MegaLinter consumers to preserve the delegation. |
| 2026-08-17 | G01 fresh re-probe | The global filter covers tracked archived/managed categories (`.owlbear/legacy`, Delivery state, Memory, sources, and knowledge records) and also tracked authored documents such as `.owlbear/ideas.md`, the active research ledger, and `.owlbear/sources/overview.md`. No source/setup consumer evidence justified treating all authored members as machine-managed. | Keep the managed/archive/database members excluded, but leave the authored research/source/control boundary as `needs-scan`; do not broaden or delete the global filter until that document class has its own policy. |
| 2026-08-17 | G02 fresh re-probe | Every directory entry is untracked present output, cache, dependency, virtual environment, report, or managed worktree state; no authored false-positive directory was found. | Retain the global directory filter as a `validated-keep`. |
| 2026-08-17 | G03 fresh re-probe | The actual `uv run lint-markdown --no-fix` hook passed. MegaLinter Markdownlint remains in `list_of_files` mode, which is the mode that permits the global path filter to apply. | Retain explicit `list_of_files` mode as a `validated-keep`. |
| 2026-08-17 | G04 fresh re-probe | Cockpit TypeScript is the CI-owned surface; local hooks intentionally trigger only on `src` and `e2e`, while project-level setup TypeScript remains in the CI superset. The only tracked TypeScript outside Cockpit is an inert fixture. | Retain the Cockpit-only MegaLinter include and narrower local hook scope as `validated-keep` boundaries. |
| 2026-08-17 | G05 fresh re-probe | Authored CSS is confined to Cockpit `src`; the package no-fix Stylelint check passed. Generated public assets and compiled `dist` CSS are outside the authored configuration. | Retain the authored-`src` CSS filter as a `validated-keep`. |
| 2026-08-17 | G06 fresh re-probe | The package no-fix HTML check passed and only Cockpit `index.html` is owned by the Cockpit HTML policy. The OwlBear diagram-render support page is a separate surface. | Retain the Cockpit-only HTML filter as a `validated-keep`. |
| 2026-08-17 | G07 fresh re-probe | `uv run lint-actions` passed. The explicit filter matches the five tracked GitHub workflow files and excludes unrelated YAML support files. | Retain the workflow-only Actionlint filter as defense-in-depth. |
| 2026-08-17 | G08 fresh re-probe | `uv run lint-json` passed with the root `@eslint/json` authority covering JSON and JSONC descriptors, including `.vscode` files; generated and machine-managed paths remain excluded. | Retain the resolved single JSON/JSONC authority; no further scope change. |
| 2026-08-17 | G09 fresh re-probe | `uv run lint-editorconfig` and the all-files pre-commit EditorConfig check passed. `disable-indent-size` delegates Python indentation to Ruff while leaving other EditorConfig checks active. | Retain the shared indentation delegation as a `validated-keep`. |
| 2026-08-17 | P01 fresh re-probe | Removing only the pre-commit top-level exclusion admitted the archived legacy tree to generic hooks; the current exclusion preserves the same effective taxonomy as MegaLinter for shared representative paths. | Retain the top-level exclusion as a `validated-keep`; resolve only the authored G01 members separately. |
| 2026-08-17 | P02 fresh re-probe | The PDS tree is generated, version-pinned vendor output. Raw whitespace/EOF checks and both no-fix formatter probes were clean; the hook-specific exclusions prevent mutation of that producer-owned tree. | Retain both PDS exclusions as `validated-keep` boundaries. |
| 2026-08-17 | P03 fresh re-probe | The EditorConfig hook passed with the PDS exclusion and `-disable-indent-size`; the latter avoids duplicate Python indentation findings while preserving style checks for other file classes. | Retain the PDS exclusion and indentation delegation. |
| 2026-08-17 | P04 fresh re-probe | Local ESLint hooks remain `src`/`e2e` triggers with `pass_filenames: false`; MegaLinter checks the broader Cockpit TypeScript superset, including `vitest.setup.ts`. The project-level difference is intentional CI authority, not a missed local source directory. | Retain the local ESLint scope as a `validated-keep`. |
| 2026-08-17 | P05 fresh re-probe | All three Stylelint hooks, the package command, and MegaLinter use authored Cockpit `src` CSS. `uv run lint-cockpit-style --no-fix` passed; generated public/dist output is excluded. | Retain the authored-`src` Stylelint scope as a `validated-keep`. |
| 2026-08-17 | P06 fresh re-probe | The manual typecheck hook pattern covers every `tsconfig.json` input (`src`, `vite.config.ts`, and `vitest.setup.ts`) and excludes E2E/Playwright-only files. `uv run typecheck-cockpit` passed. | Retain the manual whole-project typecheck trigger as a `validated-keep`. |
| 2026-08-17 | P07 fresh re-probe | Configuration validation passed. The MegaLinter hook is manual-only, always-run, and passes no filenames because it invokes a project-wide pinned container scan; normal commits cannot start Docker accidentally. | Retain manual-only, always-run, and `pass_filenames: false` behavior as `validated-keep`. |
| 2026-08-17 | M01 | An isolated `MD013`-enabled diagnostic reported widespread historical line-length debt across the Markdown corpus. The rule was restored to disabled and the normal Markdownlint policy remained clean apart from unrelated existing findings. | Keep `MD013` disabled as a deferred policy decision; the old EditorConfig delegation rationale is invalid, and no Markdown-specific length contract has been selected. |
| 2026-08-17 | M09 reconciliation | The category studies and representative-path contracts cover every category named by M09, including broad worktree coverage. | Keep managed/archive categories as validated boundaries; leave authored research and sources deferred for separate policy and remediation decisions. |
| 2026-08-17 | Y01-Y02 / F01-F08 / G01-G02 | The grouped post-fix local checks passed: yamllint, EditorConfig, ESLint, TypeScript, Stylelint, HTMLHint, and the Cockpit production build. The selected MegaLinter run exited 0 with 44 YAML, 74 TypeScript, 3 CSS, 1 HTML, 925 EditorConfig, and 18 JSON/JSONC files analyzed. | Retain the current YAML delegation, frontend ownership boundaries, and MegaLinter global/directory filters as validated keeps; no scope broadening or stricter rule activation. |
| 2026-08-17 | Y/F/G post-fix repair | The first grouped CI-equivalent pass exposed only final-newline/trailing-whitespace defects in four newly added working-tree files. The repository whitespace and EOF fixers plus one extra-blank-line repair cleared those files; the final EditorConfig pass analyzed 925 files with zero errors. The later M03/M05/M06/M07 pass removed the remaining Markdown findings in the active 118-file scope. | Keep the four controlled formatting repairs; record Markdown remediation under M03/M05/M06/M07 rather than treating it as Y/F/G scope. |
| 2026-08-17 | X03 | The root `.vscode/settings.json` retained a global `esbenp.prettier-vscode` fallback after the root Prettier policy files were removed, while the seed settings already had no such fallback. Removing only the global key preserved all explicit language-specific formatter mappings; setup initialization passed and the policy contract now prevents reintroduction. | Remove the global formatter fallback; keep formatter ownership decisions language-specific and evaluate them separately under X04. |
| 2026-08-17 | X04 | The explicit VS Code formatter matrix maps Python to Ruff, Markdown to the markdownlint extension, JSON/JSONC to VS Code's built-in language formatter, and PowerShell, TOML, and XML to their language extensions. Ruff, Markdownlint, and JSON/JSONC repository authorities remain separate lint/format contracts; the latter three mappings are editor-only conveniences. A focused settings contract now protects all seven mappings. | Retain the explicit language-specific formatter matrix as a `validated-keep`; do not add a global fallback. |

### Hook probe detail

The ten files under `.owlbear/hooks/*.py` and `seed/.owlbear/hooks/*.py` match `HEAD`. The
project's `uv` interpreter is the authoritative runtime because the repository requires Python
3.14+ and all Python quality commands use `uv run`. The system `/usr/bin/python3` result must not
be used to schedule hook repairs unless it is first shown to be the supported runtime.

## 8. Verification Checklist

- [x] Existing research was searched before creating this ledger.
- [x] Root `.prettierrc` and `.prettierignore` were removed without touching unrelated files.
- [x] No unrelated lint or formatter rule was changed outside the audit queue.
- [x] Every active authority has an inventory entry and a consumer boundary.
- [x] Global Ruff exceptions and per-file codes are individually named.
- [x] Markdownlint, EditorConfig, yamllint, MegaLinter, pre-commit, TypeScript, ESLint,
  Stylelint, and HTMLHint scope boundaries are recorded.
- [x] The hook interpreter discrepancy is recorded with the supported-runtime resolution.
- [x] G08 has one JSON/JSONC authority with local, pre-commit, and MegaLinter consumers.
- [x] G09's shared Python indentation delegation is covered by a local/CI regression contract.
- [x] R01's Ruff formatter-conflict ignore is explicit and covered by a regression contract.
- [x] R02-R22 have evidence-backed resolved or validated-keep decisions; repository-wide Ruff and format checks pass.
- [x] M09's `.owlbear/delivery/packages` exclusion is covered across root, seed, pre-commit, and MegaLinter consumers.
- [x] M09's `.owlbear/delivery/runtime` exclusion is covered across root, seed, pre-commit, and MegaLinter consumers.
- [x] M09's scoped `.owlbear/delivery/worktrees` duplicate is removed while broad worktree coverage remains protected.
- [x] M09's generated `.owlbear` index exclusions are covered across root, seed, pre-commit, and MegaLinter consumers.
- [x] M09's `.owlbear/legacy` exclusion is covered across root, seed, pre-commit, and MegaLinter consumers.
- [x] M09's `.owlbear/memory` exclusion is covered across root, seed, pre-commit, and MegaLinter consumers.
- [x] M09's `.owlbear/research` exclusion is covered across root, seed, pre-commit, and MegaLinter consumers.
- [x] M09's `.owlbear/sources` exclusion is covered across root, seed, pre-commit, and MegaLinter consumers.
- [x] M09's `.owlbear/target` runtime exclusion is covered across root, pre-commit, and MegaLinter consumers, with the documented seed omission preserved.
- [x] M03's ordered-list repairs and `style: one_or_ordered` policy pass the isolated rule probe.
- [x] M05's 14 labeled fences and enabled `MD040` policy pass the 118-file Markdownlint scope.
- [x] M06's frontmatter-aware title policy, Ideas hierarchy, and titled governance fixtures pass root CLI2 and bare Markdownlint.
- [x] M07's safe-fix and residual table normalization pass root CLI2, bare Markdownlint, focused policy tests, and MegaLinter Markdownlint.
- [x] X03 has no repository-wide Prettier fallback; language-specific formatter mappings remain explicit.
- [x] X04's language-specific formatter matrix is explicit and covered by a regression contract.
- [x] The grouped Y01-Y02 checks validate yamllint and EditorConfig ownership with no findings.
- [ ] The grouped F01-F08 checks validate ESLint, TypeScript, Stylelint, HTMLHint, and build boundaries; F04 remains under review.
- [x] G02-G09 and P01-P07 have fresh individual scope probes with validated-keep or resolved decisions; G01's authored control/research/source members remain explicitly under review.
- [x] M01's MD013 diagnostic is recorded and its Markdown ownership decision is re-evaluated as deferred.
- [x] Complete the M08 parity cycle and record its focused verification before starting M09.
- [ ] Run the first baseline no-fix scans and attach outputs under `.owlbear/scratch/`.
- [x] Re-run the final relevant local and CI-equivalent no-fix checks after the M03/M05/M06/M07 queue is complete.

## 9. Change Log

| Date | Change |
|---|---|
| 2026-08-15 | Removed obsolete root Prettier configuration and ignore files. |
| 2026-08-15 | Added this durable exception-audit ledger; no remediation decisions were applied. |
| 2026-08-16 | Removed Ruff's inert Markdown exclusion and recorded R10 as resolved. |
| 2026-08-16 | Added Markdownlint root/seed parity protection and recorded M08 as resolved; M09 remains next. |
| 2026-08-17 | Added ownership-aware Docker runtime recovery to the MegaLinter wrapper; P07 remains `needs-scan`. |
| 2026-08-17 | Live stopped-engine probe confirmed the wrapper started OrbStack, recovered Docker, and completed `uv run megalint --no-fix` with exit 0. |
| 2026-08-17 | P07 experiment removed only `always_run`, confirmed full-scan behavior and no-applicable-file skipping, then restored the hook and recorded a validated keep. |
| 2026-08-17 | Replaced MegaLinter `JSON_JSONLINT` with the shared `@eslint/json` JSON/JSONC authority, wired local quality and pre-commit consumers, and verified the pinned `JAVASCRIPT_ES` container path. |
| 2026-08-17 | Recorded G09 as a validated keep: Ruff owns Python indentation while EditorConfig continues checking other formatting dimensions. |
| 2026-08-17 | Relocated the repository-wide JSON lint command to the root `package.json`; removed the Cockpit package duplicate and made pre-commit call the root command. |
| 2026-08-17 | Removed the global VS Code Prettier fallback and recorded X03 as resolved; X04 remains queued for language-specific formatter review. |
| 2026-08-17 | Validated and retained the explicit VS Code language formatter matrix for X04; repository-backed and editor-only mappings are documented separately. |
| 2026-08-17 | Implemented the Ruff R02-R22 audit: removed global `S101`/`SIM108` waivers, narrowed `N818` and test exceptions to exact scopes, fixed ordinary findings, and verified repository-wide Ruff and formatter checks. |
| 2026-08-17 | Replaced the remaining exact test-filename Ruff ignores with code-local directives. Retained directory-wide test and inert-fixture policies; used file-local directives for high-volume acceptance/white-box patterns and line-local `# noqa` markers for isolated findings. The complete `tests` and `serve/*/tests` Ruff surface passes. |
| 2026-08-17 | Removed empty `__init__.py` markers from root and package test directories after pytest imported multiple test trees as the shared `tests.test_*` namespace. Added a policy regression for non-package test roots and retained root `INP001` alongside the existing package-test scope. Package collection now reports 999 tests without import errors. |
| 2026-08-17 | Implemented M03, M05, M06, and M07: repaired four ordered-list defects, labeled 14 code fences, enabled frontmatter-aware `MD041`, titled the two governance fixtures instead of excluding them, and normalized 952 `MD060` findings to zero. Root/seed policy parity, focused policy tests, local Markdownlint, and the full MegaLinter run pass. |
| 2026-08-17 | Validated and retained Ruff's global `COM812` ignore for R01; the normal Ruff check and formatter check pass, while an explicit `COM812` probe reports three formatter-conflicting findings. Added a regression contract for the policy. |
| 2026-08-17 | Validated and retained the `.owlbear/delivery/packages` Markdown exclusion as the next M09 category; its mixed machine-managed package boundary produced no package findings when temporarily exposed, and a six-consumer regression contract now protects the exclusion. |
| 2026-08-17 | Validated and retained the `.owlbear/delivery/runtime` Markdown exclusion as the next M09 category; exposing the operational-state root changed neither the 117-file Markdown set nor the findings, and a six-consumer regression contract now protects the exclusion. |
| 2026-08-17 | Removed the redundant scoped `.owlbear/delivery/worktrees` Markdown exclusions while retaining broad `**/worktrees/**` coverage and the pre-commit/MegaLinter directory filters; added a representative-path regression contract for the effective boundary. |
| 2026-08-17 | Validated and retained the generated `.owlbear` index exclusions; manual/pre-commit Markdownlint found 50 unique MD022/MD032 findings in `doc-index.md` when exposed, while the CI-equivalent MegaLinter run included all three indexes without findings. Added a six-consumer regression contract. |
| 2026-08-17 | Validated and retained the `.owlbear/legacy` exclusion through a bounded seven-file study spanning all Markdown-bearing legacy areas; all samples passed with no findings, and a representative-path six-consumer regression contract now protects the historical archive boundary. |
| 2026-08-17 | Validated and retained the `.owlbear/memory` exclusion through a bounded three-state lifecycle study; approved, deleted, and stale samples passed with no findings, and a representative-path six-consumer regression contract now protects the active memory store. |
| 2026-08-17 | Validated and retained the `.owlbear/research` exclusion through a bounded five-document study; three samples produced 17 MD032/MD036/MD047/MD056 findings, and a representative-path six-consumer regression contract now protects the authored research boundary. |
| 2026-08-17 | Validated and retained the `.owlbear/sources` exclusion through a bounded one-document study; manual/pre-commit Markdownlint reported one MD037 finding and the CI-equivalent MegaLinter run reported five Markdownlint findings overall, so the authored source boundary remains excluded and is protected by a representative-path six-consumer regression contract. |
| 2026-08-17 | Validated and retained the `.owlbear/target` exclusion as a machine-managed runtime boundary; the root is absent, its Delivery and migration ownership is documented, and a representative-path contract protects root, pre-commit, and MegaLinter coverage while preserving the seed omission. |
| 2026-08-17 | Closed the grouped Y/F/G pass with explicit local and CI-equivalent evidence; repaired four controlled whitespace/EOF defects and left unrelated Markdown findings unchanged. |
| 2026-08-17 | Reconciled M01 and M09 in the ledger; remaining R/E/M items are deferred for future grouped decisions rather than treated as an automatic repair queue. |
| 2026-08-17 | Re-evaluated closed findings against current authorities and consumers. Retained evidence-backed managed, formatter-conflict, parity, frontend, and editor decisions; reopened M01, authored M09 research/source exclusions and their G01/P01 portions, and F04 config-file ignores. Corrected F05 to record that `--max-warnings 0` rejects warnings. |
| 2026-08-17 | Re-probed G01-G09 and P01-P07 individually. G02-G09 and P01-P07 remain validated keeps or resolved; G01 is narrowed conceptually to managed/archive/database members while authored control, research, and source documents remain deferred for a separate scope policy. |

## 10. MegaLinter Runtime Recovery

The MegaLinter wrapper now checks `docker info` before launching any runtime. On macOS it uses a
fixed candidate list of OrbStack and Docker Desktop, starts only an installed app that is not
already running, polls for Docker readiness for up to 30 seconds, and then runs the existing
container command. `OWLBEAR_DOCKER_STOP_RUNTIME=1` opts into stopping only the app started by that
invocation; the default leaves a recovered runtime running for subsequent commands. The separate
`megalint-clean` image-pruning command was intentionally left unchanged.

The durable tests in `serve/tools/tests/test_megalinter.py` cover ready-engine bypass, startup,
readiness retry, timeout cleanup, pre-existing-runtime protection, opt-in cleanup, cleanup failure
reporting, and non-macOS failure. `uv run pytest serve/tools/tests -q` passed with 232 tests, and
Ruff passed on the touched Python files. A live probe first failed to connect to
`/Users/markus/.orbstack/run/docker.sock`, then `uv run megalint --no-fix` completed with exit 0;
the follow-up `docker info` reported Docker 29.4.0 and OrbStack processes were running. This
validates startup, readiness recovery, and the real MegaLinter invocation. Opt-in shutdown remains
unit-tested but was not exercised in this run.