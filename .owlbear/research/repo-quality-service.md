# Repository Quality Service: Linters, Protected Rules and Exceptions

> **Owning task:** owner request 2026-10-14 (follow-up to overnight decision N2, lint at builder submit)
> **Date:** 2026-10-14
> **Question:** Should OwlBear have a service separate from Delivery that runs a repository's linters and
> formatters, keeps agents from changing lint/format rules and workflows directly, and lets them request
> exceptions that are judged as legitimate or as workarounds? What should it do, through which interfaces, and
> where should it sit?

## 1. Context and Question

delivery-next lints the builder's changed files (ruff check and format check, Biome, ESLint) when the builder
submits. It refuses up to 5 submits per session; later submits pass with `lint-unresolved` (`lint.py`,
`c72ff954e`). Nothing stops a builder from adding `noqa`, editing `[tool.ruff]` ignores or Biome/ESLint config,
or changing `.github/workflows`. `permissions.py` allows every write except hook/signing bypass and force push,
and in VS Code windows Delivery's per-call policy does not apply at all (auto-approve, sandbox off: owner
decisions D2 and D5).

The owner proposed (2026-10-14):
- A separate repository-management service, not part of Delivery, that also runs the linters behind one
  trigger.
- Agents propose rule changes instead of making them.
- A judge decides whether a change is legitimate or a dirty workaround, at global or local scope.
- Possibly MCP features beyond tools, or a quick CLI agent run.

Three inputs were combined: the owner's idea, the assistant's own research, and an independent Sol research.
Sol then reviewed the combined plan; its eleven findings are folded in below.

## 2. Sources Studied

