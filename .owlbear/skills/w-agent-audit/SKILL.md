---
name: w-agent-audit
description: "Workflow: Read-only broad and deep audits of agent authority, loading, structure, and signal quality"
user-invocable: false
---

# Agent Ecosystem Audit

Audit agent customizations as an executable instruction system. The primary question is not whether
text is correct in isolation, but whether the right behavior reaches the right role at the right
time without contradiction or unnecessary context.

## Boundary

This workflow is report-only. The launcher selects VS Code's built-in `agent` mode and omits edit
tools. Terminal access exists only for read-only inspection and validators: record `git status
--short` before the first command and confirm it is unchanged at close. Do not run generators,
formatters, fixes, tests with snapshot updates, or any mutating command. Approved changes become an
implementation package for a normal editing turn.

Two modes share this workflow:

| Mode | Purpose |
|------|---------|
| **Broad Audit** | Find ecosystem-wide conflicts, loading gaps, misplaced authority, and the highest-value deep-audit targets |
| **Deep Audit** | Evaluate one artifact and its minimum sufficient loading cluster, then propose coherent changes |

Select broad mode for the whole ecosystem, a directory, an artifact class, or any multi-file scope.
Select deep mode for one named artifact or path. When the invocation supplies no request, ask one
concise question for the whole ecosystem, a scope, or a specific target before scanning.

Memory curation belongs to `/memory-audit`. Mention a memory handoff only when direct evidence shows
that stored guidance conflicts with the audited definition; do not inventory memories speculatively.

## Setup, Authority, And Evidence

Audit only active customization source in the current workspace:
`.github/copilot-instructions.md`, `share/{agents,skills,instructions,prompts}/`, and
`.owlbear/{agents,skills,instructions,prompts}/` when present. The active VS Code customization
roots are `share/` and `.owlbear/`; `.github/skills/session-review/` is auxiliary session-review
tooling and is outside this audit unless the request names it explicitly. Inspect other `.github/`
files only when the audit scope names them. Never inspect or compare sibling, installed, or
otherwise externally loaded customization trees. Discover actual local files rather than assuming
every directory exists.

Load only what the selected scope needs:

1. `share/README.md` for the loading model and current ecosystem inventory.
2. `share/WIRING.md` for declared consumers and delegation paths.
3. `share/skills/h-agent-structure/SKILL.md` for file-type and structural conventions.
4. The target files and their actual loading relationships.
5. Domain authorities such as `r-pipeline-protocol` only when the audited claim depends on them.

Existing standards are evidence, not untouchable truth. When a prompt and skill disagree, determine
which behavior best serves the system. Recommend changing the named authority, both consumers, or a
third location when that produces a clearer single source of truth. Never make files agree by
silently preserving the weaker rule.

Judge claims in this order:

1. Current frontmatter, tool boundaries, references, hooks, and executable validators.
2. Current authority files and documented loading model.
3. Current consumers and observed workflow behavior.
4. Git history, archived tasks, or research only when testing a staleness or usage claim.

Label evidence `observed`, `documented`, or `inferred`. Use `high`, `medium`, or `low` confidence;
decimal confidence implies precision the audit does not have.

## Effective Instruction Surface

For every material rule, build this working map:

| Rule or decision | Current authority | Consumers | Loading mechanism and time | Conflict or gap |
|------------------|-------------------|-----------|----------------------------|-----------------|

Map the applicable project and `applyTo` instructions, prompt, agent, required and triggered
companion skills, hooks, and tool allowlists.

A rule is mistimed when it loads for roles that rarely need it, is absent when a role normally needs
it, or arrives only after the decision it is meant to control. Required reading should represent
roughly 90% use; situational knowledge should remain on demand.

## Finding Admission

Accept a finding only when evidence supports at least one concrete condition:

