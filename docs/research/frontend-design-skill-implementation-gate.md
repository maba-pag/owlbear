# Frontend-Design Skill Implementation Gate

> **Owning task:** #934 - Create OwlBear frontend-design skill from curated Impeccable references
> **Date:** 2026-03-22 **Status:** Complete

## 1. Context and Question

Task #934 already has the higher-level direction from task #929: use a dedicated
skill with adapted references instead of copying Impeccable into always-on
instructions. The narrower question here is how to package that skill so it fits
OwlBear's existing `.github/skills/` conventions, stays separated from sibling
tasks #937 and #938, and does not accidentally break the repo's current
skill-discovery tests [S1, S2, S3, S6, S7].

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | `.github/instructions/frontend.instructions.md` | .90 | Current always-on frontend baseline and scope boundary |
| S2 | `docs/research/impeccable-design-skills.md` | .95 | Prior OwlBear recommendation that #934, #937, and #938 should be separate tasks |
| S3 | VS Code Agent Skills docs | .95 | Skill directory structure, default invocation behavior, progressive loading, and relative resource guidance |
| S4 | Impeccable raw `source/skills/frontend-design/SKILL.md`, `NOTICE.md`, and website | .95 | Reference-pack shape, context-gathering flow, command baggage, and attribution model |
| S5 | Anthropic raw `skills/frontend-design/SKILL.md` | .85 | Baseline skill that Impeccable extends; useful for separating broad direction from Impeccable-specific additions |
| S6 | OwlBear `excalidraw-diagram` and `kanban-md` skills | .80 | Existing repo convention for resource-backed skills using a `references/` directory and relative links |
| S7 | `tests/test_skills.py` and `tests/test_project_definition_skill.py` | .90 | Current discovery-count assertions and pattern for skill-specific frontmatter and content tests |

## 3. Packaging Options

| Option | Context efficiency | OwlBear fit | Attribution clarity | Test impact | Verdict |
|--------|--------------------|-------------|---------------------|-------------|---------|
| Expand `frontend.instructions.md` only | Low | Weak | Weak | None | Reject |
| Add `frontend-design/SKILL.md` only | Medium | Partial | Partial | Low | Reject |
| Add `frontend-design/SKILL.md` plus local `references/` and attribution notice | High | Strong | Strong | Known and manageable | Adopt |

The third option matches VS Code's intended skill model, OwlBear's own
resource-backed skills, and the earlier #929 research. A single large
instruction file would duplicate #937's scope and bloat always-on context,
while a single SKILL without resources would miss the seven-file reference pack
that task #934 explicitly asks for [S1, S2, S3, S6].

## 4. Scope Boundary

| Concern | Owning task | Reason |
|---------|-------------|--------|
| `frontend-design/SKILL.md` frontmatter, skill body, and discovery metadata | #934 | Core deliverable [S3, S6] |
| Seven adapted reference files | #934 | Explicit AC and main value of the skill [S2, S4, S6] |
| Upfront design-context questions for audience, use cases, and tone | #934 | Required replacement for Impeccable's `teach-impeccable` flow [S4, S5] |
| Short handoff from `frontend.instructions.md` to the skill | #937 | Keeps always-on rules lean [S1, S2] |
| Anti-pattern taxonomy that splits blockers from taste heuristics | #938 | Already separated to avoid hard-coding taste as law [S2, S4, S5] |

This split keeps #934 narrow enough for a docs-only implementation while
preventing duplicate edits across sibling tasks [S1, S2, S4].

## 5. Implementation Notes

- Use `.github/skills/frontend-design/` with `name: frontend-design`. Leave
  `user-invocable` and `disable-model-invocation` unset so the skill can both
  auto-load and appear as a slash command, matching VS Code defaults and the
  user-facing nature of design help [S3, S4, S5].
- Store the seven adapted resources in `references/`, not Impeccable's singular
  `reference/`, because OwlBear already uses `references/` for resource-backed
  skills and SkillRegistry only cares about the top-level `*/SKILL.md`
  discovery shape [S3, S6, S7].
- Replace Impeccable-specific setup with three explicit questions near the top
  of `SKILL.md`: target audience, primary use cases/jobs, and brand personality
  or tone. Do not mention `.impeccable.md`, `/teach-impeccable`, or
  provider-specific command syntax [S4, S5].
- Add attribution in a local notice file or clearly marked attribution section
  that credits both Impeccable and Anthropic. Rewriting is still required;
  Apache licensing and Impeccable's own `NOTICE.md` support attribution, not
  verbatim import [S4, S5].
- Treat #934 as docs-only with respect to runtime code paths, but not as "no
  verification needed". Adding a new skill changes the discovered skill set
  from 19 to 20 and fits the existing skill-specific test pattern, so companion
  verification work is warranted [S6, S7].

## 6. Recommendation (.92 confidence)

Implement #934 as a docs-only skill package containing:

- `SKILL.md`
- seven adapted files under `references/`
- upfront design-context questions
- an attribution notice

Do not fold in the `frontend.instructions.md` handoff or the anti-pattern
taxonomy, because those are already owned by #937 and #938. Do not carry over
Impeccable command references, `.impeccable.md`, or `/teach-impeccable` setup;
replace them with OwlBear-native context questions and relative resource links
[S1, S2, S3, S4, S5, S6].

## 7. Follow-up Tasks

1. #941 - Add RED tests for frontend-design skill discovery and reference pack
   Priority rationale: #934 changes the discovered skill surface and otherwise
   leaves the existing 19-skill assertions stale.
   Dependencies: none.
   One-line AC: add verification coverage for `frontend-design` frontmatter,
   resource presence, and the real-skill discovery count.
   Created: `kanban\kanban-md.exe create "Add RED tests for frontend-design skill discovery and reference pack" --priority nice-to-have --status ideation --tags "ui,agent,test,scope:copilot,type:test" --parent 934 --body "..."`

Existing sibling tasks #937 and #938 already cover the instruction handoff and
anti-pattern taxonomy, so they were not recreated here.
