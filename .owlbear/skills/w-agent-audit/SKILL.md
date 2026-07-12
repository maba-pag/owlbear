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

The active customization roots are `.github/copilot-instructions.md`, shared definitions under
`share/{agents,skills,instructions,prompts}/`, and project-local definitions under
`.owlbear/{agents,skills,instructions,prompts}/` when present. Discover actual files rather than
assuming every directory exists.

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

Check the effective surface rather than references in isolation:

- project instructions and universal authority files that are always present;
- matching `applyTo` instructions for the files being handled;
- the invoked prompt and selected agent body;
- skills in `<required_reading>`;
- companion skills only on paths that actually trigger them;
- hooks and tool allowlists that enforce or contradict prose.

A rule is mistimed when it loads for roles that rarely need it, is absent when a role normally needs
it, or arrives only after the decision it is meant to control. Required reading should represent
roughly 90% use; situational knowledge should remain on demand.

## Finding Admission And Steering Value

Accept a finding only when evidence supports at least one concrete condition:

- two active instructions prescribe incompatible behavior;
- a required behavior has no reliable loading or ownership path;
- duplicated guidance creates drift or material context cost;
- content is in the wrong artifact type or authority layer;
- structure, references, frontmatter, tools, hooks, or delegation violate an executable contract;
- stale or speculative guidance is contradicted by current source or verified usage.

Separate observed harm from theoretical risk. A hypothetical concern without a concrete failure
path is context, not an actionable finding.

Keep instruction text when it does at least one of these jobs:

- supplies a project fact that cannot be recovered cheaply at the decision point;
- assigns authority, ownership, routing, loading, tools, safety, or an output contract;
- intentionally overrides a common model default;
- prevents an observed recurring failure;
- preserves a non-obvious procedural dependency whose omission changes the result.

Generic trained knowledge is presumptive noise when a capable model would reliably supply it and
the local system does not require a different choice. Correctness alone does not earn context cost.
Ask the counterfactual: **if this block disappeared, which decision would change?** If no concrete
answer exists and no observed failure justifies reinforcement, delete or compress it.

Do not remove a rule merely because a model may know it. Retain concise reinforcement when evidence
shows that models routinely ignore the default, as with minimum-change and test-restraint rules.

Compress or remove framing, trained language/framework knowledge, repeated conditionals, examples,
templates, and historical cautions when they add no branch, constraint, or evidenced failure guard.

Evaluate by section or behavioral block. Sentence-by-sentence tagging is reserved for resolving a
specific ambiguity; it is not a mandatory output.

## Shared Audit Dimensions

1. **Coherence and timing** - compatible rules reach the roles that need them before the decision.
2. **Authority and duplication** - each behavior has one fit source of truth and at most one useful reinforcement.
3. **Structure and execution** - artifact type, frontmatter, tools, hooks, references, and delegation match runtime behavior.
4. **Signal quality** - retained text passes the Steering Value Test at its loading frequency and consumer count.
5. **Completeness and currency** - load-bearing behavior has an owner; stale or speculative behavior is evidenced before removal.

## Broad Audit

Use broad mode to identify patterns and priorities, not to deeply rewrite every file.

1. Resolve the selected scope. For the whole ecosystem, inspect the complete active customization
   roots.
2. Discover current files and counts; do not copy catalog counts from a prompt.
3. Run the read-only validators documented by the ecosystem when available. In this repository,
   start with `.owlbear/scripts/validate_agents.py` and `.owlbear/scripts/validate_skills.py`; use
   Markdownlint or `git diff --check` only when relevant. Validator output is evidence, not the
   entire audit.
4. Build a metadata-level loading map from frontmatter, `required_reading`, `applyTo`, prompt agents,
   tool lists, hooks, and `WIRING.md`.
5. Prioritize full body reads for:
   - conflicting or missing loading paths;
   - universal and high-consumer authorities;
   - unusually large required-reading chains;
   - duplicate rule phrases or stale references;
   - files implicated by validator or wiring mismatches.
6. Apply the Shared Audit Dimensions to those evidence-backed candidates.
7. Group related findings by the authority change that resolves them. Do not emit progressive flags
   or ask for one decision per sentence.

Return:

### Coverage

- scope and active roots inspected;
- validators run and unavailable checks;
- files read fully versus mapped from metadata;
- material evidence limits.

### Ranked Findings

| Severity | Finding | Authority and consumers | Evidence | Impact | Recommendation |
|----------|---------|-------------------------|----------|--------|----------------|

Use `high` only for routing, loading, safety, silent-failure, or direct-conflict defects. Use
`medium` for structural and authority problems with credible behavioral cost. Use `low` only when a
small cleanup has concrete context or maintenance value; omit cosmetic observations.

### Implementation Packages

Group findings that must change together. Each package names files, the authority decision, expected
behavior, smallest coherent change, and validation. Cross-cutting packages may span multiple
clusters when broad evidence is already sufficient; deep audit is not mandatory ceremony.

### Deep-Audit Priorities

Rank only targets where local content judgment remains unresolved. Consider instruction frequency,
consumer count, cluster size, conflict risk, and likely removable context. Explain the ranking in
plain language rather than synthetic numeric scores.

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

Check history or task evidence only before calling guidance stale, speculative, or unused. Do not
turn every feature section into a historical research exercise.

### Return One Coherent Proposal Set

1. **Effective surface** - files loaded, consumers sampled, loading path, authorities, and evidence limits.
2. **Findings** - conflicts and missing behavior first, then structural and compression findings grouped by shared cause.
3. **Retained content** - non-obvious blocks explicitly worth their context cost.
4. **Implementation packages** - smallest groups that can be approved and changed independently.

Each finding needs evidence, authority, impact, recommendation, and confidence. Add status quo,
options, and expected outcome only when the user faces a material decision. Do not split one
structural decision into sentence-level approval items.

## Implementation Handoff

An implementation package must be usable without rerunning the audit:

- exact affected files and current authority;
- conflict, loading gap, or noise being removed;
- selected authority and expected consumer behavior;
- smallest coherent edit and explicitly excluded adjacent work;
- references, validators, or focused checks that should prove the change.

After approval, implement through a normal editing turn with appropriate tools and re-read current
source first. The audit itself remains unchanged evidence. An exhausted report is a valid terminal
condition; do not force another command, rerun, or explicit end-session confirmation.

## Guardrails

- Do not make files agree without deciding which behavior is best.
- Do not use existing standards as a substitute for judgment about the standards themselves.
- Do not inventory or mutate memory; hand memory-specific work to `/memory-audit`.
- Do not equate file length with noise or compression with quality.
- Do not require per-sentence scoring, decimal confidence, rigid message templates, or exhaustive option matrices.
- Do not edit during an audit or hide speculative concerns among verified findings.
