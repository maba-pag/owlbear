# Linter and Formatter Exception Audit

> **Owning work:** repository lint and formatter policy audit
> **Date:** 2026-08-15
> **Status:** Ledger initialized. Prettier policy files removed; rule remediation has not started.
> **Question:** Which remaining linter, formatter, scope, and path exceptions have merit, and which should be removed, narrowed, or replaced after evidence is collected one rule at a time?

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

Each ledger item has one owning authority, its consumers, a narrow no-fix command, a finding
classification, a decision, and a recorded focused verification. The next item is not started
until the current item is restored, narrowed, removed, or accepted and its evidence is recorded.

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
| `.vscode/settings.json` | Editor formatter selection and local quality command affordances | The global Prettier formatter is an editor fallback, not a root Prettier config consumer. |
| `.owlbear/hooks/*.py` and `seed/.owlbear/hooks/*.py` | Direct-run hook source and corresponding scaffold copies | These files must be checked with the project interpreter. |
| Prior research: `delivery-operating-model-reframe.md`, `1595-tailwind-stylelint-redundancy.md`, `environment-audit-research-workflow.md`, and hook research files | Existing reasoning about exceptions, frontend linting, environment authority, and hooks | Historical documents may describe older paths or completed work. |

No new external source was required to initialize this ledger. Tool behavior must be confirmed
against the pinned versions and the live repository before a rule is changed.

## 3. Authority Inventory

| ID | Quality surface | Primary authority | Main consumers | Current scope boundary |
|---|---|---|---|---|
| A01 | Ruff lint | `pyproject.toml` `[tool.ruff.lint]` | pre-commit, `uv run lint-python`, MegaLinter | Python project discovery plus per-file ignores |
| A02 | Ruff format | `pyproject.toml` `[tool.ruff.format]` | pre-commit, `uv run format-python`, MegaLinter | Python files selected by Ruff |
| A03 | EditorConfig | `.editorconfig` | pre-commit, MegaLinter, editors | Glob sections and checker arguments |
| A04 | Markdownlint CLI | `.markdownlint.json` and `.markdownlintignore` | MegaLinter, bare markdownlint/manual runs | `MARKDOWN_MARKDOWNLINT_CLI_LINT_MODE: list_of_files` |
| A05 | Markdownlint CLI2 | `.markdownlint-cli2.jsonc` | pre-commit, VS Code extension | CLI2 ignore globs |
| A06 | YAML lint | `.yamllint.yml` | pre-commit, MegaLinter | Root YAML plus explicit legacy ignore |
| A07 | Shell lint | `.pre-commit-config.yaml` hook revision | pre-commit, MegaLinter | Shell files discovered by each consumer |
| A08 | GitHub Actions lint | `.pre-commit-config.yaml` hook revision | pre-commit, MegaLinter | `.github/workflows/*.yml` and `.yaml` |
| A09 | TypeScript ESLint | `serve/cockpit/web/eslint.config.js` | pre-commit, MegaLinter, npm tooling | Cockpit `src` and `e2e` through local hooks; all matching files through CI filter |
| A10 | TypeScript compiler | `serve/cockpit/web/tsconfig.json` | pre-commit manual hook, frontend build | `src`, `vite.config.ts`, and `vitest.setup.ts`, excluding four test patterns |
| A11 | CSS lint | `serve/cockpit/web/.stylelintrc.json` | pre-commit, npm script, MegaLinter | Cockpit `src/**/*.css` |
| A12 | HTML lint | `serve/cockpit/web/.htmlhintrc` and package script | pre-commit, npm script, MegaLinter | Package script checks `index.html`; MegaLinter filter is broader |
| A13 | JSON lint | MegaLinter configuration | MegaLinter | `.vscode/` is excluded because settings are JSONC |
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
| R01 | `COM812` ignored globally | Formatter conflict | needs-scan | Confirm Ruff formatter/check behavior at the pinned version. |
| R02 | `CPY001` ignored globally | No per-file copyright headers | needs-scan | Scan for controlled files where a header is actually required. |
| R03 | `D105` ignored globally | Magic methods inherit behavioral documentation | needs-scan | Scan public magic methods and compare repository documentation policy. |
| R04 | `D107` ignored globally | Constructor docs belong on the class | needs-scan | Check constructors with behavior not explained by class docs. |
| R05 | `ISC001` ignored globally | Formatter conflict | needs-scan | Confirm Ruff formatter/check behavior at the pinned version. |
| R06 | `S101` ignored globally | Assertions are needed in tests | fix-candidate | Prove whether production assertions exist; narrow to test scopes if so. |
| R07 | `SIM108` ignored globally | Explicit branches are often clearer | needs-scan | Sample findings and decide whether the preference belongs in policy. |
| R08 | `N818` ignored globally | Existing `TestFromAC_*` API names | fix-candidate | Identify the exact public names and narrow the waiver if possible. |
| R09 | `line-length = 120` | Shared project limit | needs-scan | Compare findings by source type and existing EditorConfig overrides. |
| R10 | `extend-exclude = ["*.md"]` | Markdown is not Ruff source | needs-scan | Confirm it is inert or remove misleading configuration. |
| R11 | Ruff format `quote-style = "double"` | Repository formatter preference | queued | Run formatter check and compare with generated/vendor boundaries. |

