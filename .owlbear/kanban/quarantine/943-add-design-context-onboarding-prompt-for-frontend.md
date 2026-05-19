---
id: 943
title: Add design-context onboarding prompt for frontend workflows
status: archived
priority: nice-to-have
created: 2026-03-22T19:01:34.8824161+01:00
updated: 2026-03-24T16:23:34.3512848+01:00
started: 2026-03-24T16:23:29.38574+01:00
completed: 2026-03-24T16:23:29.38574+01:00
tags:
    - ui
    - agent
    - scope:copilot
    - docs
    - type:docs
parent: 930
depends_on:
    - 934
class: standard
---

## Context

Adapt the useful part of Impeccable''s `/teach-impeccable` without `.impeccable.md` or provider-config mutation. The prompt should scan the repo first, ask only missing questions, and persist OwlBear-owned design context for later frontend prompts.

See docs/research/impeccable-command-patterns.md.

## Acceptance Criteria

- [ ] Add `.github/prompts/design-context.prompt.md` with description-only frontmatter.
- [ ] Prompt first inspects current repo context, then asks only missing questions about users, jobs, tone, references, anti-references, and accessibility needs.
- [ ] Prompt writes or updates `docs/design-context.md` with stable sections for Users, Jobs, Tone, References, Anti-References, Accessibility, and Design Principles.
- [ ] Prompt does not mention `.impeccable.md` or edit `.github/copilot-instructions.md`.
- [ ] Prompt can reference the frontend-design skill by relative path when that skill exists.

[[2026-03-24]] Tue 01:25

## Research

- Doc: docs/research/design-context-onboarding-prompt.md

- Checklist: all 7 items PASS

- Dependency #934: archived (frontend-design skill exists)

- AC validated: well-scoped, implementation-ready, single .prompt.md file, no code changes

- Recommendation (.92): proceed to backlog as-is, no AC refinements needed

