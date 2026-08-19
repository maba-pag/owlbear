---
description: "Project-specific documentation type rules for OwlBear canonical docs"
applyTo: "README.md,README-consumer.md,SECURITY.md,serve/*/README.md,share/README.md,setup/setup-guide.md,setup/operating-owlbear.md,setup/sharing-guide.md,.github/README-automation.md,.owlbear/README.md,store/README.md,tests/README.md"
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

### 1.1 Root READMEs (`README.md`, `README-consumer.md`)

`README-consumer.md` is renamed to `README.md` by the sync workflow and is therefore the public
front page of the repository. `README.md` on `dev` is the development checkout's front door.

`STR-1` `README-consumer.md` must contain, in this order: product name and tagline, what using
OwlBear looks like, fit and non-fit expectations, requirements, quick start, verification, first
change, what setup changes and how to undo it, surface status, and a routing table to deeper
authority. Value and expectations come before vocabulary, architecture, and routing.

`STR-2` Neither root README may duplicate content from `setup/setup-guide.md` or
`setup/operating-owlbear.md` beyond the shortest usable form. Link to the authority instead.

`STR-3` `README.md` on `dev` must contain: project identity, a pointer to `README-consumer.md` for
the product story and installation, a reader route, the development checkout and its checks, and a
directory structure overview. It must not carry consumer status tables or installation procedure.

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

### 1.5 Setup Guides (`setup/setup-guide.md`, `setup/operating-owlbear.md`, `setup/sharing-guide.md`)

`STR-11` `setup/setup-guide.md` and `setup/sharing-guide.md` must contain: Prerequisites,
step-by-step instructions numbered sequentially, expected outcome per step, and troubleshooting
hints for the most likely failure. `setup/operating-owlbear.md` must contain the installed-file
inventory, the update and removal procedures, the operator workflow, and project-local
customization; it starts after installation and does not repeat the install path.

`STR-12` Must NOT assume the reader has prior knowledge of OwlBear internals. Write for a first-time installer.

`STR-13` Must stay in sync with `setup/init.py` — any flag, path, or behavior change in the script must be reflected in the guide.

### 1.6 Folder Orientation Guide (`.github/README-automation.md`, `.owlbear/README.md`, `store/README.md`, `tests/README.md`)

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
| Setup guide | `setup/setup-guide.md`, `setup/operating-owlbear.md`, `setup/sharing-guide.md` |
| Folder orientation guide | `.github/README-automation.md`, `.owlbear/README.md`, `store/README.md`, `tests/README.md` |

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
| Operating guide | Installed users running daily work | Setup already completed; no internals assumed |
| Folder orientation guide | Contributors and maintainers | Needs a concise map of one repository area and its boundaries |