### 4.2 Ruff per-file ignores

The entries are copied from `pyproject.toml`. Codes in one row remain separate work items; the
row identifies the shared scope and the first narrow command to use.

| ID | Scope | Codes currently ignored | Status | First scan boundary |
|---|---|---|---|---|
| R12 | `.owlbear/hooks/*.py` | `C901`, `INP001`, `PLR0912`, `T201` | needs-scan | One hook script at a time under `uv run ruff check`. |
| R13 | `seed/.owlbear/hooks/*.py` | `C901`, `INP001`, `PLR0912`, `T201` | needs-scan | Compare each scaffold hook with its source counterpart. |
| R14 | `.owlbear/scripts/*.py` | `INP001`, `PLR2004`, `PTH201`, `T201` | needs-scan | One direct-run script at a time. |
| R15 | `.github/scripts/*.py` | `INP001`, `T201` | needs-scan | One CI helper at a time, preserving stdout contracts. |
| R16 | `seed/.owlbear/scripts/*.py` | `INP001`, `PLR2004`, `PTH201`, `T201` | needs-scan | Compare scaffold behavior before narrowing. |
| R17 | `.owlbear/scratch/*.py` | `ANN401`, `INP001`, `S603`, `T201` | needs-scan | Confirm scratch files are intentionally outside product proof. |
| R18 | `setup/*.py` | `INP001`, `T201` | needs-scan | Check direct-run setup entry points and stdout contracts. |
| R19 | `serve/*/examples/**/*.py` | `INP001`, `T201`, `EM101` | needs-scan | Check whether examples are shipped, imported, or documentation-only. |
| R20 | `tests/**/*.py` | `ANN`, `D`, `DTZ001`, `E402`, `E501`, `EM102`, `F811`, `I001`, `N801`, `PERF401`, `PLW1510`, `PT001`, `PT011`, `RUF100`, `S101`, `S105`, `S106`, `S603`, `S607`, `SLF001`, `ERA001`, `PLR2004`, `PLR0917`, `PLC0415`, `TCH`, `TRY003`, `PT019`, `F541` | needs-scan | One code against one test scope; preserve generated `TestFromAC_*` contracts where proven. |
| R21 | `tests/fixtures/delivery-authority/**/*.py` | `INP001` | needs-scan | Parse fixture files as data and verify whether Ruff should see them as modules. |
| R22 | `serve/*/tests/**/*.py` | `ANN`, `D`, `DTZ001`, `E402`, `E501`, `EM102`, `F811`, `I001`, `INP001`, `N801`, `PERF401`, `PLW1510`, `PT001`, `PT011`, `RUF100`, `S101`, `S105`, `S106`, `S603`, `S607`, `SLF001`, `ERA001`, `PLR2004`, `PLR0917`, `PLC0415`, `TCH`, `TRY003`, `PT019` | needs-scan | One code against one package test scope. |

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
| M01 | `MD013` | disabled | Markdownlint CLI and MegaLinter | needs-scan |
| M02 | `MD024` | `siblings_only: true` | Markdownlint CLI and MegaLinter | needs-scan |
| M03 | `MD029` | disabled | Markdownlint CLI and MegaLinter | needs-scan |
| M04 | `MD033` | disabled | Markdownlint CLI and MegaLinter | needs-scan |
| M05 | `MD040` | disabled | Markdownlint CLI and MegaLinter | needs-scan |
| M06 | `MD041` | disabled | Markdownlint CLI and MegaLinter | needs-scan |
| M07 | `MD060` | disabled | Markdownlint CLI and MegaLinter | needs-scan |

