---
name: h-codebase-orientation
description: "Handbook: Discover project context, locate code, and choose navigation or proof tools"
user-invocable: false
---

# Codebase Orientation

Use the smallest navigation aid that can locate the relevant artifact, module, or symbol. Generated
indexes and Semble are wayfinders, not authorities. Read the source before making a claim or edit.

## Establish Project Context

Local project instructions describe only the current project's identity, topology, stack, commands,
and primary resources. Read them when those facts affect the task, then verify load-bearing details
against manifests, configuration, source, or executable commands.

Use this order to establish context without turning local instructions into universal policy:

1. Project identity and intended use: local project instructions and root README.
2. Package boundaries and toolchains: manifests such as `pyproject.toml` and `package.json`.
3. Current structure and interfaces: generated indexes, then direct source reads.
4. Shared OwlBear behavior: shared agents, skills, and instructions, never copied project notes.

## Use Existing Indexes

When present, these committed artifacts are optional wayfinders:

| Artifact | Contents | Best use |
| --- | --- | --- |
| `.owlbear/doc-index.md` | Documentation paths, headings, and outbound links | Find the document that owns a topic. |
| `.owlbear/py-index.md` | Python modules, imports, classes, methods, and functions | Inspect package shape and likely interfaces. |
| `.owlbear/ts-index.md` | TS/TSX/JS/JSX modules, imports, exports, and interfaces | Inspect frontend or script structure. |

`doc-index` also has a workflow-specific role: `.owlbear/prompts/doc-audit.prompt.md` requires
regenerating it before scanning and again during closeout. The Python and ECMAScript indexes remain
optional, on-demand orientation aids; none of these artifacts is regenerated automatically by
pre-commit or CI.

The artifacts are advisory. Source files remain authoritative. Search indexes with `rg`; do not load
an entire index when one path, symbol, or topic query will do.

Do not regenerate indexes during ordinary orientation. A stale or missing index is a reason to use
exact source search or another rung of the orientation ladder, not to mutate the working tree.
Regenerate the fixed index artifacts only when index maintenance is itself part of the requested
work, following `r-workspace-governance` for artifact ownership.

```text
uv run --project {owlbear-root} indexes {project-root}
```

## Find the Test Boundary

When a repository contains multiple package roots or test runners, resolve the owning test boundary:

```text
uv run --project {owlbear-root} test-root {test-or-source-path}
```

The command returns `test_path`, `cwd`, `toolchain`, and the base test command. Use the result to run
the narrowest relevant check from the correct package directory. Multiple paths may be passed in one
call. The result is orientation, not proof; the executed test or lint command is the evidence.

## Orientation Ladder

Stop at the first adequate option:

1. **Known file or symbol:** read it directly. Use language-server references when callers matter.
2. **Documentation topic:** search `.owlbear/doc-index.md`, then read the candidate document.
3. **Known language or module area:** search an existing `.owlbear/py-index.md` or
   `.owlbear/ts-index.md`, or search source directly, then read the candidate source.
4. **Exact text, symbol, path, or exhaustive claim:** use `rg`, file search, or language-server
   references against source.
5. **Unknown behavioral owner or analogous implementation:** use Semble once to obtain a small set of
   candidates, then read source.

Do not call Semble when a known file, symbol, index result, or exact search already provides a
credible anchor. Do not repeat a Semble query after it returns a usable location.

## Semble

Use focused questions:

- Which module likely owns this behavior?
- Where is a similar validation, concurrency, cache, or API pattern implemented?
- What implementation should be read first in this unfamiliar area?

```text
uv run --project {owlbear-root} semble search "behavior or symbol" {project-root} --top-k 5
uv run --project {owlbear-root} semble find-related path/to/file.py 42 {project-root} --top-k 5
```

For an approved external-repository clone, use its path under `.owlbear/scratch/research/`. The
research workflow controls clone approval, recording, and cleanup.

## Discovery Is Not Proof

1. Treat index and Semble results as candidates.
2. Read returned source directly before claiming behavior, ownership, or interface shape.
3. Use `rg`, language-server references, direct reads, or focused tests for exhaustive claims: every
   caller, every implementation, absence, exact configuration use, and affected tests.
4. Cite source or command evidence, never a generated-index entry, ranking, or savings metric.
5. Stop after one or two focused searches. If ownership remains unclear, follow the caller's role
   boundary rather than broadening indefinitely.

## Companion Skills

| Skill | Load when |
| --- | --- |
| `h-module-design` | Source evidence requires judging module depth, locality, seams, or dependency placement rather than locating code |
| `r-workspace-governance` | Creating or committing OwlBear-managed artifacts |
