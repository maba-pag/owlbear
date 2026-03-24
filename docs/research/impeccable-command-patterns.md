# Impeccable Command Pattern Research

> **Owning task:** #930 - Research: Impeccable command patterns - skill/agent reuse for OwlBear
> **Date:** 2026-03-22 **Status:** Complete

## 1. Context and Question

Impeccable packages one deep `frontend-design` skill plus 20 `user-invocable`
commands as a cross-provider bundle. OwlBear already exposes three different
surfaces: reusable skills, user-invocable agents, and `.prompt.md` slash
commands. The question is not "copy the 20 commands?" but "which command
patterns improve OwlBear without adding auto-load surface area, test churn, or
duplicate config trees?" [S1, S2, S4, S5, S6]

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Impeccable repo: `README.md`, `source/skills/*/SKILL.md`, `.agents/skills/*`, `scripts/build.js`, `scripts/lib/transformers/*.js` | .95 | Primary evidence for the unified-skill command model, `user-invocable` frontmatter, provider adapters, and root-folder sync |
| S2 | Impeccable website + changelog | .90 | Public command taxonomy, staged `audit -> normalize -> polish` workflow, supported tools, and the v1.1.0 shift to a unified skills architecture |
| S3 | Anthropic `frontend-design` skill | .75 | Baseline skill reference used to separate the shared knowledge layer from Impeccable's added command layer |
| S4 | VS Code Agent Skills docs | .95 | `SKILL.md` structure, `user-invocable`, `argument-hint`, progressive loading, and slash-command behavior |
| S5 | OwlBear command surfaces: `.github/agents/*.agent.md`, `.github/prompts/orchestrate.prompt.md`, archived task #709 | 1.0 | Current OwlBear entrypoints and the existing prompt-file precedent for repeatable slash commands |
| S6 | OwlBear skill/runtime constraints: `src/owlbear/skills/registry.py`, `tests/test_skills.py`, `docs/research/agent-definitions-sync.md`, archived task #703 | .95 | Current skill-loading model, exact-count test seams, drift history, and the distinction between deterministic pre-hydration and interactive onboarding |

## 3. Structural Analysis

### 3.1 Pattern Verdicts

| Pattern | Impeccable evidence | OwlBear fit | Verdict |
|---------|---------------------|-------------|---------|
| One deep skill + thin task-specific wrappers | `frontend-design` plus 20 user-invocable wrappers [S1, S2] | Strong. OwlBear already separates reusable knowledge from entrypoints [S4, S5] | **Adopt** |
| User commands as `SKILL.md` files | Impeccable's unified skills architecture since v1.1.0 [S2]; skills are slash commands and auto-loadable in VS Code [S4] | Mixed. OwlBear prompt files already cover repeatable slash commands without enlarging `SkillRegistry` scope or `tests/test_skills.py` churn [S5, S6] | **Adapt as `.prompt.md`, not default `SKILL.md`** |
| Multi-provider root sync | Build generates `dist/*` and then syncs `.agents/.claude/.cursor/.codex/.gemini/.kiro/.opencode/.pi` back into the repo root [S1, S2] | Poor. OwlBear ships one VS Code repo, and it has already hit definition drift across prompt/config trees [S5, S6] | **Reject** |
| Interactive onboarding + persisted context | `/teach-impeccable` scans the repo, asks only missing questions, writes `.impeccable.md`, and can append to provider config [S1, S2] | Good flow, wrong storage target. OwlBear already explored deterministic pre-hydration in #703, but not interactive design onboarding [S5, S6] | **Adapt flow, not file target** |
| `audit -> normalize -> polish` staged workflow | Explicit pipeline in README and website examples [S1, S2] | High. It mirrors OwlBear's audit/build/gate mindset while staying user-facing [S5] | **Adapt (pilot first)** |

### 3.2 Command Map

`frontend-design` itself is already covered by #934. The table below maps the
20 Impeccable commands to the closest OwlBear analog and whether that analog is
good enough today.

| Command | Closest OwlBear analog | Outcome |
|---------|------------------------|---------|
| `/teach-impeccable` | `project-definition` skill; archived #703 pre-hydration | Partial -> add a dedicated onboarding prompt |
| `/audit` | reviewer agent + `code-review` skill | Partial -> strong pilot candidate |
| `/critique` | none | New capability |
| `/normalize` | planned `frontend-design` skill + builder workflow | New capability |
| `/polish` | reviewer or writer quality gates | Partial -> strong pilot candidate |
| `/distill` | none | New capability |
| `/clarify` | writer workflow, docs editing habits | Partial |
| `/optimize` | reviewer + `pytest-and-linting` skill | Partial |
| `/harden` | reviewer + `architecture-standards` risk checks | Partial |
| `/animate` | none | New capability |
| `/colorize` | none | New capability |
| `/bolder` | none | New capability |
| `/quieter` | none | New capability |
| `/delight` | none | New capability |
| `/extract` | `architecture-standards` + `task-decomposition` | Partial |
| `/adapt` | none | New capability |
| `/onboard` | `project-definition` skill | Partial |
| `/typeset` | none | New capability |
| `/arrange` | none | New capability |
| `/overdrive` | `visual-output` only as inspiration | New capability |

