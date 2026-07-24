---
description: "Run a read-only, evidence-calibrated frontend audit for an optional project scope"
---

# Frontend Audit

Run a read-only frontend audit and produce a ranked queue of actionable findings. This prompt is
for critique and task discovery only; do not edit source files.

Optional scope input: ${input:scope:Files or feature area to audit (optional)}

## Interaction Protocol

Use the user's language unless they ask otherwise. Present exactly one finding or decision at a
time before calling `askQuestions`; do not ask for one bulk decision across multiple findings.

For each finding, state:

- status quo and concrete evidence;
- user or product impact;
- options with pro, con, risk, and confidence;
- recommendation and expected outcome.

Use `(bp:)` for the best-practice option and `(rec:)` for the recommendation when useful. Continue
through the ranked queue until it is exhausted or the user pauses or stops. A completed queue is a
valid terminal condition; summarize it without manufacturing a continuation decision.

## Step 1 - Load standards and discover context

1. Read `../skills/h-frontend-design/SKILL.md`.
2. Read `../skills/h-frontend-conventions/SKILL.md`.
3. When test, lint, build, or browser evidence is relevant, load the project's applicable testing
   guidance and inspect its package scripts or equivalent configuration. Load
   `../skills/h-vitest-and-linting/SKILL.md` only when the project uses that toolchain.
4. Discover, rather than assume:
   - frontend package roots, framework, build tool, and test/browser tooling;
   - project design system, tokens, and established component patterns;
   - product audience, primary user jobs, brand or interaction intent, and supported viewports;
   - routes, navigation, or entry points that define the candidate user workflows.
5. Treat project documentation and established source patterns as context, then verify behavioral
   and visual claims against the running interface when possible.

Use `${input:scope}` when provided. Without it, select the primary user workflow supported by the
strongest route, navigation, or product evidence and state the rationale. If the repository contains
multiple materially different frontend applications and no primary target is evident, ask the user
to select one before continuing.

## Step 2 - Plan and scope

Before auditing, state:

1. The selected workflow or surface and its primary user goal.
2. Relevant states to inspect: normal, loading, empty, error, destructive or confirmation, and
   permission-limited states where the product supports them.
3. Applicable audit dimensions and project-specific conventions.
4. Available evidence levels and constraints that limit confidence.

## Step 3 - Execute audit

Trace the selected workflow end to end. Audit only dimensions relevant to that workflow:

1. Product fit and workflow completeness
2. Information hierarchy, content, and action clarity
3. Interaction behavior, state feedback, recovery, and destructive-action safety
4. Visual and design-system consistency
5. Responsive behavior at project-supported viewports
6. Accessibility blockers that prevent use or contradict project requirements
7. Test and proof adequacy for the behavior being claimed

Use this evidence ladder:

- **E1 - source evidence:** implementation, styles, configuration, or static test inspection;
- **E2 - runtime evidence:** component/integration execution with observable behavior;
- **E3 - browser evidence:** real layout geometry, interaction, viewport behavior, or screenshot.

Do not claim overlap, clipping, visibility, reachability, responsive correctness, or visual quality
from E1 evidence alone. Use E3 for those claims. If browser proof is unavailable, describe the
specific risk and confidence limit instead of presenting it as observed harm.

Record three independent attributes for every accepted finding:

- **Impact:** `critical`, `high`, `medium`, or `low`, based on affected user goal and frequency.
- **Confidence:** `high`, `medium`, or `low`, based on evidence level and reproducibility.
- **Type:** `objective defect` or `contextual heuristic`.

Reject taste-only findings that cannot be tied to the discovered audience, workflow, brand intent,
design system, or an observable usability cost. Distinguish observed harm from theoretical risk.
Rank objective defects before heuristics, then by impact, confidence, and breadth of affected users.

## Step 4 - Present and close

Present findings one at a time using the Interaction Protocol. Each finding must name the affected
workflow state, evidence level, impact, confidence, type, and concrete source or browser anchor.

For an approved follow-up, use the project's available task tracker when configured and include the
reproduction evidence, expected user-visible outcome, and required proof level. Do not create tasks
for rejected findings or unverified taste preferences.

When the queue is exhausted:

1. Summarize accepted, rejected, and deferred finding counts.
2. List any audit dimensions or states that lacked adequate evidence.
3. State whether the audited workflow has no remaining known issues or where residual risk remains.

## Guardrails

- Do not silently broaden scope beyond the selected surface.
- Do not run destructive actions or submit real production mutations while gathering evidence.
- Do not infer project conventions from OwlBear, Cockpit, Porsche Design System, React, or any other
  specific product or stack unless the target repository provides that evidence.
- Keep out-of-scope structural observations separate from findings; propose them only as optional
  follow-ups with explicit user approval.
