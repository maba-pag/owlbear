# Research Notes — doc-writer quality

## Verified Findings

### F1: Doc-writer has no systematic README↔code mapping

The `w-doc-update` skill (Step 1) builds the changed-files set from task body sections (`## Files`, `## Builder Notes`, `## Review Evidence`). But there is no systematic mapping from "this code file changed" → "these READMEs describe it." The doc-index has `describes` fields only for `.excalidraw` diagrams, not for READMEs. The doc-writer must use LLM judgment to guess which READMEs are affected, which is unreliable.

### F2: Doc-writer never reads README content for verification

Item 1 of the checklist says "read each affected doc, verify accuracy, update as needed" but the mechanism for identifying affected docs is so weak (F1) that the agent almost always resolves to "no prose docs affected." The agent has the *instruction* to verify but lacks the *infrastructure* to find what to verify.

### F3: doc-audit.prompt.md exists at `.owlbear/prompts/doc-audit.prompt.md`

Located in the `.owlbear/prompts/` directory (project-specific, not in `share/prompts/`). Has a comprehensive 8-dimension audit framework (Structural, Duplication, Placement, Accuracy, Coverage, Currency, Cross-Reference, Audience Fitness). Does NOT do signature/code-block verification. Currently emits one remediation task per finding.

### F4: doc-index skips code blocks

`_parse_markdown()` in `serve/tools/src/owlbear_tools/doc_index.py` explicitly skips fenced code blocks (`in_fenced = True` continues without parsing). Code blocks in READMEs (which contain API examples, method signatures) are invisible to the index.

### F5: `describes` field works well for diagrams

The doc-index already supports `describes` metadata for `.excalidraw` files, with glob patterns like `serve/kanban/src/**`. The doc-writer uses this for diagram checklist item 5. This same mechanism could be extended to READMEs.

### F6: Pipeline diagram references removed orchestrator

`pipeline.excalidraw` shows "orchestrator: supervisory layer (auxiliary)" at the top. The orchestrator was removed long ago. Footer reads "Last verified: 2026-05-05 (3cc2149f)" — the doc-writer stamped a verification date without checking diagram content.

### F7: Memory-layers diagram has rendering errors

Text clipping on right side ("VS Code user d..." cut off). "dual-write migration" text overlaps "Canonical replaces Repo Inbox." These are graphical quality issues, not content issues, but contribute to the perception that diagrams are low quality.

### F8: No PNG exports are embedded in READMEs

All 7 diagrams have user-created PNG screenshots alongside the `.excalidraw` files, but no README references or embeds these images. The diagrams exist as standalone files with no integration into the documentation they describe.

## Candidate Implications

### I1: Adding `describes` to READMEs would fix the mapping problem

If `serve/kanban/README.md` had a `describes: ['serve/kanban/src/**', 'serve/mcp-kanban/src/**']` field (like diagrams do), the doc-writer could mechanically determine: "task changed `serve/kanban/src/engine.py` → read `serve/kanban/README.md`." This reverses the current problem where the doc-writer never finds the README.

### I2: Structural verification needs a separate tool, not doc-index extension

Doc-index is a static analysis tool (language-agnostic). Adding Python signature comparison to it would violate its design. A separate verification module (reads doc-index, imports Python modules, extracts code blocks from READMEs, compares signatures) is cleaner. This could live in `serve/tools/` alongside `doc-index`.

### I3: TODO markers in docs need a convention

If the doc-writer inserts `<!-- TODO: [description] -->` markers, doc-audit needs to know how to find and interpret them. The convention should be stable, machine-parseable, and include enough context for doc-audit to act (e.g., `<!-- TODO(doc-writer): stale reference to orchestrator — removed in task #xyz -->`).

### I4: The doc-audit prompt may need significant revision

The existing doc-audit has 8 dimensions but doesn't cover signature verification, TODO marker resolution, or diagram content review. If the redesigned doc-writer creates TODO markers and the doc-audit must resolve them, the audit prompt needs new dimensions.

### I5: "Honest per-task gate" rate will drop from 90% no-op

The original brief explicitly targeted a 90/80% no-op rate. The redesigned doc-writer with full-file reading + TODO marking will have a significantly lower no-op rate. Tasks touching any `serve/*/src/` code will trigger README reads and potentially TODO inserts. This is the intended behavior change, not a bug.

## Open Research Questions

### Q1: How many READMEs have stale content right now?

We checked `serve/kanban/README.md` and found multiple issues. The other 8 `serve/*/README.md` files, the root README, and the consumer README have not been audited. A full audit would quantify the scope of pre-existing rot.

### Q2: Is Python `ast.parse` comparison practical at doc-writer runtime?

The doc-writer runs per task. If it needs to import Python modules or parse them with `ast` to compare against README code blocks, that adds runtime dependency and potential failure modes. An alternative is `grep`-based heuristics (simpler, less accurate but more robust).

### Q3: Should `describes` be in the doc-index or in the README frontmatter?

For diagrams, `describes` is metadata inside the `.excalidraw` JSON. For READMEs, it could be either (a) a YAML frontmatter field in the README itself, or (b) a configuration in the doc-index script. Frontmatter pollutes the README for human readers; script config is centralized but another file to maintain.

### Q4: What happens to the existing 7-item checklist?

Items 5-6 (diagram maintenance/creation) get removed. Items 1-4 and 7 remain but are restructured. The "full-file read + structural check + TODO marking" behavior replaces item 1. The overall checklist shape may change significantly.
