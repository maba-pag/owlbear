---
name: owlbear-design-review
description: "The design judge's rubric for a visual review: blind before and after, two phases, specificity, heuristics, severities and what fails a change"
user-invocable: false
---

# UI Review

Use when you judge the design of a Change's screenshots. Adapted from Impeccable's critique (see `NOTICE.md` beside
this folder). Read it together with `owlbear-interface-design`, whose rules you cite.

## What you judge

Whether the Change leaves each state at least as good as it was, and whether its design is specific to this
product. Correctness against the brief is another judge's question; you judge design.

## Two phases

1. **Your own judgement first.** Judge from the screenshots, the brief and the owner's criteria before you see
   any detector output, and submit that verdict. Deterministic findings anchor judgement; yours must stand
   without them.
2. **Then the detector.** Delivery sends its findings, each marked new, existing or unknown. Submit your final
   verdict: name where the detector agrees with you, what it caught that you missed, and which findings are
   false positives here (for example a font the brief names).

## Blind comparison

- Each state comes as two images, A and B, in random order. You are not told which is the Change. Say per state
  which is better and why, or that they are equal.
- Never assume the newer one is the better one. Delivery maps A and B back afterwards.
- A state with only one image is new or not comparable: judge it against the rubric alone and say so. A missing
  comparison is never evidence of improvement.

## Rubric

- **Specificity:** does the design read as authored for this product, or could an unrelated product use it
  unchanged?
- **Heuristics, 0 to 4,** on the states you see: visibility of status, match with the real world, user control,
  consistency, error prevention, recognition over recall, flexibility, aesthetic and minimal design, error
  recovery, help. Use `n/a` where a heuristic cannot apply to the surface. 4 is genuinely excellent; most real
  interfaces land between 2 and 3.
- **Cognitive load:** single focus, chunking of at most four items, grouping, visible hierarchy, one decision at
  a time, at most four visible options at a decision point, no memory bridges between screens, progressive
  disclosure.
- **Severity of each finding:**

  | | Meaning |
  | --- | --- |
  | P0 | blocks the task |
  | P1 | significant difficulty or confusion; a user would ask for help |
  | P2 | an annoyance with a workaround |
  | P3 | polish |

## Findings

- Each finding names the image, what is wrong, why it matters, the rule or principle it breaks (a section of
  `owlbear-interface-design`, a detector rule id, or an owner's criterion by its id) and its severity. Report a problem
  on every image that shows it, A and B alike: Delivery maps them back, so a problem both show is one the Change
  did not cause.
- Taste alone is not a finding. "I would prefer" without a cited rule is not reported.

## Verdict

You judge the images; Delivery maps A and B back and decides what the Change did.

- **Fail:** an image has a P0 or P1 problem or misses one of the owner's criteria, or one image of a pair is
  clearly worse than the other on a cited rule.
- **Pass:** nothing above.
- **Unsure:** the evidence cannot decide: a state cannot be compared and the rubric alone is not enough, images
  are unreadable, or the brief and a rule conflict in a way only the owner can settle. Say exactly what would
  decide it.
