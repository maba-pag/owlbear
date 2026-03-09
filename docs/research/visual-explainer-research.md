# Visual Explainer Research

> **Owning task:** #592 — Research: nicobailon/visual-explainer
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

Epic #582 asks: what diagram generation, visual explanation, and UI patterns can OwlBear adopt? This doc covers `nicobailon/visual-explainer` (v0.5.1, MIT) — a Claude Code plugin/agent skill that generates self-contained HTML pages for architecture diagrams, diff reviews, plan reviews, data tables, slide decks, and project recaps. It replaces ASCII art with styled HTML opened in the browser.

**Key question:** Which patterns are reusable by OwlBear agents to produce visual output via its existing Playwright/`ScreenshotService`/`VisualFeedbackToolset` stack?

## 2. Sources Studied

| Source | URL | License | Relevance |
|--------|-----|---------|-----------|
| nicobailon/visual-explainer | <https://github.com/nicobailon/visual-explainer> | MIT | Primary: HTML diagram generation skill with templates, commands, CSS/Mermaid references |
| Anthropic skills repo | <https://github.com/anthropics/skills> | Apache-2.0 | Prior art: Agent Skills specification, frontend-design skill pattern (credited by visual-explainer) |
| Dammyjay93/interface-design | <https://github.com/Dammyjay93/interface-design> | MIT | Prior art: design system memory (`system.md`), design token persistence across sessions, audit/extract commands |

## 3. Analysis

### 3a. What visual-explainer provides

The repo is **not a library** — it's a structured prompt engineering system. There is zero runtime code (no Python, no JS modules). It consists of:

- **SKILL.md** (~400 lines) — master instructions teaching an LLM how to generate styled HTML
- **8 command prompts** (`commands/*.md`) — slash commands for diff-review, plan-review, etc.
- **4 reference docs** (`references/*.md`) — CSS patterns, Mermaid theming, responsive nav, slide patterns
- **4 HTML templates** (`templates/*.html`) — reference examples the LLM reads before generating
- **1 shell script** — deploy to Vercel

### 3b. Reusable patterns for OwlBear

| Pattern | Description | OwlBear fit | Effort |
|---------|-------------|-------------|--------|
| Self-contained HTML generation | Single `.html` file with inline CSS/JS, Mermaid CDN, Google Fonts | High — agents write file, Playwright opens it | Low |
| Aesthetic constraint system | Forbidden colors/fonts, curated palettes, "squint test" / "swap test" | High — prevents AI-slop visual output | Prompt-only |
| Mermaid diagram routing | Decision table: content type → Mermaid vs CSS Grid vs `<table>` | High — agent can pick right tool | Prompt-only |
| Diff-review command | Git diff → architecture comparison + code review HTML | Medium — needs OwlBear `TerminalToolset` integration | Medium |
| Project-recap command | Git log + codebase scan → mental model snapshot | Medium — valuable for context-switching between projects | Medium |
| Fact-check command | Extract claims → verify against code → correct in-place | Medium — quality gate for generated visual output | Medium |
| Slide deck mode | Magazine-quality HTML slides with keyboard navigation | Low priority — nice to have, not core | Medium |
| Vercel share script | One-command deployment of HTML to public URL | Low — OwlBear is laptop-resident, sharing not in scope | N/A |

### 3c. Architecture fit with OwlBear

| OwlBear component | Integration point |
|-------------------|-------------------|
| `ScreenshotService` | Could capture browser screenshot of generated HTML for Slack delivery |
| `VisualFeedbackToolset` | `share_screenshot` already captures browser pages — extend to HTML files |
| `BrowserToolset` (Playwright) | `page.goto(f"file://{html_path}")` opens the generated HTML |
| `TerminalToolset` | Diff-review and project-recap commands need `git diff`, `git log` output |
| `KanbanToolset` | Project-recap could read kanban board state |
| Agent prompt system | SKILL.md patterns map to OwlBear `.instructions.md` or `.agent.md` files |
| `docs/` output dir | Generated HTML → `.owlbear/diagrams/` (per visual-explainer convention) |

