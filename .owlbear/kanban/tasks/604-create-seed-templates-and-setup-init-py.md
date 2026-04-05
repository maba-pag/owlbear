---
id: 604
title: Create seed/ templates and setup/init.py
status: in-progress
priority: needed
created: 2026-04-04T20:31:05.5323847+02:00
updated: 2026-04-04T23:50:43.9227539+02:00
tags:
    - scope:infra
    - type:build
    - phase-2
parent: 598
depends_on:
    - 600
    - 603
class: standard
---

## Summary

Create seed/ directory with template files that mirror the target project structure. Create setup/ directory with init.py (replacing scripts/setup.py) and user docs.

## Acceptance Criteria

### Seed Templates (static + placeholder files)

- [ ] AC1: seed/.vscode/settings.json -- JSON template with `chat.agentFilesLocations`, `chat.agentSkillsLocations`, `chat.instructionsFilesLocations` keys. Path values use `{{owlbear_path}}` double-brace placeholder (e.g., `{{owlbear_path}}/share/agents: true`).
- [ ] AC2: seed/.vscode/mcp.json -- JSON template. Server keys: `github` (http), `owlbear-kanban`, `owlbear-knowledge`, `owlbear-memory`, `owlbear-project` (kebab-case). Stdio servers include `--project, {{owlbear_path}}` in args array.
- [ ] AC3: seed/.owlbear/kanban/config.yml -- Static file. next_id: 1, standard statuses matching current board config.
- [ ] AC4: seed/.owlbear/kanban/setup.ps1 -- Static file. Copy of current kanban/setup.ps1.
- [ ] AC5: seed/.owlbear/hooks/deny-writes.ps1 and lint-changed.ps1 -- Static files. Copies of current scripts/hooks/ hook scripts.
- [ ] AC6: seed/.owlbear/knowledge/.gitkeep -- Empty directory marker file.
- [ ] AC7: seed/owlbear-project.json -- JSON template with `{{name}}` and `{{type}}` placeholders. `schema_version: 1` hardcoded. `owlbear_path` and `created_at` are computed by init.py at runtime (NOT template placeholders).

### Setup Script (init.py replaces scripts/setup.py)

- [ ] AC8: setup/init.py created with function `init(target_dir: Path, owlbear_dir: Path, *, name: str | None = None, project_type: str = bare)`. Walks seed/ tree, copies static files to target, replaces `{{placeholder}}` tokens in .json/.yml templates. Generates computed fields for owlbear-project.json (owlbear_path via os.path.relpath, created_at via datetime.now(tz=UTC)). CLI: `python ../owlbear/setup/init.py [--name NAME] [--type TYPE]` with `if __name__ == __main__` guard. Idempotent: skips existing mcp.json and owlbear-project.json; merges settings.json per AC12; creates directories idempotently. Excludes seed/scratch-pad.txt from template walk.
- [ ] AC9: setup/init.py does NOT create .github/ in target projects (copilot-instructions.md creation removed -- target projects create their own).
- [ ] AC12: Deep merge for `chat.*Locations` keys in settings.json: when existing settings.json contains a `chat.*Locations` key, merge inner path dicts (union of owlbear + user paths). User path values (bool) take priority over owlbear defaults for same-path keys. Non-Location keys use shallow merge (owlbear keys as defaults, existing user keys override).

### Doc Moves

