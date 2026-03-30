# Copilot Memory Boundary Instructions

> **Owning task:** #11 — Write Copilot Memory boundary instructions
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

OwlBear's three-layer knowledge architecture (docs/decisions/resolved/v2-architecture.md) separates knowledge by scope: Copilot Memory (agent learning), general KB (company/tech), project KB (product/process). Task #5 researched Memory behavior and tested boundary instruction effectiveness. This research determines **where** to place the boundary instruction and **what content** it should contain.

Key question: Should the boundary go in `copilot-instructions.md` (always-on) or a dedicated `instructions/memory-boundaries.instructions.md` file?

## 2. Sources Studied

| # | Source | URL / Path | Relevance |
|---|--------|-----------|-----------|
| S1 | VS Code settings reference — Memory settings | code.visualstudio.com/docs/copilot/reference/copilot-settings | .95 |
| S2 | VS Code custom instructions docs | code.visualstudio.com/docs/copilot/customization/custom-instructions | 1.0 |
| S3 | VS Code cheat sheet — Planning section | code.visualstudio.com/docs/copilot/reference/copilot-vscode-features | .85 |
| S4 | GitHub Docs — Managing Copilot Memory | docs.github.com/en/copilot/how-tos/use-copilot-agents/copilot-memory | .80 |
| S5 | Task #5 research findings | docs/research/copilot-memory.md | 1.0 |
| S6 | Direct observation — memoryInstructions system block | Agent context in this session | 1.0 |
| S7 | agent-common.instructions.md — existing patterns | instructions/agent-common.instructions.md | .90 |

## 3. Analysis

### 3a. Placement Options

| Criterion | copilot-instructions.md (.85) | instructions/memory-boundaries.instructions.md (.70) |
|-----------|-------------------------------|------------------------------------------------------|
| Loading guarantee | Always-on for all requests (S2) | Depends on applyTo match + settings (S2) |
| Priority | Repository-level (high) (S2) | File-based (lower than repo) (S2) |
| Complexity | Add section to existing file (KISS) | New file + frontmatter + applyTo pattern |
| Already has memory context | Yes — line 65 re: GitHub-hosted (S5) | No — starts from scratch |
| Separation of concerns | Mixed with other project conventions | Clean modular separation |
| Discoverability | Single file to check | Must know to look for it |

### 3b. Content Design: What Exists Already

VS Code auto-injects a `<memoryInstructions>` system block (S6) with:
- **memoryGuidelines:** Generic rules (brevity, topic files, key insights only, update/remove stale entries)
- **repoMemoryInstructions:** Repo memory constraints (conventions, build commands, codebase patterns, factsCriteria filter)

OwlBear's existing constraints (S7):
- `agent-common.instructions.md` §Post-task reflection: agents write `/memories/repo/inbox/{task-id}-{agent}.md`

**Gap:** No OwlBear-specific rules for WHAT goes in user memory (`/memories/`). The system block says "preferences, patterns, general insights" — too broad for the three-layer architecture.

### 3c. Boundary Content: Proposed Instruction

Based on #5 section 4 (S5), refined for OwlBear's architecture:

```markdown
## Memory governance

**Built-in memory tool** (`/memories/`) stores agent-centric learning only. This prevents duplication with the general KB and project KB layers.

**User memory** (`/memories/`) — store:
- Tool usage patterns and CLI flag recipes (e.g., "use bare `--cov` for scoped pytest")
- Agent behavior observations (what worked, what failed, effective workflows)
- Process pitfalls to avoid (e.g., "PS 5.1 here-strings split in ArgumentList")

**User memory** — do NOT store:
- Architecture decisions (use `docs/decisions/`)
- Research findings (use `docs/research/`)
- Domain knowledge or project conventions (use project KB via MCP)
- Code snippets or implementation details
- Task-specific context (use session memory — auto-cleared)

**Repo memory** (`/memories/repo/`) follows the built-in `repoMemoryInstructions` constraints. Agents write lessons-learned to `/memories/repo/inbox/` per `agent-common.instructions.md`.

**Management:** Run `Chat: Show Memory Files` to view stored memories. Delete stale entries with the `memory delete` command.

GitHub-hosted Copilot Memory is disabled in workspace settings to preserve OwlBear's local-first model. See `docs/research/copilot-memory.md` for rationale.
```

### 3d. Discrepancy (Resolved)

The workspace settings previously showed `github.copilot.chat.copilotMemory.enabled: true`, contradicting `copilot-instructions.md`. This was corrected — the setting is now `false` in `.vscode/settings.json`. No follow-up needed.

## 4. Recommendation (.85 confidence)

**Add a "Memory governance" section to `copilot-instructions.md`** using the content from §3c.

Rationale:
- Guaranteed always-on for every chat request (S2), unlike `.instructions.md` which depends on applyTo matching
- KISS — no new file, no extra frontmatter, no extra settings
- Naturally extends the existing Memory paragraph at line 65
- Repository-level priority means it takes precedence over org/extension instructions (S2)

Risk: Makes `copilot-instructions.md` longer. Mitigated: the section is ~15 lines, and the file is the correct home for project-wide conventions (S2 recommendation: "Start with copilot-instructions.md for project-wide coding standards").

Testing approach for AC4: After implementation, run 2–3 agent sessions (builder, reviewer, researcher) with explicit prompts that would trigger memory writes. Verify via `Chat: Show Memory Files` that only allowed categories are stored. This is a manual verification — no automated test possible for behavioral constraints (S5 §4a).

## 5. Follow-up Tasks

Task #11 itself is the implementation task — add the "Memory governance" section to `copilot-instructions.md` per §3c/§4 recommendation. No additional follow-up tasks needed.

The discrepancy noted in §3d has been resolved (setting is now `false`). The originally proposed follow-up task for fixing the setting is no longer needed.
