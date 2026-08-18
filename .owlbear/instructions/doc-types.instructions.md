---
description: "Project-specific documentation type rules for OwlBear canonical docs"
applyTo: "README.md,README-consumer.md,SECURITY.md,serve/*/README.md,share/README.md,setup/README.md,setup/setup-guide.md,setup/sharing-guide.md,.github/README-automation.md,.owlbear/README.md,store/README.md,tests/README.md"
---

# OwlBear Documentation Types

Project-local rule IDs for documentation shape, placement mapping, and audience targets.

These files also use `r-doc-standards` for cross-reference integrity, audience fitness, and the
eight audit dimensions.

## Rule IDs

| Prefix | Section |
| --- | --- |
| `STR` | Required Sections |
| `PLC` | Placement Mapping |
| `AUD` | Audience Targets |

## 1. Doc Types and Required Sections

### 1.1 Root README (`README.md`)

`STR-1` Must contain: Project identity (what OwlBear is), Quick start, Directory structure overview, and a pointer to where consumers should go next.

`STR-2` Must NOT duplicate content from `setup/setup-guide.md`. Link to it instead.

`STR-3` Required content order: project name / tagline, reader route, overview paragraph, current
surfaces or status, development or consumer next step, and directory structure overview. The
reader route comes before implementation detail so the front door remains useful to newcomers.

### 1.2 `SECURITY.md`

`STR-4` Must contain: Supported versions table, vulnerability reporting instructions (contact method, response SLA), and disclosure policy.

`STR-5` Must NOT contain installation guides, feature descriptions, or anything unrelated to security posture.

### 1.3 Package README (`serve/*/README.md`)

`STR-6` Must contain: Package purpose (one paragraph), entry points / launch commands, configuration options (env vars, flags), and a link to the parent README.

`STR-7` Must NOT reproduce content already in `copilot-instructions.md` or root README beyond a 1-line summary. Link to the authoritative source.

`STR-8` Required headings (in order): package name and purpose, launch / usage, configuration, dependencies (if non-obvious).

### 1.4 Share README (`share/README.md`)

`STR-9` Must contain: Purpose of the category, inventory summary (what files live here, what prefixes/naming conventions apply), and loading/invocation notes for consumers.

`STR-10` Must NOT enumerate every file by name — categories change. A table of conventions is preferred over a list of file names.

### 1.5 Setup Guide (`setup/setup-guide.md`, `setup/sharing-guide.md`)

`STR-11` Must contain: Prerequisites, step-by-step instructions numbered sequentially, expected outcome per step, and troubleshooting hints for the most likely failure.

`STR-12` Must NOT assume the reader has prior knowledge of OwlBear internals. Write for a first-time installer.

`STR-13` Must stay in sync with `setup/init.py` — any flag, path, or behavior change in the script must be reflected in the guide.

### 1.6 Folder Orientation Guide (`setup/README.md`, `.github/README-automation.md`, `.owlbear/README.md`, `store/README.md`, `tests/README.md`)

`STR-14` Must contain the folder's purpose, an inventory summary, ownership boundaries, and pointers to the canonical detailed sources.

`STR-15` Must explain important absent or generated content when a reader could reasonably expect it in the folder, without becoming a second procedural or implementation authority.

## 2. Placement Mapping

`PLC-3` Doc-type-to-location mapping:

| Doc type | Canonical location |
| --- | --- |
| Root README | `/README.md` |
| Consumer README | `/README-consumer.md` (if needed) |
| SECURITY.md | `/SECURITY.md` |
| Package README | `serve/{package}/README.md` |
| Share README | `share/README.md` |
| Setup guide | `setup/setup-guide.md`, `setup/sharing-guide.md` |
| Folder orientation guide | `setup/README.md`, `.github/README-automation.md`, `.owlbear/README.md`, `store/README.md`, `tests/README.md` |

`PLC-4` Docs that do not fit an existing doc type go in `.owlbear/research/` for durable findings. Change-specific decisions belong in native Delivery authority rather than standalone documentation. They are not placed in `share/`, `serve/`, or `setup/` unless they match a canonical doc type.

## 3. Audience Targets

`AUD-1` Each doc type has a defined primary audience. Content must match that audience's knowledge level and intent.

| Doc type | Primary audience | Knowledge level |
| --- | --- | --- |
| Root README | New evaluators, contributors | No prior OwlBear knowledge |
| SECURITY.md | Security researchers, users | Familiar with disclosure norms |
| Package README | Developers integrating the package | Python-fluent, unfamiliar with this package |
| Share README | Pipeline agents, contributors | OwlBear internals familiar |
| Setup guide | First-time installers | Follows instructions; no internals assumed |
| Folder orientation guide | Contributors and maintainers | Needs a concise map of one repository area and its boundaries |
