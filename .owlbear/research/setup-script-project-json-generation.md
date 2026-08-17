# Setup Script owlbear-project.json Generation

> **Owning task:** #69 — Add owlbear-project.json generation to setup script
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #69 adds owlbear-project.json generation to the setup script (#12). The schema is defined (#53, archived) and the Pydantic model is in progress (#68). This research validates the implementation approach for: relative path computation, project metadata input method, idempotency pattern, cross-platform path handling, and dependency ordering.

**Key questions:** How should `owlbear_path` be computed cross-platform? How does the setup script obtain `name` and `type`? What's the correct write-then-validate pattern?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Python `os.path.relpath` docs | <https://docs.python.org/3/library/os.path.html#os.path.relpath> | .95 |
| 2 | Python `pathlib.PurePath.as_posix()` docs | <https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.as_posix> | .90 |
| 3 | npm init behavior | <https://docs.npmjs.com/cli/v10/commands/npm-init> | .80 |
| 4 | v1 ProjectWorkspace scaffolder | `v1/src/owlbear/projects/workspace.py` | .85 |
| 5 | Schema spec | `docs/research/owlbear-project-json-schema.md` | 1.0 |
| 6 | #68 model research | `docs/research/owlbear-project-file-model-impl.md` | .95 |

## 3. Analysis

### 3.1 Relative Path Computation — `owlbear_path`

| Approach | API | Cross-platform | KISS |
|----------|-----|----------------|------|
| **A: `os.path.relpath` + `as_posix()` (.90)** | `PurePath(os.path.relpath(owlbear, project)).as_posix()` | Forward slashes always | **High** |
| B: `Path.relative_to(walk_up=True)` (.70) | `owlbear.resolve().relative_to(project.resolve(), walk_up=True)` | Needs `.as_posix()` too; resolves symlinks (side effect) | Medium |
| C: `os.path.relpath` raw (.60) | `os.path.relpath(owlbear, project)` | Backslashes on Windows — breaks JSON config consumers | Low |

**Recommendation (.90):** Option A. `os.path.relpath` is a pure string computation (no filesystem access, Source 1). Wrapping in `PurePath().as_posix()` normalizes to forward slashes (Source 2), which VS Code MCP configs require. `Path.relative_to(walk_up=True)` resolves symlinks unnecessarily and is newer API (3.12).

**Example:** `PurePath(os.path.relpath(Path("C:/code/owlbear"), Path("C:/code/my-project"))).as_posix()` → `"../owlbear"`.

### 3.2 Project Metadata Input Method (`name`, `type`)

| Approach | Pattern | Automation-safe | KISS |
|----------|---------|-----------------|------|
| **A: argparse with defaults (.85)** | `--name` (default: dir name), `--type` (default: `bare`) | Yes | **High** |
| B: Interactive prompts (.55) | `input("Project name: ")` | No — blocks in CI | Low |
| C: Infer only (.70) | name from dirname; type from heuristics | Partial — type detection is fragile | Medium |

**Recommendation (.85):** Option A. `npm init -y` (Source 3) infers name from directory, defaults other fields. v1's `ProjectWorkspace.create_project(name, template)` takes both as explicit parameters (Source 4). Argparse with sensible defaults gives both automation safety and interactive convenience.

Defaults: `name` = `Path.cwd().name`, `type` = `bare`. The setup script (`scripts/setup.py`) already takes no args per #12 AC — adding optional `--name`/`--type` flags is backwards-compatible.

### 3.3 Idempotency Pattern

AC: "does not overwrite existing file". Pattern:

```python
path = Path("owlbear-project.json")
if path.exists():
    print("owlbear-project.json already exists, skipping")
    return
```

Matches `npm init` behavior (Source 3) and #12's idempotency AC. Simple `exists()` check before write — no need for file locking or atomic writes (single-user local tool).

### 3.4 Validation via Model Construction

AC: "Validates output against OwlbearProjectFile model before writing". The cleanest pattern is construct-then-serialize:

```python
project = OwlbearProjectFile(
    schema_version=1,
    name=name,
    type=project_type,
    owlbear_path=owlbear_path,
    created_at=datetime.now(tz=UTC),
)
path.write_text(project.model_dump_json(indent=2), encoding="utf-8")
```

Pydantic validates on construction (Source 6) — if the constructor succeeds, the data is valid. No separate validation call needed. Use `model_dump_json(indent=2)` for human-readable output matching the schema example (Source 5, §3.6).

### 3.5 Dependency Chain

| Task | Status | Relationship to #69 |
|------|--------|---------------------|
| #68 (Pydantic model) | backlog | **Direct dependency** — #69 imports the model |
| #74 (TDD tests for model) | ideation | Indirect — #68 depends on #74 |
| #12 (setup script) | ideation | **Parent task** — #69 is one step in #12's scope |
| #7 (monorepo skeleton) | ideation | Transitive — #68 → #41 → #7 |

**Gap:** #69 has no `depends_on` set. It must depend on #68 (the model must exist to import). It does NOT depend on #12 completing — #69 is a focused subtask that can be built into the setup script independently.

## 4. Recommendation (.90 confidence)

Use `os.path.relpath()` + `PurePath.as_posix()` for cross-platform relative path computation. Accept `name` and `type` via argparse with sensible defaults (dirname and `bare`). Use Pydantic construct-then-serialize for validation. Simple `Path.exists()` guard for idempotency. Set `depends_on: [68]`.

**Risks:**
- Setup script (#12) doesn't exist yet — builder must create the generation function even if the full script isn't ready. Mitigation: implement as a standalone function callable from any entry point.
- `os.path.relpath` raises `ValueError` on Windows when paths are on different drives (Source 1). Mitigation: document that owlbear and project must be on the same drive; this is the expected case.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Test: owlbear-project.json generation in setup script" --priority needed --status ideation --tags "phase-1,scope:cli,test" --body "## Objective\nTDD RED phase: write failing tests for owlbear-project.json generation before builder implements.\n\n## Test Scenarios\n- [ ] Generates valid owlbear-project.json with all 5 required fields\n- [ ] schema_version is 1\n- [ ] owlbear_path is a forward-slash relative path (even on Windows)\n- [ ] created_at is timezone-aware UTC ISO 8601\n- [ ] Idempotent: does not overwrite existing file\n- [ ] Output validates against OwlbearProjectFile model\n- [ ] Name defaults to directory name when not provided\n- [ ] Type defaults to bare when not provided\n- [ ] Explicit name and type override defaults\n\n## Context\nParent impl task: #69.\nModel: OwlbearProjectFile from #68.\nSee docs/research/setup-script-project-json-generation.md."
```
