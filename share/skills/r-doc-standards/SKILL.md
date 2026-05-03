---
name: r-doc-standards
description: "Rules: Documentation standards — required sections, placement, cross-references, audience fitness, and audit dimensions"
user-invocable: false
---

# Documentation Standards

Rules for OwlBear documentation. Covers five doc types, placement rules, cross-reference integrity, audience fitness, and the eight audit dimensions used by `doc-audit`.

Companion wiring: `share/instructions/doc-standards.instructions.md` applies this standard and routes audits through `.owlbear/prompts/doc-audit.prompt.md`.

## Citation Format

Rules use **`{SECTION}-{N}`** IDs (e.g., `STR-1`, `PLC-1`, `AUD-1`). The prefix maps to the section below:

| Prefix | Section |
|--------|---------|
| `STR` | Required Sections |
| `PLC` | Placement |
| `XREF` | Cross-Reference Integrity |
| `AUD` | Audience Fitness |
| `DIM` | Audit Dimensions |

Audit findings cite rule IDs so every finding is traceable to a specific rule here.

## 1. Doc Types and Required Sections

Five doc types are in scope. Each has a required section set.

### 1.1 Root README (`README.md`)

`STR-1` Must contain: Project identity (what OwlBear is), Quick start, Directory structure overview, and a pointer to where consumers should go next.

`STR-2` Must NOT duplicate content from `setup/setup-guide.md`. Link to it instead.

`STR-3` Required headings (in order): project name / tagline, overview paragraph, directory structure table, getting started pointer.

### 1.2 `SECURITY.md`

`STR-4` Must contain: Supported versions table, vulnerability reporting instructions (contact method, response SLA), and disclosure policy.

`STR-5` Must NOT contain installation guides, feature descriptions, or anything unrelated to security posture.

### 1.3 Package README (`workspace/*/README.md`)

`STR-6` Must contain: Package purpose (one paragraph), entry points / launch commands, configuration options (env vars, flags), and a link to the parent README.

`STR-7` Must NOT reproduce content already in `copilot-instructions.md` or root README beyond a 1-line summary. Link to the authoritative source.

`STR-8` Required headings (in order): package name and purpose, launch / usage, configuration, dependencies (if non-obvious).

### 1.4 Share-Category README (`share/*/README.md`)

`STR-9` Must contain: Purpose of the category, inventory summary (what files live here, what prefixes/naming conventions apply), and loading/invocation notes for consumers.

`STR-10` Must NOT enumerate every file by name — categories change. A table of conventions is preferred over a list of file names.

### 1.5 Setup Guide (`setup/*.md`)

`STR-11` Must contain: Prerequisites, step-by-step instructions numbered sequentially, expected outcome per step, and troubleshooting hints for the most likely failure.

`STR-12` Must NOT assume the reader has prior knowledge of OwlBear internals. Write for a first-time installer.

`STR-13` Must stay in sync with `setup/init.py` — any flag, path, or behavior change in the script must be reflected in the guide.

## 2. Placement Rules

`PLC-1` Each doc type belongs in exactly one location. Do not duplicate a doc across locations.

`PLC-2` For general file placement rules (source files, tests, research, scratch), defer to `r-project-standards` § File Placement. This section covers only documentation files.

`PLC-3` Doc-type-to-location mapping:

| Doc type | Canonical location |
|----------|--------------------|
| Root README | `/README.md` |
| Consumer README | `/README-consumer.md` (if needed) |
| SECURITY.md | `/SECURITY.md` |
| Package README | `workspace/{package}/README.md` |
| Share-category README | `share/{category}/README.md` |
| Setup guide | `setup/{name}.md` |

`PLC-4` Docs that do not fit an existing doc type go in `.owlbear/research/` (findings) or `.owlbear/decisions/` (decision records). They are NOT placed in `share/`, `workspace/`, or `setup/` unless they match a canonical doc type.

`PLC-5` A doc file in the wrong location is a placement violation regardless of its content quality.

## 3. Cross-Reference Integrity

`XREF-1` Every link in a doc file MUST resolve to an existing file or a valid external URL at the time of commit.

`XREF-2` Relative links are preferred over absolute paths. Use paths relative to the doc file's location.

`XREF-3` No orphan references: if a doc is removed or renamed, all links pointing to it must be updated or removed in the same commit.

`XREF-4` Cross-doc references to rule IDs (e.g., `r-project-standards § File Placement`) use the pattern `{skill-name} § {section-heading}`. Section headings must match exactly.

`XREF-5` Circular references (A references B which references A for the same content) are a duplication violation — one becomes the source of truth, the other links to it.

## 4. Audience Fitness

`AUD-1` Each doc type has a defined primary audience. Content must match that audience's knowledge level and intent.

| Doc type | Primary audience | Knowledge level |
|----------|-----------------|-----------------|
| Root README | New evaluators, contributors | No prior OwlBear knowledge |
| SECURITY.md | Security researchers, users | Familiar with disclosure norms |
| Package README | Developers integrating the package | Python-fluent, unfamiliar with this package |
| Share-category README | Pipeline agents, contributors | OwlBear internals familiar |
| Setup guide | First-time installers | Follows instructions; no internals assumed |

`AUD-2` Jargon specific to OwlBear internals (agent tiers, pipeline stages, MCP tools) MUST be explained or linked on first use in docs targeting external audiences (root README, SECURITY.md, setup guides).

`AUD-3` Docs targeting internal audiences (share-category READMEs) MAY assume OwlBear internals knowledge and SHOULD NOT over-explain standard pipeline concepts.

`AUD-4` A doc that mixes audiences within a single section is a fitness violation. If content is needed for both audiences, split into clearly labeled subsections.

## 5. Audit Dimensions

These eight dimensions are applied by `doc-audit`. Each maps to one or more rule sections above.

`DIM-1` **D1 — Structural**: Does the doc contain all required sections for its type? (`STR-*` rules)

`DIM-2` **D2 — Duplication**: Does the doc reproduce content that belongs in (or already exists in) another canonical source? (`STR-2`, `STR-7`, `XREF-5`)

`DIM-3` **D3 — Placement**: Is the doc in the correct location for its type? (`PLC-3`, `PLC-5`)

`DIM-4` **D4 — Accuracy**: Does the doc accurately describe the current state of the system? (No rule ID — requires empirical verification against source code / config)

`DIM-5` **D5 — Coverage Integrity**: Are all significant components, commands, or options documented? Does omission mislead users into thinking an undocumented feature doesn't exist? (No rule ID — requires scope assessment)

`DIM-6` **D6 — Currency / Staleness**: Was the doc updated when the system it describes changed? (`STR-13` for setup guides; general discipline for all types)

`DIM-7` **D7 — Cross-reference Integrity**: Do all links resolve? Are there orphan references? (`XREF-1`, `XREF-2`, `XREF-3`)

`DIM-8` **D8 — Audience Fitness**: Is the content appropriate for the doc type's defined audience? (`AUD-1` through `AUD-4`)
