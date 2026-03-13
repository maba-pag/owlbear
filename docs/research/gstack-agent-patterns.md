# gstack Agent Patterns for OwlBear Improvement

> **Owning task:** #783 — Research garrytan/gstack agent patterns for OwlBear improvement
> **Date:** 2026-03-13 **Status:** Complete

## 1. Context and Question

gstack (garrytan/gstack) is a Claude Code skill pack that turns a single LLM session into specialist modes via `/slash` commands. It ships 8 skills: plan-ceo-review, plan-eng-review, review, ship, browse, qa, setup-browser-cookies, retro. What patterns can OwlBear adopt or adapt?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| garrytan/gstack v1.1.0 | https://github.com/garrytan/gstack | .90 | Full repo analysis — 8 skills, review checklist, browse binary |
| OwlBear agent ecosystem | local codebase | 1.0 | 11 agents, 15+ skills, orchestration pipeline |

## 3. Analysis

### Architecture Comparison

| Dimension | gstack | OwlBear | Delta |
|-----------|--------|---------|-------|
| Agent count | 8 (skills) | 11 (agents) + 15 (skills) | OwlBear has deeper pipeline |
| Orchestration | Manual (user invokes `/command`) | Automated (orchestrator + planner + waves) | OwlBear far ahead |
| Tool restriction | `allowed-tools` in YAML | `tools` per agent | Both enforce least-privilege |
| Task mgmt | TODOS.md (flat file) | kanban-md (structured pipeline) | OwlBear far ahead |
| TDD | No TDD pipeline | test-writer → builder → reviewer | OwlBear far ahead |
| Safety | None | 6-layer safety stack | OwlBear far ahead |
| Product thinking | CEO review (10-star vision) | None | gstack ahead |
| Failure mode analysis | Error & Rescue Map table | Ad hoc in reviews | gstack ahead |
| Review checklist | Two-pass (critical + info) with suppressions | Single-pass checklist | gstack ahead |
| Shipping workflow | Automated merge-test-version-PR | Auditor commits (no version/changelog) | gstack ahead |
| Retrospective | Git metrics, sessions, per-contributor analysis | None | gstack ahead |
| QA testing | Structured health scores, regression baselines | Browser tools exist but no QA workflow | gstack ahead |
| Question protocol | "One issue per question, recommend+WHY+options" | "askQuestions liberally" (unstructured) | gstack ahead |
| Scope modes | EXPANSION / HOLD / REDUCTION | KISS/YAGNI principles (no explicit modes) | gstack ahead |

### Patterns Worth Adopting

**A. Review Checklist with Two-Pass Priority + Suppressions (.85 confidence)**

gstack's `/review` skill splits checks into CRITICAL (blocks ship) and INFORMATIONAL (included but non-blocking), with an explicit suppressions list to reduce false positives. OwlBear's reviewer skill is single-pass — all findings are treated equally. A two-pass system would let the reviewer focus on blocking issues first and reduce noise from style-level findings. The suppressions list is especially valuable: it prevents agents from flagging harmless patterns repeatedly.

**B. Error & Rescue Map Template (.80 confidence)**

gstack's plan-ceo-review requires a structured table: METHOD → WHAT CAN GO WRONG → EXCEPTION CLASS → RESCUED? → USER SEES. This is a forcing function for exhaustive failure analysis. OwlBear's architect skill checks "security surface" but has no structured template for mapping every new codepath to its failure modes. Adding this to the arch-review skill would catch gaps the current checklist misses.

**C. Retrospective Workflow Skill (.75 confidence)**

gstack's `/retro` analyzes git history with specific metrics: commits, LOC, test ratio, session detection, per-contributor breakdown, focus score. OwlBear has no equivalent — the curator triages lessons learned but doesn't analyze development patterns. A retro skill would give the user a data-driven view of project velocity and quality trends.

**D. Structured Question Protocol (.70 confidence)**

gstack enforces: "one issue per AskUserQuestion; recommend + WHY + lettered options." OwlBear says "askQuestions liberally" with no format standard. Standardizing would make question output more consistent across agents. Risk: over-prescriptive protocol may slow down agents that need quick clarification.

### Patterns to Skip

| Pattern | Why Skip |
|---------|----------|
| Compiled browser binary | OwlBear already uses Playwright CDP; native binary is a Bun-specific optimization |
| Cookie import from real browsers | OwlBear confines browser to localhost only (SEC-07); importing real cookies is a security surface expansion |
| CEO "10-star product" review | Architecturally interesting but OwlBear's automated pipeline has no human-in-the-loop for product ideation; would need a new interactive agent mode outside the normal pipeline |
| Ship workflow (version/changelog/PR) | OwlBear doesn't use version files or PRs — it's a daemon, not a shipped library. The auditor's commit workflow is sufficient for now |
| Scope mode selection | KISS/YAGNI + architect gate already handle scope control |

## 4. Recommendation

**Primary (.85): Adopt two-pass review checklist with suppressions.** Lowest effort, highest ROI — directly improves reviewer agent quality by reducing noise and prioritizing critical findings. Model after gstack's `review/checklist.md` structure.

**Secondary (.80): Add Error & Rescue Map to arch-review skill.** Structured failure analysis template catches gaps that prose-based review misses. Add as a new step in the architecture-standards or arch-review skill.

**Tertiary (.75): Create a retro skill for development analytics.** Useful for longer-term project health visibility. Lower priority since OwlBear's pipeline already tracks quality through the 3-line defense model.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add two-pass review checklist with suppressions to reviewer skill" --priority needed --status ideation --tags "research,scope:agent-config,type:docs" --body "## Goal\nAdapt gstack's two-pass review checklist pattern for OwlBear's reviewer agent.\n\n## AC\n- [ ] code-review SKILL.md has a two-pass structure: Pass 1 (CRITICAL: security, injection, data safety) and Pass 2 (INFORMATIONAL: style, naming, dead code)\n- [ ] Suppressions section lists patterns the reviewer should NOT flag (e.g., harmless redundancy, threshold values)\n- [ ] reviewer.agent.md references the two-pass structure\n- [ ] No changes to .py files\n\nSee docs/research/gstack-agent-patterns.md for prior art."
kanban\kanban-md.exe create "Add Error and Rescue Map template to arch-review skill" --priority important --status ideation --tags "research,scope:agent-config,type:docs" --body "## Goal\nAdd a structured failure-mode analysis template to the arch-review skill, inspired by gstack's Error & Rescue Map.\n\n## AC\n- [ ] arch-review SKILL.md Step 3 includes a new sub-step: 'Failure Mode Map'\n- [ ] Template table: CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT\n- [ ] architect.agent.md mentions failure mode analysis in its self-critique checklist\n- [ ] No changes to .py files\n\nSee docs/research/gstack-agent-patterns.md for prior art."
kanban\kanban-md.exe create "Create retro skill for development analytics" --priority nice-to-have --status ideation --tags "research,scope:agent-config,type:docs" --body "## Goal\nCreate a retrospective workflow skill that analyzes git history and produces development metrics.\n\n## AC\n- [ ] New SKILL.md at .github/skills/retro/SKILL.md\n- [ ] Metrics: commits, LOC, test LOC ratio, session detection (45min gap), per-contributor breakdown\n- [ ] Output: structured markdown report\n- [ ] No new Python dependencies\n- [ ] No changes to .py files\n\nSee docs/research/gstack-agent-patterns.md for prior art (gstack retro skill)."
```