### 3d. Comparison: visual-explainer vs interface-design

| Criterion | visual-explainer (.80) | interface-design (.50) |
|-----------|------------------------|------------------------|
| Scope | Full diagrams, reviews, tables, slides | UI component design tokens only |
| Persistence | Stateless — generates fresh each time | Stateful — `system.md` persists design decisions |
| OwlBear fit | Direct — agents generate reports/diagrams | Indirect — OwlBear doesn't build UIs |
| Complexity | ~400-line SKILL.md + 4 templates | Simpler — design token persistence pattern |
| Key takeaway | HTML generation prompts + aesthetic guards | Design token memory across sessions |

### 3e. KISS/YAGNI assessment

- **KISS-aligned:** The core pattern is trivially simple — agent writes an HTML file, browser opens it. No build step, no dependencies beyond Mermaid CDN.
- **YAGNI risk:** Slide decks, Vercel sharing, surf-cli AI image generation are all out of scope for OwlBear's needs. The diff-review and plan-review commands are feature-rich but only worth adopting in simplified form.
- **Recommended adoption scope:** (1) HTML generation skill for agents, (2) curated template library, (3) Mermaid routing table, (4) aesthetic constraint system. Skip slides, sharing, and AI image generation.

## 4. Recommendation (.80 confidence)

**Adopt the HTML diagram generation pattern as an OwlBear agent skill.** Specifically:

1. **Create a `visual-output` skill** (`.github/skills/visual-output/SKILL.md`) adapting the core workflow: think → structure → style → deliver. Include the Mermaid routing table, aesthetic constraints, and forbidden-pattern rules. Simplify heavily — OwlBear needs ~100 lines, not 400.
2. **Add 2–3 HTML templates** to the skill as reference examples (architecture overview, data table, flowchart). Adapted from visual-explainer's MIT-licensed templates.
3. **Integrate with existing infrastructure:** agents write HTML to `.owlbear/diagrams/`, Playwright opens it, `ScreenshotService` captures PNG for Slack delivery.
4. **Create a `DiagramToolset`** exposing `generate_diagram` and `open_diagram` tools so agents can produce visual output programmatically.
5. **Defer:** diff-review, plan-review, project-recap, slides, fact-check, and sharing commands. These are agent workflow enhancements that can be added incrementally once the foundation works.

**Risk:** LLM quality varies — generated HTML may be inconsistent. Mitigation: curated templates + aesthetic constraints reduce variance. Fact-check pattern (from visual-explainer) can be adopted later as a quality gate.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Create visual-output agent skill" --priority needed --tags "phase-research,scope:copilot,agent" --parent 582 --body "Create .github/skills/visual-output/SKILL.md adapting visual-explainer's core workflow (think/structure/style/deliver). Include Mermaid routing table, aesthetic constraints, forbidden patterns. Target ~100 lines. See docs/visual-explainer-research.md §4."

kanban\kanban-md.exe create "Add HTML diagram templates to visual-output skill" --priority important --tags "phase-research,scope:copilot,docs" --parent 582 --body "Adapt 2-3 reference HTML templates from visual-explainer (MIT): architecture overview, data table, Mermaid flowchart. Place in .github/skills/visual-output/templates/. See docs/visual-explainer-research.md §3b."

kanban\kanban-md.exe create "Implement DiagramToolset for agent HTML generation" --priority needed --tags "phase-research,scope:core,tooling" --parent 582 --body "FunctionToolset with generate_diagram (writes HTML to .owlbear/diagrams/) and open_diagram (Playwright page.goto). Integrate with ScreenshotService for Slack delivery. See docs/visual-explainer-research.md §3c."

kanban\kanban-md.exe create "Add project-recap visual command" --priority nice-to-have --tags "phase-research,scope:copilot,agent" --parent 582 --body "Adapt visual-explainer's project-recap pattern as an OwlBear agent command. Reads git log + kanban board + codebase → generates HTML mental model snapshot. Requires DiagramToolset. See docs/visual-explainer-research.md §3b."
```
