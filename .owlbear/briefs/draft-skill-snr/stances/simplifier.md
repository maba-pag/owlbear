# Simplifier Stance — Skill SNR Audit

## Cuts

**Cut 1: Decouple broad audit from deep-dive compression.** These solve different problems (ecosystem structure vs. prose density). The broad audit doesn't need to run first — you already know the reviewer is bloated. Bundling them creates false sequencing and inflates the initiative.

**Cut 2: Skip the `.prompt.md` for deep-dive.** A reusable prompt is premature. The "deep-dive" is just: read file → score sentences → compress → verify pipeline. Do it directly as a task on the reviewer. If it works and you want to repeat it 10 more times, *then* templatize. Right now you're building tooling before proving the intervention works.

**Cut 3: Drop "measurable token reduction" as a formal outcome.** `wc -w` before/after is the measurement. You don't need infrastructure or scoring rubrics for a pilot. The real verification is: does the reviewer still reject bad code and not death-loop?

## Decomposition Pressure

The actual minimum viable scope is **one task**:

> Compress `reviewer.agent.md` + its linked skills/instructions. Run reviewer on a recent task. Confirm no regression.

That's it. Everything else — the broad audit improvements, the reusable prompt, the SNR scoring methodology — is P2 work that should only exist if P1 succeeds and reveals that templating saves effort across 35 skills.

## Boundary Correction

The framing implies "80 files need auditing, here's my system." But 80 files don't need auditing simultaneously. The 80-file problem is a backlog, not a scope. The scope is: prove compression works on one agent without breaking behavior. Then iterate.

## Confidence

**0.85** — The two-prompt approach is over-coupled and the broad audit is a separate initiative. The deep-dive "prompt" should start as a direct task, not a tool.