- two active instructions prescribe incompatible behavior;
- a required behavior has no reliable loading or ownership path;
- duplicated guidance creates drift or material context cost;
- content is in the wrong artifact type or authority layer;
- structure, references, frontmatter, tools, hooks, or delegation violate an executable contract;
- stale or speculative guidance is contradicted by current source or verified usage.

Separate observed harm from theoretical risk. A hypothetical concern without a concrete failure
path is context, not an actionable finding.

Instruction text earns its context cost when it:

- supplies a project fact that cannot be recovered cheaply at the decision point;
- assigns authority, ownership, routing, loading, tools, safety, or an output contract;
- intentionally overrides a common model default;
- prevents an observed recurring failure;
- preserves a non-obvious procedural dependency whose omission changes the result.

Generic trained knowledge, framing, repeated conditionals, examples, templates, and historical
cautions are presumptive noise when they add no local choice, branch, constraint, or evidenced
failure guard. Correctness alone does not earn context cost, but model familiarity alone does not
justify deletion: retain concise reinforcement for observed recurring failures such as excess scope
or low-value tests. Ask: **if this block disappeared, which decision would change?** If none, compress
or delete it.

For duplication or context-cost findings, report the affected block or loading cluster's approximate
word count, loading tier or timing, and direct-consumer count. Estimate removable words only after
classifying concrete blocks; use measurements for impact and priority, never as a finding threshold,
quota, or tokenizer-precision exercise.

### Temporal Narration Test

In audited agents, skills, instructions, and prompts, treat migration stories, milestone or
task IDs, superseded behavior, prior implementation details, and future-phase framing as presumptive
noise. This includes indirect framing such as a later phase, migration point, or post-cutover state;
it is not a lexical test for words such as "until" or "pending". Ask whether a presently observable
condition changes a consumer action now.

- If it does, state the current condition and action directly. Retain an identifier only when the
   consumer must resolve it to decide or act.
- If it does not, delete the narration or move it to its planning, task-history, decision, research,
   or test authority.

Do not apply this presumption to artifacts whose purpose is planning or history. Historical truth
alone does not justify runtime context cost. Current loop stop conditions and named data states are
operational contracts, not temporal narration.

### Rewrite Conservation

Before proposing a rewrite, classify the affected section or behavioral block as `keep`,
`strengthen`, `compress`, `move`, or `delete`. `Strengthen` makes an obligation more explicit or
prominent without changing its scope. For every action except `keep`, map the block's authority,
routing, safety, timing, scope, imperative force, exceptions, evidence, and output obligations to
surviving text and its loading path.

Reject rewrites that merge materially different conditions, weaken imperative force, change scope,
or leave a load-bearing obligation implied. Apply this test to the changed block, not the whole
ecosystem; use sentence-level tagging only to resolve a specific ambiguity.

When the block controls operations, extend the map with:

| Condition or decision point | Tool, delegate, hook, or validator | Required arguments and ordering | Results, retries, recovery, and stop behavior | Surviving owner and loading path |
|-----------------------------|------------------------------------|---------------------------------|---------------------------------------------|----------------------------------|

Inventory only affected operations, including prose that changes whether, when, or how they run.
Use separate rows when conditions change an operation or its arguments. Preserve every argument,
ordering dependency, result branch, retry, recovery action, and stop condition. Remove an operation
from the target only when another authority defines the complete obligation and reliably loads
before the decision; otherwise the explicit call remains. Name the surviving owner and loading path
in the finding or implementation package.

## Shared Audit Dimensions

Apply the gates above across five dimensions: coherence and timing; authority and duplication;
structure and execution; signal quality at the actual loading frequency; and completeness and
currency.

## Broad Audit

Use broad mode to identify patterns and priorities, not to deeply rewrite every file.

1. Resolve the selected scope. For the whole ecosystem, inspect the complete local customization
   roots defined above.