The bare Markdownlint exclusions are `.owlbear/completed`, `.owlbear/delivery/packages`,
`.owlbear/delivery/runtime`, `.owlbear/delivery/worktrees`, the generated `.owlbear` index
files, `.owlbear/legacy`, `.owlbear/memory`, `.owlbear/research`, `.owlbear/sources`,
`.owlbear/target`, `.venv`, `**/node_modules`, `**/scratch`, `**/test-results`, `**/worktrees`,
and `megalinter-reports`. The CLI2 file expresses the same effective categories with explicit
`/**` globs and relies on `**/worktrees/**` for nested Delivery worktrees. These are M08 and M09:
review the semantic set once per consumer, then verify that the two glob syntaxes remain
behaviorally equivalent where equivalence is intended.

### 4.5 YAML, MegaLinter, and pre-commit scope

| ID | Surface | Current limiter or waiver | Status |
|---|---|---|---|
| Y01 | yamllint | `line-length: disable` because EditorConfig owns text length | needs-scan |
| Y02 | yamllint | `.owlbear/legacy/**` ignored | needs-scan |
| G01 | MegaLinter global filter | Egg-info, generated `.owlbear` records, and audit/knowledge DB files excluded | needs-scan |
| G02 | MegaLinter directory filter | `.benchmarks`, caches, virtualenvs, build/dist, reports, downloads, dependencies, scratch, worktrees, and package artifacts excluded | needs-scan |
| G03 | MegaLinter Markdown | `list_of_files` mode selected so the global filter applies | needs-scan |
| G04 | MegaLinter TypeScript | Include only `serve/cockpit/web/.*\.(ts|tsx)` | needs-scan |
| G05 | MegaLinter CSS | Include only `serve/cockpit/web/.*\.css` | needs-scan |
| G06 | MegaLinter HTML | Include `serve/cockpit/web/.*\.html` | needs-scan |
| G07 | MegaLinter Actionlint | Include only `.github/workflows/*.yml` and `.yaml` | needs-scan |
| G08 | MegaLinter JSON | Exclude `.vscode/` because settings are JSONC | needs-scan |
| G09 | MegaLinter EditorConfig | `--disable-indent-size`; indentation remains checked by Ruff for Python | needs-scan |
| P01 | pre-commit top-level `exclude` | Duplicates generated, archived, vendor, cache, database, and worktree taxonomy | needs-scan |
| P02 | pre-commit whitespace/EOF hooks | Excludes generated PDS assets | needs-scan |
| P03 | pre-commit EditorConfig hook | Excludes generated PDS assets and disables indent-size | needs-scan |
| P04 | pre-commit frontend ESLint | Local hook explicitly covers `src` and `e2e` TypeScript files | needs-scan |
| P05 | pre-commit frontend Stylelint | Local hook covers `src` CSS only | needs-scan |
| P06 | pre-commit frontend typecheck | Manual whole-project command is triggered only by `src` file matching | needs-scan |
| P07 | pre-commit MegaLinter | Manual-only and always-run; no staged-file narrowing | needs-scan |

