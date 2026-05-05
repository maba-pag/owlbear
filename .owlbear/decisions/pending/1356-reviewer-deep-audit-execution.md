---
# >> Your action: set response to completed or rejected
response: completed
notes: "instructions are unreasonable. a user cannot seriously be asked to compare before and after and crerate a table with the changed and the JUSTIFICATION for the change if they dont know the reason. however, here are the reasonable metrics: file before: Tokens 1625, Characters 6925, after: Tokens 1632, Characters 6959. chat protocol see `.owlbear/scratch/1356-deep-audit-output.md`. please compare before/after yourself via git, changes are uncommitted."
request_type: action
task_id: 1356
agent: builder
created: 2026-05-05
urgency: blocking
---

# Action Request: Execute Deep Audit and Measure Reviewer Token Reduction

## Context

Task 1356 is an evaluation gate that depends on user execution of the reviewer-agent deep-audit workflow. No measurable token reduction or pipeline regression verification has been recorded yet. This action request formalizes the execution steps and completion criteria.

The goal is to systematically evaluate the reviewer agent against `share/prompts/agent-deep-audit.prompt.md`, quantify token savings, validate that no pipeline regression occurs, and document which noise-taxonomy categories were most effectively pruned.

## Steps

- [ ] **Step 1: Run the deep-audit prompt**
  - Execute `share/prompts/agent-deep-audit.prompt.md` against the reviewer agent
  - Save the full output to `.owlbear/scratch/1356-deep-audit-output.md`
  - Record the proposed cuts and per-section justification for each removal

- [ ] **Step 2: Quantify token reduction**
  - For each proposed cut, measure the token delta using VS Code token counter or prompt analyzer
  - Compile a table with: `Section | Original Tokens | Cut Tokens | Reduction % | Justification`
  - Calculate total baseline → post-cut token count
  - Document where the largest savings came from (e.g., examples section, historical context, repetition)

- [ ] **Step 3: Verify pipeline regression (no loss of function)**
  - Select one **known, previously passing reviewer task** (e.g., a recent code-review task that executed cleanly)
  - Apply the proposed cuts to the reviewer agent's instructions/skills
  - Re-run the reviewer on that same task with the pruned guidance
  - Verify the output quality, decision accuracy, and coverage remain equivalent or improve
  - Record pass/fail and any quality changes (e.g., "output was 3% shorter but identified same issues")

- [ ] **Step 4: Document noise-taxonomy findings**
  - Categorize each cut using the noise-taxonomy buckets: `redundancy`, `context-stack`, `example-bloat`, `historical-debt`, `meta-process`, `other`
  - Tally which categories appeared most frequently in the audit report
  - Identify if any category dominated (e.g., "50% of cuts were redundancy")
  - Note edge cases: what was over-cut or would have benefited from refinement instead

- [ ] **Step 5: Submit completion notes**
  - Record findings in the task body under `## Audit Execution Complete`
  - Include: token table, regression verification result, category histogram, and recommendations for final cut acceptance

## Completion Instructions

When all steps are complete, set `response: completed` and provide notes summarizing:
1. **Total token reduction**: baseline → final (absolute and %)
2. **Regression verdict**: pass or fail with evidence
3. **Dominant noise category**: top 1–3 categories by frequency
4. **Over-cut findings**: any cuts that seemed too aggressive or any omissions
5. **Recommendation**: proceed with cuts as-is, request modifications, or reject

Return to this DR file and update the frontmatter `response` and `notes` fields, then the scribe will unblock the task.