- Follow-up tasks: none new (existing #944-#946 cover downstream consumers)

- Sources logged in docs/sources/overview.md

[[2026-03-24]] Tue 02:53

## Architecture Review

**Verdict:** Approved

### AC Assessment

- AC1: Add .github/prompts/design-context.prompt.md with description-only frontmatter -> Clear, verifiable. Matches agent-audit.prompt.md precedent (description-only). Kept.
- AC2: Prompt inspects repo context, asks only missing questions (users, jobs, tone, references, anti-references, accessibility) -> Behavioral spec with 6 named categories. Verifiable by reading prompt body. Kept.
- AC3: Prompt writes/updates docs/design-context.md with 7 stable sections -> All 7 sections enumerated (Users, Jobs, Tone, References, Anti-References, Accessibility, Design Principles). Verifiable by inspection. Kept.
- AC4: Prompt does not mention .impeccable.md or edit copilot-instructions.md -> Negative constraint, verifiable by grep. Kept.
- AC5: Prompt can reference frontend-design skill by relative path when skill exists -> Dependency #934 archived, skill exists at .github/skills/frontend-design/SKILL.md. Intent is clear: include a reference. Kept.

### Architecture Notes

- type:docs task producing a single .prompt.md file. No code changes, no module layering concerns, no security surface, no failure modes.
- TDD not applicable: pure documentation/prompt file, verified by inspection only.
- Follows existing prompt format precedent: orchestrate.prompt.md uses description+agent frontmatter, agent-audit.prompt.md uses description-only. AC correctly specifies description-only.
- Output file docs/design-context.md does not yet exist (confirmed). It will be created by the prompt at runtime, consumed by downstream tasks #944-#946.
- Dependency #934 (frontend-design skill) archived. Skill confirmed at .github/skills/frontend-design/SKILL.md.
- Single domain: copilot/docs. No multi-domain concern.

### Changes Made

- Approved #943 to todo.

### Dependencies

- Verified: #934 (frontend-design skill) archived
- Verified: #944, #945, #946 depend on #943 as downstream consumers
- No new dependencies needed

[[2026-03-24]] Tue 02:53

## Architecture Review

**Verdict:** Approved

### AC Assessment

- AC1: Add .github/prompts/design-context.prompt.md with description-only frontmatter -> Clear, verifiable. Matches agent-audit.prompt.md precedent (description-only). Kept.
- AC2: Prompt inspects repo context, asks only missing questions (users, jobs, tone, references, anti-references, accessibility) -> Behavioral spec with 6 named categories. Verifiable by reading prompt body. Kept.
- AC3: Prompt writes/updates docs/design-context.md with 7 stable sections -> All 7 sections enumerated (Users, Jobs, Tone, References, Anti-References, Accessibility, Design Principles). Verifiable by inspection. Kept.
- AC4: Prompt does not mention .impeccable.md or edit copilot-instructions.md -> Negative constraint, verifiable by grep. Kept.
- AC5: Prompt can reference frontend-design skill by relative path when skill exists -> Dependency #934 archived, skill exists at .github/skills/frontend-design/SKILL.md. Intent is clear: include a reference. Kept.

### Architecture Notes

- type:docs task producing a single .prompt.md file. No code changes, no module layering concerns, no security surface, no failure modes.
- TDD not applicable: pure documentation/prompt file, verified by inspection only.
- Follows existing prompt format precedent: orchestrate.prompt.md uses description+agent frontmatter, agent-audit.prompt.md uses description-only. AC correctly specifies description-only.
- Output file docs/design-context.md does not yet exist (confirmed). It will be created by the prompt at runtime, consumed by downstream tasks #944-#946.
- Dependency #934 (frontend-design skill) archived. Skill confirmed at .github/skills/frontend-design/SKILL.md.
- Single domain: copilot/docs. No multi-domain concern.

### Changes Made

- Approved #943 to todo.

### Dependencies

- Verified: #934 (frontend-design skill) archived
- Verified: #944, #945, #946 depend on #943 as downstream consumers
- No new dependencies needed

[[2026-03-24]] Tue 02:53

## Architecture Review

**Verdict:** Approved

### AC Assessment

- AC1: Add .github/prompts/design-context.prompt.md with description-only frontmatter -> Clear, verifiable. Matches agent-audit.prompt.md precedent (description-only). Kept.
- AC2: Prompt inspects repo context, asks only missing questions (users, jobs, tone, references, anti-references, accessibility) -> Behavioral spec with 6 named categories. Verifiable by reading prompt body. Kept.
- AC3: Prompt writes/updates docs/design-context.md with 7 stable sections -> All 7 sections enumerated (Users, Jobs, Tone, References, Anti-References, Accessibility, Design Principles). Verifiable by inspection. Kept.
- AC4: Prompt does not mention .impeccable.md or edit copilot-instructions.md -> Negative constraint, verifiable by grep. Kept.
- AC5: Prompt can reference frontend-design skill by relative path when skill exists -> Dependency #934 archived, skill exists at .github/skills/frontend-design/SKILL.md. Intent is clear: include a reference. Kept.

### Architecture Notes

- type:docs task producing a single .prompt.md file. No code changes, no module layering concerns, no security surface, no failure modes.
- TDD not applicable: pure documentation/prompt file, verified by inspection only.
- Follows existing prompt format precedent: orchestrate.prompt.md uses description+agent frontmatter, agent-audit.prompt.md uses description-only. AC correctly specifies description-only.
- Output file docs/design-context.md does not yet exist (confirmed). It will be created by the prompt at runtime, consumed by downstream tasks #944-#946.
- Dependency #934 (frontend-design skill) archived. Skill confirmed at .github/skills/frontend-design/SKILL.md.
- Single domain: copilot/docs. No multi-domain concern.

### Changes Made

- Approved #943 to todo.

### Dependencies

- Verified: #934 (frontend-design skill) archived
- Verified: #944, #945, #946 depend on #943 as downstream consumers
- No new dependencies needed

[[2026-03-24]] Tue 03:31

## Test-Writer Notes

- Non-implementation task (tagged type:docs) — no tests applicable.
- Architecture review explicitly states: TDD not applicable, pure documentation/prompt file, verified by inspection only.
- Passing through to builder.

[[2026-03-24]] Tue 16:23

## Audit

### AC Verification

AC1: File exists with description-only frontmatter. PASS.
AC2: Step 1 scans repo context, Step 2 asks only missing questions for all 6 categories. PASS.
AC3: Step 3 template has all 7 sections (Users, Jobs, Tone, References, Anti-References, Accessibility, Design Principles). PASS.
AC4: No .impeccable.md mention; copilot-instructions.md read only, editing explicitly forbidden in Rules. PASS.
AC5: Line 61 references .github/skills/frontend-design/SKILL.md. PASS.

### Test Results

- Full suite: 4235 passed, 39 failed (all pre-existing), 20 skipped
- ruff: All checks passed

### Commit Verification

- 2cda971 docs: add design-context onboarding prompt (#943, writer) -- 1 file, 113 insertions

### AC Quality Score: 4/5

### Confidence: .97

### Action: archive