The duplicated MegaLinter/pre-commit taxonomy is not automatically a defect. The tools use
different path languages and one is a containerized project scan while the other is a hook
dispatcher. The scan must compare effective file sets, not text equality.

### 4.6 Frontend compiler and linter boundaries

| ID | Surface | Current limiter or exception | Status |
|---|---|---|---|
| F01 | TypeScript `include` | `src`, `vite.config.ts`, and `vitest.setup.ts` only | needs-scan |
| F02 | TypeScript `exclude` | `src/**/*.test.ts`, `src/**/*.test.tsx`, `src/**/*.spec.ts`, `src/**/*.spec.tsx` | fix-candidate |
| F03 | TypeScript E2E coverage | Eleven E2E TypeScript files are linted but are not in `tsconfig.json` | fix-candidate |
| F04 | ESLint ignores | `dist`, coverage, Playwright reports, node_modules, generated PDS assets, and config files | needs-scan |
| F05 | ESLint unused-vars | Warnings allowed; underscore-prefixed args/vars ignored | needs-scan |
| F06 | ESLint raw PDS elements | Five custom elements rejected through `no-restricted-syntax` | queued |
| F07 | Stylelint Tailwind | Eight Tailwind at-rules allowed: `theme`, `utility`, `apply`, `source`, `reference`, `variant`, `custom-variant`, `plugin` | needs-scan |
| F08 | HTMLHint package script | Only `index.html` is checked by `lint:html` | needs-scan |

The source-test and E2E split is a priority because a green `tsc --noEmit` result is not proof
for those files. The first scan should compare `eslint`, `tsc`, Vitest, and Playwright ownership
without changing the build contract.

### 4.7 Editor and formatter residue

| ID | Surface | Current state | Status |
|---|---|---|---|
| X01 | Root Prettier config | `.prettierrc` removed in this change | resolved |
| X02 | Root Prettier ignore | `.prettierignore` removed in this change | resolved |
| X03 | VS Code global formatter | `editor.defaultFormatter` still names `esbenp.prettier-vscode` | needs-scan |
| X04 | Language-specific formatters | Python uses Ruff; Markdown uses markdownlint; JSON/JSONC and other languages have explicit formatter settings | queued |

X03 is intentionally not changed here. Removing an editor extension fallback is a separate
policy decision from removing unused repository Prettier files.

## 5. One-Rule Workflow

Use this exact cycle for every `R*`, `E*`, `M*`, `Y*`, `G*`, `P*`, and `F*` item:

1. **Record authority and baseline.** Confirm the setting, its consumers, the affected file set,
   current git status, and the narrow no-fix command. Put long output in `.owlbear/scratch/`.
2. **Deactivate one item only.** Remove one rule, one ignore code, one path, or one scope
   limiter in a temporary working change. Do not combine neighboring entries.
3. **Scan without fixes.** Run the narrowest consumer that can expose the rule's findings. Keep
   the exact command, pinned tool version, affected paths, and exit status.
4. **Classify every finding.** Use exactly one primary class: controlled source defect,
   intentional contract, generated/vendor/machine-managed artifact, archived record, false
   positive/noise, or consumer mismatch.
5. **Choose the smallest durable response.** Fix controlled source; reactivate the rule;
   narrow the exception; modify the rule; or document a validated keep. Do not hide a finding
   with a new broad ignore.
6. **Restore and verify.** Re-enable the rule when the experiment is over, then run the focused
   check with the final configuration and the relevant neighboring consumer if the decision
   changed a shared boundary.
7. **Close the ledger row.** Record the decision, evidence paths, commit or working-tree proof,
   residual risk, and the next queue item. A row is not complete because the scanner is green.

Useful consumer commands are the repository wrappers where available: `uv run lint-python
--no-fix`, `uv run lint-markdown --no-fix`, `uv run lint-yaml`, `uv run lint-editorconfig`,
`uv run lint-cockpit --no-fix`, and `uv run megalint --no-fix`. Use the underlying pinned tool
only when the wrapper cannot isolate the item. Frontend commands live in
`serve/cockpit/web/package.json`; TypeScript scope experiments should use `npx tsc --noEmit
--project serve/cockpit/web/tsconfig.json`.

