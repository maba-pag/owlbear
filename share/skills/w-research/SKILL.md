---
name: w-research
description: "Workflow: Research — source-grounded shaping research for uncertain scope, architecture, or prior art"
user-invocable: false
---

# Research

Investigate a material shaping question and return source-grounded evidence to the selected shaping
workflow. Research supports a decision; it does not approve a graph, create follow-up work, or route
the board independently.

Use this companion only when local evidence is insufficient to assess a consequential feasibility,
architecture, dependency, security, external-contract, or prior-art claim. A clear source owner or
one narrow authoritative answer does not require a research ceremony.

## Step 1 — Frame The Question

State the specific unknown, why it matters to the active shaping decision, and what evidence would
resolve it. Return control to the caller when the question is actually missing product intent rather
than an evidence gap; research must not choose intent on the user's behalf.

## Step 2 — Check Existing Research

Before gathering sources:

1. Search `.owlbear/research/` for the task ID and topic keywords. If a doc references this task, read it first.
2. Check task body for `See .owlbear/research/` links.
3. If a complete, recent document exists, validate its load-bearing claims against current source and
  return the still-current findings instead of repeating the investigation.

> Skipping this check is the most common research time-sink.

## Step 3 — Research Scope Gate

Bounded read-only research needed to assess the active shaping question is autonomous. This includes
local code and documentation, focused web/source-page lookups, and a proportionate multi-source or
comparative check when architecture, contracts, or prior art require it.

Obtain explicit user approval through `askQuestions` before:

- an exceptional-cost or open-ended investigation whose scope materially exceeds the active change;
- cloning a large external repository when source pages or focused retrieval are insufficient;
- executing external code, setup scripts, package installs, hooks, or other untrusted operations.

Present the remaining question, why bounded research is insufficient, proposed scope, expected outcome,
cost level, and a narrower alternative. If the user is unavailable, create a blocking request and
keep the task in `shape`.

For an approved clone, use `.owlbear/scratch/research/{repo-name}/`, inspect it only, record the
repository URL and resolved commit/ref in the findings, and delete the clone before returning. Do not
execute repository code, setup scripts, package installs, or hooks.

## Step 4 — Gather Proportional Evidence

- **Codebase:** follow `h-codebase-orientation` for indexes, exact search, and Semble. Use direct reads
  and exact tools to ground findings.
- **Explore:** use the `Explore` subagent for broad read-only codebase context when local search would be noisy.
- **Web:** use the `web` toolset for known public pages, browser acquisition for rendered or authenticated pages, and `markitdown/*` for supported document conversion. Open-ended DDGS search is unavailable; do not silently substitute another search provider.
- **External repositories:** prefer source pages, docs, and extracted files. Clone only when the
  approved exceptional investigation needs cross-file source inspection.

Use the smallest source set that can support or falsify the claim. One primary source is sufficient
for an exact contract it owns; independent corroboration is useful for disputed behavior, comparative
claims, or uncertain prior art. Track source, URL or local path, relevant fact, and evidence limits.

## Step 5 — Analyze And Compare

Compare meaningful alternatives when more than one viable approach exists. State trade-offs, risks,
evidence gaps, and calibrated confidence. Do not manufacture a matrix for a single adequate answer.
The calling workflow decides whether a finding changes the planning package or provisional graph and
owns any required challenger review or user decision.

## Step 6 — Preserve Durable Findings When Useful

Write `.owlbear/research/{slug}.md` only when the evidence has durable value beyond the active shaping
conversation. Keep it focused and source-grounded:

```markdown
# {Title}

> **Owning task:** #{id} — {title}
> **Date:** {date}
> **Question:** {specific shaping question}

## 1. Context and Question
## 2. Sources Studied (table)
## 3. Analysis (trade-off matrices)
## 4. Recommendation, Confidence, And Limits
```

Log materially used external sources in `.owlbear/sources/overview.md` per
`r-workspace-governance`. Delete approved clones from `.owlbear/scratch/research/` before returning.

## Step 7 — Return Evidence To The Caller

Return a compact evidence package:

```
## Research
- Question: {specific unknown}
- Findings: {source-grounded facts}
- Recommendation: {brief recommendation and confidence}
- Alternatives: {meaningful alternatives, or none}
- Risks and limits: {remaining uncertainty}
- Durable artifact: {.owlbear/research/{slug}.md, or none}
```

Do not edit native authority, invoke admission challenge, request approval, or create Delivery work.
The selected shaping workflow incorporates the evidence, resolves material decisions, challenges the
complete graph when applicable, and owns all task history and routing.
