# Design-Context Onboarding Prompt Research

> **Owning task:** #943 — Add design-context onboarding prompt for frontend workflows
> **Date:** 2026-03-24 **Status:** Complete

## 1. Context and Question

Task #943 adds a `.prompt.md` file that gathers project-specific design context
(users, jobs, tone, references, anti-references, accessibility) via an
interactive onboarding flow and persists it to `docs/design-context.md`. The
parent research (#930, `docs/research/impeccable-command-patterns.md`) already
recommended this adaptation of Impeccable's `/teach-impeccable`. This research
gate validates the AC is achievable, identifies implementation pitfalls, and
confirms the dependency (#934) is satisfied.

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | Impeccable repo: `/teach-impeccable` pattern (via parent #930 research) | .95 | Scan-first, ask-only-missing, persist-to-file onboarding flow [S1] |
| S2 | VS Code Prompt Files docs | .95 | Frontmatter format (`description`, `agent`, `tools`, `model`), file references via relative paths, `${input:}` syntax [S2] |
| S3 | OwlBear `frontend-design` skill (`SKILL.md` §Design Context) | 1.0 | Already asks for audience, use cases, and tone — the prompt fills this gap by persisting answers [S3] |
| S4 | OwlBear existing prompts (`orchestrate.prompt.md`, `agent-audit.prompt.md`) | 1.0 | Format precedent: description-only or description+agent frontmatter, markdown body [S4] |
| S5 | VS Code Customization Overview | .85 | Confirms prompt files for repeatable tasks, skills for reusable knowledge, agents for persistent personas [S5] |

## 3. Research Checklist

### 3.1 Theoretical Validity — PASS

The concept is sound: an interactive prompt that gathers design context
unavailable from code (target audience, brand tone, accessibility needs) and
persists it to a stable file that downstream prompts (#944–#946) can reference.
This is the "scan first, ask only missing" pattern from Impeccable [S1],
well-supported by the VS Code prompt format [S2, S5].

### 3.2 Prior Art — PASS (2+ sources)

| Pattern | Source | Evidence |
|---------|--------|----------|
| Scan repo → ask missing → persist context | Impeccable `/teach-impeccable` [S1] | Parent research §4.5 |
| Prompt files with description-only frontmatter | VS Code docs [S2] | `description` is optional; body is markdown |
| Design-context gathering (audience, use cases, tone) | OwlBear `frontend-design` skill §Design Context [S3] | Already defines the 3 core questions |

### 3.3 Technical Feasibility — PASS

| Requirement | Feasible? | Evidence |
|-------------|-----------|----------|
| Description-only frontmatter | Yes | VS Code docs: all frontmatter fields optional [S2] |
| Read existing `docs/design-context.md` | Yes | Prompt body can reference files via relative paths [S2] |
| Ask only missing questions | Yes | Prompt instructs AI to check file first, then ask gaps [S1, S2] |
| Write/update `docs/design-context.md` | Yes | Agent mode writes files; no special tools needed |
| Reference `frontend-design` skill | Yes | Relative path `../../.github/skills/frontend-design/SKILL.md` not needed — the AI can `#tool:readFile` or the body can include a markdown link [S2] |
| No code changes | Yes | Pure `.prompt.md` file creation |

### 3.4 Architecture Fit — PASS

- **Location:** `.github/prompts/design-context.prompt.md` alongside existing prompts [S4]
- **Output:** `docs/design-context.md` — outside `.github/` and config trees
- **No forbidden targets:** Does not touch `.impeccable.md` or `copilot-instructions.md`
- **Downstream consumers:** #944 (audit), #945 (normalize), #946 (polish) all reference `docs/design-context.md`
- **Dependency #934:** Archived (frontend-design skill exists) — satisfied

### 3.5 Implementation Approach — Single file, no code changes

The prompt file needs:

1. YAML frontmatter with `description:` only (per AC)
2. Body that instructs the AI to:
   - Check if `docs/design-context.md` exists and read it
   - For each of 7 sections (Users, Jobs, Tone, References, Anti-References,
     Accessibility, Design Principles), check if content is already present
   - Ask the user only for missing sections
   - Write or update the file with all sections populated
3. A relative-path reference to the frontend-design skill

**Key design decision:** The AC specifies 7 output sections (6 from parent
research + Design Principles). The skill's Design Context section asks for 3
of these (audience ≈ Users, use cases ≈ Jobs, tone ≈ Tone). The prompt expands
the skill's lightweight questions into a structured persistent document.

**Pitfall to avoid:** The prompt should not force agent mode via the `agent:`
frontmatter field. The user invokes it in agent mode naturally since it writes
files. Keeping frontmatter description-only matches the AC and keeps it simple.

### 3.6 Testing Strategy — Inspection-only

This is a `type:docs` task producing a `.prompt.md` file. No automated tests
apply. Verification is by file inspection: correct frontmatter, all 7 sections
covered, skill reference present, no forbidden targets mentioned.

### 3.7 Findings Documented — This document

## 4. Recommendation (.92 confidence)

The AC is well-scoped and implementation-ready with no blockers. The dependency
(#934) is satisfied. The implementation is a single `.prompt.md` file requiring
no code changes. No follow-up tasks are needed beyond the existing #943 task
and its downstream consumers (#944–#946) already created by #930.

**One refinement:** The prompt body should explicitly link to the frontend-design
skill via a markdown reference so the AI can load design guidance when
generating the Design Principles section. This is already implied by AC line 5
but worth noting for the builder.

## 5. Follow-up Tasks

No new follow-up tasks needed. Task #943 and its downstream consumers
(#944–#946) were already created by the parent research (#930). The AC is
complete and the dependency is satisfied.