## 6. Ordered Work Queue

The queue is ordered to expose high-blast-radius scope errors before spending time on cosmetic
exceptions. Every listed rule remains an individual experiment within its group.

1. **Baseline and authority sanity:** R10, M08, M09, G03, P01. Confirm effective file sets and
   remove only inert or duplicated configuration after proof.
2. **Markdown document structure:** M06, M05, M04, M03, M02, M07, then M01. These rules affect
   many authored documents and should be measured with the correct CLI consumer.
3. **YAML and text length delegation:** Y01, Y02, then E01-E05. Check whether delegated length
   ownership produces useful, non-duplicated diagnostics.
4. **Ruff global exceptions:** R06, R08, R02, R03, R04, R07, R01, R05, then R09 and R11.
   Formatter-conflict entries are still recorded even if the pinned tool confirms them.
5. **Ruff scoped exceptions:** R12-R19, then each code in R20-R22 and R21. Test scopes must be
   kept separate from direct-run scripts and fixture data.
6. **Frontend proof boundary:** F02, F03, F04, F05, F06, F07, and F08. Resolve the compiler,
   ESLint, test, and E2E ownership mismatch before changing style rules.
7. **Generated and machine-managed records:** E06-E15 and G01-G02. Inspect representative
   files and producer behavior before considering any waiver removal.
8. **Local/CI parity:** G04-G09 and P02-P07. Compare effective scopes and retained fix behavior,
   then adjust only the consumer whose semantics are wrong.
9. **Editor residue:** X03-X04. Decide whether a default Prettier extension is still a useful
   editor fallback after repository policy no longer uses Prettier.

## 7. Evidence and Decision Log

| Date | Item | Observation | Decision |
|---|---|---|---|
| 2026-08-15 | X01-X02 | No repository quality command or config consumer was found for the root Prettier files; their settings were fallback policy. | Remove both files. |
| 2026-08-15 | Hook syntax probe | `uv run --frozen python` parses all ten root/seed Python hooks. `/usr/bin/python3` reports syntax errors in the same `HEAD` bytes. | Treat as an interpreter/tooling mismatch, not a source defect; use the project interpreter for future scans. |
| 2026-08-15 | Research inventory | Existing research covers environment audits, hook ports, frontend Stylelint, and package assurance, but no repository-wide exception ledger. | Create this ledger and preserve the prior research as supporting evidence. |

### Hook probe detail

The ten files under `.owlbear/hooks/*.py` and `seed/.owlbear/hooks/*.py` match `HEAD`. The
project's `uv` interpreter is the authoritative runtime because the repository requires Python
3.14+ and all Python quality commands use `uv run`. The system `/usr/bin/python3` result must not
be used to schedule hook repairs unless it is first shown to be the supported runtime.

## 8. Verification Checklist

- [x] Existing research was searched before creating this ledger.
- [x] Root `.prettierrc` and `.prettierignore` were removed without touching unrelated files.
- [x] No remaining lint or formatter rule was changed in this initialization step.
- [x] Every active authority has an inventory entry and a consumer boundary.
- [x] Global Ruff exceptions and per-file codes are individually named.
- [x] Markdownlint, EditorConfig, yamllint, MegaLinter, pre-commit, TypeScript, ESLint,
  Stylelint, and HTMLHint scope boundaries are recorded.
- [x] The hook interpreter discrepancy is recorded with the supported-runtime resolution.
- [ ] Run the first baseline no-fix scans and attach outputs under `.owlbear/scratch/`.
- [ ] Complete one rule cycle and record its focused verification before starting the next.
- [ ] Re-run the final relevant local and CI-equivalent no-fix checks after the queue is complete.

## 9. Change Log

| Date | Change |
|---|---|
| 2026-08-15 | Removed obsolete root Prettier configuration and ignore files. |
| 2026-08-15 | Added this durable exception-audit ledger; no remediation decisions were applied. |