---
description: "Run a codebase-wide architecture audit of serve/ packages using Module Quality Vocabulary and the Deletion Test"
---

# Architecture Module Quality Audit

You are running a read-only architecture audit over all top-level packages in `serve/`.

## Step 1 - Load the standard first

Before any scanning or conclusions, read:

- `share/skills/r-architecture-standards/SKILL.md`
- The section `## Module Quality Vocabulary`
- The subsections `### Deletion Test` and `### Dependency Classification`

Do not continue until these terms are loaded and used as the authority for labels.

## Step 2 - Define the audit unit

Audit unit is each top-level package directory under `serve/` (for example: `serve/mcp-kanban/`, `serve/knowledge/`, `serve/mcp-memory/`).

For each package, inspect:

- Public interfaces exposed to callers
- Primary caller set and call sites
- Internal complexity hidden behind the package boundary
- Dependency edges to other packages, MCP servers, and external services

## Step 3 - Evaluate with full vocabulary

For every package, classify all required dimensions:

1. Depth: `deep` or `shallow`
2. Leverage: caller count and reuse level
3. Locality: `self-contained` or `leaky`
4. Seam status: `real`, `hypothetical`, or `none` (include adapter context)
5. Dependency classification: `in-process`, `local-substitutable`, `remote-but-owned`, or `true-external`

Apply the Deletion Test for each package:

- Assume the package is removed.
- State what complexity reappears in callers.
- Decide whether the package is earning its keep or acting as pass-through.

Evidence must be concrete. Reference affected callers, interfaces, and complexity that would have to be reintroduced.

## Step 4 - Output format

Return one structured table row per package with exactly these columns:

| Package | Depth (deep/shallow) | Leverage (caller count) | Locality (self-contained/leaky) | Seam status (real/hypothetical/none) | Deletion Test result (earning-keep/pass-through/candidate-for-removal) | Evidence | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |

Within `Evidence`, explicitly include the dependency classification label (`in-process`, `local-substitutable`, `remote-but-owned`, or `true-external`) and the concrete caller/dependency proof supporting that label.

After the table, add a short summary:

- Top 3 candidates for deepening or consolidation
- Top 3 packages that clearly earn their keep
- Cross-package dependency risks observed during classification

## Step 5 - Optional follow-up tasks

If clear improvements are identified, you may create kanban tasks. Keep them atomic and include:

- Package in scope
- Which vocabulary dimension failed
- Concrete remediation target and expected impact

This audit remains read-only unless task creation is explicitly needed for actionable follow-up.
