# Frontend-Design Skill RED Test Gate

> **Owning task:** #941 - Add RED tests for frontend-design skill discovery and reference pack
> **Date:** 2026-03-22 **Status:** Complete

## 1. Context and Question

Task #941 is the RED gate for the new `frontend-design` skill package that #934
will add. The package does not exist yet, so the decision is not "how do we
test a finished skill?" but "what is the smallest checked-in contract that
should fail now and turn green only when #934 lands?" The main choice is
whether to keep this coverage in generic temp-directory registry tests, update
only the real-skill count, or add a dedicated repo-path test file for the
future package [S1, S2, S3, S4].

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | `docs/research/frontend-design-skill-implementation-gate.md` | .95 | #934 package shape, the seven required references, and why #941 exists as the RED predecessor |
| S2 | `tests/test_skills.py` | .95 | Current real-repo discovery contract: hard-coded count of 19 plus list-skills coverage |
| S3 | `tests/test_project_definition_skill.py` | .95 | Existing skill-specific test pattern using repo-relative paths and direct frontmatter assertions |
| S4 | `src/owlbear/skills/registry.py` | .90 | Discovery rule is one-level `*/SKILL.md`; frontmatter parse is the seam the tests should exercise |
| S5 | VS Code Agent Skills docs | .95 | Required skill directory layout, `name` or `description` frontmatter, and relative resource files inside the skill directory |
| S6 | Anthropic `frontend-design` skill tree | .75 | Minimal precedent: a `frontend-design` skill can be a single `SKILL.md` package without extra local resources |
| S7 | Impeccable `frontend-design` skill tree | .90 | Reference-pack precedent: `SKILL.md` plus a companion reference directory for deeper design guidance |
| S8 | `kanban/tasks/938-add-owlbear-frontend-anti-pattern-taxonomy.md` | .70 | Later sibling work may add more frontend-design resources, so #941 should test only the required contract |

## 3. Options

| Option | Confidence | What changes | Pros | Risks | Verdict |
|--------|:----------:|--------------|------|-------|---------|
| A. Update only `tests/test_skills.py` to 20 | .42 | Change the real-skill count and list-skills assertions | Smallest diff | Misses file-level contract for `SKILL.md`, frontmatter, and required references | Reject |
| B. Add `tests/test_frontend_design_skill.py` and update `tests/test_skills.py` | .95 | New repo-path package test plus count change from 19 to 20 | Matches the checked-in skill contract and naturally fails until #934 lands | Depends on a package that does not exist yet, which is the intended RED state | Recommend |
| C. Keep coverage in temp-fixture registry tests only | .28 | Add more synthetic `tmp_path` skill fixtures | Isolated and easy to author | Can pass without the real `.github/skills/frontend-design/` package ever existing | Reject |

## 4. Findings

1. `#941` should add a dedicated repo-path test file, not rely only on
   temp-fixture registry tests. `SkillRegistry` discovers checked-in
   `*/SKILL.md` files and VS Code treats the skill directory as the unit that
   owns both `SKILL.md` and local resources, so the RED contract must fail on
   the actual `.github/skills/frontend-design/` path until #934 creates it
   [S3, S4, S5, S7].
2. The real-skill discovery regression belongs in `tests/test_skills.py`. That
   file already asserts the live `.github/skills` inventory and `list_skills()`
   output, so changing the three `19` expectations to `20` is the correct
   integration guard for the new package [S1, S2, S4, S5].
3. The new file should assert the required package facts and stop there:
   `SKILL.md` exists, frontmatter parses, `name == "frontend-design"`,
   description is non-empty, and the seven named `references/*.md` files exist.
   Do not add assertions for optional `NOTICE.md`, anti-pattern resources, or
   other future files, because those are either optional in #934 or owned by
   sibling task #938 [S1, S3, S7, S8].
4. RED should be obvious and local. Mirroring `tests/test_project_definition_skill.py`
   means the missing package fails via `Path.exists()` or
   `_parse_frontmatter(...) is None` immediately, while `tests/test_skills.py`
   fails separately on the stale real-skill count of 19 [S2, S3, S4].
5. While changing the count, update the stale human-facing labels in
   `tests/test_skills.py` too. The current class docstring says "18 skills"
   while the assertions already expect 19, so carrying those strings forward to
   20 without fixing the prose would leave the test intent misleading [S1, S2].

## 5. Recommendation (.95 confidence)

Use option B.

- Add `tests/test_frontend_design_skill.py` as a dedicated checked-in package
  test.
- Follow the same file-local pattern as `tests/test_project_definition_skill.py`:
  repo-root constant, direct path assertions,
  `SkillRegistry._parse_frontmatter(...)`, and raw text reads only where
  needed [S3, S4].
- In that file, assert only the task-scoped contract:
  - `.github/skills/frontend-design/SKILL.md` exists
  - frontmatter parses
  - `name` is `frontend-design`
  - description is non-empty
  - the seven required files under `.github/skills/frontend-design/references/`
    exist
- Update `tests/test_skills.py` to expect 20 discovered real skills in the
  three live assertions and keep `list_skills()` coverage on the real
  directory [S2, S4].
- Do not add temp fixtures, shared helpers, or broader content assertions for
  the skill body. Those would either test the wrong seam or exceed #941's
  RED-only scope [S1, S2, S3].

This gives #934 a clean GREEN target: when the skill package lands, the new
file turns green, the real-skill count moves from 19 to 20, and no optional
sibling-work contract is accidentally frozen early [S1, S2, S8].

## 6. Follow-up Tasks

1. Existing task: #941 - Add RED tests for frontend-design skill discovery and reference pack.
   Priority: nice-to-have. Dependency role: RED predecessor before #934 GREEN work. AC: add `tests/test_frontend_design_skill.py`, update the real-skill count assertions in `tests/test_skills.py` from 19 to 20, verify `frontend-design` frontmatter, and assert the seven required reference files exist.
2. No new kanban task was created. Reason: #941 already captures the full RED change, and #934 already exists as the paired GREEN consumer. Splitting further would create overlapping test tasks without new implementation leverage.