- [ ] AC10: docs/setup-guide.md to setup/setup-guide.md via git mv. Content unchanged (path updates belong to #607).
- [ ] AC11: docs/sharing-guide.md to setup/sharing-guide.md via git mv. Content unchanged (path updates belong to #607).

## Notes

- Template vs. computed distinction: seed/ defines the file tree structure and static content. Template files (.json, .yml) use `{{placeholder}}` double-brace syntax for simple string replacement. Computed values (owlbear_path from os.path.relpath, created_at from datetime) are generated in Python -- they are NOT template placeholders.
- seed/scratch-pad.txt is an existing VS Code focus helper, not a project template. init.py must skip it during template walk.
- scripts/setup.py deletion is NOT in scope. Deletion owned by #609 (post-migration cleanup). Both files may coexist temporarily.
- Cross-task sequencing (#603 AC8): #603 AC8 says docs/ folder deleted but docs/setup-guide.md and docs/sharing-guide.md are still present until AC10/AC11 here. Since #604 depends on #603, the builder for #603 must leave docs/ with only those two files. Final docs/ deletion deferred to #609.
- No OwlbearProjectFile dependency: init.py generates owlbear-project.json via plain json.dumps (not Pydantic model). The model in mcp-project is for read-time validation, not generation.

[[2026-04-04]] Sat 22:26
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Seed templates + init.py are tightly coupled (data + processor). Doc moves (AC10/AC11) are ancillary to setup/ directory creation. |
| Interface clarity | PASS (refined) | All 12 AC items now specify: placeholder syntax (double-brace), function signature, CLI invocation, idempotency contract, merge semantics. |
| Dependency correctness | PASS (with cross-task note) | #600 provides share/ paths for template references, #603 provides .owlbear/ structure. Cross-task issue: #603 AC8 cannot fully delete docs/ until AC10/AC11 here complete -- documented in Notes. |
| Module layering | PASS | setup/init.py is a standalone script using pathlib, json, os. No package imports from serve/ (OwlbearProjectFile not used). |
| TDD compliance | PASS | type:build tag, produces testable Python. Test-writer will process at todo. Existing tests in test_setup_script.py cover similar API; #608 handles test migration. |
| KISS/YAGNI | PASS | Template walk + string replacement is simpler than current 180-line hardcoded approach. Computed values (3 fields) remain in Python. No template engine dependency. |
| Premise challenge | PASS | Current scripts/setup.py needs replacement per decision doc (scripts/ being eliminated). Data-driven approach validated by decision doc. |
| Pattern consistency | PASS | init() signature mirrors current setup() signature. CLI invocation pattern (python path/init.py) follows convention. |
| Security surface | PASS | Reads only from local seed/ dir (trusted). Writes to user-specified target dir. No external APIs. owlbear_path computed via os.path.relpath (no path traversal risk -- both dirs are user-provided local paths). |
| Single domain | PASS | scope:infra. Project bootstrapping infrastructure. |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| os.path.relpath cross-drive | Windows cross-drive paths | ValueError | Pre-existing -- documented in setup-guide.md | Setup fails with clear error |
| seed/ dir not found | init.py run from wrong location | FileNotFoundError | AC8: owlbear_dir auto-detection from __file__ | Setup fails -- user error |
| settings.json parse | Malformed existing JSON | json.JSONDecodeError | Not in AC -- builder should handle | Merge fails instead of overwriting |
| Template walk | seed/scratch-pad.txt | N/A | AC8: explicit exclusion | Unwanted file in target |

### Refinements Applied

1. AC1, AC2, AC7: Placeholder syntax specified -- double-brace `{{placeholder}}`
2. AC7: Distinguished template placeholders (name, type) from computed values (owlbear_path, created_at)
3. AC8: Function signature specified: init(target_dir, owlbear_dir, *, name, project_type)
4. AC8: CLI invocation specified: python ../owlbear/setup/init.py [--name] [--type]
5. AC8: Idempotency contract: skip mcp.json/project.json, merge settings.json, mkdir idempotent
6. AC8: seed/scratch-pad.txt exclusion specified
7. AC9: Clarified copilot-instructions.md is intentionally removed (targets create their own)
8. AC12: Deep merge semantics: inner-dict union for chat.*Locations, user values win on conflict, shallow merge for other keys
9. Added cross-task note: #603 AC8 (docs/ deletion) must defer to #609 due to sequencing
10. Added note: scripts/setup.py deletion owned by #609, not this task
11. Added note: No OwlbearProjectFile dependency (plain json.dumps)

### Challenge Results

- Challenger: reconsider (confidence: 0.40)
- Concerns raised: (C1) docs/ deletion deadlock, (C2) false data-driven premise, (C3) scratch-pad.txt copied, (C4) setup.py unowned, (C5) deep merge incomplete, (C6) 12 AC items too many, (B1) package ambiguity, (B2) CLI undefined, (B3) idempotency undefined, (B4) Pydantic dependency
- Architect response: Accepted C1-C5, B2-B3 via AC refinements; overridden C6 (seed + init.py are one logical unit)
  - C1: Cross-task note added; #603 must leave 2 files, #609 owns final deletion
  - C2: AC8 now distinguishes template walk (static copies + placeholder replacement) from computed values (Python-generated)
  - C3: AC8 specifies scratch-pad.txt exclusion
  - C4: Note added -- deletion owned by #609
  - C5: AC12 now specifies inner-dict union, user-wins-on-conflict, shallow for non-Location keys
  - C6: Override -- seed templates without processor are useless; this is one feature
  - B1: Acknowledged -- setup/ is not on Python path, naming collision unlikely
  - B2: AC8 now specifies CLI invocation pattern
  - B3: AC8 now specifies idempotency contract
  - B4: Note added -- init.py uses plain json.dumps, no Pydantic dependency

### Verdict: APPROVE
### Action Taken: Rewrote all 12 AC lines with precise specifications. Added 5 operational notes. Documented cross-task sequencing issue. Advanced to todo.

[[2026-04-04]] Sat 22:26
APPROVED #604 -> todo | Create seed/ templates and setup/init.py. Rewrote all 12 AC lines with precise specs: double-brace placeholder syntax, init() function signature, CLI invocation pattern, idempotency contract, deep merge semantics (inner-dict union for chat.*Locations). Documented cross-task sequencing (#603 AC8 must defer docs/ deletion to #609). Challenger overridden (0.40) -- all 10 concerns addressed via AC refinements and operational notes.

[[2026-04-04]] Sat 23:50
## Test-Writer Notes
- Test file: tests/test_setup_init.py
- Classes: TestFromAC_SeedSettingsTemplate, TestFromAC_SeedMcpTemplate, TestFromAC_SeedKanbanConfig, TestFromAC_SeedSetupPs1, TestFromAC_SeedHooks, TestFromAC_SeedKnowledgeGitkeep, TestFromAC_SeedOwlbearProjectJson, TestFromAC_InitFunction, TestFromAC_NoGithubDir, TestFromAC_SettingsDeepMerge, TestFromAC_CliInterface
- Tests per category: happy 20, edge 8, error 6, boundary 12
- Total: 46 tests, all FAIL
- ruff: clean
- AC coverage: AC1 (5), AC2 (5), AC3 (3), AC4 (1), AC5 (2), AC6 (1), AC7 (5), AC8 (17 — function + CLI), AC9 (1), AC12 (5)
