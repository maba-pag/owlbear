---
name: w-delivery-attention-resolution
description: "Workflow: Diagnose and resolve one exact Delivery Integration attention through an interactive user decision"
user-invocable: false
---

# Delivery Attention Resolution

Resolve one exact retained Integration attention outside the portfolio worker chain. This is an
interactive operator session: inspect current evidence, explain materially different remedies, ask
the user to choose, and perform only a selected operation that current Delivery authority permits.

## Step 0 - Bind The Exact Current Attention

Parse the supplied value as exactly one lowercase-hyphenated `change_id` followed by one 64-character
lowercase hexadecimal `attention_id`. Reject missing, extra, or malformed identities.

If Delivery tools are deferred, run `tool_search` for
`OwlBear Delivery show_integration_attention integrate_ready_change list_work_items`. Call
`show_integration_attention(change_id)` and require a current attention whose change and attention
identities equal the supplied values. If no attention exists, its identity differs, or Delivery
reports that the retained condition is superseded, report the current state and stop without
mutation. Never substitute a newer attention silently.

Treat the returned code, heads, target, diagnostics, and retry condition as retained evidence, not
as permission to edit a worktree or target.

## Step 1 - Diagnose Current State Read-Only

Read the owning Delivery coordination and relevant repository state without mutation. Verify the
current source branch, reviewed boundary, Integration target, worktree existence, worktree branch
and head, and staged, unstaged, and untracked paths when they bear on the reported condition.
Inspect only enough diff, package, completed-history, or verification evidence to distinguish the
current cause and viable remedy classes.

Use structured Delivery operations for Delivery facts and structured Git commands for repository
facts. Do not run checkout, switch, reset, restore, clean, commit, merge, rebase, worktree removal,
reference updates, target updates, or another mutating command while diagnosing.

Classify the result as one of:

- `resolved-or-stale` - current state no longer supports the retained condition;
- `single-authorized-route` - one non-destructive existing Delivery operation can advance it;
- `decision-required` - two or more materially different valid remedies remain;
- `authority-gap` - the selected remedy needs a Delivery-owned operation that does not exist;
- `unknown` - current evidence cannot responsibly identify the cause or remedy.

## Step 2 - Present One Decision

When a material choice remains, present exactly one decision before calling `askQuestions`:

```markdown
### Decision: <one precise Integration resolution choice>

**Current condition:** <current evidence and whether retained evidence still matches>
**Why this blocks Integration:** <bounded causal explanation>
**Options:** <two to four genuine remedies, each with pros, cons, risks, confidence, and outcome>
**Recommendation:** <one evidence-based option and why>
**Confidence:** <calibrated confidence and remaining uncertainty>
```

Use `askQuestions` with those options and stop for the answer. Do not batch another decision, infer
approval from discussion, or turn a single responsible route into artificial alternatives.

For uncommitted work, distinguish at least preservation, adoption into reviewed Delivery work, and
intentional discard when each is genuinely viable. Explain exactly what evidence each option keeps
or loses. Never describe destructive loss as cleanup.

## Step 3 - Apply Only Existing Authority

After an explicit answer, re-read the exact attention and all preconditions used by the chosen
route. Abort if the attention, heads, target, worktree state, or relevant evidence changed.

Use only an existing operation whose contract owns the selected result:

- retryable or superseded Integration: `integrate_ready_change(change_id)` only when current Delivery
  state authorizes retry;
- Design or admitted-authority revision: hand off with `/design <change_id>` and explain the exact
  revision required;
- reviewed merge conflict: hand off with `/orchestrate`; the claimed Integration repair workflow
  owns edits, proof, review, and admission;
- claim recovery: use the exact claim-bound recovery operation only when current context supplies
  its attempt and claim identities.

If preservation, adoption, discard, worktree recreation, package restoration, completed-history
repair, target correction, or verification-profile correction lacks a public Delivery operation,
return `authority-gap`. Name the missing operation and the evidence it must preserve; do not replace
it with raw Git or filesystem mutation.

Never overwrite the Integration target, force-update a reference, discard uncommitted work,
force-remove a worktree, hand-edit Delivery state, or bypass review and compare-and-swap boundaries.
Explicit user preference selects among admitted routes; it does not manufacture missing authority.

## Step 4 - Verify And Close

After any operation, re-read the work item and exact Integration attention. Report:

- prior attention identity and condition;
- selected route and operation actually performed;
- current attention or completion state;
- preserved evidence and any remaining authority gap;
- the exact next command only when another interactive workflow is required.

Do not claim resolution from a command exit alone. Resolution requires Delivery state to show the
attention cleared, superseded by a newly identified condition, or advanced through the selected
owned route.

## Known Pitfalls

- **Trusting copied prompt evidence:** always re-read current Delivery and repository state.
- **Treating user approval as Git authority:** use a Delivery-owned mutation or report an authority gap.
- **Retrying an operator condition:** generic retry text does not make an operator-required attention retryable.
- **Choosing for the user:** preservation, adoption, and discard have materially different outcomes.
- **Resolving the wrong attention:** bind and revalidate the exact attention ID before every mutation.