The key pattern is asymmetry: OwlBear has good generic research, review, and
prompt infrastructure, but almost none of the design-specific user vocabulary
that makes Impeccable valuable [S1, S2, S5]. That means the right reuse move is
not a full 20-command import. It is a thin command layer on top of OwlBear's own
frontend-design skill once #934 and #938 exist [S1, S3, S5].

## 4. Recommendation (.89 confidence)

1. Finish #934 and #938 first. OwlBear should not build command wrappers on top
   of raw Impeccable text; the shared knowledge layer must be OwlBear-owned
   first [S1, S3, S6].
2. Use `.prompt.md` as the first user-facing command surface for design
   workflows. In OwlBear's repo, prompt files are already the correct abstraction
   for a repeatable slash command (#709), while skills remain background
   knowledge and agents remain kanban pipeline roles [S4, S5, S6].
3. Pilot only four adoptions: design-context onboarding, frontend audit,
   frontend normalize, and frontend polish. Those four capture the best of the
   system without importing all 20 commands at once [S1, S2, S5].
4. Do not sync multi-provider folders into OwlBear. If OwlBear later publishes a
   public cross-tool pack, build it from a separate source tree or release step,
   not from hand-maintained root folders inside the main repo [S1, S2, S6].
5. Adapt `/teach-impeccable` as "scan first, ask only missing questions,
   write/update a dedicated design-context file under `docs/`". The onboarding
   flow should gather six categories adapted from Impeccable's four UX-focused
   question groups [S1, S2]: **users** (who they are, context, job-to-be-done),
   **jobs** (core tasks and emotional goals), **tone** (brand personality,
   3-word voice), **references** (sites or apps that capture the right feel),
   **anti-references** (what the UI must not look like), and **accessibility
   needs** (WCAG level, reduced-motion, color-blindness accommodations). The
   target storage file is `docs/design-context.md`. The flow must not write to
   `.github/copilot-instructions.md`, `.impeccable.md`, or any provider-config
   file [S1, S4, S5].

## 5. Follow-up Tasks

1. #942 - Codify prompt-vs-skill-vs-agent rules for user-facing OwlBear commands.
   Priority rationale: prevents future Impeccable-style command work from expanding the auto-load skill surface by default.
   Dependencies: none.
   One-line AC: add a short decision table that chooses `.prompt.md`, `SKILL.md`, or `.agent.md` by use case.
   Created: `kanban\kanban-md.exe create "Codify prompt-vs-skill-vs-agent rules for user-facing command surfaces" --priority nice-to-have --status ideation --tags "agent,scope:copilot,docs,type:docs" --parent 930 --body "See docs/research/impeccable-command-patterns.md §5."`

2. #943 - Add a design-context onboarding prompt for frontend workflows.
   Priority rationale: captures the best part of `/teach-impeccable` without mutating provider config files.
   Dependencies: #934.
   One-line AC: add a prompt that scans the repo, asks only missing design questions, and writes or updates `docs/design-context.md`.
   Created: `kanban\kanban-md.exe create "Add design-context onboarding prompt for frontend workflows" --priority nice-to-have --status ideation --tags "ui,agent,scope:copilot,docs,type:docs" --parent 930 --depends-on 934 --body "See docs/research/impeccable-command-patterns.md §5."`

3. #944 - Add a frontend-audit prompt that uses the frontend-design skill.
   Priority rationale: the audit stage is the cleanest first command in the `audit -> normalize -> polish` pipeline.
   Dependencies: #934, #938, #943.
   One-line AC: add a prompt that runs a scoped frontend audit, reports severity-ranked findings, and recommends next commands without editing code.
   Created: `kanban\kanban-md.exe create "Add frontend-audit prompt built on frontend-design skill" --priority nice-to-have --status ideation --tags "ui,agent,scope:copilot,docs,type:docs" --parent 930 --depends-on 934,938,943 --body "See docs/research/impeccable-command-patterns.md §5."`

4. #945 - Add a frontend-normalize prompt that uses the frontend-design skill.
   Priority rationale: normalization is the highest-value remediation command once OwlBear has its own shared design guidance.
   Dependencies: #934, #943.
   One-line AC: add a prompt that aligns a scoped feature with local design-context and frontend-design guidance before making edits.
   Created: `kanban\kanban-md.exe create "Add frontend-normalize prompt built on frontend-design skill" --priority nice-to-have --status ideation --tags "ui,agent,scope:copilot,docs,type:docs" --parent 930 --depends-on 934,943 --body "See docs/research/impeccable-command-patterns.md §5."`

5. #946 - Add a frontend-polish prompt that uses the frontend-design skill.
   Priority rationale: polishing is the lightest-weight finishing command and completes the initial staged workflow.
   Dependencies: #934, #943.
   One-line AC: add a prompt that performs a final detail pass for spacing, interaction states, copy, and accessibility before ship.
   Created: `kanban\kanban-md.exe create "Add frontend-polish prompt built on frontend-design skill" --priority nice-to-have --status ideation --tags "ui,agent,scope:copilot,docs,type:docs" --parent 930 --depends-on 934,943 --body "See docs/research/impeccable-command-patterns.md §5."`

No follow-up task was created for multi-provider root sync. The research verdict is
to reject that pattern for OwlBear's main repo.
