---
name: owlbear-change-shaping
description: Shape a Change into a brief with the owner, save it for approval, show Delivery status, answer worker questions
user-invocable: false
---

# Delivery in chat

Delivery turns an approved brief into a reviewed, merged pull request. Chat is for the
conversation; approvals, merge consent and recovery happen in the Changes page.

## Shape a brief

1. Read the repository parts the idea touches before asking anything. To continue an existing
   Change, call `show_status` with its handle and read its saved brief back to the owner, its
   decisions and non-goals included, before changing any of them. If the read-back lists
   `proposed_wording`, show each with the challenger's verdict and let the owner decide whether to
   adopt it; an adopted one goes into the next `save_brief` like any other change.
2. Ask the owner one question at a time, with the answer you recommend and why, and only what the
   code cannot answer: the outcome, what must be true when it is done, what is out of scope, and
   whether something can only be checked by a person (for example by looking at a page). Ask for
   the observable pain, the current workaround, and which statements are evidence and which are
   assumptions. Never infer a business constraint from code. Depth follows uncertainty and stakes,
   not a count: ask until no material gap remains. A reduction of what the owner asked for is a
   scope choice the owner makes explicitly.
3. Write acceptance criteria a test or command can check; a criterion may state what must not
   happen. Consider how the criteria could all pass while missing the owner's outcome, and close a
   material gap with a criterion or a person check. Where an expected result is not obvious, take it
   from the rule that governs it, a real input with its known result, or the owner's explicit
   choice, not from your guess. A check only a person can perform becomes a person check with steps
   and what to expect.
4. For a UI change ask which page states must render: each visual state has a `name`, a `path`
   under the preview root and what to `expect`. Write each expectation as what a screenshot shows
   ("the Dark mode button is filled and darker than in light mode"), not as a state only the code
   knows ("the button is pressed"); ask the owner what should be visible when that is unclear.
   A state can need clicks or typing first (open a menu, search for a name): each step clicks a
   control or types into a field, named exactly as the page shows it. Steps run only on a
   test copy the project's declared preparation options prepare. If the project has no preview to render, offer three choices: add
   one in this Change, declare a person-only visual check, or change the scope.
5. Propose a split when the idea is more than one reviewable pull request.
6. Run the closing check before saving for approval (see Read-Back below).
7. Call `save_brief` with title, outcome, criteria, scope, non-goals (what the owner agreed is out),
   decisions and person checks. `decisions` holds every choice the owner made and each consequential
   choice of yours, as question, answer and origin: `decided` (the owner chose it), `approved` (it
   came with something the owner approved without being asked) or `autonomous` (you chose it). Send
   all of them again with every save, each with its question unchanged so it keeps its identity. Every
   decision's scope is the owner's: give it `scope: project` (a lasting rule for later Changes in this
   project) only when he said so; otherwise it keeps the default, this Change only. Never change a
   saved decision's scope yourself; ask him. `specified` names
   the criteria the owner stated himself (`AC-1`
   is the first); a state or person check he stated himself gets `owner: true`. Everything else is
   your proposal, and the approval page shows it as such. Leave `change` empty for a new Change; pass its handle
   (`c3`) to revise. For a UI change then call
   `save_visual_check` with that handle, `ui`, the states and their steps. If either returns
   errors, each names a field: fix those and call again. Never invent a handle.
8. Once the draft is ready, call `challenge_brief` with the handle and the saved version. A challenger
   judges that version; the tool waits for its verdict and returns the findings by ID (if it says the
   challenge still runs, call `show_status` with the handle later: its brief's `challenge` shows them).
   Judge each finding critically: take the ones that hold and revise the brief with the owner where the
   choice is his (`save_brief`, Read-Back for changed choices); a finding you judge wrong you reject, by
   its ID, with your evidence, in the next `challenge_brief` call. A finding marked as the owner's is never
   rejected. Then ask for the next round the same way. The next challenger judges your rejections; one it
   does not accept goes to the owner in the Changes page, and nothing can be saved until he decides.
   Before a version's first round Delivery picks the decisions in force that its work must follow; the
   reply's `picked` shows them by title. If the pick failed, or the approval says the decisions changed
   since, call `challenge_brief` for the same version with `retry_pick` true: it uses no round.
9. When the challenge says the brief is approvable, tell the owner to approve that version in the Changes
   page, using the link exactly as given (it carries the page's access token), and name the rejections
   that stand and a last revision no round reviewed (the owner ticks that he accepts it). Nothing starts
   before that approval; a later save needs one more challenge round.

## Read-Back

Read back a free-text or unclear answer at once, before building on it; a chosen option counts as
confirmed and is not asked again. Ask one decision per question, paraphrased at the level of the
owner's intent, never quoting the record, with the structured question tool when there is one:

- three close variants of the recorded choice (fewer only when fewer really differ in consequence,
  never padded), the matching one at a varying position and never verbatim; a one-line consequence where
  it helps;
- one or two other directions where real ones exist, the opposite among them;
- then, always in this order: "take your recommendation (…)" with your recommendation named in the
  brackets, "none of these: show me more options", "explain first"; no other recommendation mark;
  free text stays open.

A chosen variant or direction is `decided`. "Take your recommendation": state your choice and why,
record it `autonomous`. "Show me more options": ask again with options across directions, each with
benefits, costs, risks and its own percentage that it is a good choice (they need not add up), your
recommendation marked. "Explain first": explain each option's consequences neutrally, then ask again.
Free text is never recorded as written: offer two to five readings that fill its gaps differently,
plus "your words as written", "show me more readings" and "explain first". When the direction itself
is in doubt, ask the direction first, then its variants.

Before saving for approval, end with one closing check of everything the brief records: every choice
the owner made and your own consequential ones (those that change what the owner sees or does, cost,
safety or reversibility, each with a one-line consequence), listed together and asked once. Read back
an item he corrects as above, then save.

## Status and questions

- Call `show_status` when the owner asks what is happening. Repeat each line as given. If it
  says Delivery is not running, give its start action; nothing advances until it runs. If
  `readiness` lists a problem, give the owner its fix.
- A question with `answer_in: chat` is a worker's question: put it to the owner as it stands,
  then call `answer_question` with its id, the chosen option id and the owner's words.
- A question with `answer_in: changes-page`, merge consent and every stop are the owner's
  decisions in the Changes page. Point there; do not answer them for the owner.
