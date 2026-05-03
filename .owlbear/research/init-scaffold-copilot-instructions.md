# Init.py — Scaffold Consumer copilot-instructions.md

> **Owning task:** #1284 — P1-04: Update setup/init.py — scaffold consumer copilot-instructions.md
> **Date:** 2026-05-03 **Status:** Complete

## 1. Context and Question

Task #1284 requires `setup/init.py` to generate a consumer-facing `.github/copilot-instructions.md` scaffold when initializing new workspaces. The current `seed/.github/copilot-instructions.md` is a verbatim copy of OwlBear-dev's project-specific file (cockpit details, tools package, branches, etc.) — unsuitable for consumer projects.

**Questions:** (a) What content should the consumer scaffold contain? (b) Does `init.py` need code changes beyond the seed template? (c) Will existing tests from #1281 pass with the new template?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| GitHub Blog — 5 Tips for Custom Instructions | github.blog/ai-and-ml/github-copilot/5-tips-for-writing-better-custom-instructions-for-copilot/ | 0.9 — canonical recommended sections |
| VS Code Docs — Custom Instructions | code.visualstudio.com/docs/copilot/customization/custom-instructions | 0.9 — file format, auto-detection, priority rules |
| Graham Knapp — My Copilot Instructions File | grahamknapp.com/blog/my-copilot-instructions-file/ | 0.7 — real-world consumer perspective |
| Brief: Neutral Shared Layer | `.owlbear/briefs/draft-neutral-shared/brief.md` | 1.0 — notation convention, D5/D7 decisions |
| Codebase: `setup/init.py` | `setup/init.py` lines 1–400 | 1.0 — seed-walk logic, `_SKIP_IF_EXISTS_REL` pattern |
| Codebase: `tests/test_neutral_shared_1281.py` | AC4 test class `TestFromAC_InitScaffold` | 1.0 — test constraints on generated content |

## 3. Analysis

### Current init.py Behavior

`init.py` walks `seed/` and dispatches per file. `.github/copilot-instructions.md` falls through to `_write_seed_file()` → `shutil.copy2()`. No placeholder replacement (`.md` not in suffix list). Not in `_SKIP_IF_EXISTS_REL` — re-running init() overwrites existing customized file.

### Seed Template Content

GitHub Blog recommends 5 sections: project overview, tech stack, coding guidelines, project structure, resources. VS Code docs confirm: "Use copilot-instructions.md for coding style, tech stack, architectural patterns, security requirements, documentation standards."

Brief D5: "Prose-first notation with framed examples." Brief D7: "80% rule for copilot-instructions.md." Brief notation convention: "Use concrete illustrative paths with comments indicating customization needed."

### Implementation Trade-offs

| Approach | Description | Tests pass? | Consumer UX | KISS | Score |
|----------|-------------|-------------|-------------|------|-------|
| A: Consumer scaffold + skip-if-exists | Rewrite seed as generic scaffold; add to `_SKIP_IF_EXISTS_REL` | Yes | Good: useful start, customizations preserved | Yes | 0.85 |
| B: Consumer scaffold + overwrite | Rewrite seed; no skip-if-exists | Yes | Poor: customizations blown away on re-init | Yes | 0.60 |
| C: Keep OwlBear-dev copy | No changes | Yes (currently) | Bad: confuses consumers with OwlBear-specific content | — | 0.20 |

### Test Compatibility (#1281 AC4)

`TestFromAC_InitScaffold` checks:
- `test_generates_copilot_instructions` — file exists after init() ✓
- `test_has_directory_section_heading` — any heading containing "directory"/"path"/"structure" ✓
- `test_has_path_entry` — any non-separator table row ✓
- `test_path_entry_within_directory_section` — table rows within the directory section ✓
- `test_idempotent` — identical content on second run ✓ (skip-if-exists preserves first run's content)

All tests pass with Approach A as long as the scaffold has a `## Directory Structure` heading with table rows.

### Skip-if-exists Rationale

`_SKIP_IF_EXISTS_REL` already handles `.editorconfig`, `.gitattributes`, `.markdownlint-cli2.jsonc` etc. — files consumers customize post-init. `copilot-instructions.md` is the same pattern: scaffold once, consumer customizes, never overwrite. AC1 says "generates...for new consumer projects" — "new" implies first-run only.

### Scope of init.py Changes

Two changes:
1. Add `".github/copilot-instructions.md"` to `_SKIP_IF_EXISTS_REL` (1 line)
2. Replace `seed/.github/copilot-instructions.md` content (template file, no Python code change)

No placeholder replacement needed — the consumer template is project-generic.

## 4. Recommendation

**Approach A: Consumer scaffold + skip-if-exists** (confidence: 0.85)

Seed template structure:
- Project Identity placeholder (brief description prompt)
- `## Directory Structure` table with illustrative example rows and HTML comments
- Tech Stack placeholder section
- Resources section (MCP servers, scripts)

init.py: add `".github/copilot-instructions.md"` to `_SKIP_IF_EXISTS_REL`.

Challenge: FALLBACK — trivial implementation, T1 autonomous, no challenger needed.

Risks: (1) seed template diverges from OwlBear-dev's file — this is intentional per the brief. (2) Skip-if-exists means re-init won't update an outdated scaffold — acceptable because consumers customize the file.

## 5. Follow-up Tasks

No additional follow-up tasks needed. #1284 itself covers the full implementation scope. The dependency (#1282) is already completed (archived).
