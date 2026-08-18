---
name: r-doc-standards
description: "Rules: Documentation quality standards — cross-references, audience fitness, and audit dimensions"
user-invocable: false
---

# Documentation Quality Standards

Shared documentation quality rules for any project. Project-specific doc-type and placement mappings are loaded from a local companion instruction.

Companion wiring: the matching project instruction applies this standard and routes audits through
the repository's documentation-audit workflow.

## Citation Format

Rules use **`{SECTION}-{N}`** IDs (for example, `STR-1`, `PLC-1`, `AUD-2`). The prefix maps to the section below:

| Prefix | Section |
| --- | --- |
| `STR` | Required Sections (project-defined companion instruction) |
| `PLC` | Placement (project-defined companion instruction + shared placement rules below) |
| `XREF` | Cross-Reference Integrity |
| `AUD` | Audience Fitness |
| `DIM` | Audit Dimensions |

Audit findings cite rule IDs so every finding is traceable to a specific rule.

## 1. Shared Placement Rules

`PLC-1` Each doc type belongs in exactly one location. Do not duplicate a doc across locations.

`PLC-2` For OwlBear-managed research and scratch placement, defer to `r-workspace-governance` §
OwlBear-Managed Artifact Placement. Project-owned source and test placement comes from local
manifests and established structure. This section covers only documentation files.

`PLC-5` A doc file in the wrong location is a placement violation regardless of content quality.

## 2. Cross-Reference Integrity

`XREF-1` Every link in a doc file must resolve to an existing file or a valid external URL at the time of commit.

`XREF-2` Relative links are preferred over absolute paths. Use paths relative to the doc file's location.

`XREF-3` No orphan references: if a doc is removed or renamed, all links pointing to it must be updated or removed in the same commit.

`XREF-4` Cross-doc references to rule IDs (for example, `r-workspace-governance` § `Commit
Discipline`) use the pattern `{skill-name} § {section-heading}`. Section headings must match exactly.

`XREF-5` Circular references (A references B while B references A for the same content) are a duplication violation. One becomes the source of truth, the other links to it.

## 3. Audience Fitness

`AUD-2` Project-internal jargon (agent tiers, pipeline stages, specialized tools) must be explained or linked on first use in docs targeting external audiences.

`AUD-3` Docs targeting internal audiences may assume project-internal knowledge and should not over-explain standard operational concepts.

`AUD-4` A doc that mixes audiences within a single section is a fitness violation. If content is needed for both audiences, split into clearly labeled subsections.

## 4. Audit Dimensions

These eight dimensions are applied by doc-audit. Each maps to one or more rule sections.

`DIM-1` **D1 — Structural**: Does the doc contain all required sections for its type? (`STR-*` rules from project-defined doc-type instructions)

`DIM-2` **D2 — Duplication**: Does the doc reproduce content that belongs in (or already exists in) another canonical source? (`XREF-5` and any project-specific duplication rules)

`DIM-3` **D3 — Placement**: Is the doc in the correct location for its type? (`PLC-*` project mappings and shared placement rules)

`DIM-4` **D4 — Accuracy**: Does the doc accurately describe the current state of the system? (No rule ID; requires empirical verification against source code or config)

`DIM-5` **D5 — Coverage Integrity**: Are all significant components, commands, or options documented? Does omission mislead readers into thinking an undocumented feature does not exist? (No rule ID; requires scope assessment)

`DIM-6` **D6 — Currency / Staleness**: Was the doc updated when the system it describes changed? (Project-defined staleness rules plus general update discipline)

`DIM-7` **D7 — Cross-reference Integrity**: Do all links resolve? Are there orphan references? (`XREF-1`, `XREF-2`, `XREF-3`)

`DIM-8` **D8 — Audience Fitness**: Is the content appropriate for the doc type's defined audience? (`AUD-*` rules)