| # | Source | Relevant fact | Limits |
| --- | --- | --- | --- |
| S1 | delivery-next `lint.py`, `results.py`, `permissions.py`, `vscode_adapter.py` (`next/m4-slice1` `c72ff954e`) | Submit-time lint on changed files, no fix mode; the refusal valve lives in `Lint` state owned by `Gate`; builder writes are unrestricted; window sessions run with auto-approve and sandbox off | Read at one commit |
| S2 | `serve/tools/src/owlbear_tools/quality.py`, `quality_runtime.py` | Aggregate `lint`, `quality`, `megalint` commands with safe and unsafe fix modes; tied to the installed repository root | Repository tool; product packages may not import it |
| S3 | [linter-formatter-rule-audit.md](linter-formatter-rule-audit.md) | A manual exception ledger already exists: owning authority, consumers, no-fix probe, status, decision; about 14 authority files | Manual; dated 2026-08-18 |
| S4 | [MegaLinter coding agents](https://megalinter.io/latest/coding-agents/), [runner](https://megalinter.io/latest/mega-linter-runner/), [LLM Advisor](https://megalinter.io/latest/llm-advisor/) | Agent skills check, fix and re-check (max 3 loops); "disabling a linter or a rule always requires your confirmation"; the advisor is advisory and needs review | Docker; judge is a human |
| S5 | [Trunk ignoring issues](https://docs.trunk.io/code-quality/linters/ignoring-issues-and-files), [qlty](https://docs.qlty.sh/) | One trigger for many linters, changed-files and "hold the line" modes; ignore comments; unused-ignore reports; qlty says its CLI makes an MCP server unnecessary for agents | Reasons on ignores are optional |
| S6 | [pre-commit](https://pre-commit.com/), [lefthook](https://lefthook.dev/) | `run --files`/`--from-ref`; `language: fail` forbids files; `check-useless-excludes` | Git-event scoped; bypassable |
| S7 | [Ruff suppression](https://docs.astral.sh/ruff/linter/), [RUF100](https://docs.astral.sh/ruff/rules/unused-noqa/), [PGH004](https://docs.astral.sh/ruff/rules/blanket-noqa/); [ESLint rules config](https://eslint.org/docs/latest/use/configure/rules), [eslint-comments require-description](https://eslint-community.github.io/eslint-plugin-eslint-comments/rules/require-description.html); [Biome suppressions](https://biomejs.dev/analyzer/suppressions/) | Several suppression syntaxes per tool; unused-suppression detection exists in all three; ESLint can require a reason | No Ruff rule found that requires a reason |
| S8 | [CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners), [Danger JS](https://danger.systems/js/) | Required owner review protects merging, not local edits; Danger can fail on modified files in CI | After the fact |
| S9 | [MCP sampling (latest)](https://modelcontextprotocol.io/specification/latest/client/sampling), [elicitation](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation), [prompts](https://modelcontextprotocol.io/specification/2025-11-25/server/prompts) | Sampling is deprecated in the 2026-07-28 spec (SEP-2577: new implementations should not adopt it; it uses the requesting client's model). Prompts are user-controlled templates. Elicitation needs an interactive client | Verified on the spec pages |
| S10 | [Copilot CLI](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/use-copilot-cli) | `copilot -p` runs one prompt non-interactively with `--allow-tool`/`--deny-tool`, `--agent`, `--model`; each run costs credits | Path scoping is heuristic |
| S11 | [OWASP LLM prompt injection cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) | Code comments are an injection channel | — |
| S12 | [architecture.instructions.md](../instructions/architecture.instructions.md), `tests/test_package_boundary.py` | Core library + MCP server topology; product packages must not import repository tools; new edges need the allowlist | — |

No automated rule-exception judge was found **in the prior art investigated** (S4–S8); the search was not
exhaustive (the MCP Registry was not searched).

## 3. Analysis

| Question | Owner idea | Assistant research | Sol research | Combined |
| --- | --- | --- | --- | --- |
| Separate from Delivery? | Yes | Not yet; inside delivery-next first | Yes, small core | Yes: core package; Delivery stays a thin caller |
| One trigger for linters | Yes | Exists already (`quality`, MegaLinter); keep | Fixed commands, structured results | Fast supported-tool runner first; existing suite stays |
| Who decides exceptions | A judge | Judge session, owner for global | Owner; judge advisory only | Owner only in v1; judge advisory in v2; delegation later and only by owner decision |
| Interface | MCP tool, prompts, agent answers, quick CLI run | Library + CLI; judge via short agent run; no sampling | Library + CLI; MCP thin and optional; no mandatory sampling | Library + CLI; judge by short read-only agent run; MCP only on demand; no sampling (deprecated) |
| Enforcement | Agents may not edit rules | Diff guard at submit | Detection + acceptance backstop; prevention needs sandbox | Detection at submit and at the merge gate; SDK prevention only for intercepted file-write calls |

Sol's review corrected the first combined draft. Each fix and the plan step it applies to:

| Finding | Fix | Where |
| --- | --- | --- |
| Approval authority | Approvals come only from host-recorded owner decisions, never from a caller-supplied "approver"; protection is evaluated from the trusted baseline, not the candidate's own policy | Plan steps 3 and 5 |
| SDK enforcement claim | Overstated: the callback sees shell commands but not the file writes they make. It prevents only intercepted file-write calls; everything else is detection | Plan step 6 |
| v0 had no resolution path | v0 is now report-only; refusals start in v1 together with owner approval | Plan step 7 |
| Existing suppressions | Grandfather the baseline; compare effective rule and scope changes rather than added lines; tell real directives from strings | Plan step 1 |
| Approval identity | Bind an approval to the exceptional paths' content transition, the repository and the policy version; a rebase revalidates it, never silently carries it over | Plan step 3 |
| Shared ledger | Unique decision records, revision-checked transitions, explicit publication state, defined freshness at acceptance; local-only without a shared repository | Plan step 3 |
| Extraction contract | Deterministic planning and execution move with their tests; refusal state and logging stay in Delivery; one boundary edge `owlbear_delivery_next → owlbear_quality` | Plan steps 1 and 4 |
| Runner scope | v0 is the fast supported-tool runner; Markdown, YAML, shell, workflow, EditorConfig and HTML checks stay in the existing suite; fix mode deferred | Plan step 1 |
| Valve vs policy | Policy refusals are separate from lint exhaustion and do not count as invalid submits; the merge gate re-checks at the exact head | Plan step 4 |
| Phase consistency | v1 is owner-only and needs no judge; judge orchestration stays outside the core; MCP is demand-triggered | Plan steps 5 and 7 |
| Missing owner questions | Added: rollout strictness, grandfathering, offline approvals, coverage gaps, expiry | Section 4 |

## 4. Recommendation, Confidence, and Limits

**Recommendation (confidence: high on the boundary and the owner-only approval; medium on the enforcement
details until tested):**

1. New core package `serve/quality` (`owlbear_quality`) with its own CLI, separate from Delivery. It knows
   nothing of Changes. It owns:
   - fast check execution for the supported tools on a file set, with structured results;
   - the repository's protected-surface list;
   - diff inspection of suppression and protected-surface changes against a grandfathered baseline;
   - exception and decision records.
2. CLI `owlbear-quality check|inspect|request|show`, JSON output, fixed operations, no passthrough flags. There
   is no agent-usable `decide`: decisions are recorded only by the owner's host or UI.
3. Exception records live in the shared repository beside the backlog. They are revision-checked, carry their
   publication state, and are local-only without a shared repository.
4. delivery-next becomes a thin caller (one new boundary edge):
   - Submit lint runs through the core; the refusal valve, logging and invalid-submit accounting stay in
     Delivery.
   - Policy refusals are not lint refusals and never pass by exhaustion.
   - The builder gets a `request_exception` result tool. The request becomes an owner question on the
     Change.
   - The merge gate re-checks the exact head.
5. Advisory judge in v2: a short non-interactive agent run with read-only tools, bounded time and output, a
   fixed role, and evidence passed as data. If it fails, the request goes to the owner without a
   recommendation. It never approves.
6. Enforcement is stated honestly:
   - SDK steps: prevention for intercepted file-write calls to protected paths; detection for everything
     else.
   - Windows: detection only, while the sandbox stays off (D5).
   - The guarantee covers Delivery-managed merges; other routes need CI or required review.
7. Order:
   - v0: runner extraction and report-only inspection. Useful alone: one CLI, visible new suppressions.
   - v1: refusal, owner decision path, records, merge-gate check.
   - v2: advisory judge.
   - Later, on demand: MCP adapter, delegation categories by owner decision.

**Open owner decisions (to ask before building):**

1. Rollout strictness: report-only first (recommended), or refuse from the start?
2. Grandfather existing suppressions and ignores (recommended), or review them?
3. Which surfaces are protected: lint/format configs, ignore files, workflows, hooks, runner scripts?
4. Do approvals expire (review date), and what happens to approvals made offline or not yet published?
5. Scope: OwlBear's own repository first, or consumer projects from the start?
6. Placement: `serve/quality` with delivery-next importing it (recommended), or delivery-next calling its CLI?
7. Delegation to the judge: deferred (recommended); revisit after v2 data.
8. Timing: after delivery-next M4's open demonstrations (recommended), or now?

**Limits:**

- Prior-art search covered the named tools and spec pages only.
- No prototype was run, so enforcement against shell-made edits and in windows is analysis, not proof.
- MCP elicitation support in VS Code was not verified.