2. Discover current files and counts; do not copy catalog counts from a prompt.
3. Run the read-only validators documented by the ecosystem when available. In this repository,
   start with `uv run python .owlbear/scripts/validate_agents.py`,
   `uv run python .owlbear/scripts/validate_skills.py`, and
   `uv run python .owlbear/scripts/validate_prompts.py`; use Markdownlint or `git diff --check`
   only when relevant. If a validator is absent or fails to run, record the command and result under
   Coverage, then continue with source inspection. Validator output is evidence, not the entire
   audit.
4. Build a metadata-level loading map from frontmatter, `required_reading`, `applyTo`, prompt agents,
   tool lists, hooks, and `WIRING.md`.
5. Prioritize full body reads for:
   - conflicting or missing loading paths;
   - universal and high-consumer authorities;
   - unusually large required-reading chains;
   - duplicate rule phrases or stale references;
   - files implicated by validator or wiring mismatches.
   For context-cost candidates, prefer high-frequency and high-consumer surfaces over raw file size.
6. Apply the Shared Audit Dimensions to those evidence-backed candidates.
7. Group findings by the authority change that resolves them.

Return:

### Coverage

- scope and local roots inspected;
- validators run and unavailable checks;
- files read fully versus mapped from metadata;
- material evidence limits.

### Ranked Findings

| Severity | Finding | Authority and consumers | Evidence | Impact | Recommendation |
|----------|---------|-------------------------|----------|--------|----------------|

Use `high` only for routing, loading, safety, silent-failure, or direct-conflict defects. Use
`medium` for structural and authority problems with credible behavioral cost. Use `low` only when a
small cleanup has concrete context or maintenance value; omit cosmetic observations.

### Deep-Audit Priorities

Rank unresolved targets by instruction frequency, consumer count, cluster size, conflict risk, and
likely removable context. Explain the ranking without synthetic scores.

## Deep Audit

Use deep mode for one agent, skill, instruction, prompt, or workspace-instruction target. Infer the
artifact type from source; ask for clarification only when two live targets match.

### Build The Minimum Sufficient Cluster

| Target | Load |
|--------|------|
| Agent | Agent body, required skills, invoking prompts, matching instructions, and behavior-changing companions |
| Skill | Skill body, representative direct consumers, and immediate authorities or companions needed to resolve claims |
| Instruction | Instruction body, its `applyTo` surface, and representative affected roles or files |
| Prompt | Prompt body, selected agent, explicit skill references, and inherited instruction surface relevant to the command |
| Workspace instructions | Instruction body plus representative high-impact consumers and narrower authorities it may conflict with |

Do not load every reachable file by default. Expand one hop only when needed to resolve authority,
timing, contradiction, or behavioral impact. For large consumer sets, sample the heaviest and most
different consumers, then report the sample and total set.

### Analyze Behavioral Blocks

For each section or coherent block, determine:

1. Which consumer decision it changes and at what workflow step.
2. Whether this target is the fit authority and loading tier.
3. Whether another loaded block duplicates or contradicts it.
4. Whether it passes the Steering Value Test.
5. Whether to keep, compress, delete, move, or revise the authority itself.

### Return One Coherent Finding Set

1. **Effective surface** - files loaded, consumers sampled, loading path, authorities, and evidence limits.
2. **Findings** - conflicts and missing behavior first, then structural and compression findings.
3. **Retained content** - non-obvious blocks explicitly worth their context cost.
4. **Recommendations** - intended direction and affected authority without detailed edit design.

Each finding needs evidence, authority, impact, recommendation, and confidence. Add options only for
a material user decision; do not split one structural decision into sentence-level approvals.

## Implementation Handoff - Second Pass Only

Produce implementation-ready packages only when the user selects findings or requests them with the
audit.

An implementation package must be usable without rerunning the audit:

- exact affected files and current authority;
- conflict, loading gap, or noise being removed;
- selected authority and expected consumer behavior;
- smallest coherent edit and explicitly excluded adjacent work;
- references, validators, or focused checks that should prove the change.

After approval, use a normal editing turn and re-read current source. An exhausted report is a valid
terminal condition; do not force another command or confirmation.
