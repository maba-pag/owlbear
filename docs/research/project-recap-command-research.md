# Project-Recap Visual Command

> **Owning task:** #709 — Add project-recap visual command
> **Date:** 2026-03-10 **Status:** Complete

## 1. Context and Question

Task #709 asks: how should OwlBear implement a project-recap command that reads git history, kanban board state, and codebase structure, then generates an HTML mental model snapshot? The parent research (#592, `docs/research/visual-explainer-research.md`) identified project-recap as a medium-priority adoption candidate from visual-explainer (MIT). The visual-output skill (#706) and HTML templates (#708) provide the rendering foundation.

**Key question:** What format (`.prompt.md` vs `.instructions.md` vs custom agent) and what content sections best serve the project-recap use case?

## 2. Sources Studied

| Source | URL | What | Relevance |
|--------|-----|------|-----------|
| nicobailon/visual-explainer v0.6.3 — project-recap.md | <https://github.com/nicobailon/visual-explainer/blob/main/plugins/visual-explainer/commands/project-recap.md> | ~60-line command prompt: 8-section HTML page (identity, architecture, activity, decisions, state, mental model, cognitive debt, next steps) | .90 — primary pattern |
| Aider-AI/aider — RepoMap | <https://github.com/Aider-AI/aider/blob/main/aider/repomap.py> | 867-line Python module: tree-sitter + PageRank codebase map for LLM context | .65 — validates "repo overview" concept, different approach (programmatic vs prompt-based) |
| VS Code — Prompt files docs | <https://code.visualstudio.com/docs/copilot/customization/prompt-files> | .prompt.md format spec: YAML frontmatter (description, agent, tools, model), Markdown body, `${input:var}` interpolation, `/slash-command` invocation | .85 — format authority |
| OwlBear existing prompt files | Local `.github/prompts/*.prompt.md` | 2 files (orchestrate, commit-and-archive): delegate to custom agents via `agent:` field | .80 — internal pattern |

## 3. Analysis

### 3a. Implementation format comparison

| Criterion | `.prompt.md` (.85) | Custom agent (.40) | Skill extension (.30) |
|-----------|--------------------|--------------------|----------------------|
| Complexity | ~40 lines, one file | ~200+ lines, full persona | Modify existing skill |
| Invocation | `/project-recap` slash command | `@recap ...` agent mention | No direct invocation |
| VS Code native | Yes — designed for "single repeatable tasks" | Overkill for one command | Not a command |
| OwlBear daemon use | Via agent the prompt delegates to | Yes | Indirect |
| Tool access | Specify in `tools:` or inherit from `agent:` | Full control | Calling agent's tools |
| Precedent | `orchestrate.prompt.md`, `commit-and-archive.prompt.md` | 10+ agents but for multi-step roles | 15+ skills but for capabilities, not one-shot tasks |
| KISS | High | Low | Medium (wrong abstraction) |

**Decision (.85):** `.prompt.md` file. VS Code docs explicitly state "prompt files are best for single, repeatable tasks invoked as slash commands" — project-recap is exactly that.

### 3b. Section mapping: visual-explainer → OwlBear

visual-explainer's project-recap defines 8 HTML sections. Mapping to OwlBear data sources:

| Section | visual-explainer | OwlBear data source | Include? |
|---------|-----------------|---------------------|----------|
| Project Identity | Repo name, purpose, tech stack | `copilot-instructions.md` §Project purpose + §Tech stack | Yes |
| Architecture Snapshot | Top-level dirs, key modules | `src/` tree + `pyproject.toml` dependencies | Yes |
| Recent Activity | `git log --oneline -20` | `git log --oneline --since="2 weeks ago"` via terminal | Yes |
| Decision Log | Recent PRs, closed issues | Kanban `done`/`archived` tasks via `kanban_list` | Yes |
| State of Things | Open issues, WIP | Kanban `in-progress` + `review` + `todo` tasks | Yes |
| Mental Model Essentials | Core abstractions, data flow | Agent definitions + key module list from `src/` | Yes |
| Cognitive Debt Hotspots | Tech debt, stale issues | Kanban `blocked` tasks + `backlog` with `blocked:*` tags | Yes (.70) |
| Next Steps | Priority actions | Kanban `todo` sorted by priority | Yes |

All 8 sections are viable. The prompt instructs the agent to gather data, then render HTML using visual-output skill patterns.

### 3c. Data gathering tools

The prompt file needs these tools for data collection:

| Data | Tool | Command / method |
|------|------|-----------------|
| Git history | Terminal | `git log --oneline --since="2 weeks ago"` |
| Directory tree | Terminal | `Get-ChildItem -Recurse -Depth 2 -Name` or file listing tool |
| Kanban board | KanbanToolset | `kanban_list --status in-progress,todo,done,review --compact` |
| Blocked tasks | KanbanToolset | `kanban_list --blocked --compact` |
| Project context | File read | `copilot-instructions.md`, `pyproject.toml` |
| HTML output | File write | Write to `.owlbear/diagrams/project-recap.html` |
| Screenshot | VisualFeedbackToolset | `share_screenshot` after browser opens the HTML |

