---
id: 787
title: Implement two-pass review checklist in code-review SKILL.md
status: archived
priority: needed
created: 2026-03-13T17:04:23.9569863+01:00
updated: 2026-03-13T19:42:51.9270883+01:00
started: 2026-03-13T19:42:20.5001003+01:00
completed: 2026-03-13T19:42:20.5001003+01:00
tags:
    - scope:agent-config
    - type:docs
class: standard
---

## Goal
Restructure code-review SKILL.md to use two-pass review with suppressions.

## AC
- [ ] Steps 5/5a/5b/5c reorganized under Pass 1 (CRITICAL) and Pass 2 (INFORMATIONAL) headers
- [ ] Pass 1 includes: security (5b), test integrity (5c WEAKENED/REMOVED), test quality (5a WEAK), data safety
- [ ] Pass 2 includes: style, documentation, minor test improvements, code structure
- [ ] New 'Suppressions' section with 9 DO-NOT-flag patterns
- [ ] reviewer.agent.md workflow summary updated to mention two-pass structure
- [ ] Review output format template updated with CRITICAL/INFORMATIONAL sections
- [ ] No changes to .py files

See docs/research/two-pass-review-checklist.md for analysis.

[[2026-03-13]] Fri 18:02
## Test-Writer Notes
- Non-implementation task (tagged type:docs, scope:agent-config)  no tests applicable.
- AC targets only .md files (SKILL.md, .agent.md). No .py files involved.
- Passing through to builder.

[[2026-03-13]] Fri 18:31
## Builder Notes
- Files changed: .github/skills/code-review/SKILL.md, .github/agents/reviewer.agent.md
- Tests: N/A (type:docs task, no .py changes)
- Lint: N/A
- Steps 5/5a/5b/5c reorganized under Pass 1 (CRITICAL) and Pass 2 (INFORMATIONAL)
- Pass 1: 5.1 Security, 5.2 Test integrity, 5.3 Test quality, 5.4 Data safety (new)
- Pass 2: 6.1 Code reading, 6.2 Documentation, 6.3 Minor test improvements, 6.4 Code structure
- Suppressions section: 9 patterns from research doc
- Verdict section updated to reference Pass 1/Pass 2 semantics
- Review output template restructured with CRITICAL/INFORMATIONAL sections
- reviewer.agent.md workflow summary updated

[[2026-03-13]] Fri 18:59
## Review Evidence - PASS .95 - all AC verified

[[2026-03-13]] Fri 18:59
## Review Evidence Detail

### Test/Lint/Coverage
N/A â€” type:docs task, no .py files changed.

### Pass 1 CRITICAL
No findings. Only .md files modified â€” no executable code, no security risks, no tests to compare, no data safety concerns.

### Pass 2 INFORMATIONAL
No findings. Files are clean and well-structured.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| Steps reorg under Pass 1/Pass 2 | SKILL.md L56 + L166 | PASS |
| Pass 1: security, test integrity, test quality, data safety | SKILL.md 5.1(L60), 5.2(L98), 5.3(L139), 5.4(L160) | PASS |
| Pass 2: style, docs, test improvements, code structure | SKILL.md 6.1(L170), 6.2(L181), 6.3(L186), 6.4(L191) | PASS |
| 9 Suppressions | SKILL.md L201-L213, items 1-9 match research doc | PASS |
| reviewer.agent.md workflow updated | reviewer.agent.md L69-73 mentions Pass 1, Pass 2, 9 suppressions | PASS |
| Review output template updated | SKILL.md L258 Pass 1 CRITICAL + L279 Pass 2 INFORMATIONAL | PASS |
| No .py changes | git diff HEAD --name-only *.py shows no task-related .py changes | PASS |

### Verdict: PASS (.95)

[[2026-03-13]] Fri 19:41
## Audit - .97 confidence - all 7 AC items PASS - archive

[[2026-03-13]] Fri 19:42
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 3f904a5 | docs | SKILL.md, reviewer.agent.md | #787 |
