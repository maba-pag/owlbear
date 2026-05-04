# Extract r-architecture-standards sections to .owlbear/instructions/

> **Owning task:** #1289 — P2-05: Extract r-architecture-standards sections to .owlbear/instructions/
> **Date:** 2026-05-03 **Status:** Complete

## 1. Context and Question

Task #1289 requires extracting three project-specific sections from `share/skills/r-architecture-standards/SKILL.md` into a new project-local `.owlbear/instructions/architecture.instructions.md` with `applyTo: "serve/**"`. The shared skill should retain only generic MCP server conventions, module-quality rules, and error handling patterns.

**Pre-flight finding:** The shared skill in `owlbear-dev` was already path-neutralized by an earlier task (serve/ → workspace/, legacy headers renamed). Tests `test_r_arch_standards_no_serve_path_refs` and `test_r_arch_standards_no_legacy_section_headers` already PASS. The extraction itself (creating the new file + removing sections) is the remaining work.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `share/skills/r-architecture-standards/SKILL.md` (dev) | Codebase | 1.0 — the file being split |
| `.owlbear/briefs/draft-neutral-shared/brief.md` | Design doc | 0.9 — specifies notation convention and extraction target |
| `tests/test_path_neutrality_1285.py` | Codebase | 0.9 — defines pass criteria |
| `.vscode/settings.json` | Codebase | 0.7 — confirms `.owlbear/instructions` discovery enabled |
| `share/instructions/python.instructions.md` | Codebase | 0.6 — reference pattern for instruction stubs |
| Brief decisions D3, D7 | Design doc | 0.8 — project specifics in local config; 80% rule |

## 3. Analysis

### Sections to extract

| Section | Currently in skill | Reason for extraction |
|---------|-------------------|----------------------|
| `## Architecture Overview` | Lines 10-24 (workspace/ diagram) | Project-specific deployment topology |
| `## Dependency Rules` | Lines 137-146 | References project-specific `test_package_boundary.py` |
| `## Domain Scope Map` | Lines 148-end | Project-specific domain→path list |

### Sections to retain

| Section | Reason |
|---------|--------|
| Intro paragraph | Generic framing |
| `## Module Quality Vocabulary` (+ subsections) | Generic design vocabulary |
| `## MCP Server Conventions` (+ all subsections) | Generic MCP patterns |
| `## Configuration` | Generic MCP config patterns |

### Path convention for new file

Per brief notation convention: `.owlbear/instructions/` is the project-local resolution layer — use concrete `serve/` paths (not `workspace/`). This aligns with D7: project specifics in local config.

### VS Code discovery

`.vscode/settings.json` line 39: `".owlbear/instructions": true` — confirmed the directory is already configured for instruction file discovery. `applyTo: "serve/**"` will trigger when agents touch `serve/` files.

## 4. Recommendation

**Proceed with extraction.** Confidence: 0.95.

- Cut three sections from shared skill → paste into `.owlbear/instructions/architecture.instructions.md` with `serve/` paths restored
- Shared skill retains intro + Module Quality Vocabulary + MCP Server Conventions + Configuration
- Minimal risk: file split with clear boundaries, no behavioral change

Challenge: SKIP — trivial restructuring with no design trade-offs.

**Tier:** T1 — Autonomous (config/docs refactoring, no new capability).

## 5. Follow-up Tasks

No additional research tasks needed. Task #1289 itself transitions to backlog for implementation.