### 3d. Comparison with aider RepoMap

| Criterion | aider RepoMap | OwlBear project-recap |
|-----------|--------------|----------------------|
| Approach | Programmatic (tree-sitter + PageRank) | Prompt-based (LLM generates HTML) |
| Output | Text (ranked file map for LLM context) | HTML (visual mental model for human) |
| Scope | Code structure only | Code + activity + decisions + state |
| Runtime code | 867 lines Python | 0 lines — pure prompt engineering |
| Dependencies | tree-sitter, pygments, networkx, diskcache | None (uses existing tools) |
| KISS alignment | Medium (complex algorithm) | High (agent + prompt = done) |

aider's approach validates the need for "codebase overview" but optimizes for LLM context, not human understanding. Project-recap optimizes for human context-switching — different goal, complementary approaches.

### 3e. Dependencies and risks

| Dependency | Status | Risk | Mitigation |
|------------|--------|------|------------|
| #706 visual-output skill | In-progress (architect) | Prompt references skill for HTML aesthetics | Prompt works without skill — agent still generates HTML, just less polished |
| #708 HTML templates | Todo, depends on #706 | Templates improve output consistency | Not strictly required — soft dependency |
| VisualFeedbackToolset | Available in codebase | None | Already integrated |
| KanbanToolset | Available in codebase | None | Already integrated |

**Risk assessment (.80):** The prompt is self-contained — it can function without #706/#708 by including inline aesthetic instructions. The visual-output skill and templates improve quality but are not blockers.

### 3f. KISS/YAGNI assessment

- **KISS-aligned (.90):** A ~40-line `.prompt.md` file — zero runtime code, zero new tools, zero new agents. The agent reads data, generates HTML, saves it. Simplest possible implementation.
- **YAGNI check:** visual-explainer's project-recap includes a "fact-check" verification step. Skip for v1 — add if output quality proves inconsistent.
- **Architecture fit (.85):** All data sources and tools already exist. The prompt is pure instruction composition.

## 4. Recommendation (.85 confidence)

Create `.github/prompts/project-recap.prompt.md` with:

1. **Frontmatter:** `description`, `agent: agent` (default mode for full tool access), `tools:` list including terminal and file tools
2. **Body — Data gathering phase:** Instructions to collect git log, kanban state, directory tree, and project context
3. **Body — HTML generation phase:** Reference visual-output skill, specify the 8-section structure, require self-contained HTML with inline CSS
4. **Body — Delivery phase:** Save to `.owlbear/diagrams/project-recap.html`, open in browser, capture screenshot

Estimated prompt length: ~35-45 lines. The prompt delegates rendering quality to the visual-output skill rather than duplicating aesthetic rules.

**The prompt file should NOT duplicate visual-output skill content.** It references the skill via a Markdown link (`[visual-output skill](.github/skills/visual-output/SKILL.md)`) — the agent loads the skill for rendering guidance.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement project-recap prompt file" --priority nice-to-have --status backlog --tags "scope:copilot,agent" --depends-on 706 --body "Create .github/prompts/project-recap.prompt.md (~40 lines). YAML frontmatter: description, agent: agent. Body: 3 phases (gather data via terminal+kanban, generate 8-section HTML per visual-output skill, save to .owlbear/diagrams/ and capture screenshot). Reference visual-output skill via markdown link. See docs/research/project-recap-command-research.md §4."

kanban\kanban-md.exe create "Test project-recap prompt on OwlBear workspace" --priority nice-to-have --status backlog --tags "scope:copilot,test" --depends-on 709 --body "Manual validation: invoke /project-recap in VS Code chat, verify all 8 sections populated, HTML renders correctly in browser, screenshot captured. Check that kanban data and git log are accurate. See docs/research/project-recap-command-research.md §3b for section mapping."
```

## 6. Attribution

Add to `docs/sources/overview.md`:

| Source | URL | License | What | Where Used | Date |
|--------|-----|---------|------|------------|------|
| nicobailon/visual-explainer — project-recap.md | <https://github.com/nicobailon/visual-explainer/blob/main/plugins/visual-explainer/commands/project-recap.md> | MIT | 8-section project recap HTML structure, data gathering pattern | `.github/prompts/project-recap.prompt.md` | 2026-03-10 |
| Aider-AI/aider — RepoMap | <https://github.com/Aider-AI/aider/blob/main/aider/repomap.py> | Apache-2.0 | Repo overview concept validation (tree-sitter + PageRank codebase map) | `docs/research/project-recap-command-research.md` | 2026-03-10 |
| VS Code prompt files docs | <https://code.visualstudio.com/docs/copilot/customization/prompt-files> | CC-BY-4.0 | .prompt.md format specification (frontmatter, variables, tool lists) | `.github/prompts/project-recap.prompt.md` | 2026-03-10 |
