# First-Principles Stance — Agent & Skill SNR

## Irreducible Core

The actual claim reduces to: **some tokens in share/ don't change model behavior, and removing them would free context for tokens that do.** That's it. Everything else is inherited structure.

## Assumptions Challenged

### 1. "~1/3 noise" is a measurement, not a guess

**Status: Unearned.** There is no methodology behind this number. "Noise" requires a definition of "signal," which requires a definition of "behavioral steering the model wouldn't produce alone." The user's own context.md acknowledges the estimate but treats it as a target ("reducing total share/ token footprint by ~30%"). You cannot set the reduction target before measuring the noise — that's backwards. You're shopping for evidence to hit a pre-selected number.

**Irreducible question:** What's the falsification criterion? If ablation shows only 10% is removable without regression, is the project still worth it?

### 2. The problem is content density, not routing

The framing assumes the right files are being loaded and the problem is that they contain fluff. But there's a prior question: **are the right files reaching the right agents at the right time?** If an agent loads 6 skills but only 2 are relevant to the current task, the other 4 are 100% noise regardless of how tightly written they are. Compression inside a file that shouldn't be loaded at all is wasted effort.

**Irreducible question:** Is the token budget problem better solved by loading fewer files (routing) or by shrinking all files (compression)? These are different interventions with different cost/benefit profiles. The framing chose compression without testing routing.

### 3. "The model already knows" is empirically unverifiable without ablation

You cannot introspect what a model "already knows." You can only measure: does behavior change when you remove the instruction? This varies by:
- Model version (today's model may know it; next month's may not)
- Context length (instruction near top vs buried under 50K tokens)
- Task complexity (trivial tasks need no instruction; hard tasks may need reminders of "obvious" things)

The proposed audit asks a human (or model) to judge "does the model already know this?" — but that judgment has no ground truth. The only valid test is removal + behavioral observation.

**Irreducible question:** Will the deep-dive prompt actually ablate (remove and test), or will it rely on a reviewer's intuition about what's "trivial"? If the latter, you're replacing one guess (organic growth) with another (gut-feel pruning).

### 4. "Two prompts" is inherited from the audit prompt's existence

The broad/deep decomposition maps 1:1 to "we already have an audit prompt, let's improve it + add a new one." But the actual need is: identify noise, remove it, verify no regression. That's one workflow, not two tools.

The broad audit's value is dubious for compression: it finds *cross-file* patterns (duplication, inconsistency) but the proposed metric is per-file token reduction. The deep-dive does the actual work. The broad audit is pre-existing infrastructure looking for a role in this project.

**Stronger decomposition:** (a) measure which files/sections steer behavior (ablation), (b) compress what remains. That's empirical-then-editorial, not broad-then-deep.

### 5. "Sentence-level" is probably the wrong granularity

If the problem were sentence-level verbosity, the fix would be "rewrite terse." But the context.md hints at structural issues: "paragraphs added but rarely reorganized," "over-specification that kills creative latitude." These are architectural problems — wrong sections exist, wrong decomposition across files, wrong level of prescription. Sentence-level editing on a structurally broken file produces a tight, well-written file that still shouldn't exist in that shape.

**Irreducible question:** Should the deep-dive first ask "does this section need to exist?" before asking "is this sentence minimal?"

### 6. "No pipeline regression" conflates absence-of-evidence with evidence-of-absence

The verification signal is "reviewer-rejects, auditor-rejects, hangs, death-loops." But pipeline failures are noisy, infrequent, and multi-causal. A subtle behavioral degradation (e.g., reviewer produces shallower reviews, builder skips a convention 20% of the time) won't surface as a clear regression signal. You'd need A/B comparison on identical tasks, which the pipeline doesn't support.

**Irreducible question:** What sample size of pipeline runs constitutes "no regression"? Without answering this, the verification signal is theater.

## What Survives

After stripping inherited assumptions, the irreducible project is:

1. **Ablation testing** — Remove file/section, run representative task, observe behavioral delta. This is the only empirically valid measure of signal.
2. **Editorial compression** — For sections confirmed to steer behavior, minimize token cost while preserving the steering.
3. **Regression detection** — Must be defined before compression starts, with a threshold for "acceptable degradation."

## Simplest Validating Experiment

Pick the largest skill file. Remove it entirely from one agent's context. Run 3 representative tasks that previously relied on it. Score output quality blind (without knowing which run had the skill). If quality is indistinguishable: the file was noise. If quality drops: the file was signal — now you know what to preserve when compressing.

This experiment costs ~1 hour and answers the foundational question the entire project rests on. If you can't detect behavioral difference from removing a whole file, sentence-level editing is premature optimization.

## Confidence

**0.82** — High confidence that the framing has unearned assumptions, particularly the noise estimate and the content-vs-routing confusion. Moderate uncertainty about whether ablation testing is practical at scale (it may be too slow for 80 files, requiring sampling).
