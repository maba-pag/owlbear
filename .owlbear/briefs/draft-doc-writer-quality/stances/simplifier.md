# Simplifier Stance — doc-writer quality

## Scope Cuts

### Cut 1: Drop outcome #2 (module-level docstring verification)

The problem statement is about READMEs being stale and diagrams being verification theater. Module-level docstrings are a *new* responsibility that the doc-writer never had and nobody complained about. Adding it here conflates "fix the broken thing" with "add a nice-to-have while we're in there." If docstring quality matters, it's a separate task with its own acceptance criteria.

**Severity: high.** This outcome increases the skill's read surface (every modified `.py` file), adds a new verification dimension orthogonal to the README problem, and makes the agent slower without addressing the root cause.

### Cut 2: Drop outcome #5 (tiered speed)

This is not a deliverable — it's a restatement of "do #1 and #4." Calling it an outcome inflates the apparent scope and creates a false sense of additional work. The tiering emerges mechanically from having a bounded per-task gate (#1) and a periodic audit (#4). No artifact, skill section, or code corresponds to "tiered speed" as a standalone outcome.

**Severity: low** (cosmetic, but worth naming to keep the brief honest).

## Decomposition Pressure

### Split doc-audit (#4) into its own task

Outcome #4 (doc-audit periodic prompt) has zero dependency on outcomes #1 and #3. It's a new `.prompt.md` file with its own acceptance criteria. Bundling it with the doc-writer refactor means the brief ships a two-concern deliverable: "fix the pipeline gate" + "create an audit workflow." These are different authors, different review criteria, and different risk profiles.

**Recommended decomposition:**

- **P1 task (the actual fix):** Outcomes #1 + #3 — rewrite `w-doc-update` to read full README, remove diagram responsibility. This is the root-cause fix and should ship alone.
- **P2 task:** Outcome #4 — create `doc-audit.prompt.md` as a periodic deep-sweep tool. Can be designed and tested independently.

### Boundary correction on #1

"Flags pre-existing issues as follow-up kanban tasks" sounds clean in prose but is operationally tricky. The doc-writer runs per task. If three tasks touch the same package in a sprint, does each one create duplicate follow-up tasks for the same pre-existing issue? The brief needs a dedup mechanism or a simpler rule: **flag once per README per audit cycle, not per task.** Alternatively, just log the finding in the task's Docs Gate section and let doc-audit handle the follow-up creation — this avoids giving the doc-writer kanban-write authority it doesn't currently have.

## What's Already Simple Enough

- Outcome #3 (remove diagram work) is a clean subtraction. No challenge.
- The root-cause diagnosis is correct and well-evidenced. The fix direction (read the whole file, not just the diff) is right.

## Confidence

**0.82** — high confidence in cut #1 and the P1/P2 split. Moderate uncertainty on the dedup boundary for follow-up flagging, which needs a concrete rule before the brief locks.
